# Qwen3.8-27B (Rig 2) - best configs

Dense 27B from the Qwen3.8 family (arch `qwen35`): hybrid SSM + attention, only every
4th layer full attention (`full_attention_interval=4`), embedded MTP head. Not a MoE,
so the Codacus fork has nothing to add. Native context 262144.

The recommended stack is **vLLM** on `W4A16-AutoRound-fast`: the
[syv-ai/qwen38-27b-rtx3090](https://github.com/syv-ai/qwen38-27b-rtx3090) container
(vLLM 0.28.0), two contexts: MTP at 150000 (4 chained drafts, fp8 KV) for the fastest
decode, and MTP at 250000 (KVarN 4/2-bit KV, pinned pool) for long requests. The
llama.cpp `UD-Q4_K_S` quant and the DFlash2 profile are archived (see Alternatives).

Rig details and setup: [../../rig2-3090.md](../../rig2-3090.md). Methodology:
[../../methodology.md](../../methodology.md). Full experiment log:
[qwen38-27b-archive.md](qwen38-27b-archive.md). Low-level knob transferability
study: [../../experiments/qwen38-27b-da3dsoul-arc-transfer.md](../../experiments/qwen38-27b-da3dsoul-arc-transfer.md).
Model card: [unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF).
vLLM weights: [dbirks/Qwen3.8-27B-W4A16-AutoRound](https://huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound)
(the container requantizes the lm_head/embeddings/MTP in place on first boot: the base
checkpoint to int8, the `-fast` variant to int4-GPTQ. On this 3090 the int4 widths are
what let a 150k-context boot fit the 22.5 GB cap at all - the int8 base loads ~0.9 GiB
heavier and lands over it - and int4 leaves enough headroom to raise the pool pin and
boot at MAX_LEN=170000, a ceiling not yet wired into the configs below.)

The vLLM rows use the Rig 2 coding prompts (C#+React averaged) and recommended sampling
(temp 1.0, top_p 0.95, top_k 20, min_p 0.0, presence_penalty 1.5) but a single pass
(weights are VRAM-resident, and prefix caching would fake a re-send) with timings read
from vLLM's own server metrics. The archived llama.cpp `UD-Q4_K_S` rows use the standard
Rig 2 llama.cpp protocol (second-pass prefill, cold load, q8_0 KV) - see
[qwen38-27b-archive.md](qwen38-27b-archive.md).

## Measured results at c 150000 (vLLM, coding prompts C#+React averaged, single pass, + 512 gen)

| Quant | Spec | ctx | KV | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | MTP | 150000 | fp8 | 1124 | 113 | ~0.54 | 22289 MiB |

- Stack: [syv-ai/qwen38-27b-rtx3090](https://github.com/syv-ai/qwen38-27b-rtx3090)
  container (vLLM 0.28.0), `CTX=long`: `MAX_LEN=150000`, `DRAFT_TOKENS=4` chained drafts,
  fp8 KV through FlashInfer, pool pinned by bytes (`EXTRA_ARGS=--kv-cache-memory=5800000000`,
  5.4 GiB) -> 150,769 tokens (1.01x at 150k). `MAX_SEQS=4` is required: at the default 8 the
  4-draft spec buffers push the pool below 150k and the engine refuses to boot. See the KVarN
  section for why the pool is pinned.
- Warm runs, +-10% on decode: C# 115 / 0.55, React 112 / 0.53; vs stock llama.cpp
  UD-Q4_K_S (1019.7 / 61.6) prefill +10% / decode +83%. MTP trades short-context decode for
  context (DFlash2 is 37 t/s faster at short prompts but 30k shorter - see Alternatives;
  KVarN goes further still, next section).
- React stops at 1 token on raw completion without `ignore_eos: true`; the guard is used
  for the timed runs (see the messy section, same convention).
- Long-context prefill (7369-token React x24): 1274 t/s; a 139,686-token prompt prefills at
  708 t/s. These are first-send prefills (single pass); a re-send of the same prompt hits the
  prefix cache (`cached=138,224`, prefill collapses to ~2.8 s), so follow-up turns are cheap
  while every cold measurement stays a real prefill.

## Measured results at c 250000 (vLLM, KVarN 4/2-bit KV, pinned pool, coding prompts C#+React averaged, single pass, + 512 gen)

| Quant | Spec | ctx | KV | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | MTP | 250000 | KVarN k4v2 | 960 | 86 | ~0.58 | 22340 MiB |

- Same container, `CTX=huge`: KVarN `kvarn_k4v2_g128` KV (4-bit keys / 2-bit values per
  128-token tile), 3 chained MTP drafts, `MAX_SEQS=8`. The pool is pinned by bytes
  (`EXTRA_ARGS=--kv-cache-memory=4200000000`, 3.91 GiB) -> 259,057 tokens (1.04x at 250000).
- Pinning is required, not cosmetic: `KV_MEM` is ignored on the MTP branch (it is wired into
  DFlash2 only), so `EXTRA_ARGS` is used; `GPU_UTIL` auto-sizing floats with free desktop
  memory and at every util tested spiked to ~23,900-24,000 MiB during the cold load
  (200k/0.88, 230k/0.90, 260k/0.93 all crossed 22528). Pinned: idle 21885, peak 22340 MiB,
  0 samples over.
- Decode is flat across context on the 116K refactor: 30.7 (200k) / 30.5 (230k) / 30.4 (250k).
  A lone 38.6 reading was a high-acceptance (0.592) outlier, not a config effect. Prefill
  falls with length: ~805-816 at 116K, 598 at 230K.
- Verified end-to-end: a 230,251-token prompt prefills at 598.4 t/s (~385 s) and decodes at
  31.5 t/s. A 254,811-token prompt does NOT fit - it sits in `waiting (capacity)` with the
  pool at 0% - because padding layers and SSM state make the real requirement ~1.04x the
  token count, so ~250k is the honest ceiling (the API ceiling is set to 250000).
- 250000 is just under the model's native 262144 (`max_position_embeddings`); vLLM refuses
  290000 unless `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1`, which risks NaN beyond native RoPE.
- Draft count does not transfer from fp8: at this profile 2 drafts fits (peak 22089 MiB) but
  short decode drops to 82.5, while 4 drafts is rejected (idle 22543, peak 23930 MiB), so the
  launcher default 3 stays.
- Warm short runs, +-10%: C# 979 prefill / 79 decode (0.573), React 946 / 94 (0.591). The
  first csharp prefill of a boot is a JIT artifact and is discarded.
- Project quality numbers for KVarN (docs/long-context.md): perplexity +0.16%, needle
  correct 4k-240k; the cost is speed, not accuracy. The `MTP + huge + PREFIX_CACHE=1`
  combination corrupts `prompt_logprobs` only (ordinary generation is fine), so leave
  prefix caching off here.

## Best config per quant

### W4A16-AutoRound-fast - vLLM

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/qwen38-27b-rtx3090:latest single

    # env: CTX=long  MAX_LEN=150000  GPU_UTIL=0.88
    #      DRAFT_TOKENS=4  MAX_SEQS=4
    #      EXTRA_ARGS=--kv-cache-memory=5800000000
    #
    # long-context profile (KVarN 4/2-bit KV, pinned pool, slower decode):
    # env: CTX=huge  MAX_LEN=250000  GPU_UTIL=0.88
    #      EXTRA_ARGS=--kv-cache-memory=4200000000
    #
    # prefill-optimized add-on (W4A8 int8 Marlin activations; decode -9%):
    # env: INT8_ACT=int8

-> 113 t/s decode @ c 150000 (prefill 1124, acceptance ~0.54), 22289 MiB.
-> 86 t/s decode @ c 250000 (prefill 960, acceptance ~0.58), 22340 MiB.

Adding `INT8_ACT=int8` to the `CTX=long` env trades ~9% short-context decode for a
large prefill win: short C#+React prefill 1095 -> 2006 t/s (+83%) and a 139,686-token
prompt 699 -> 973 t/s (+39%), at the same pool (150,769) and +0.4 GiB VRAM (21,517 MiB);
acceptance holds (~0.5) and output stays coherent. `INT8_LAYERS=mlp` is a smaller middle
point (1,615 / 878); `PREFILL_ATTN=int8` adds nothing on top.

Built from [syv-ai/qwen38-27b-rtx3090](https://github.com/syv-ai/qwen38-27b-rtx3090):
W4A16 AutoRound weights with 4 chained MTP drafts. `CTX=long` selects fp8 KV; `CTX=huge`
switches to KVarN 4/2-bit KV. Both pools are pinned by bytes
(`EXTRA_ARGS=--kv-cache-memory=...`; `KV_MEM` is not read on the MTP branch).

## Alternatives (archived)

- **DFlash2** (`W4A16-AutoRound-fast` on vLLM, `SPEC=dflash2`): 150 t/s decode at short
  context, but its pinned int8 KV pool caps the request at 120000. MTP gives up 37 t/s
  decode (113 vs 150) for 30k more context (150000 vs 120000) and wins long prompts
  outright (116K refactor: MTP 791.2 / 69.3 vs DFlash2 335.2 / 44.5). Retired in favour
  of MTP.

      # env: CTX=long  SPEC=dflash2  PREFIX_CACHE=1
      #      GPU_UTIL=0.90  KV_MEM=5000000000  DFLASH_MAX_LEN=120000

  -> 150 t/s decode @ c 120000 (prefill 1221, acceptance ~0.37), 22293 MiB; long-prompt
  prefill 1182.0 t/s. `KV_MEM` pins int8 per-token-head KV through Triton and must cover
  `DFLASH_MAX_LEN` (the launcher reads `DFLASH_MAX_LEN`, not `MAX_LEN`, for that cap);
  while `KV_MEM` is set, `GPU_UTIL` is ignored.

  A `CTX=huge` variant (KVarN, 206000-req ceiling, `KV_MEM=4320000000`) also failed the cap:
  short decode 143.2 and 116K prefill 886.8 look good, but idle sat at 22177 MiB, steady use
  at 22647 MiB, and a load transient at 23443 MiB. The drafter+speculator overhead leaves no
  room at a useful context, so DFlash2 stays retired.

- **KVarN `g64` / `k4v4` tiles** (`CTX=huge`, same 3.91 GiB pin): tested `k4v4_g128`,
  `k4v2_g64`, `k4v4_g64` against the default `k4v2_g128`. All are within noise on
  prefill/decode and none recover MTP acceptance; every one costs KV capacity, forcing
  MAX_LEN down (`k4v4` stores 2x V bytes: ~24-26% fewer pool tokens, ~192-200k ceiling;
  `g64` doubles scale overhead for ~5%). The default tile is the only one worth serving.

- **UD-Q4_K_S** (stock llama.cpp, GGUF): 155648 was the largest context under the 22 GB cap
  (1019.7 / 61.6 short; 809.8 / 28.9 at 116K), but vLLM beats it on decode (~1.8x short,
  ~2.4x at 116K) at the same VRAM and reaches 250000 via KVarN. Retired in favour of vLLM;
  full log in [qwen38-27b-archive.md](qwen38-27b-archive.md).

## Messy-code refactor benchmark (real-task ~116K prompt, single-pass)

A deliberately messy ~116K-token refactor prompt, single run:

| Quant / engine | Spec | ctx | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| W4A16 / vLLM | MTP | 150000 | 791.2 | 69.3 | 0.41 | 22289 MiB |
| W4A16 / vLLM | MTP (KVarN) | 250000 | 805.3 | 30.4 | 0.444 | 22334 MiB |

- Long context is expensive on this dense model: fp8 decode falls from 113 t/s short to
  69.3 at ~116K (-39%), KVarN to 30.4 (its 250k ceiling) from an 86 t/s short baseline.
- The decode hit is larger than the 35B-A3B's on the same task (-37%): every token here
  runs ~27B dense params against a 116K context, while the MoE only wakes ~3B.
- Both ran the full 512 (`ignore_eos: true`); no crash or EOS quirk - see
  [issues.md](../../issues.md). Acceptance 0.41 (fp8) / 0.44 (KVarN).
- The archived llama.cpp UD-Q4_K_S run read 809.8 / 28.9 here - prefill on par, decode
  ~2.4x slower.

## Key arch notes

- Hybrid SSM + attention: only ~16 of 65 layers own a growing KV cache
  (`full_attention_interval=4`), so context is much cheaper than a same-size dense
  transformer; the SSM state is constant-size.
- 4 KV heads x 256 key/value length; q8_0 KV costs ~0.045 MiB/token, which is why the
  llama.cpp path capped at 155648 under the 22 GB cap. The vLLM stack instead compresses
  KV (fp8 at 150000, KVarN 4/2-bit at 250000) to fit the same budget.
- Embedded MTP (`nextn_predict_layers=1`): no separate draft model needed. n-max 2 was the
  llama.cpp decode peak; VRAM rises ~150 MiB per extra draft token.
- vLLM W4A16 trades context against decode speed: fp8 (`CTX=long`) reaches 150000 at
  113 t/s short and 69.3 at 116K; KVarN (`CTX=huge`) reaches 250000 at 86 t/s short but
  ~2.3x slower long-context decode (30.4 vs 69.3). DFlash2 traded prefill for short-context
  decode (335.2 / 44.5) and is archived. KVarN quality cost is negligible (project:
  perplexity +0.16%, needle 4k-240k).

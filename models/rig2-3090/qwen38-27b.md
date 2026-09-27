# Qwen3.8-27B (Rig 2) - best configs

Dense 27B from the Qwen3.8 family (arch `qwen35`): hybrid SSM + attention, only every
4th layer full attention (`full_attention_interval=4`), embedded MTP head. Not a MoE,
so the Codacus fork has nothing to add. Native context 262144.

The recommended stack is **vLLM** on `W4A16-AutoRound-fast`: the
[syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) container
(vLLM 0.29.0; all rows on this page were re-measured 2026-09-27 with `INT8_ACT=int8`
served, on the post-rename container - fp8 profile build `31f8b7a3`, KVarN profile build
`c68ac895`, Swift profiles `641274bd`/`4f4a6a1f`), two contexts: MTP at 150000
(4 chained drafts, fp8 KV) for the fastest decode, and MTP at 250000 (KVarN 4/2-bit
KV, pinned pool) for long requests. The
llama.cpp `UD-Q4_K_S` quant and the DFlash2 profile are archived (see Alternatives).
The [Swift-1.5-Qwen3.8-27b-INT4](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b-INT4)
fine-tune quant was measured on the same stack (see its section under Best config per
quant): it tracks the base quant closely (a shade behind on short decode, near-parity
prefill) across both contexts.

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
serve up to 170000 (verified with a 164,553-token request, though a near-full one sits
~13 MiB under the cap).)

The vLLM rows use the Rig 2 coding prompts (C#+React averaged) with the server's
configured sampling defaults (requests carry no per-request sampling overrides; only
request shape: `max_tokens`, plus the `ignore_eos` guard for the timed 512-token
decode), timings read from vLLM's own server metrics, requests routed through
llama-swap. All rows are single passes, served
with `INT8_ACT=int8`. Per-run spread matters: decode swings +-5-10%
run to run (boot-to-boot variance is material - earlier single-boot readings of the
same configs differed by up to ~20%), while prefill is +-0.5% stable. VRAM figures
are the vLLM::EngineCore process allocation only (the engine's own allocation, not
the desktop-inclusive nvidia-smi total; the 22528 MiB line is judged the same way).
The archived llama.cpp `UD-Q4_K_S` rows use the standard
Rig 2 llama.cpp protocol (second-pass prefill, cold load, q8_0 KV) - see
[qwen38-27b-archive.md](qwen38-27b-archive.md).

## Measured results at c 150000 (vLLM, fp8 KV, coding prompts C#+React averaged, single pass, `INT8_ACT=int8`, + 512 gen)

| Quant | Spec | ctx | KV | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | MTP | 150000 | fp8 | 1672.7 | 103.3 | ~0.48 | 21990 MiB |
| Swift-1.5-INT4 | MTP | 150000 | fp8 | 1621.5 | 96.1 | ~0.47 | 22510 MiB |

- Stack: [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen)
  container (vLLM 0.29.0, build `31f8b7a3`), `CTX=long`: `MAX_LEN=150000`, `DRAFT_TOKENS=4` chained drafts,
  fp8 KV through FlashInfer, pool pinned by bytes (`EXTRA_ARGS=--kv-cache-memory=5800000000`,
  5.4 GiB) -> 150,769 tokens (1.01x at 150k). `MAX_SEQS=4` is required: at the default 8 the
  4-draft spec buffers push the pool below 150k and the engine refuses to boot. See the KVarN
  section for why the pool is pinned.
- **This profile can reach 170000 on the same int4 build, but only just** (verified on the
  pre-rename 0.28.0 build; config unchanged): raising the pin
  to 6.5 GB (`MAX_LEN=170000`, pool 170,776) boots and served a 164,553-token prompt
  (prefill 655.7 t/s, decode 83.1 t/s, acceptance 0.625, coherent output). The catch is
  headroom: a near-full request pushed steady VRAM to 22,515 MiB, ~13 MiB under the
  22,528 cap, so 170k is a documented capability rather than a comfortable default - keep
  150000 for normal use. The 170k ceiling is unlocked by the int4 `-fast` head/drafter
  (the int8 base would not even fit 150000 here).
- Single pass C# 1768.4 / 93.2, React 1576.9 / 113.3; the decode gap between the two
  prompts is the known per-run spread (+-5-10%; prefill +-0.5%). vs stock llama.cpp
  UD-Q4_K_S (1019.7 / 61.6) prefill +64% / decode +68%. MTP trades short-context decode for
  context (DFlash2 is 47 t/s faster at short prompts but 30k shorter - see Alternatives;
  KVarN goes further still, next section).
- React stops at 1 token on raw completion without `ignore_eos: true` (observed on the
  pre-rename build with the old sampling protocol); the guard is used
  for the timed runs (see the messy section, same convention).
- Long-context prefill (0.28.0-build readings): 7369-token React x24 1274 t/s; a
  139,686-token prompt 708 t/s. These are first-send prefills (single pass); a re-send of the
  same prompt hits the
  prefix cache (`cached=138,224`, prefill collapses to ~2.8 s), so follow-up turns are cheap
  while every cold measurement stays a real prefill.

## Measured results at c 250000 (vLLM, KVarN 4/2-bit KV, pinned pool, coding prompts C#+React averaged, single pass, `INT8_ACT=int8`, + 512 gen)

| Quant | Spec | ctx | KV | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | MTP | 250000 | KVarN k4v2 | 1716.6 | 92.7 | ~0.50 | 21736 MiB |
| Swift-1.5-INT4 | MTP | 250000 | KVarN k4v2 | 1683.0 | 86.7 | ~0.49 | 22052 MiB |

- Same container, `CTX=huge`: KVarN `kvarn_k4v2_g128` KV (4-bit keys / 2-bit values per
  128-token tile), 3 chained MTP drafts, `MAX_SEQS=8`. The pool is pinned by bytes
  (`EXTRA_ARGS=--kv-cache-memory=4200000000`, 3.91 GiB) -> 259,057 tokens (1.04x at 250000).
- Pinning is required, not cosmetic: `KV_MEM` is ignored on the MTP branch (it is wired into
  DFlash2 only), so `EXTRA_ARGS` is used; `GPU_UTIL` auto-sizing floats with free desktop
  memory and at every util tested spiked to ~23,900-24,000 MiB during the cold load
  (200k/0.88, 230k/0.90, 260k/0.93 all crossed 22528). Pinned: idle 21885, peak 22340 MiB,
  0 samples over (0.28.0-build readings; the updated container measures 21736 MiB by
  process allocation).
- Decode across context on the 116K refactor (0.28.0-build sweep): 30.7 (200k) / 30.5
  (230k) / 30.4 (250k). A lone 38.6 reading was a high-acceptance outlier, not a config
  effect. Prefill falls with length: ~805-816 at 116K, 598 at 230K (updated build:
  784.4 at 116K / 27.5 t/s decode).
- Verified end-to-end (0.28.0 build): a 230,251-token prompt prefills at 598.4 t/s (~385 s) and decodes at
  31.5 t/s. A 254,811-token prompt does NOT fit - it sits in `waiting (capacity)` with the
  pool at 0% - because padding layers and SSM state make the real requirement ~1.04x the
  token count, so ~250k is the honest ceiling (the API ceiling is set to 250000).
- 250000 is just under the model's native 262144 (`max_position_embeddings`); vLLM refuses
  290000 unless `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1`, which risks NaN beyond native RoPE.
- Draft count does not transfer from fp8: at this profile 2 drafts fits (peak 22089 MiB) but
  short decode drops to 82.5, while 4 drafts is rejected (idle 22543, peak 23930 MiB), so the
  launcher default 3 stays.
- Single pass: C# 1816.0 prefill / 84.0 decode (0.420), React 1617.2 / 101.4 (0.578). The
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
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: CTX=long  MAX_LEN=150000  GPU_UTIL=0.88
    #      DRAFT_TOKENS=4  MAX_SEQS=4
    #      EXTRA_ARGS=--kv-cache-memory=5800000000
    #      INT8_ACT=int8
    #
    # long-context profile (KVarN 4/2-bit KV, pinned pool, slower decode):
    # env: CTX=huge  MAX_LEN=250000  GPU_UTIL=0.88
    #      EXTRA_ARGS=--kv-cache-memory=4200000000
    #      INT8_ACT=int8

-> 103.3 t/s decode @ c 150000 (prefill 1672.7, acceptance ~0.48), 21990 MiB.
-> 92.7 t/s decode @ c 250000 (prefill 1716.6, acceptance ~0.50), 21736 MiB.

All rows on this page are served with `INT8_ACT=int8`, so the figures above already
include it: it borrows batch mode's W4A8 Marlin path (weights stay int4, activations
int8) for every linear except the already-int8 lm_head/embed and the MTP module. It
verified fitting with headroom to spare, judged on the vLLM::EngineCore process
allocation (the 22528 MiB line). `INT8_LAYERS=mlp` is a smaller middle point
(0.28.0-build readings: 1,615 / 878); `PREFILL_ATTN=int8` adds nothing on top.

Built from [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen):
W4A16 AutoRound weights with 4 chained MTP drafts. `CTX=long` selects fp8 KV; `CTX=huge`
switches to KVarN 4/2-bit KV. Both pools are pinned by bytes
(`EXTRA_ARGS=--kv-cache-memory=...`; `KV_MEM` is not read on the MTP branch).

### Swift-1.5-INT4 - vLLM

The [Swift-1.5-Qwen3.8-27b-INT4](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b-INT4)
fine-tune ships as its own quant (AWQ smoothing + GPTQ INT4 W4A16 via
LLM Compressor, symmetric, group 128, actorder static, FP8 static per-tensor KV; the BF16
MTP head restored and bitwise verified against the fine-tune). Served on the same
[syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) container (vLLM 0.29.0) with the
same profile: `CTX=long`, `MAX_LEN=150000`, `DRAFT_TOKENS=4` chained drafts, fp8 KV,
pool pinned at 5.8 GB. The HyperQwen prepare pipeline rebuilt the MTP draft head over
Swift's own output distribution (~25.9k distinct tokens vs ~54k for the base model), so
the drafter is not shared with the AutoRound build.

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: MODEL=Swift-1.5-INT4  CTX=long  MAX_LEN=150000  GPU_UTIL=0.88
    #      DRAFT_TOKENS=4  MAX_SEQS=4
    #      EXTRA_ARGS=--kv-cache-memory=5800000000
    #      INT8_ACT=int8

-> 96.1 t/s decode @ c 150000 (prefill 1621.5, acceptance ~0.47), 22510 MiB.
-> 86.7 t/s decode @ c 250000 (prefill 1683.0, acceptance ~0.49), 22052 MiB.

`INT8_ACT=int8` is served on this profile too (see the note in the W4A16 section).

- Measured with the same single-pass protocol and the server's configured sampling
  defaults: requests carry no per-request sampling overrides (only request shape:
  `max_tokens`, plus the `ignore_eos` guard for the timed 512-token decode), timings
  read from vLLM's own server metrics, requests routed through llama-swap like the
  base-model rows.
- The 250k row is a second profile matched to the base row's KVarN setup (`CTX=huge`
  style: 250000, KVarN 4/2-bit KV, pinned pool), same container image family
  (vLLM 0.29.0; build `4f4a6a1f` vs `641274bd` on the fp8 profile - a newer image pull,
  config unchanged). Single-pass reading; see the variance note in the protocol paragraph.
- Single pass: C# 1714.0 prefill / 92.5 decode, React 1528.9 / 99.6; decode swings
  +-5-10% run to run, prefill +-0.5%. The first csharp prefill of a boot is a JIT
  artifact and is discarded.
- Unguarded React naturally stops early: it emitted EOS at 339 tokens (decode 128.8,
  acceptance 0.899) - the fine-tune finishes coding answers without padding, unlike the
  base model which must be held to 512 with `ignore_eos`. The 512-guarded React pass is
  what feeds the table for protocol parity.
- VRAM: the engine allocates 22510 MiB, just under the 22528 line (~18 MiB) - this quant
  (group-128 GPTQ + restored BF16 MTP head + fp8 KV) still sits ~520 MiB heavier than the
  AutoRound int4 build (21990 MiB). Tighter than the base quant.
- vs `W4A16-AutoRound-fast` (same single-pass protocol): the base leads on short decode
  at both contexts (150k 103.3 vs 96.1; 250k 92.7 vs 86.7) while Swift sits close behind
  on prefill (150k 1621.5 vs 1672.7; 250k 1683.0 vs 1716.6) - treat the deltas as
  one-boot data (decode swings +-5-10%). The Swift fine-tune targets ~58.5% fewer thinking
  tokens at comparable quality (per its model card), and its coding answers stop early
  instead of padding.

## Alternatives (archived)

- **DFlash2** (`W4A16-AutoRound-fast` on vLLM, `SPEC=dflash2`): 150 t/s decode at short
  context, but its pinned int8 KV pool caps the request at 120000. MTP gives up 37 t/s
  decode (103.3 vs 150) for 30k more context (150000 vs 120000) and wins long prompts
  outright (116K refactor, 0.28.0-build readings: MTP 791.2 / 69.3 vs DFlash2 335.2 / 44.5).
  Retired in favour of MTP.

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
  (1019.7 / 61.6 short; 809.8 / 28.9 at 116K), but vLLM beats it on decode (~1.7x short,
  ~2x at 116K) at the same VRAM and reaches 250000 via KVarN. Retired in favour of vLLM;
  full log in [qwen38-27b-archive.md](qwen38-27b-archive.md).

## Messy-code refactor benchmark (real-task ~60K prompt, single-pass)

| Quant | Engine | ctx | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | vLLM | 150000 | 1640.7 | **84.5** | 0.463 | 21990 MiB |
| W4A16-AutoRound-fast | vLLM | 250000 | 1713.3 | 40.9 | 0.332 | 21736 MiB |
| Swift-1.5-INT4 | vLLM | 150000 | 1617.3 | **78.9** | 0.447 | 22510 MiB |
| Swift-1.5-INT4 | vLLM | 250000 | 1698.5 | 41.9 | 0.369 | 22052 MiB |

- Single timed pass per boot on the ~60K-token prompt (212,829 chars, `--repeats 79`),
  cold load, vLLM server metrics, every request cache-cold (`prefix_hits 0`), all
  profiles served `INT8_ACT=int8`. Measured 2026-09-27 on the container builds named
  above.
- The prompt was reduced from ~116K to ~60K tokens on 2026-09-27; the retired ~116K
  run is archived in [qwen38-27b-archive.md](qwen38-27b-archive.md).
- fp8 150k decodes fastest (84.5 base / 78.9 Swift); the KVarN 250k profiles drop to
  ~41 t/s once KV bandwidth dominates, with prefill nearly flat across profiles.

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
  103.3 t/s short and 84.5 on the 60K refactor; KVarN (`CTX=huge`) reaches 250000 at 92.7
  t/s short but ~2x slower long-context decode (40.9 vs 84.5 on the 60K refactor). DFlash2
  traded prefill for short-context decode (335.2 / 44.5) and is archived. KVarN quality
  cost is negligible (project: perplexity +0.16%, needle 4k-240k).
- Swift-1.5-INT4 on the same vLLM stack tracks the base quant closely: a shade behind on
  short decode (single pass: 150k 96.1 vs 103.3; 250k 86.7 vs 92.7) with near-parity prefill
  (1621.5 vs 1672.7; 1683.0 vs 1716.6). Its drafter is rebuilt on the fine-tune's own output
  distribution (~25.9k tokens instead of the base model's ~54k). Its headline win is the
  fine-tune itself (far fewer thinking tokens at comparable quality, and coding answers that
  stop early instead of padding).

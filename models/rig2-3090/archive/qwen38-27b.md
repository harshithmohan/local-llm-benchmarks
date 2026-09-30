# Qwen3.8-27B (Rig 2) - experiment archive

> **Retired-prompt note:** rows on this page were measured with the retired timing prompts (short C#/React, pre-2026-09-29; and the retired ~116K long-context prompt) unless a section says otherwise. The current timing prompt is the single ~10k-token opencode session context ([test-prompts.md](../../../test-prompts.md)); the two are not directly comparable.

This archive is the experiment log for [qwen38-27b.md](../qwen38-27b.md): the retired
llama.cpp `UD-Q4_K_S` quant, the retired vLLM profiles (DFlash2, KVarN `g64`/`k4v4` tile
variants), the pre-unification timing rows (retired short C#/React prompts and the retired
~116K long-context prompt), and the container/pool notes moved off the model page. The
current recommended configs are on the model page.

llama.cpp protocol: second-pass prefill, sampling per the then-current protocol, cold load,
q8_0 KV, `--threads 8 --threads-batch 16`, 22 GB VRAM cap (22 GB +- 250 MB, desktop
reserve). vLLM protocol: single pass per boot, timing from the vLLM server metrics
([engine-notes/vllm.md](../../../engine-notes/vllm.md)), pool pinned by bytes,
`INT8_ACT=int8`, cold load. Methodology in [methodology](../../../methodology.md); gotchas in
[issues](../../../issues.md). Model card:
[unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF).

Quants:

- `UD-Q4_K_S` (15.36 GB, ~4.55 bpw) - llama.cpp, retired (dominated by the vLLM stack)
- `W4A16-AutoRound-fast` - vLLM, current recommended (see the model page)
- `Swift-1.5-INT4` - vLLM fine-tune, current recommended (see the model page)

## Max context probe (stock)

VRAM at load, default params (q8_0 KV, MTP n-max 2, `--threads-batch 16`):

| ctx | VRAM used | verdict |
| --- | --- | --- |
| 122880 | 20651 MiB | fits |
| 131072 | 21019 MiB | fits |
| 147456 | 21757 MiB | fits |
| 152576 | 21987 MiB | fits |
| **155648** | **22127 MiB** | adopted - largest with a real reserve (~400 MiB under 22528) |
| 159744 | 22311 MiB | too thin (~215 MiB reserve) |
| 163840 | 22495 MiB | over - no reserve (33 MiB under the line) |
| 180224 | 23233 MiB | over |
| 196608 | 23971 MiB | over |
| 212992+ | load fails | MTP context allocation fails |

- q8_0 KV costs ~0.045 MiB/token on the ~16 full-attention layers, so the ceiling is
  ~155k, not the native 262144.
- `-ngld 0` (draft head on CPU) is a no-op for this model: byte-identical VRAM at every
  ctx tested. There is no separate `-md` draft - the MTP head is embedded - so the
  draft-offload knob has nothing to move.

## Speed at c 155648 (stock)

| pass | prompt | prefill t/s | decode t/s | acceptance | mean len |
| --- | --- | --- | --- | --- | --- |
| second | C# | 1064.8 | 59.7 | 0.664 | 2.33 |
| second | React | 974.6 | 63.6 | 0.742 | 2.48 |
| avg | C#+React | **1019.7** | **61.6** | 0.703 | 2.41 |

Cold load, single slot (`--parallel 1`), 512 gen, timings from the `llama-server`
request log. VRAM 22127 MiB at load. A second n-max 2 session (below) read 63.1 t/s -
run-to-run decode varies by a few t/s with sampled acceptance, so compare within a
table only.

## `--threads-batch` sensitivity (stock, c 155648)

Short C#+React passes were noise-bound (per-tb spread smaller than the run-to-run
spread), so the check was repeated on a 7369-token prompt (React text x24), second pass:

| `--threads-batch` | long-prompt prefill t/s |
| --- | --- |
| 8 | 1247.7 |
| 16 | 1244.7 |
| 32 | 1241.2 |

Flat within 0.5%. With `-ngl 999` the model is fully offloaded; prefill is GPU-bound and
the CPU batch threads only feed it. Generation uses `--threads`, not `--threads-batch`.
No reason to change from the default 16. (The retired `llama-bench` had no threads-batch
option, hence the server-side long-prompt method.)

## MTP `--spec-draft-n-max` sweep (stock, c 155648)

Same-session second-pass C#+React averages (this build's default is n-max 3):

| n-max | C# decode | React decode | avg decode | acceptance | mean len | VRAM |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 57.5 | 55.5 | 56.5 | 0.819 | 1.82 | 21977 MiB |
| 2 | 63.9 | 62.2 | **63.1** | 0.752 | 2.50 | 22127 MiB |
| 3 | 55.8 | 67.3 | 61.5 | 0.630 | 2.95 | 22277 MiB |
| 4 | 61.2 | 58.0 | 59.6 | 0.547 | 3.19 | 22427 MiB |

- n-max 1's second pass hit an early EOS, so its row is first-pass C#+React (the most
  accepted but only 1.82 tokens/step).
- Same inverted-U as the 35B: decode peaks at n-max 2. Acceptance falls as n-max rises
  while the accepted run lengthens; n-max 3's wide C#/React spread (55.8 vs 67.3) is
  sampled-acceptance noise.
- VRAM rises ~150 MiB per extra draft token; n-max 4 at 155648 is within ~100 MiB of the
  cap, another reason to keep n-max 2.

## `-b`/`-ub` (compute buffer vs prefill) (stock, c 122880)

Larger ubatch trades VRAM for prefill. 7369-token prompt, second pass (the desktop
session used ~400 MiB in this series):

| `-b`/`-ub` | prefill t/s | VRAM used |
| --- | --- | --- |
| 2048 / 512 | 1299.3 | 21030 MiB |
| 4096 / 1024 | 1319.0 | 21430 MiB |
| 8192 / 2048 | 1339.2 | 22232 MiB |

- ub 512 -> 2048 buys only +3.1% prefill for +1.2 GiB of compute buffer; decode is
  per-token and does not move.
- At the 155648 ceiling it is unaffordable: the base config already sits at ~22440 MiB
  in a 400 MiB desktop (22127 MiB at the 86 MiB baseline), so even ub 1024 (+400 MiB)
  would cross 22528. The winner keeps the default 512.

## `--threads` sweep (stock, c 155648)

C# prompt, second pass (only the CPU-side slice uses threads, so a small effect was
expected):

| `--threads` | prefill t/s | decode t/s | acceptance |
| --- | --- | --- | --- |
| 6 | 1095.4 | 59.3 | 0.592 |
| 8 (winner) | 1064.8 | 59.7 | 0.664 |
| 12 | 1094.2 | 61.6 | 0.636 |

Flat within run-to-run noise (the 8 row is the headline session). The model is GPU-bound
with `-ngl 999`; `--threads` only feeds it. Keep 8. One session hit the 1-token warm-up
transient on the second pass and had to be repeated.

## Long-context refactor (stock, c 155648, retired ~116K prompt)

Winner config (MTP n-max 2), single `/v1/chat/completions` pass, no warm-up, ~116K-token
prompt, 512 gen:

| prompt tokens | prefill t/s | decode t/s | acceptance | mean len | finish | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| 116277 | 809.8 | 28.9 | 0.411 | 1.82 | length | 22440 MiB |

- Prefill and decode both fall off vs the short-prompt headline: prefill 1019.7 -> 809.8
  (-21%), decode 61.6 -> 28.9 (-53%). MTP acceptance drops 0.703 -> 0.411 (230/560), so
  the draft head does less useful work at long context as well as the attention/SSM cost
  rising.
- The decode regression is steeper than the 35B-A3B's on the same task (-37%): the MoE
  only activates ~3B params per token, this dense model runs ~27B.
- No crash or early EOS; the run hit the 512-token cap.
- Measured in a desktop session (Hyprland) using ~400 MiB, so VRAM read 22440 MiB total
  (~88 MiB under the 22528 line) vs 22127 MiB in the headline's 86 MiB-desktop session.
  The config is identical; only the desktop baseline moved.

## KV cache type: q8_0 vs f16 (stock)

Second-pass C#+React at c 77824 (f16's practical ceiling):

| KV type | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- |
| q8_0 | 1050.1 | 64.1 | 19000 MiB |
| f16 | 1051 | 65.5 | 21018 MiB |

- Throughput is identical - the KV read is not the bottleneck at these speeds. The only
  real difference is memory: f16 costs ~2 GiB more at the same context.
- That drops the context ceiling from 155648 (q8_0) to ~98304 (f16 loads at 22460 MiB
  with almost no reserve; fails at 122880). With no quality harness to justify trading
  ~37% of the context for f16 precision, q8_0 stays.

## `--load-mode none` (stock, c 155648)

Adding `--load-mode none` to the winner: VRAM 22508 MiB and C# decode 60.6 t/s
(acceptance 0.623), indistinguishable from the headline 59.7 t/s. The flag only changes
the load path; steady-state VRAM and throughput are unchanged. Not needed here.

## Warm-up note

Across sessions, the first raw `/completion` call (and occasionally a second) after load
returned a single token (`stop processing: n_tokens = prompt`, eval time 0.00 ms) before
steady-state runs produced the full 512. Treated as a load/first-use transient and
discarded, per the cold-load-then-second-pass convention.

## vLLM stack and pool notes (moved off the model page)

- The container requantizes the lm_head/embeddings/MTP in place on first boot: the base
  checkpoint to int8, the `-fast` variant to int4-GPTQ. On this 3090 the int4 widths are
  what let a 150k-context boot fit the 22.5 GB cap at all (the int8 base loads ~0.9 GiB
  heavier and lands over it) and leave enough headroom to raise the pool pin and serve up to
  170000.
- Profiles: `CTX=long` = fp8 KV, 4 chained MTP drafts, `MAX_LEN=150000`, pool pinned by bytes
  (`EXTRA_ARGS=--kv-cache-memory=5800000000`, 5.4 GiB) -> 150,769 tokens (1.01x at 150k).
  `CTX=huge` = KVarN `kvarn_k4v2_g128` KV (4-bit keys / 2-bit values per 128-token tile), 3
  chained drafts, `MAX_LEN=250000`, pool pinned (`--kv-cache-memory=4200000000`, 3.91 GiB) ->
  259,057 tokens (1.04x at 250k).
- `MAX_SEQS=4` is required at `CTX=long`: at the default 8 the 4-draft spec buffers push the
  pool below 150k and the engine refuses to boot. `CTX=huge` runs `MAX_SEQS=8`.
- Pinning is required, not cosmetic: `KV_MEM` is ignored on the MTP branch (it is wired into
  DFlash2 only), so `EXTRA_ARGS` is used; `GPU_UTIL` auto-sizing floats with free desktop
  memory and at every util tested spiked to ~23,900-24,000 MiB during the cold load
  (200k/0.88, 230k/0.90, 260k/0.93 all crossed 22528). Pinned: idle 21885, peak 22340 MiB,
  0 samples over (0.28.0-build readings).
- The fp8 profile can reach 170000 on the same int4 build, but only just (verified on the
  pre-rename 0.28.0 build; config unchanged): raising the pin to 6.5 GB (`MAX_LEN=170000`,
  pool 170,776) boots and served a 164,553-token prompt (prefill 655.7 t/s, decode 83.1 t/s,
  acceptance 0.625, coherent output). A near-full request pushed steady VRAM to 22,515 MiB,
  ~13 MiB under the 22,528 cap - a documented capability rather than a comfortable default.
  Keep 150000.
- Draft count does not transfer from fp8: at the KVarN profile 2 drafts fits (peak 22089 MiB)
  but short decode drops to 82.5, while 4 drafts is rejected (idle 22543, peak 23930 MiB), so
  the launcher default 3 stays.

## vLLM short-prompt rows (retired C#/React prompts, 2026-09-27)

`INT8_ACT=int8` served throughout (fp8 profile build `31f8b7a3`, KVarN `c68ac895`, Swift
`641274bd`/`4f4a6a1f`); retired short C#/React prompts averaged, single pass, requests
routed through llama-swap. Superseded by the ~10k-prompt rows on the model page.

| Quant | Spec | ctx | KV | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | MTP | 150000 | fp8 | 1672.7 | 103.3 | ~0.48 | 21990 MiB |
| W4A16-AutoRound-fast | MTP | 250000 | KVarN k4v2 | 1716.6 | 92.7 | ~0.50 | 21736 MiB |
| Swift-1.5-INT4 | MTP | 150000 | fp8 | 1621.5 | 96.1 | ~0.47 | 22510 MiB |
| Swift-1.5-INT4 | MTP | 250000 | KVarN k4v2 | 1683.0 | 86.7 | ~0.49 | 22052 MiB |

- Decode swings +-5-10% run to run (boot-to-boot variance is material - earlier single-boot
  readings of the same configs differed by up to ~20%), while prefill is +-0.5% stable. VRAM
  is the vLLM::EngineCore allocation.
- Single pass C# 1768.4 / 93.2, React 1576.9 / 113.3 (base, 150k); the decode gap between the
  two prompts is the known per-run spread. The first csharp prefill of a boot is a JIT
  artifact and is discarded.
- Swift single pass C# 1714.0 / 92.5, React 1528.9 / 99.6. Unguarded React naturally stops
  early: it emitted EOS at 339 tokens (decode 128.8, acceptance 0.899) - the fine-tune
  finishes coding answers without padding, unlike the base model which must be held to 512
  with `ignore_eos`. The 512-guarded React pass is what fed the table for protocol parity.
- Base led short decode at both contexts in these rows (150k 103.3 vs 96.1; 250k 92.7 vs
  86.7) with Swift close behind on prefill (1621.5 vs 1672.7; 1683.0 vs 1716.6) - one-boot
  data; on the current ~10k prompt the order flips (Swift ahead on decode).
- Long-context prefill (0.28.0-build readings): 7369-token React x24 1274 t/s; a
  139,686-token prompt 708 t/s. These are first-send prefills (single pass); a re-send of the
  same prompt hits the prefix cache (`cached=138,224`, prefill collapses to ~2.8 s), so
  follow-up turns are cheap while every cold measurement stays a real prefill.
- `INT8_ACT=int8` borrows batch mode's W4A8 Marlin path (weights stay int4, activations int8)
  for every linear except the already-int8 lm_head/embed and the MTP module. `INT8_LAYERS=mlp`
  is a smaller middle point (0.28.0-build readings: 1,615 / 878); `PREFILL_ATTN=int8` adds
  nothing on top.

## Retired profiles (alternatives)

- **DFlash2** (`W4A16-AutoRound-fast` on vLLM, `SPEC=dflash2`): 150 t/s decode at short
  context, but its pinned int8 KV pool caps the request at 120000. MTP gives up 37 t/s
  decode (103.3 vs 150) for 30k more context (150000 vs 120000) and wins long prompts
  outright (116K refactor, 0.28.0-build readings: MTP 791.2 / 69.3 vs DFlash2 335.2 / 44.5).
  Retired in favour of MTP.

      # env: CTX=long  SPEC=dflash2  PREFIX_CACHE=1
      #      GPU_UTIL=0.90  KV_MEM=5000000000  DFLASH_MAX_LEN=120000

  -> 150 t/s decode @ c 120000 (prefill 1221, acceptance ~0.37), 22293 MiB; long-prompt
  prefill 1182.0 t/s. `KV_MEM` pins int8 per-token-head KV through Triton and must cover
  `DFLASH_MAX_LEN` (the launcher reads `DFLASH_MAX_LEN`, not `MAX_LEN`, for that cap); while
  `KV_MEM` is set, `GPU_UTIL` is ignored.

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
  full log above.

## Long-context refactor (vLLM, retired ~116K prompt)

A deliberately near-repetitive ~116K-token refactor prompt; fp8 rows are 3-run means, KVarN rows
are single passes:

| Quant / engine | Spec | ctx | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| W4A16 / vLLM | MTP | 150000 | 746.7 | 63.8 | 0.442 | 21722 MiB |
| W4A16 / vLLM | MTP (KVarN) | 250000 | 784.4 | 27.5 | 0.365 | 21650 MiB |
| Swift-1.5-INT4 / vLLM | MTP | 150000 | 757.4 | 62.4 | 0.444 | 22704 MiB |
| Swift-1.5-INT4 / vLLM | MTP (KVarN) | 250000 | 836.0 | 32.4 | 0.512 | 22388 MiB |

- Long context is expensive on this dense model: fp8 decode falls from its 112.4 t/s
  short baseline (pre-2026-09-27; now 103.3 single-pass) to 63.8 at ~116K (-43%), KVarN to
  27.5 (its 250k ceiling) from 107.8 (now 92.7).
- The decode hit is larger than the 35B-A3B's on the same task (-37%): every token here
  runs ~27B dense params against a 116K context, while the MoE only wakes ~3B.
- All ran the full 512 (`ignore_eos: true`); no crash or EOS quirk - see
  [issues.md](../../../issues.md). Acceptance 0.442 (base fp8) / 0.365 (base KVarN) / 0.444
  (Swift fp8) / 0.512 (Swift KVarN).
- The archived llama.cpp UD-Q4_K_S run read 809.8 / 28.9 here - prefill on par, decode
  ~2x slower.
- Swift-1.5-INT4 is near-parity with the base quant on the fp8 profile (757.4 / 62.4 vs
  746.7 / 63.8) and leads on the single-pass KVarN reading (836.0 / 32.4 vs 784.4 / 27.5,
  +6.6% prefill, +17.8% decode).

## Long-context refactor (~60K prompt, retired single-pass rows)

Single-pass, cache-cold rows measured 2026-09-27 on the container builds named above,
before the protocol unification; superseded by the current rows on the model page.

| Quant | Engine | ctx | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | vLLM | 150000 | 1640.7 | 84.5 | 0.463 | 21990 MiB |
| W4A16-AutoRound-fast | vLLM | 250000 | 1713.3 | 40.9 | 0.332 | 21736 MiB |
| Swift-1.5-INT4 | vLLM | 150000 | 1617.3 | 78.9 | 0.447 | 22510 MiB |
| Swift-1.5-INT4 | vLLM | 250000 | 1698.5 | 41.9 | 0.369 | 22052 MiB |

- Single timed pass per boot on the ~60K-token prompt, cold load, vLLM server metrics, every
  request cache-cold (`prefix_hits 0`).
- fp8 150k decoded fastest (84.5 base / 78.9 Swift); the KVarN 250k profiles dropped to ~41
  t/s once KV bandwidth dominates, with prefill nearly flat across profiles.

## Key arch notes

- Hybrid SSM + attention: only ~16 of 65 layers own a growing KV cache
  (`full_attention_interval=4`), so context is much cheaper than a same-size dense
  transformer; the SSM state is constant-size.
- 4 KV heads x 256 key/value length; q8_0 KV costs ~0.045 MiB/token, which is why the
  llama.cpp path capped at 155648 under the 22 GB cap. The vLLM stack instead compresses KV
  (fp8 at 150000, KVarN 4/2-bit at 250000) to fit the same budget.
- Embedded MTP (`nextn_predict_layers=1`): no separate draft model needed. n-max 2 was the
  llama.cpp decode peak; VRAM rises ~150 MiB per extra draft token.
- vLLM W4A16 trades context against decode speed: fp8 (`CTX=long`) reaches 150000; KVarN
  (`CTX=huge`) reaches 250000 at ~2x slower long-context decode (40.9 vs 84.5 on the retired
  single-pass refactor run). DFlash2 traded prefill for short-context decode and is archived.
  KVarN quality cost is negligible (project: perplexity +0.16%, needle 4k-240k).
- Swift-1.5-INT4 tracks the base quant closely; its drafter is rebuilt on the fine-tune's own
  output distribution (~25.9k tokens instead of the base model's ~54k). On the current ~10k
  prompt it leads the base on decode at both contexts.

## Conclusions

- The vLLM stack is the current recommendation: `W4A16-AutoRound-fast` and `Swift-1.5-INT4`,
  fp8 at 150000 for short-context decode and KVarN 4/2-bit at 250000 for long requests, all
  under the 22 GB cap.
- UD-Q4_K_S was the best llama.cpp config at c 155648 (MTP n-max 2): 61.6 t/s decode
  (prefill 1019.7, acceptance 0.703), 22127 MiB. It is now retired - the vLLM stack beats it
  on decode (~1.7x short, ~2.4x at 116K) at the same VRAM and reaches 250000 via KVarN.
- Dense model, stock llama.cpp only - MoE-specific expert-cache features do not apply.
- 155648 is the llama.cpp context ceiling (native 262144 does not fit); `-ngld 0` does not
  buy more.
- `--threads-batch` is irrelevant here (GPU-bound); MTP n-max 2 is the llama.cpp decode peak.
- `--threads` 6/8/12 is likewise flat, and `-b`/`-ub` above the default 512 does not fit
  under the cap at 155648. The llama.cpp defaults are already the practical optimum.
- f16 KV runs at the same speed as q8_0 but cuts the llama.cpp context ceiling to ~98304, so
  q8_0 stays. `--load-mode none` changes nothing steady-state.

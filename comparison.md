# Cross-model comparison (Rig 1: RTX 3060 12GB)

All rows: llama-server single request (coding prompt, avg of C# + React, + 512 generated), -ngl 99 -fa 1,
KV q8_0 (-ctk q8_0 -ctv q8_0). Env vars
(GGML_CUDA_REGISTER_HOST=1, GGML_SCHED_PREFETCH_EXPERTS=1) on for every row unless noted.
Methodology in [methodology.md](methodology.md).

The 35B family is measured at 262144 only - 204800 was dropped for it (speed is within
6-9% of 256k on this model; see the model page note). The Flash-Next family is measured
at 230400 only - its practical ceiling (204800 was dropped: same speed class for 25k
fewer tokens; 256k loads but is unusable in practice).

## Qwen3.6-35B-A3B (two quants compared; UD-Q6_K archived - weakest at 256k)

### c 262144

| Quant | binary | MTP | ncmoe | prefill t/s | decode t/s | VRAM free after req |
| --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS 17.3G | stock | on | 28 | 525.7 | 49.4 | acceptance 0.67-0.70 |
| UD-Q4_K_M 21.1G | stock | on | 99 | 370.3 | 32.5 | acceptance 0.63-0.73 |
| UD-Q4_K_M 21.1G | Codacus fork | on | 99 | 268.6 | 38.8 | acceptance 0.59-0.72, cache 40 slots |

"binary" column: stock = upstream llama-server (no fork
features); Codacus fork = this repo's build ([thecodacus/llama.cpp](https://github.com/thecodacus/llama.cpp), branch `perf`) with
prefill env vars on. The stock binary cannot run the expert cache, so MTP-only stock
rows show n/a for slots.
n/m = prefill line not captured for that run.

## Qwen3.8-Flash-Next (different model family, 177B MoE - not comparable to the 35B)

### c 230400

| Quant | ncmoe | prefill t/s | decode t/s | VRAM free after req |
| --- | --- | --- | --- | --- |
| AD-Q4_K_M-M64 88.0G | 99 | 154.7 | 13.1 | ~770 MB (-b 512 -ub 512) |
| UD-IQ3_XXS 76.3G | 99 | 157.1 | 18.1 | ~860 MB (-b 512 -ub 512, MTP on) |

204800 rows were dropped: same speed class for 25k fewer tokens of window (old
protocol values; see the archive).

Full-256k rows were removed for both quants: each leaves only ~60 MB free - not usable
in practice. 230400 is the practical ceiling. See the archive for the 256k measurements.

## Rig 2 cross-check (RTX 3090, same prompts/protocol)

The same three Qwen3.6-35B-A3B quants were benchmarked on Rig 2 with the same protocol
(22 GB VRAM cap; full tables in [models/rig2-3090/qwen36-35b-a3b.md](models/rig2-3090/qwen36-35b-a3b.md), UD-IQ3_XXS is the
winner there, the rest archived). Decode is 3-4x Rig 1
because the 3090 fits the expert tensors on GPU (ncmoe 0-12):

| Quant | ncmoe | cache slots | ctx | decode t/s |
| --- | --- | --- | --- | --- |
| UD-IQ4_XS | 0 | n/a | 262144 | 165.1 |

## Reading guide

- Prefill at these contexts is attention-bound and dominated by CPU-expert streaming:
  quants with more GPU expert layers (lower ncmoe) prefill faster. IQ4_XS runs ncmoe 30
  (12 GPU layers), UD quants run ncmoe 99 with the cache - that is why IQ4 prefills
  +56-72% faster despite being the smaller file.
- Decode at 256k is MTP-bound where MTP is active: IQ4+MTP (51.4) beats every non-MTP
  row and the Q4_K_M cache+MTP row (38.1, pack starved by KV + draft context).
- Without MTP, decode between IQ4 and UD-Q4_K_M is a tie; IQ4 wins prefill decisively.
  Q4_K_M's only argument might be quantization quality (bpw 4.4-4.8 vs 4.19) - never tested, treat as an unverified alternative.
- IQ4_XS cannot use the expert cache (fused gate_up) - it always runs cache-less.
  ncmoe 26 OOMs at 262144 (VRAM ceiling); ncmoe 30 is required there.
- Qwen3.8-Flash-Next is a different, much larger model (177B vs 35B, 512 experts, hybrid
  Mamba2+attention): its rows show what that quality class costs on this GPU, not a
  like-for-like speed comparison with the 35B family.
- All decode outputs are token-identical to baseline (Codacus fork guarantees).

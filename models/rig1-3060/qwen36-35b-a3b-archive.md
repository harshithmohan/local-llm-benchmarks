# Qwen3.6-35B-A3B (Rig 1) - experiment archive

This archive holds supporting measurements and experiments not on the main card
([qwen36-35b-a3b.md](qwen36-35b-a3b.md)): rejected configs, sweeps, superseded quants,
and old-protocol baselines. Headline configs cover 262144; the extended-context YaRN
summary is on the main page, with the full probes below, and the headline numbers live
on the main card only. Lower-context points
(4096 / 131072 / 204800) appear only inside the sweep tables below. Methodology in [methodology](../../methodology.md); gotchas in [issues](../../issues.md).
Model cards: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(`UD-*` quants); [byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF) (`IQ4_XS-4.19bpw`).

Quants:

- `IQ4_XS-4.19bpw.gguf` (17.32 GiB, fused gate_up experts - cache incompatible)
- `UD-Q6_K.gguf` (27.94 GiB, separate gate/up/down)
- `UD-Q4_K_M.gguf` (21.10 GiB, separate gate/up/down)

Routing profiles at `<models>/moe-cache-profiles/`: `qwen36-udq6-merged.csv` (traced at
ncmoe 34), `qwen36-udq4km-merged.csv` (traced at ncmoe 26). Both made with
`llama-moe-trace`, code + chat prompts. The IQ4 trace exists but is unused (cache incompatible).

## Prefill patches (llama-bench, pp2048 / tg512, -b 2048 -ub 2048)

| Quant | ncmoe | env | pp2048 | tg512 |
| --- | --- | --- | --- | --- |
| IQ4_XS | 26 | none | 1120.66 | 43.61 |
| IQ4_XS | 99 | none | 866.33 | 33.78 |
| IQ4_XS | 99 | both | 2107.39 | 33.79 |
| IQ4_XS | 26 | both | 2307.13 | 43.57 |
| UD-Q4_K_M | 26 | none | 968.79 | 38.11 |
| UD-Q4_K_M | 34 | none | 875.74 | 33.57 |
| UD-Q4_K_M | 99 | none | 799.73 | 29.48 |
| UD-Q4_K_M | 26 | both | 1976.94 | 38.08 |
| UD-Q4_K_M | 34 | both | 1944.00 | 32.69 |
| UD-Q4_K_M | 99 | both | 1908.87 | 29.26 |
| UD-Q6_K | 34 | none | 739.70 | 26.89 |
| UD-Q6_K | 99 | none | 656.66 | 23.52 |
| UD-Q6_K | 99 | both | 1696.48 | 23.48 |
| UD-Q6_K | 34 | both | 1753.82 | 25.74 |

Findings:

- Prefill patches: +104-137% on the UD quants, +106% on IQ4. Decode (tg) unaffected.
- Batch size caps prefill: the first IQ4 run without -b/-ub 2048 gave pp 480.89 - always
  bench with -b 2048 -ub 2048 to match the Codacus fork README methodology.

## UD-Q6_K - expert cache sweep (llama-server, ~770-tok prompt + 512 gen, q8_0 KV)

| ctx | slots | decode t/s | VRAM notes |
| --- | --- | --- | --- |
| 4096 | 64 | 36.69 | pack 6346 MiB, 9463 MiB used |
| 4096 | 80 | 41.27 | pack 7933 MiB - OOM on large prompt (see issues.md) |
| 4096 | 72 | (stable, not re-measured) | pack 7140 MiB, big-prompt test passed |
| 131072 | 56 | 33.49 | pack 5553 MiB, KV 1360 MiB, 11453 MiB used after request |
| 204800 | 45 | 30.42 | pack 4462 MiB, KV 2125 MiB, 11561 MiB used - tight |
| 262144 | 0 (no cache) | ~23.5 (bench) | KV only 2720 MiB, 7147 MiB used total |

- Pack cost ~99.2 MiB/slot (the most expensive of the three quants). Slots scale roughly
  linearly: t/s ~= 16 + 0.32 * slots (fit).
- KV per token ~10.6 KiB (q8_0): c 4096 -> 80 MiB, c 131072 -> 1360 MiB, c 204800 ->
  2125 MiB, c 262144 -> 2720 MiB. Compute buffer grows with ctx: 560 MiB (c 4096) ->
  1602-1938 MiB (c 131k-256k).
- 256k fits without the cache (~7.1 GB used); with the cache only ~38 slots fit there
  (est. ~27-28 t/s) - diminishing returns.

## UD-Q4_K_M - expert cache (llama-server, ~770-tok prompt + 512 gen, q8_0 KV)

| ctx | slots | decode t/s | VRAM notes |
| --- | --- | --- | --- |
| 131072 | 80 | 40.49 | pack 5832 MiB, KV 1360 MiB, 11381 MiB used after request |
| 204800 | 66 | 39.46 | pack 4811 MiB, KV 2125 MiB, 11561 MiB used - tight (~350 MB free) |
| 262144 | 52 | 37.07 | pack 3791 MiB, KV 2720 MiB, 11471 MiB used - stable |

- Pack cost ~72.9 MiB/slot (cheaper than Q6's ~99.2). All three ctx points passed the
  large-prompt stability test. 80 slots at c 131072 is near the ceiling (~84 might fit,
  not tested).
- Full-256k no-cache reference: ~7.1 GB used, decode 29.5 t/s (bench); the cache at
  52 slots recovers it to 37.1 t/s.

## Stock (upstream) llama-server baseline vs Codacus fork

Stock binary: upstream llama-server (upstream v0.4.0-dev 30b6a75), running the same
commands (c 262144, q8_0 KV incl. draft, threads 12, MTP
`--spec-draft-n-max 2`, single ~770-tok prompt + 512 generated):

| Quant / ncmoe | binary | env | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- |
| IQ4_XS / 28 | stock | none | 686.5 | 51.4 |
| IQ4_XS / 28 | Codacus fork | both | 663.9 | 49.8 |
| IQ4_XS / 28 | Codacus fork + MTP | both | 668.5 | 50.7 (acc 0.67) |
| UD-Q6_K / 34 | stock | none | OOM | OOM |
| UD-Q6_K / 36 | stock | none | 447.1 | 31.3 (acc ~0.73) |
| UD-Q4_K_M / 99 | stock | none | 710.7 | 29.5 |
| UD-Q4_K_M / 99 | stock + MTP | none | 680.1 | 35.1 (acc 0.77) |
| UD-Q4_K_M / 99 | Codacus fork + MTP | both | 612.3 | 38.1 (acc 0.69) |

Findings:

- With MTP active, decode is spec-bound: fork and stock are equal for IQ4 (~50 t/s) -
  a wash, since IQ4 cannot use the fork's cache anyway.
- Prefill at 256k is attention-bound: the prefill patches add nothing measurable here
  (663.9 vs 686.5 - noise). Their gain was measured on pure prefill at short ctx
  (1121 -> 2307 t/s on IQ4, see the prefill table above).
- UD-Q6_K at ncmoe 34 + MTP OOMs at 262144 on the stock binary; ncmoe 36 works.
  Suggested config: ncmoe 36+, lower ctx, or drop MTP.

## UD-Q4_K_M + MTP at full context

Fork, ncmoe 99, cache + MTP (c 262144, q8_0 KV incl. draft, prefill env vars on):

| ctx | slots | decode t/s | notes |
| --- | --- | --- | --- |
| 262144 | 52 | OOM | pack 3791 MiB + MTP draft context > 12 GB |
| 262144 | 20 | 38.1 | acceptance 0.69, mean draft len 2.38, 11677 used |

- MTP acceptance on this model is ~0.69-0.77 (vs 0.92 on Flash-Next) - moderate.
- Q4_K_M + cache + MTP (38.1) does NOT beat IQ4_XS + MTP on stock (49.4 on the current
  protocol; 51.4 was the old-protocol baseline): the 256k KV +
  draft context starve the pack (20 slots = weak coverage), and all-CPU layers lose the
  14 GPU-expert layers IQ4 keeps at ncmoe 28.
- Small-ctx cache+MTP stacking (the Codacus fork README's 74.2 t/s class) was not
  measured - large ctx is the target use case.
- Re-test under the dual-prompt/temperature-0/ub-512 protocol: 40 slots + MTP now fit
  (the smaller compute buffer frees the room) -> 45.6 t/s decode, acceptance 0.77-0.84.
  The cache+MTP stack works at 256k once ub is 512; stock + MTP is 36.2, so the cache is
  worth +26% decode.

## YaRN context extension - 512K probe (UD-Q4_K_M)

The GGUF carries no YaRN metadata (native ctx 262144; `rope.freq_base` 10000000,
`rope.dimension_count` 64 = 25% partial rotary, mrope sections [11,11,10,0] - Qwen's
documented YaRN config for this family, simply not embedded), so extension is passed on
the command line. Both binaries honour it: the Codacus fork logs `custom YaRN scaling
detected, re-adjusting n_ctx_train(262144)`, and neither binary caps the slot at the
native window at this build (both report n_ctx_slot 524288). Config: ncmoe 99 - every
expert on CPU, the only way the 512K KV fits - q8_0 KV throughout, YaRN 2x
(`--rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144`) -> `--ctx-size 524288`,
ub 512, coding prompts C#+React averaged, second pass, +512 gen:

| Quant / binary | MTP | cache slots | VRAM (load) | prefill t/s | decode t/s | notes |
| --- | --- | --- | --- | --- | --- | --- |
| UD-Q4_K_M / stock | off | n/a | 9365 MiB | 248.7 | 29.0 | clean |
| UD-Q4_K_M / Codacus fork | off | n/a | 9365 MiB | 188.5 | 28.4 | clean |
| UD-Q4_K_M / Codacus fork | off | 20 | 10813 MiB | 161.4 | 30.0 | clean, prompt-dependent (31.6 / 28.4) |
| UD-Q4_K_M / Codacus fork | on | n/a | 11685 MiB | 238.4 | 32.3 (acc 0.66-0.68) | cudaMalloc OOM warnings in warm-up |

- The 512K q8_0 KV is ~5.3 GiB (~10.6 KiB/token); at ncmoe 99 weights + compute add
  ~4.4 GB, so the no-MTP/no-cache config leaves ~2.9 GB under the 12 GB cap.
- MTP is the decode winner, but with only ~600 MiB headroom it threw transient
  `cudaMalloc ... out of memory` during warm-up (the timed pass itself completed). Parked
  as not-clean rather than recorded as a usable row.
- Short-prompt prefill differences between stock and fork read large here (248.7 vs
  188.5), but with only 192/155-token prompts and two samples that is not a robust
  separation; decode is the meaningful column.
- 1M is the model's documented YaRN target (factor 4) but needs ~10.6 GiB of q8_0 KV
  alone - infeasible on this 12 GB rig. 512K is the practical ceiling for the cache/MTP
  configs; dropping MTP and cache (stock) reaches ~672K - see the scaling subsection.
- Long-range retrieval under YaRN was not validated - that needs a >262144-token needle
  and a slow full prefill.

### Stock + MTP off - context scaling to the 12 GB ceiling

Same flags as the 512K stock row (UD-Q4_K_M, ncmoe 99, q8_0 KV, ub 512), no MTP and no
cache, with `--rope-scale` = ctx/262144. Extra VRAM is mostly KV (~10.6 KiB/token) plus a
compute buffer that keeps growing with ctx (~3.4 KiB/token):

| ctx | rope-scale | VRAM (load) | prefill t/s | decode t/s | fits |
| --- | --- | --- | --- | --- | --- |
| 524288 | 2.0 | 9365 MiB | 248.7 | 29.0 | clean |
| 655360 | 2.5 | 11109 MiB | 248.4 | 28.6 | clean |
| 688128 | 2.625 | 11545 MiB | 247.7 | 28.7 | edge (~370 MiB free) |
| 704512 | 2.6875 | 11763 MiB | - | - | loads, ~130 MiB free - not usable |
| 720896 | 2.75 | - | - | - | OOM at load |

- The 12288 MiB card reserves ~376 MiB driver overhead (~11912 MiB usable); 720896 aborts
  at context creation on a 2336 MiB compute-buffer `cudaMalloc`.
- Throughput is flat across the range (decode 28.6-29.0, prefill ~248): going from 512K to
  672K costs no speed, only headroom.
- Ceiling: ~672K (688128) is the largest that runs, but at ~370 MiB free it is not a
  comfortable config. 640K (655360, ~800 MiB free) is the safe maximum; 512K (~2.5 GB
  free) stays the recommended point when headroom matters.
- YaRN is engaged throughout; retrieval quality at these lengths is still unvalidated.

### IQ4_XS - extended context (512K-736K)

Stock binary, q8_0 KV, YaRN (`--rope-scale` = ctx/262144), ub 512, coding C#+React
averaged, second pass, +512 gen. IQ4_XS is smaller than UD-Q4_K_M, so GPU expert layers
stay resident further: block_count is 41, so ncmoe <41 keeps `41 - ncmoe` expert layers on
GPU (~437 MiB each) and ncmoe >=41 is all-CPU (ncmoe 64 and 99 identical).

| ctx | ncmoe | MTP | prefill t/s | decode t/s | VRAM (load) | fits |
| --- | --- | --- | --- | --- | --- | --- |
| 524288 | 34 | off | 332.46 | 37.07 | 11037 MiB | clean - 7 GPU expert layers |
| 524288 | 40 | on | 284.55 | 36.33 | 11317 MiB | MTP acc ~0.60 - loses to MTP-off |
| 524288 | 36 | off | - | - | 10101 MiB | fits |
| 524288 | 32 | off | - | - | 11851 MiB | ~61 MiB free - too tight |
| 524288 | 28 | off | - | - | OOM | cudaMalloc 1682 MiB compute buffer |
| 688128 | 99 | off | 286.43 | 33.51 | 10653 MiB | clean |
| 720896 | 99 | off | - | - | 11089 MiB | fits (not measured) |
| 753664 | 99 | off | 282.05 | 32.30 | 11525 MiB | edge |
| 770048 | 99 | off | - | - | 11743 MiB | loads, ~170 MiB free - not measured |
| 786432 | 99 | off | - | - | OOM | cudaMalloc 2450 MiB compute-pp buffer |

- Per-prompt prefill/decode: 512K ncmoe 34 C# 354.28/36.87, React 310.63/37.27; 512K
  ncmoe 40 + MTP C# 305.18/35.76 (acc 0.590), React 263.93/36.90 (acc 0.603); 672K
  C# 310.25/33.11, React 262.61/33.91; 736K C# 301.64/32.26, React 262.45/32.34.
- MTP is a net loss at extended ctx: the draft context costs ~2.3 GiB, which evicts the
  GPU expert layers; acceptance is only ~0.60 (vs 0.67-0.70 at 256K).
- IQ4_XS beats UD-Q4_K_M at every shared extended point (512K 332.5/37.1 @11037 vs UD
  fork+MTP 238.4/32.3 @11685; 672K 286.4/33.5 @10653 vs UD 247.7/28.7 @11545) and reaches
  ~736K where UD stops at ~672K.
- Ceiling ~736K usable / 752K loads / 768K OOM. All IQ4 rows logged a benign
  `common_fit_params: failed to fit params ... n_gpu_layers already set by user to 999`
  warning and served normally.
- Messy-code refactor (116,259-token prompt, single `/v1/chat/completions` pass,
  max_tokens 512, ignore_eos, cold load): 512K/ncmoe 34 = 491.48 prefill / 23.33 decode
  (11037 MiB); 736K/ncmoe 99 = 452.04 / 21.97 (11525 MiB). Both decoded the full 512
  tokens (finish_reason length); the decode drop vs the 256K MTP-on messy row (32.63) is
  MTP-off plus attention over the larger allocated KV.
- YaRN engaged throughout; retrieval quality at these lengths is still unvalidated.

### UD-Q4_K_M - 262144 headline (archived from the main page)

IQ4_XS proved faster at every context, so UD-Q4_K_M was demoted off the main page.
Current protocol (coding prompts C#+React averaged, second pass, +512 gen, q8_0 KV,
c 262144):

| binary | MTP | ncmoe | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- |
| stock | on | 99 | n/a | 370.3 | 32.5 |
| Codacus fork | on | 99 | 40 | 268.6 | 38.8 |

- The 40-slot expert cache + MTP is UD-Q4_K_M's best 256k decode (38.8, acceptance
  0.59-0.72) but prefill stays cache-bound (268.6 vs 370.3) and it stays below IQ4_XS
  stock+MTP (49.4). Stock + MTP without the cache is 32.5.
- Q4_K_M's only argument might be quantization quality (bpw 4.4-4.8 vs 4.19) - never
  tested, treat as an unverified alternative.
- Messy-code refactor (116,259-token prompt, single /v1/chat/completions pass, max_tokens
  512, ignore_eos, cold load): Codacus fork + 40-slot cache + MTP = 400.39 prefill /
  31.00 decode, VRAM 10061 MiB, MTP acceptance 0.806 (mean len 2.61); an earlier attempt
  was aborted by a power loss and the re-run reproduced - the config is reproducible.
  The original two-pass numbers (399.25/30.25) match within single-run noise.

## Conclusions

- Final verdict at large ctx: IQ4_XS via stock llama-server + MTP, 49.4 t/s @ 262144 on
  the current protocol, is the fastest config (the 51.4 t/s in the stock-baseline table
  was the old-protocol baseline).
- The Codacus fork's role for the 35B family: UD-Q4_K_M's cache at mid-ctx
  (40.5 @ 131072 without MTP) and its prefill patches for short-ctx/cold prefill -
  not the 256k decode crown.
- UD-Q6_K is the weakest at large ctx in every measured config; archived from the
  main surfaces.
- Q4_K_M's only argument might be quantization quality (bpw 4.4-4.8 vs 4.19) - never
  tested, treat as an unverified alternative.

# Qwen3.6-35B-A3B (Rig 1) - experiment archive

> **Timing-prompt note:** numbers on this page were measured with the retired short C#/React timing prompts (pre-2026-09-29). The current prompt is the single ~10k-token opencode session context ([test-prompts.md](../../../test-prompts.md)); the two are not directly comparable.

This archive holds supporting measurements and experiments not on the main card
([qwen36-35b-a3b.md](../qwen36-35b-a3b.md)): rejected configs, sweeps, retired quants,
and old-protocol baselines. Headline configs cover 262144; the extended-context YaRN
summary is on the main page, with the full probes below, and the headline numbers live
on the main card only. Lower-context points
(4096 / 131072 / 204800) appear only inside the sweep tables below. Methodology in [methodology](../../../methodology.md); gotchas in [issues](../../../issues.md).
Model cards: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(`UD-*` quants); [byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF) (`IQ4_XS-4.19bpw`).

Quants:

- `IQ4_XS-4.19bpw.gguf` (17.32 GiB, fused gate_up experts - the moe-cache fork caches them)
- `UD-Q6_K.gguf` (27.94 GiB, separate gate/up/down)
- `UD-Q4_K_M.gguf` (21.10 GiB, separate gate/up/down; cache-compatible)

## Prefill patches (llama-bench, retired tool; pp2048 / tg512, -b 2048 -ub 2048)

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
  bench with -b 2048 -ub 2048.

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

## GenerelSchwerz moe-cache fork - dynamic expert cache (llama-server + /completion)

A dynamic CUDA LRU/frequency cache (`--moe-expert-cache-size N` = expert slabs per tensor
kept on GPU; cold experts stay in host pinned memory), with no routing-trace step.
Measured with the
C# coding prompt, second pass, +512 gen, q8_0 KV, ncmoe 28, **MTP on**, ctx 32768, cold
load. VRAM is the load reading against the 12288 MiB cap.

| Quant | cache slots | prefill t/s | decode t/s | VRAM (load) |
| --- | --- | --- | --- | --- |
| UD-Q4_K_M | 0 (control) | 330.9 | 45.5 | 9213 |
| UD-Q4_K_M | 16 | 296.3 | 30.9 | 4309 |
| UD-Q4_K_M | 32 | 307.1 | 53.0 | 5371 |
| UD-Q4_K_M | 64 | 334.1 | 67.7 | 7761 |
| UD-Q4_K_M | 96 | 400.1 | 80.1 | 10151 |
| UD-Q4_K_M | 112 | 459.1 | 90.4 | 11463 |
| UD-Q4_K_M | 128 / 160 / 192 | - | OOM at spawn | - |
| IQ4_XS | 0 (control) | 381.0 | 52.5 | 7871 |
| IQ4_XS | 16 | 335.4 | 39.1 | 3315 |
| IQ4_XS | 32 | 354.4 | 59.8 | 4269 |
| IQ4_XS | 64 | 387.2 | 79.9 | 6279 |
| IQ4_XS | 96 | 457.2 | 96.2 | 8361 |
| IQ4_XS | 128 | 587.8 | 103.1 | 10371 |

- The fork caches IQ4_XS's **fused gate_up** experts, so IQ4_XS is again the fastest 35B
  quant in this regime.
- Caches below the routed-group width are a net **loss** vs the cache-off control
  (UD-Q4_K_M 16 slots = 30.9 vs 45.5): with the cache on, `--n-cpu-moe` placement is
  overridden, so an undersized cache thrashes while the control keeps whole expert layers
  resident. The cache only pays from ~32 slots up.
- VRAM scales ~linearly with slots; the 12 GB ceiling at 32768 is ~112 slots (UD-Q4_K_M)
  / ~128 (IQ4_XS).
- `--moe-early-router`: +1-4% decode (IQ4_XS 128: 104.5 vs 103.1; UD-Q4_K_M 96: 82.9 vs
  80.1).
- `--moe-expert-cache-mib 5000` (IQ4_XS) = 87.8 decode @ 7493 MiB - a coarser knob that
  lands between the 64- and 96-slot points.
- `--moe-expert-cache-layers 0-23` (half the layers, IQ4_XS 128) = 56.2 decode - far worse
  than caching all layers (103.1); leave the layer selector off.
- MTP still matters: IQ4_XS 128 slots with MTP off = 81.2 vs 103.1 with MTP (~+27%).
- Validation (`--experimental-logs`, IQ4_XS 96 @ 32768): `moe-grouped-decode calls=2358
  covered=41 fallback=0 rollback=0 prepare_error=0 finish_error=0 upload_errors=0`, and
  `decode_grouped=2238 cache_hits=32291 cache_misses=5042` = **86.5% hit rate** - the
  grouped cache path is genuinely engaged (not merely a VRAM-placement effect).

### Context scaling (coding prompts C#+React averaged)

| Quant | cache slots | ctx | prefill t/s | decode t/s | VRAM (load) |
| --- | --- | --- | --- | --- | --- |
| IQ4_XS | 64 | 131072 | 388.0 | 82.8 | 7785 |
| IQ4_XS | 48 | 262144 | 355.1 | 72.0 | 8825 |
| IQ4_XS | 96 | 262144 | - | OOM | - |
| IQ4_XS | 128 | 131072 | - | OOM | - |
| UD-Q4_K_M | 64 | 262144 | 301.7 | 69.3 | 11275 |
| IQ4_XS | 48 | 524288 | 363.2 | 60.8 | 10937 |
| IQ4_XS | 56 | 524288 | 358.3 | 63.0 | 11405 |
| IQ4_XS | 64 | 524288 | - | crash (OOM) | - |

- At 256k the q8_0 KV (2720 MiB) plus the cache lowers the slot ceiling: IQ4_XS 48 /
  UD-Q4_K_M 64 are the largest that fit with headroom. IQ4_XS @ 256k/48 = 72.0 decode
  beats stock's 54.9 by +31% at prefill parity (355.1 vs 356.9).
- Extended context (YaRN scale 2, MTP off): the fork keeps working at 512K. C#-only slot
  sweep: 8 = 40.3, 16 = 45.6, 24 = 52.1, 32 = 54.5, 48 = 58.3, 56 = 61.0 decode
  (VRAM 8521 -> 11405); 64 crashes (OOM). Both-prompt averages: cache 48 = 363.2/60.8,
  cache 56 = 358.3/63.0. Cache 48 leaves ~1.35 GiB headroom, 56 ~0.88 GiB. Beats the ik
  512K row (337.1/42.4) by ~+43% decode at ~+8% prefill.

### IQ4_XS - 256k expert-cache ceiling (peak-vs-load + 48-vs-64 A/B, ub 2048)

Measured 2026-09-29 on the 10k opencode session prompt (current timing prompt), ctx 262144,
`-b 2048 -ub 2048`, MTP on, `--n-cpu-moe` dropped (ignored while the cache is on, above).

- **Peak == load.** Sampling `nvidia-smi` every 200 ms across a full 10k prefill + 512 gen
  held flat at **9471 MiB** (225 samples, min = max) - no hidden prefill transient at this
  ctx/ubatch, so the load reading is the true high-water mark and the leftover headroom is
  genuinely untuned.
- **Cache ceiling at 256k** (load VRAM): 48 = 9471, 56 = 9957, 64 = 10439, 80 = 11553; 96
  would be ~12.5 GB -> OOM. The earlier "48 is the largest that fits" rule predates the
  current ubatch/config and was over-conservative (it fit only because 48 left 2.8 GiB
  unspent).
- **48-vs-64 A/B** (interleaved 64/48/64/48, 4 measured passes each, to cancel drift):
  64 = **76.8 t/s** decode (8 passes, acceptance 0.841), 48 = **70.0** (7 valid, acceptance
  0.876). Cache 64 wins ~+10% *despite the lower acceptance* (i.e. ~+12% raw decode);
  prefill is identical (1377 both). Cache 80 gave no further gain and leaves only ~735 MiB.
- **Picked cache 64** (10439 MiB, ~1.85 GiB margin). Stability: one cache-48 and one
  cache-64 pass returned `predicted_n` 1 (EOS as first token, empty output) - rare,
  cache-independent, a retry decodes normally.

### IQ4_XS - 256k ubatch sweep + ub 2048-vs-6144 A/B (2026-09-29)

Follow-up to the cache work: the compute arena is sized by `min(n_ctx, n_ubatch)`, so the
physical ubatch is the prefill lever (the logical `-b` only caps `-ub`). Measured on the
10k opencode prompt, ctx 262144, cache 64, MTP on:

| `-b`/`-ub` | prefill t/s | decode t/s | VRAM (load) |
| --- | --- | --- | --- |
| 2048 | 1374 | 76-79 | 10439 MiB |
| 4096 | 1744 | ~70 | 10923 MiB |
| 6144 | **1909** | 77 | 11545 MiB |
| 8192 | crash | - | - |

- Prefill scales with ubatch: 2048 -> 4096 = +27%, 4096 -> 6144 = +10%, **+39% total**.
  ub 8192 passes the health check then dies on the first inference (runtime crash, not a
  load OOM). Peak VRAM at 6144 is flat at the load reading (sampled every 200 ms across a
  full prefill+gen), so 6144 leaves ~740 MiB margin.
- Decode is ubatch-independent: an interleaved ub 2048/6144 A/B (3 measured passes each,
  alternating loads to cancel drift) gave 79.4 t/s (acceptance 0.88) vs 76.6 (0.86) - the
  ~3.5% gap tracks MTP acceptance, not the ubatch. The ub-4096 decode reading was a
  lower-acceptance session for the same reason.
- The base entry was moved to `-b 6144 -ub 6144` (+39% prefill for ~1.1 GiB, still under
  the 12288 MiB cap).

### IQ4_XS - 512K ubatch + cache ceiling (2026-09-29)

The 512K extended-context entry was tuned the same way as the 256K one (raise `-b/-ub`, then
the cache to the ceiling): measured on the 10k opencode prompt, ctx 524288 (YaRN 2x), cache
48, MTP off:

| `-b`/`-ub` | prefill t/s | decode t/s | VRAM (load) |
| --- | --- | --- | --- |
| 2048 | 1449 | ~52 | 11249 MiB |
| 4096 | 1861 | ~55 | 11497 MiB |
| 6144 | **2063** | 52 | 11749 MiB |

- The ubatch lift is larger here than at 256K: prefill 1449 -> 2063 (**+42%**). `-b/-ub 6144`
  is the applied value (the 843K entry stays at ubatch 512 - VRAM-tight).
- Decode is ubatch-independent (all rows ~50-55; the spread is sampling/acceptance noise).
- Cache 56 at `-b/-ub 6144` fails on load (OOM, reproduced twice). The larger compute arena
  competes with the cache slabs, so the cache ceiling drops from 56 (at ub 512) to 48 at
  ub 6144. `-b/-ub 8192` was not retested here; at 256K it crashes the fork at runtime.
- Superseded (retired short-prompt protocol, cache 48, ub 512): 363.2 / 60.8 @10937 MiB.

### IQ4_XS - 843776 fork max-ctx probe (archived from the main page, retired-protocol)

The fork's maximum serving context on this rig (scale 3.21875), retired short-prompt
protocol. All experts on CPU (ncmoe 41), cache 0 - at this ctx the q8_0 KV leaves no VRAM
for cache slabs plus the compute buffer. ubatch 512 (VRAM-tight).

| Quant | binary | MTP | ncmoe | cache slots | ctx | prefill t/s | decode t/s | VRAM (load) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | moe-cache fork | off | 41 | 0 | 843776 | 278.2 | **34.7** | 11837 MiB |

- 851968 (scale 3.25) loads but crashes the fork child on the first request; the retired ik
  engine was the only one that served 851968 (all-CPU, 11153 MiB).
- Timing: at this ctx both retired short prompts emit EOS as their first token over raw
  `/completion` (a YaRN-scale artifact - the older ik rows decoded normally), so the row was
  timed with `ignore_eos: true`, which does not affect the decode rate
  ([test-prompts.md](../../../test-prompts.md)).
- MTP stays off at every extended row - the draft context's VRAM cost evicts GPU expert
  layers (stock) or eats the KV headroom (ik); the fork runs all-CPU at 843K.

## Stock (upstream) llama-server baseline

Stock binary: upstream llama-server (upstream v0.4.0-dev 30b6a75), running the same
commands (c 262144, q8_0 KV incl. draft, threads 12, MTP
`--spec-draft-n-max 2`, single ~770-tok prompt + 512 generated):

| Quant / ncmoe | binary | env | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- |
| IQ4_XS / 28 | stock | none | 686.5 | 51.4 |
| UD-Q6_K / 34 | stock | none | OOM | OOM |
| UD-Q6_K / 36 | stock | none | 447.1 | 31.3 (acc ~0.73) |
| UD-Q4_K_M / 99 | stock | none | 710.7 | 29.5 |
| UD-Q4_K_M / 99 | stock + MTP | none | 680.1 | 35.1 (acc 0.77) |

Findings:

- Prefill at 256k is attention-bound: the prefill patches add nothing measurable here.
  Their gain was measured on pure prefill at short ctx
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
- Q4_K_M + cache + MTP (38.1) does NOT beat IQ4_XS + MTP on stock (54.9 on the current
  protocol; 51.4 was the old-protocol baseline): the 256k KV +
  draft context starve the pack (20 slots = weak coverage), and all-CPU layers lose the
  14 GPU-expert layers IQ4 keeps at ncmoe 28.
- Re-test under the dual-prompt/temperature-0/ub-512 protocol: 40 slots + MTP now fit
  (the smaller compute buffer frees the room) -> 45.6 t/s decode, acceptance 0.77-0.84.
  The cache+MTP stack works at 256k once ub is 512; stock + MTP is 36.2, so the cache is
  worth +26% decode.

## YaRN context extension - 512K probe (UD-Q4_K_M)

The GGUF carries no YaRN metadata (native ctx 262144; `rope.freq_base` 10000000,
`rope.dimension_count` 64 = 25% partial rotary, mrope sections [11,11,10,0] - Qwen's
documented YaRN config for this family, simply not embedded), so extension is passed on
the command line. The stock binary honours it and does not cap the slot at the
native window at this build (n_ctx_slot 524288). Config: ncmoe 99 - every
expert on CPU, the only way the 512K KV fits - q8_0 KV throughout, YaRN 2x
(`--rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144`) -> `--ctx-size 524288`,
ub 512, coding prompts C#+React averaged, second pass, +512 gen:

| Quant / binary | MTP | cache slots | VRAM (load) | prefill t/s | decode t/s | notes |
| --- | --- | --- | --- | --- | --- | --- |
| UD-Q4_K_M / stock | off | n/a | 9365 MiB | 248.7 | 29.0 | clean |

- The 512K q8_0 KV is ~5.3 GiB (~10.6 KiB/token); at ncmoe 99 weights + compute add
  ~4.4 GB, so the no-MTP/no-cache config leaves ~2.9 GB under the 12 GB cap.
- Short-prompt prefill with only 192/155-token prompts and two samples is not a robust
  separation; decode is the meaningful column.
- 1M is the model's documented YaRN target (factor 4) but needs ~10.6 GiB of q8_0 KV
  alone - infeasible on this 12 GB rig. Dropping MTP (stock) reaches ~672K - see the
  scaling subsection.

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
  248.7/29.0 @9365; 672K 286.4/33.5 @10653 vs UD 247.7/28.7 @11545) and reaches
  ~736K where UD stops at ~672K.
- Ceiling ~736K usable / 752K loads / 768K OOM. All IQ4 rows logged a benign
  `common_fit_params: failed to fit params ... n_gpu_layers already set by user to 999`
  warning and served normally.
- Long-context refactor (retired ~116K prompt): the 512K/ncmoe 34 and 736K/ncmoe 99 rows
  are consolidated under the retired-prompt section below. Both decoded the full 512
  tokens (finish_reason length); the decode drop vs the 256K MTP-on long-context row (32.63) is
  MTP-off plus attention over the larger allocated KV.

### IQ4_XS ik - extended-context rows (archived from the main page)

Retired short-prompt protocol. The ik engine extended furthest (all-CPU experts at the top
end); its extended rows were replaced on the main page by the moe-cache fork, which maxes
out at 843776 (cache 0). ik build 3bb386e except the 512K row (build 1aaf710).

| ctx | rope-scale | ncmoe | GPU experts | prefill t/s | decode t/s | VRAM (load) | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 524288 | 2.0 | 28 | 13 | 337.1 | 42.4 | 11767 MiB | re-measured 2026-09-27 (build 1aaf710), config-served sampling |
| 753664 | 2.875 | 36 | 5 | 262.4 | 34.7 | 11361 MiB | ik best at 736K |
| 851968 | 3.25 | 41 | 0 | 240.2 | 32.4 | 11153 MiB | ik max measured, serves fine |

- ik lean/sweep probes (no rows): at 512K, ncmoe 34 = 289.4/37.3 @9379 MiB and deeper packs
  (26) OOM; at 736K, all-CPU ncmoe 41 = 252.8/33.0 @10037 MiB. All-CPU ceiling sweep:
  786432 (scale 3.0) = 255.0/32.8 @10409 MiB; 851968 (scale 3.25) = 240.2/32.4 @11153 MiB.
- ik ceiling detail: 917504 (scale 3.5) loads at 11897 MiB but crashes on the first request
  (runtime CUDA OOM in the decode cublas path - loads-fine is not proof of serviceability
  near the ceiling, [issues.md](../../../issues.md)); 983040 (scale 3.75) OOMs at init; ncmoe 34
  at 736K crashes at init (cublasCreate OOM).
- ik's per-GPU-expert-layer cost at 736K is ~265 MiB vs ~437 MiB on stock, so ik packs ~4
  more experts on GPU at equal VRAM - the main reason for its extended decode lead.
- ik-specific: ncmoe above the 41 layer count clamps to 41 (all-CPU) - ncmoe 99 == 41.
- Stock extended (retired): 524288 ncmoe 34 = 332.5/37.1 @11037 MiB; 753664 ncmoe 99 =
  282.0/32.3 @11525 MiB (edge, ~370 MiB free). 704K-752K sit between; 752K loads tight,
  768K OOMs at context creation. The 512K->736K step costs ~15% prefill / ~13% decode on
  stock. Full sweep table above.
- MTP at extended ctx (ik) is a loser: fits only on the lean 512K split (`--n-cpu-moe 34` +
  `--spec-type mtp:n_max=2 -ctkd q8_0 -ctvd q8_0`: 41.8 decode / 269.6 prefill, 11729 MiB,
  acceptance ~0.76-0.82 - decode ~parity with MTP-off ncmoe 28 at 42.4, prefill much worse);
  the draft context eats the KV headroom at ncmoe 28 and OOMs at 736K even all-CPU (ncmoe 41,
  the per-step recurrent speculative checkpoint init OOMs the main KV alloc, 782 MiB).

### IQ4_XS ik - 256k probes + engine notes (archived from the main page)

ik-llama.cpp (build 3bb386e) was tested at 256k but offers no win, so it never got a main-
page table row. Short-prompt probes: best row 311.6 prefill / 47.5 decode with MTP; MTP-off
probe 358.7 / 45.0. MTP acceptance is higher on ik (0.81-0.84 vs 0.67-0.70 on stock) but
does not convert to throughput, and the ik MTP draft context does not fit with deeper GPU
packs (ncmoe 18/24 + MTP fail at init; the 256k MTP ceiling is ncmoe 28).

- ik ncmoe clamps at the 41 layer count (values above = all-CPU experts).
- Per-GPU-expert-layer VRAM cost at extended ctx is ~265 MiB on ik vs ~437 MiB on stock, so
  ik keeps ~4 more experts on GPU at equal VRAM at 736K.
- ik's extended ceiling fails past 852K with a runtime CUDA OOM crash on the first request
  rather than a clean init-time rejection (see the ik extended rows above).
- ik-llama.cpp flags/notes: [methodology.md](../../../methodology.md); gotchas: [issues.md](../../../issues.md).

### IQ4_XS stock + MTP - 262144 headline (archived from the main page)

The moe-cache fork is faster at 256k, so the stock row was demoted off the main page.
Stock binary + MTP, ncmoe 28, c 262144, q8_0 KV, config-served sampling:

    llama-server -m <models>/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      --n-cpu-moe 28 --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --reasoning-preserve \
      --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0

| prompt | prefill t/s | decode t/s | VRAM | notes |
| --- | --- | --- | --- | --- |
| 10k opencode session prompt (2026-09-29) | 659 | 56.5 | 11823 MiB | post-rebuild stock (v0.5.0-dev 2b129cc); acceptance ~0.85; 5 passes, decode 54.1-57.9 |
| retired C#+React short prompts (2026-09-27) | 356.9 | 54.9 | | v0.5.0-dev d834d44; acceptance 0.69-0.78; earlier v0.4.0-dev 30b6a75 = 525.7 / 49.4 |

- On the ~10k prompt the fork (cache 48, MTP on, `-b 2048 -ub 2048`) does 1374 prefill /
  73 decode (9471 MiB): stock stays archived - ~+29% fork decode and ~2.1x prefill, and
  stock uses ~2.7 GiB more VRAM.
- Ubatch probe (2026-09-29): the entry already runs `-b 2048` by default; raising `-ub`
  512 -> 2048 lifted prefill 654 -> 1374 t/s (~2.1x) with decode unchanged within
  acceptance noise, for +350 MiB (9471 vs 9121). Cache 48 + MTP still fit at 256k.
- `--n-cpu-moe` is ignored while the expert cache is on (the cache overrides CPU-MoE
  placement): the registered 256k and 512K entries no longer set it (verified - identical
  VRAM and speed with the flag present or absent at 256k). Cache-off control for this quant
  is `--n-cpu-moe 28` with `--moe-expert-cache-size 0`.

### UD-Q4_K_M - 262144 headline (archived from the main page)

IQ4_XS proved faster at every context, so UD-Q4_K_M was demoted off the main page.
Retired protocol (coding prompts C#+React averaged, second pass, +512 gen, q8_0 KV,
c 262144):

| binary | MTP | ncmoe | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- |
| stock | on | 99 | n/a | 370.3 | 32.5 |

- Q4_K_M's only argument might be quantization quality (bpw 4.4-4.8 vs 4.19) - never
  tested, treat as an unverified alternative.

## Long-context refactor (retired ~116K prompt)

One-time real-task speed test of the long-context refactor prompt (see
[test-prompts.md](../../../test-prompts.md), generated by `scripts/generate-long-context-prompt.py`,
seed 42, 116,259 prompt tokens), the IQ4_XS 256K headliner plus the two extended-context
IQ4_XS recipes, q8_0 KV, cold load, single-run protocol (ONE timed pass, no warm-up;
/v1/chat/completions, max_tokens 512, `ignore_eos: true` per the long-context-prompt rules in
test-prompts.md). Retired 2026-09-27 when the prompt was reduced to ~60K tokens; the
~60K re-run lives on [qwen36-35b-a3b.md](../qwen36-35b-a3b.md). This section is the
single home for the retired run's numbers.

| Quant | binary | MTP | ncmoe | ctx | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | stock | on | 28 | 262144 | n/a | 522.16 | 32.63 |
| IQ4_XS | stock | off | 34 | 524288 | n/a | 491.48 | 23.33 |
| IQ4_XS | stock | off | 99 | 753664 | n/a | 452.04 | 21.97 |

- Single-pass redo (2026-09): the original two-pass numbers (IQ4_XS 518.69/32.54)
  predate the single-run protocol. The redo confirms them: every value matches within
  single-run noise, and the row uses `--load-mode none` (eager weight load), so there
  was no mmap page-in effect to warm anyway. Old and new numbers are interchangeable
  for comparison purposes.
- IQ4_XS: MTP acceptance 0.652 (mean len 2.30), VRAM 11797 MiB at load (under the
  12 GB cap), /v1/chat/completions. No crash: the near-repetitive prompt is safe on
  qwen35moe (the PLE n-gram crash risk is qwen4exp-only). No EOS quirk either - the
  qwen35moe arch decodes normally on /completion and /v1/chat/completions.
- Decode is 32.63 t/s at 256K vs the 54.9 headline on the ~192/~155-token coding prompts,
  with MTP acceptance normal: the gap is attention cost over 116K cached KV tokens, not an
  MTP failure. The coding-prompt protocol stays unchanged for headline numbers.
- Chat-endpoint gotchas vs the raw /completion protocol: a closed ``` fence at prompt end
  makes the model emit EOS immediately in raw /completion (end-of-turn); n_predict is
  ignored by /v1/chat/completions (use max_tokens).
- Extended-context rows (IQ4_XS, YaRN, MTP off): the same 116,259-token prompt runs
  491.48/23.33 at 512K (ncmoe 34, 11037 MiB) and 452.04/21.97 at 736K (ncmoe 99,
  11525 MiB). The 256K MTP-on row's higher decode (32.63) reflects MTP plus the smaller
  allocated KV; every row decoded the full 512 tokens (finish_reason "length").

### IQ4_XS fork - ~60K long-context rows (unified protocol, 2026-09-29)

Re-measured on the current configs under the unified timing protocol (raw
`/v1/completions`, two-pass, `ignore_eos: true`; prompt_n 59751):

| MTP | ctx | cache | ub | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- | --- | --- |
| on | 262144 | 64 | 6144 | 1552 | 59.2 | 11551 MiB |
| off | 524288 | 48 | 6144 | 1693 | 40.8 | 11747 MiB |

Superseded rows (2026-09-28, first fork run; retired protocol - `/v1/chat/completions`,
single-pass, cache 48, ub 512, prompt_n 59760):

| MTP | ctx | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- |
| on | 262144 | 580.36 | 54.23 | 9141 MiB |
| off | 524288 | 609.06 | 40.54 | 11095 MiB |

### IQ4_XS stock/ik - ~60K long-context rows (archived from the main page)

The ~60K re-run's stock and ik rows (2026-09-27, stock build d834d44 / ik build 1aaf710,
config-served sampling, /v1/chat/completions, max_tokens 512, `cache_prompt: false`,
`ignore_eos: true`, `cached_tokens` 0):

| Quant | binary | MTP | ncmoe | ctx | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | stock | on | 28 | 262144 | n/a | 580.70 | 46.36 |
| IQ4_XS | ik | off | 28 | 524288 | n/a | 435.82 | 30.20 |

- prompt_n 59760 (stock) / 59759 (ik); VRAM 11791 MiB / 11755 MiB, both under cap. Every
  row decoded the full 512 tokens (finish_reason "length"). The moe-cache fork beats both
  on this prompt under the retired protocol (256K 580.36/54.23, ~+17% decode; 512K
  609.06/40.54, ~+34%); the current-config re-run is on the main page.

## Conclusions

- Final verdict at large ctx: IQ4_XS on the GenerelSchwerz moe-cache fork (cache 64 at
  `-b/-ub 6144`, MTP on) is the fastest config at 262144 - 76 t/s decode, +35% over
  stock+MTP (54.9); it also takes 512K (52) and is the first engine here to serve YaRN up to
  843776. Cache 64 is the ceiling at 256k/ub 6144 (80 no longer fits, 96 OOMs); at 32k the
  same fork reaches 103 t/s (128 slots).
- UD-Q6_K is the weakest at large ctx in every measured config; archived from the
  main surfaces.
- Q4_K_M's only argument might be quantization quality (bpw 4.4-4.8 vs 4.19) - never
  tested, treat as an unverified alternative.
- Context choice: 262144 is the headline. 204800 and 131072 runs exist (204800 is within
  6-9% of 262144); 200k only buys 1-2 extra cache slots for 57k tokens of window, so they
  stay off the main page.

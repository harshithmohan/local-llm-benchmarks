# Qwen3.6-35B-A3B - experiment archive

All measurements behind [qwen36-35b-a3b.md](qwen36-35b-a3b.md) (main file covers 262144
only). Lower-context points (4096 / 131072 / 204800) appear only inside the sweep tables
below. Methodology in [methodology](../../methodology.md); gotchas in [issues](../../issues.md).

Models:

- `IQ4_XS-4.19bpw.gguf` (17.32 GiB, fused gate_up experts - cache incompatible)
- `UD-Q6_K.gguf` (27.94 GiB, separate gate/up/down)
- `UD-Q4_K_M.gguf` (21.10 GiB, separate gate/up/down)

Routing profiles in the models root's `moe-cache-profiles/` folder: `qwen36-udq6-merged.csv` (traced at
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

Stock binary: upstream llama-server (upstream v0.4.0-dev 30b6a75), running the
config.yaml commands (c 262144, q8_0 KV incl. draft, threads 12, MTP
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
- The config.yaml Q6 entry (ncmoe 34 + MTP) OOMs at 262144 on the stock binary; ncmoe 36
  works (verified at ncmoe 36). Fix: ncmoe 36+, lower ctx, or drop MTP for the Q6 entry.

## UD-Q4_K_M + MTP at full context

Fork, ncmoe 99, cache + MTP (c 262144, q8_0 KV incl. draft, prefill env vars on):

| ctx | slots | decode t/s | notes |
| --- | --- | --- | --- |
| 262144 | 52 | OOM | pack 3791 MiB + MTP draft context > 12 GB |
| 262144 | 20 | 38.1 | acceptance 0.69, mean draft len 2.38, 11677 used |

- MTP acceptance on this model is ~0.69-0.77 (vs 0.92 on Flash-Next) - moderate.
- Q4_K_M + cache + MTP (38.1) does NOT beat IQ4_XS + MTP on stock (51.4): the 256k KV +
  draft context starve the pack (20 slots = weak coverage), and all-CPU layers lose the
  14 GPU-expert layers IQ4 keeps at ncmoe 28.
- Small-ctx cache+MTP stacking (the Codacus fork README's 74.2 t/s class) was not
  measured - large ctx is the target use case.
- Re-test under the dual-prompt/temperature-0/ub-512 protocol: 40 slots + MTP now fit
  (the smaller compute buffer frees the room) -> 45.6 t/s decode, acceptance 0.77-0.84.
  The cache+MTP stack works at 256k once ub is 512; stock + MTP is 36.2, so the cache is
  worth +26% decode.

## Conclusions

- Final verdict at large ctx: IQ4_XS via stock llama-server + MTP (51.4 t/s @ 262144)
  is the fastest config.
- The Codacus fork's role for the 35B family: UD-Q4_K_M's cache at mid-ctx
  (40.5 @ 131072 without MTP) and its prefill patches for short-ctx/cold prefill -
  not the 256k decode crown.
- UD-Q6_K is the weakest at large ctx in every measured config; archived from the
  main surfaces.
- Q4_K_M's only argument might be quantization quality (bpw 4.4-4.8 vs 4.19) - never
  tested, treat as an unverified alternative.

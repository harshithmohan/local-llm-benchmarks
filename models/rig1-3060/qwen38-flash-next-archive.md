# Qwen3.8-Flash-Next (Rig 1) - experiment archive

All measurements behind [qwen38-flash-next.md](qwen38-flash-next.md) (main file covers
230400 with MTP; this archive holds the rest). Methodology in
[methodology](../../methodology.md); model-specific issues in [issues](../../issues.md).

Quants:

- `UD-IQ3_XXS` (76.32 GiB, 3 shards) - the recommended one
- `AD-4.27bpw-Q4_K_M-M64` (88.02 GiB, 33 shards)
- `UD-Q3_K_XL` (83.80 GiB, 3 shards) - dropped from the main page: at large ctx it never
  beats the other two (ties at 204800), kept here in full

Routing profiles: `qwen38-q3xl-merged.csv` (traced at ncmoe 45), `qwen38iq3-merged.csv`
(traced at ncmoe 43), both code + chat prompts.

## Prefill patches (llama-bench, pp2048 / tg512, -b 2048 -ub 2048)

| Quant | ncmoe | env | pp2048 | tg512 |
| --- | --- | --- | --- | --- |
| UD-Q3_K_XL | 48 (all CPU) | none | 78.82 | 6.82 |
| UD-Q3_K_XL | 46 | none | 83.58 | 8.56 |
| UD-Q3_K_XL | 45 | none | 86.34 | 10.74 |
| UD-Q3_K_XL | 45 | both | 522.22 | 13.78 |
| UD-Q3_K_XL | 48 | both | 595.76 | 12.43 |
| AD-Q4_K_M-M64 | 48 (all CPU) | none | 183.62 | 12.47 |
| AD-Q4_K_M-M64 | 46 | none | 184.78 | 12.84 |
| AD-Q4_K_M-M64 | 45 | none | 185.13 | 12.98 |
| AD-Q4_K_M-M64 | 44 | none | 184.55 | 13.16 |
| AD-Q4_K_M-M64 | 44 | both | 525.67 | 13.89 |
| AD-Q4_K_M-M64 | 48 | REGISTER_HOST only | 519.68 | 12.56 |
| UD-IQ3_XXS | 48 (all CPU) | none | 150.51 | 13.62 |
| UD-IQ3_XXS | 46 | none | 182.52 | 14.07 |
| UD-IQ3_XXS | 45 | none | 182.26 | 14.22 |
| UD-IQ3_XXS | 44 | none | 339.15 | 15.00 |
| UD-IQ3_XXS | 43 | none | 323.64 | 15.12 |
| UD-IQ3_XXS | 43 | both | 526.07 | 14.88 |

Findings:

- Prefill patches: +656% on Q3_K_XL (79 -> 596, the biggest win of any model tested -
  it streams ~10x more expert bytes per token than the 35B); +183% on AD; +63% on IQ3.
- The prefetch stream also helps decode on the cold Q3_K_XL (+28% at ncmoe 45), but it
  costs VRAM: with both env vars on, AD caps at ncmoe 44 (45+ abort at context creation);
  REGISTER_HOST alone lets all 48 CPU layers fit.
- Split preference on Q3_K_XL: prefill prefers ALL-CPU layers (48: 596) while decode
  prefers some GPU-expert layers (45: 13.8 vs 12.4). Each GPU expert layer costs
  ~1.2 GB VRAM. ncmoe 44 OOMs in llama-bench graph alloc; on IQ3, ncmoe 42 does not load.
- Cold vs warm cache: the Q3_K_XL table ran cold; AD/IQ3 tables ran warm (page cache
  inflates baselines - RAM-resident experts decode much faster than NVMe-streamed ones).

## Context ladders (llama-server decode, q8_0 KV, no MTP)

| Quant | ctx | ncmoe | env | ubatch | decode t/s | VRAM notes |
| --- | --- | --- | --- | --- | --- | --- |
| UD-Q3_K_XL | 131072 | 48 | - | 2048 | 11.95 | 11677 used, ~230 MB free - very tight |
| UD-Q3_K_XL | 204800 | 48 | RH only | 512 | 12.56 | 10895 used, ~1 GB free |
| AD-Q4_K_M-M64 | 131072 | 46 | both | 512 | 13.12 | 11113 used, ~800 MB free |
| AD-Q4_K_M-M64 | 131072 | 48 | RH only | 512 | 11.94 | 8823 used, ~3 GB free |
| AD-Q4_K_M-M64 | 204800 | 48 | RH only | 512 | 12.61 | ~1.7 GB free |
| AD-Q4_K_M-M64 | 230400 | 48 | RH only | 512 | 12.57 | ~770 MB free |
| UD-IQ3_XXS | 131072 | 46 | - | 512 | 11.29 | 9839 used, ~2.1 GB free |
| UD-IQ3_XXS | 204800 | 48 | - | 512 | 12.80 | 9285 used, ~2.6 GB free |
| UD-IQ3_XXS | 230400 | 48 | - | 512 | 12.80-ish | no-MTP not measured (MTP run: 14.69) |

Findings:

- The compute buffer scales with `-ub` on this arch (indexer): ub 2048 needs ~3.5x the
  compute of ub 512 at large ctx. The `-ub 512` trick unlocks large contexts, not KV
  savings (KV is only ~4.9 KiB/token); Mamba RS state is 450 MiB (constant, 4 seqs).
- Q3_K_XL cannot free VRAM via ncmoe (capped at 48 = all layers) and 256k does not fit
  for it (~800 MB over budget even at ub 512). AD and IQ3 load at 256k but leave only
  ~60 MB free - removed from the main tables as unusable in practice; 230400 is the
  practical ceiling for both.
- ncmoe 43 at c 131072 on IQ3 fails at compute-pp buffer alloc even with ub 512
  (5 GPU-expert layers eat the room); 46 fits.

## Expert cache verdicts

- UD-Q3_K_XL: the only quant where the cache paid off - 32 slots -> 14.54 t/s at c 4096
  (+16%). The pack (~104 MiB/slot, 48 layers) cannot coexist with large-ctx compute
  buffers, so it only ever paid at small ctx.
- AD-Q4_K_M-M64: not usable - at ncmoe 44 only ~750 MB is left after load; ~5 slots x
  ~118 MiB/slot = ~2% coverage. Skipped as meaningless.
- UD-IQ3_XXS: a net loss at 12 GB VRAM - measured at small ctx: 24 slots, 11% coverage,
  decoded slower than plain ncmoe 43. Keep GPU expert layers instead of a pack.
- Root cause for all three: 512 experts with flat routing traffic (30 slots cover only
  ~19% of traffic, 128 slots ~57% but need a 13 GB pack - impossible at 12 GB).

## MTP spec decode history

- At c 65536 (README config: -ncmoe 99, 48-slot cache, -no-sched-async-cpu, -t 6):
  baseline 11.71 -> cache 48 + MTP Q8_0 draft (n-max 1) 14.59 -> n-max 2 15.41
  (acceptance 0.92, mean draft len 2.85). Q4_K_M draft = Q8_0 draft in speed (14.57).
  The Codacus fork README's 24.4 t/s was not reproduced on this rig - hardware-bound
  (RAM bandwidth / NVMe at all-CPU decode).
- At large ctx (no cache, ub 512, REGISTER_HOST, 12 threads, async on): IQ3_XXS + MTP
  Q8_0 draft (-ngld 0, n-max 2) -> 15.78 t/s @ 204800 (+23%), 14.69 @ 230400, 15.43 @
  262144 (unusable ~60 MB free). Acceptance varies 0.62-0.92 by run/prompt.
- ncmoe experiments with MTP at 204800: ncmoe 46 OOMs (GPU-expert layers + draft
  context); ncmoe 47 fits but is within single-run noise of ncmoe 99 on both decode
  (16.07 vs 15.78) and prefill - not worth the headroom.
- AD + shared MTP head: acceptance only ~0.71 and decode slower than no-MTP -> skipped;
  no MTP for AD.

## Conclusions

- Best Flash-Next config on this rig: UD-IQ3_XXS + MTP at 230400 (14.69 t/s), 204800 if
  more headroom is wanted (15.78).
- AD-Q4_K_M-M64 is the quality alternative (bpw 4.27 vs 3.06, untested) - slower in
  every measured config, no MTP.
- UD-Q3_K_XL never wins at large ctx; its cache win is small-ctx only.
- Context is capped by compute buffers (not KV) on this arch; -ub 512 is mandatory for
  large ctx.

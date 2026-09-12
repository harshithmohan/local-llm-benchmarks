# Qwen3.6-35B-A3B (Rig 2) - experiment archive

Measurements behind [qwen36-35b-a3b.md](qwen36-35b-a3b.md) (main file: UD-IQ4_XS only).
Protocol identical: coding prompts C#+React averaged, second-pass prefill, recommended
sampling, cold load, q8_0 KV, `--threads 8`, 22 GB VRAM cap (22 GB +- 250 MB, desktop
reserve). Methodology in [methodology](../../methodology.md); gotchas in
[issues](../../issues.md).

Quants:

- `UD-IQ4_XS` - the winner (separate gate/up/down, cache-compatible)
- `IQ4_XS-4.19bpw` - faster at reduced ctx, cache incompatible (fused gate_up)
- `UD-Q4_K_M` - cache-compatible

Routing profiles at `<models>/moe-cache-profiles/` (the same `*-merged.csv` files as
Rig 1, made with `llama-moe-trace`).

## Rejected configs (VRAM over the cap)

| Quant | ncmoe | ctx | VRAM used | verdict |
| --- | --- | --- | --- | --- |
| IQ4_XS-4.19bpw | 0 | 262144 | 22771 MiB | over cap |
| IQ4_XS-4.19bpw | 1 | 262144 | 22549 MiB | over cap |
| UD-Q4_K_M | 8 | 262144 | 22779 MiB | over cap |

## Archived alternatives

### IQ4_XS-4.19bpw (stock + MTP)

| ncmoe | ctx | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- | --- |
| 2 | 262144 | 1999.0 | 147.7 | 22283 MiB |
| 0 | 230400 | 2408.0 | 178.1 | 22223 MiB |

Faster than UD-IQ4_XS at 230400 (178.1 vs 165.1) but: cannot use the expert cache ever
(fused gate_up), and trading 31k tokens of window for +13 t/s is not worth it for the
default setup. Kept in the archive as the max-speed-at-200k option.

### UD-Q4_K_M (stock + MTP, ncmoe 10)

| ncmoe | cache slots | ctx | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- | --- | --- |
| 10 | n/a | 262144 | 1160.4 | 94.1 | 21853 MiB |

The winner in the table is the Codacus fork cache+MTP variant (ncmoe 12 + 64 slots ->
119.3, +27% over this stock row). Q4_K_M's only argument might be quantization quality
(bpw 4.4-4.8 vs IQ4's ~4.2) - never tested, unverified.

Rejected VRAM-over-cap configs: ncmoe 8 @ 262144 (22779 MiB, with or without cache).

## Conclusions

- Final verdict: UD-IQ4_XS at ncmoe 0 + MTP (165.1 t/s @ 262144) is the config of
  choice - the only quant that holds full ctx within the 22 GB cap.
- IQ4_XS-4.19bpw is the max-speed option if a reduced window is acceptable
  (178.1 @ 230400); it can never use the expert cache (fused gate_up).
- UD-Q4_K_M's cache+MTP variant (119.3, +27% over its stock row) is the quality
  alternative - never tested, unverified.
- No prefill-patch, context-ladder, or MTP sweep tables were run on this rig; at
  ncmoe 0 the fork's cache and prefill patches have nothing to add (see the main page).

# Qwen3.6-35B-A3B (Rig 2) - experiment archive

This archive holds the supporting measurements and experiments that are not on the main
card ([qwen36-35b-a3b.md](qwen36-35b-a3b.md)): rejected configs, sweeps, superseded quants,
and old-protocol baselines. Headline numbers live on the main card only.
Protocol identical: coding prompts C#+React averaged, second-pass prefill, recommended
sampling, cold load, q8_0 KV, `--threads 8`, 22 GB VRAM cap (22 GB +- 250 MB, desktop
reserve). Methodology in [methodology](../../methodology.md); gotchas in
[issues](../../issues.md).
Model cards: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(`UD-*` quants); [byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF) (`IQ4_XS-4.19bpw`).

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

## MTP draft-count sweep (UD-IQ4_XS, stock, ncmoe 0, c 262144)

Same-session comparison, second-pass, C#+React averaged, q8_0 KV incl. draft, cold load:

| spec-draft-n-max | prefill t/s | decode t/s | acceptance | mean len | VRAM used |
| --- | --- | --- | --- | --- | --- |
| 1 | 2517.8 | 155.9 | 0.832 | 1.83 | 22001 MiB |
| 2 (control) | 2532.7 | **169.3** | 0.690 | 2.38 | 22065 MiB |
| 3 | 2518.3 | 161.3 | 0.579 | 2.72 | 22127 MiB |

- 2 is the peak: decode traces an inverted U (155.9 -> 169.3 -> 161.3). All three fit
  comfortably (22001-22127 MiB, full 262144).
- n-max 1 trades too much: acceptance is highest (0.832) but the mean accepted run is only
  1.83, so each draft step yields too few tokens and step overhead dominates.
- n-max 3 rejects the third token too often (acceptance 0.690 -> 0.579 for a mean run of
  only 2.38 -> 2.72), so the extra draft/verify step is not recovered. n-max 4 alone was
  not run - the trend is against it; it was later probed with a p-min threshold (see the
  p-min sweep below).
- Control read 169.3 vs the 165.1 headline: same-session vs earlier-session variance
  (methodology caveat). The within-table comparison is the valid one; the headline stands.

## MTP `--spec-draft-p-min` sweep (UD-IQ4_XS, stock, ncmoe 0, c 262144)

`--spec-draft-p-min` (default 0.00) stops the MTP draft as soon as the head's top token
falls below the threshold (that token is dropped, not accepted) - the adaptive counterpart
to a fixed `--spec-draft-n-max`. Same protocol as above; every row is a fresh cold load.

Matched batch across three prompts (C# and React coding, plus a short prose probe built
from the TCP/UDP chat text in [test-prompts](../../test-prompts.md)), pass-2 decode:

| config | decode t/s (C#/React/prose) | mean | acceptance (C#/React/prose) | mean | mean len | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| n-max 3, p-min 0 (control) | 148.9 / 162.0 / 153.4 | 154.8 | 0.515 / 0.625 / 0.560 | 0.567 | 2.70 | 22127 MiB |
| n-max 3, p-min 0.5 | 143.1 / 163.2 / 154.3 | 153.5 | 0.634 / 0.738 / 0.746 | 0.706 | 2.74 | 22127 MiB |
| n-max 4, p-min 0.5 | 169.2 / 152.2 / 156.0 | 159.1 | 0.735 / 0.656 / 0.694 | 0.695 | 3.05 | 22191 MiB |

Earlier spot checks (C#+React only): n-max 2 p-min 0 control averaged 158.3 over three
cold loads (154.7 / 159.8 / 160.6, acceptance ~0.635); n-max 2 + p-min 0.5 read 161.5
(0.790); n-max 4 + p-min 0.3 read 167.2 (0.603).

- p-min raises draft acceptance consistently, and most on the weakest domain: at fixed
  n-max 3 the mean goes 0.567 -> 0.706 (prose alone 0.560 -> 0.746); at n-max 2 it goes
  0.635 -> 0.790.
- Acceptance does not convert to decode speed on this setup. n-max 3 + p-min 0.5 is flat
  against its own control (153.5 vs 154.8 t/s) despite +0.14 acceptance, and the prose
  probe moves only 153.4 -> 154.3 t/s (+0.6%) despite +0.19 acceptance. The saving lands on
  the draft side (fewer drafted tokens per step); the mean accepted run barely moves
  (2.70 -> 2.74), and decode tracks the accepted run and fixed per-step cost instead.
- What does move decode is a longer accepted run: n-max 4 + p-min 0.5 has the longest mean
  run (3.05) and the best batch average (159.1), but its C#/React spread is wide (169.2 vs
  152.2) and overlaps the other rows. Both highest single rounds needed n-max 4 (167.2 at
  p-min 0.3, 169.2 at p-min 0.5).
- Verdict: p-min is a genuine acceptance control but roughly throughput-neutral here; no
  p-min row clears the 165.1/169.3 sessions of the n-max 2 headline, so the headline is
  unchanged. n-max 4 + p-min 0.5 (longest accepted run) is the documented alternative.
- Inert knobs: `--spec-draft-p-split` is parsed but never used by the build, and
  `--spec-draft-n-min` is not consulted by the MTP draft loop. Draft-model flags
  (`--spec-draft-n-cpu-moe`, `-ngld`, `-md`, ...) apply only to a separate draft model;
  this MTP head is embedded in the 35B file.
- Prose-probe caveat: 36-token prompt, 512 generated, so its prefill column is not
  comparable - only decode and acceptance are. One early pass hit EOS at 2 tokens and was
  discarded.

## UD-IQ4_XS - extended context (512K-1M, YaRN)

Stock, q8_0 KV, `--rope-scale` = ctx/262144, coding C#+React second-pass, cold load;
MTP off unless noted. The full ladder needs expert offload; ncmoe was tuned to the
minimum that fits the 22 GB cap at each ctx.

| ctx | rope-scale | MTP | ncmoe | prefill t/s | decode t/s | VRAM used | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 524288 | 2.0 | off | 6 | 1656.7 | 89.9 | 21915 MiB | best; C# 1738.69/89.89, React 1574.61/89.98 |
| 524288 | 2.0 | on | 12 | 1249.1 | 83.9 | 22461 MiB | acc 0.729, mean len 2.45; C# 1316.84/83.88, React 1181.45/83.96 |
| 786432 | 3.0 | off | 15 | 1181.9 | 65.2 | 22205 MiB | best; C# 1240.10/65.38, React 1123.61/64.97 |
| 786432 | 3.0 | on | 26 | 828.8 | 55.9 | 22017 MiB | acc 0.777; C# 877.01/56.66, React 780.52/55.14 |
| 1048576 | 4.0 | off | 25 | 871.8 | 49.4 | 22141 MiB | best; C# 932.25/49.75, React 811.41/49.10 |
| 1048576 | 4.0 | on | 38 | 595.3 | 35.2 | 22209 MiB | acc 0.612; C# 619.09/33.25, React 571.48/37.08 |

- MTP is a net loss at every extended point: dropping it frees the ~2.3 GiB draft context,
  which funds 6-7 more GPU expert layers. 512K: 89.9 vs 83.9 decode (1656.7 vs 1249.1
  prefill); 768K: 65.2 vs 55.9; 1M: 49.4 vs 35.2. Acceptance is higher with MTP
  (0.61-0.78) but does not recover the evicted experts - the Rig 1 extended-ctx pattern.
- ncmoe tuning was to the minimum that fits. Probe points: 512K ncmoe 6 = 21915 MiB;
  768K ncmoe 20 = 20429 MiB, ncmoe 15 = 22205 MiB; 1M ncmoe 32 = 19653 MiB, ncmoe 24 =
  22497 MiB (within the cap but only ~31 MiB of margin, so ncmoe 25 was measured).
- A 768K MTP-on probe at ncmoe 20 failed to allocate the 2.47 GB prefill compute buffer
  (`failed to allocate CUDA0 buffer of size 2466545792`); MTP-off at the same ncmoe fits
  (20429 MiB). At 768K-1M the prefill compute buffer, not KV alone, is the load limit.
- Extra probe: 736K (rope-scale 2.875) MTP on ncmoe 30 = 20595 MiB (fits; speed not
  measured). `--ctx-size` is clamped to `n_ctx_train * rope-scale`, so rope-scale must
  equal ctx/262144 exactly (2.875 yields a 753664 slot, not 786432).
- Retrieval quality at these lengths is unvalidated.

## Conclusions

- Final verdict: UD-IQ4_XS at ncmoe 0 + MTP (165.1 t/s @ 262144) is the config of
  choice - the only quant that holds full ctx within the 22 GB cap.
- IQ4_XS-4.19bpw is the max-speed option if a reduced window is acceptable
  (178.1 @ 230400); it can never use the expert cache (fused gate_up).
- UD-Q4_K_M's cache+MTP variant (119.3, +27% over its stock row) is the quality
  alternative - never tested, unverified.
- No prefill-patch or context-ladder tables were run on this rig; at ncmoe 0 the fork's
  cache and prefill patches have nothing to add (see the main page).
- MTP draft count was swept (n-max 1/2/3, all fit); decode peaks at n-max 2 (169.3
  same-session vs 155.9 at 1 and 161.3 at 3), so the headline n-max 2 stands. See the
  sweep section.
- MTP `--spec-draft-p-min` was also swept. It lifts acceptance clearly (fixed n-max 3:
  0.567 -> 0.706; prose probe 0.560 -> 0.746) but is throughput-neutral: the prose probe
  moved only 153.4 -> 154.3 t/s and n-max 3 + p-min 0.5 was flat against its control.
  Acceptance is not the decode lever here - a longer accepted run is - so the best p-min
  row is n-max 4 + p-min 0.5 (mean accepted run 3.05, batch 159.1 t/s). The headline stays
  n-max 2; n-max 4 + p-min 0.5 is the documented alternative. See the p-min section.

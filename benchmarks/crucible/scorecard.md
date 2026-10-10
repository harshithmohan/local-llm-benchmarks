# Consolidated score card — crucible

One row per model + checkpoint quant + KV-cache type. Per-model detail (engine results,
capability verdicts, run context) is in `scorecards/<model>.md`; raw run logs under `results/`
are deleted once recorded — the scorecards are the persistent record. The Crucible harness does
**not** follow this repo's timing protocol, so these numbers are **not comparable to the
model-card timing rows** (see README → Protocol deviations).

## How to read

Crucible reports per-engine results, not one scalar score. Record the headline metric for each
engine — `C1` NIAH cells passed, `C2` challenges passed, `C3` JSON-compliance level reached. A
model's row summarizes its scores; the full breakdown stays in `scorecards/<model>.md`.

| Model | Quant | KV cache | C1 NIAH | C2 reasoning | C3 structured |
|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | q8_0 | 66/77 (85.7%) | 11/13 (84.6%) | 2/3 (1 partial) |

- `Model` and `Quant` are named as in the main [README](../../README.md) model tables, so a
  checkpoint can be added as its own row.
- `C1` is cells passed out of 77 (7 context sizes × 11 depths); `C2` challenges passed out of 13;
  `C3` schema levels compliant out of 3.
- `KV cache` is the served KV-cache type (`--cache-type-k` / `--cache-type-v`). It changes all
  three scores, so a row is only comparable to another row recorded at the same KV-cache type.
- Suite-wide rules — thinking off for C1/C3, the engine exclusions, and why timing and energy are
  not recorded — are in the [suite README](README.md).

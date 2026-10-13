# Consolidated score card — crucible

One row per model + checkpoint quant + KV-cache type + served context size. Per-model detail (engine results, capability verdicts, run context) is in `scorecards/<model>.md`; raw run logs under `results/` are deleted once recorded — the scorecards are the persistent record. The Crucible harness does **not** follow this repo's timing protocol, so these numbers are **not comparable to the model-card timing rows** (see README → Protocol deviations).

## How to read

Crucible reports per-engine results, not one scalar score. Record the headline metric for each engine — `C1` NIAH cells passed, `C2` challenges passed, `C3` JSON-compliance level reached. A model's row summarizes its scores; the full breakdown stays in `scorecards/<model>.md`.

| Model | Quant | KV cache | ctx | C1 NIAH | C2 reasoning | C3 structured |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | UD-IQ4_XS | q8_0 | 262144 | 35/35 (100.0%) | 13/13 (100.0%) | 3/3 |
| Qwen3.6-35B-A3B | UD-IQ4_XS | q4_0 | 262144 | 35/35 (100.0%) | 13/13 (100.0%) | 3/3 |

- `Model` and `Quant` are named as in the main [README](../../README.md) model tables, so a checkpoint can be added as its own row.
- `C1` is cells passed out of the **fitted** cell count for that row's served context — the pinned ladder is 8 context sizes (16k → 512k) × 5 depths = 40 cells, trimmed so no cell exceeds the served context (a 512k prefill must also stay inside the timeout); `C2` challenges passed out of 13; `C3` schema levels compliant out of 3.
- `KV cache` is the served KV-cache type (`--cache-type-k` / `--cache-type-v`); the MTP draft cache is held at q8_0 throughout. A C3 penalty figure varies run to run and is not comparable between rows.
- `ctx` is the context size the row was measured at.
- Suite-wide rules — the engine exclusions and why timing and energy are not recorded — are in the [suite README](README.md).

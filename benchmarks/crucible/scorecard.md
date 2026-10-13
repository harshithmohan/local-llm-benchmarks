# Consolidated score card — crucible

One row per model + checkpoint quant + KV-cache type + served context size. Per-model detail (engine results, capability verdicts, run context) is in `scorecards/<model>.md`; raw run logs under `results/` are deleted once recorded — the scorecards are the persistent record. The Crucible harness does **not** follow this repo's timing protocol, so these numbers are **not comparable to the model-card timing rows** (see README → Protocol deviations).

> **Deprecated (2026-10-13).** Every row below was measured on Crucible **v0.1.3**. v0.1.5 (2026-10-12) changes the capability protocol, so these numbers are kept for reference only and are **not comparable** to a v0.1.5 run; re-measure on the current binary before comparing. The C1 ladder has since changed from the 2k→128k × 11-depth (77-cell) default to the suite's pinned 16k→512k × 5-depth ladder (max 40 cells, trimmed per served context), so C1 denominators differ; rows above are not comparable to a run on the current ladder.

## How to read

Crucible reports per-engine results, not one scalar score. Record the headline metric for each engine — `C1` NIAH cells passed, `C2` challenges passed, `C3` JSON-compliance level reached. A model's row summarizes its scores; the full breakdown stays in `scorecards/<model>.md`.

| Model | Quant | KV cache | ctx | C1 NIAH | C2 reasoning | C3 structured |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | UD-IQ4_XS | q8_0 | 262144 | 77/77 (100.0%) | 11/13 (84.6%) | 2/3 (1 partial) |
| Qwen3.6-35B-A3B | UD-IQ4_XS | q4_0 | 262144 | 77/77 (100.0%) | 10/13 (76.9%) | 2/3 (1 partial) |

- `Model` and `Quant` are named as in the main [README](../../README.md) model tables, so a checkpoint can be added as its own row.
- `C1` is cells passed out of the **fitted** cell count for that row's served context — the pinned ladder is 8 context sizes (16k → 512k) × 5 depths = 40 cells, trimmed so no cell exceeds the served context (a 512k prefill must also stay inside the timeout); `C2` challenges passed out of 13; `C3` schema levels compliant out of 3.
- `KV cache` is the served KV-cache type (`--cache-type-k` / `--cache-type-v`); the MTP draft cache is held at q8_0 throughout. A C3 penalty figure varies run to run and is not comparable between rows.
- `ctx` is the context size the row was measured at.
- Suite-wide rules — the engine exclusions and why timing and energy are not recorded — are in the [suite README](README.md).

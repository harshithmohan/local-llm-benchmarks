# Consolidated score card — crucible

One row per model + engine set. Per-model detail (engine results, capability verdicts, run
time, notes) is in `scorecards/<model>.md`; raw run logs under `results/` are deleted once
recorded — the scorecards are the persistent record. The Crucible harness does **not** follow
this repo's timing protocol, so these numbers are **not comparable to the model-card timing
rows** (see README → Protocol deviations).

## How to read

Crucible reports per-engine results, not one scalar score. Record the headline metrics for each
engine that ran (`C1` NIAH cells passed, `C2` challenges passed, `C3` JSON-compliance level
reached), the engines selected, and any deviation from a default run (thinking on/off per
engine). A model's row summarizes the engines run; the full breakdown stays in
`scorecards/<model>.md`.

| Model | Engines run | C1 NIAH | C2 reasoning | C3 structured | Notes | Time |
|---|---|---|---|---|---|---|
| qwen36-35b-iq4xs | C1, C2, C3 | 66/77 (85.7%) | 11/13 (84.6%) | 2/3 (1 partial) | **Suite set** (2026-10-10, Rig 1 RTX 3060, binary v0.1.3; cold load inside Crucible's internal warmup). C1/C3 run with thinking **disabled** (`--reasoning off`); with the model's default thinking they scored 5/77 and 0/3 — a harness artifact, not a capability verdict (C1 counts reasoning chunks, C3 reads content chunks only). C2 ran on the default serving config (thinking on). VRAM ~91%. | — |

## Notes

- `C1` is reported as cells passed out of 77 (7 context sizes × 11 depths); `C2` as
  challenges passed out of 13; `C3` as schema levels compliant out of 3.
- Run time is wall-clock for the whole headless run, including model load.
- **Thinking is disabled for C1 and C3** (the target server is started with `--reasoning off`):
  both engines' generation caps are tight and they treat the reasoning channel differently, so
  a thinking model fails them for reasons unrelated to capability. `C2` keeps the model's
  default — it is meant to exercise reasoning.
- Timing and energy are deliberately **not** recorded here: Crucible's speed / concurrency /
  flat-out engines are excluded from this suite, and its energy engine reports a whole-window
  estimate rather than a per-token figure (see README → Engines). Prefill and decode numbers
  live on the model cards.

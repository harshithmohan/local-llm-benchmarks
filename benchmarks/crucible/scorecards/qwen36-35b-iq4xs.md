# qwen36-35b-iq4xs — crucible results

Parameter set: default serving config (`--ctx-size 262144`), with **thinking disabled for C1/C3**
(see Notes). Endpoint: Rig 1 (RTX 3060). Binary: crucible-llm v0.1.3.

> Engines run: C1, C2, C3 (suite set).

## Run

**2026-10-10** · suite set C1, C2, C3 across two headless runs: C2 against the registered
serving config (thinking on), C1 and C3 against a direct server started with `--reasoning off`.
Cold load happened inside Crucible's internal warmup; the model was resident at ~11.8 / 12.9 GB
(~91%) VRAM.

## Engine results

| Engine | Metric | Result |
|---|---|---|
| C1 · NIAH | cells passed | 66 / 77 (85.7%) |
| C2 · Reasoning | challenges passed | 11 / 13 (84.6%) |
| C3 · Structured | JSON-compliance level | 2 / 3 compliant, 1 partial |
| C3 · Structured | grammar penalty | -20.1% |

## Capability verdicts

- **Long-context retrieval (C1):** 66 / 77 cells retrieved (85.7%) across the 7 context sizes
  (2k → 128k) × 11 depths, with thinking disabled.
- **Reasoning (C2):** 11 / 13 solved (84.6%), avg 85.9 t/s across the challenges (thinking on).
- **Structured output (C3):** 2 / 3 schema levels compliant, 1 partial, with thinking disabled;
  grammar penalty -20.1%.

## Notes

- **Thinking off for C1/C3.** Crucible caps generation per engine (NIAH 64, structured 256,
  reasoning 512 tokens) and its engines differ on the reasoning channel: C1 counts
  `reasoning`/`reasoning_content` chunks as the answer, while C3 reads content chunks **only**.
  With the model's default (thinking on) it streamed 256/256 reasoning chunks and 0 content, and
  scored **C1 5/77, C3 0/3** — a harness artifact, not a capability result. Re-run with
  `--reasoning off` on the server, the same checks scored **C1 66/77 and C3 2/3** (above).
- **C2 keeps thinking on** — it is meant to exercise reasoning, and its 512-token cap is wide
  enough for the challenges.
- **Timing and energy are not recorded here.** Crucible's speed/flat-out engines are excluded
  (the speed engine's "prefill t/s" is `prompt_tokens / TTFT` over a fixed ~45-token prompt, and
  flat-out at one stream merely restates its decode rate); real prefill and decode numbers live
  on the model card, which uses this repo's protocol. The energy engine is excluded because its
  J/token is a whole-window estimate, not a per-token measurement (see the suite README →
  Engines).
- C1 per-cell detail is **not persisted** (Crucible's `needle_evaluations` table is empty); only
  the 66/77 aggregate is available.

Raw run logs: `results/qwen36-35b-iq4xs/` (C2) and `results/qwen36-35b-iq4xs-nothink/`
(C1, C3) — deleted once this card is recorded.

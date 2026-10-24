<!-- Scorecard template — copy to scorecards/<model>.md and fill in.

Shape: ONE CARD PER MODEL (not per model + quant) — title -> `Parameter set:` line -> optional blockquote -> one section per parameter set / reasoning level -> ## Summary last. Keep the section order, and keep a heading (marked "not run") rather than deleting it. Where two rigs serve near-identical quants of one model, bench one and mark the other "not run (duplicate of <quant>)".

ONE TRAJECTORY per model per quant/level paramset: a clean-base implementation run (Stage 0), then up to TWO review-driven repair rounds in the SAME opencode session (each followed by re-checking gates + harness, giving Stage 1 and Stage 2). Maximum 3 stages. There are NO repeats, NO median and NO mean — every model runs the same single trajectory, self-hosted or cloud alike.

Converged = the build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) all pass AND the Playwright harness (37 assertions, benchmarks/shoko-logs/harness/) is 37/37. Record the outcome as `converged: stage 0` (green on the first run, no review needed), `converged: stage 1`, `converged: stage 2`, or `not converged` (still failing after two review rounds — a real, publishable result that is never re-run or averaged).

A card records the model under test and what it produced — nothing about the apparatus used to grade it.

Each stage reports TWO independent scores, never summed: **Score A** (ticket conformance, lines A1–A21, graded from `prompt.md` only) and **Score B** (robustness & reference fidelity, lines B1–B11). Build gates are a precondition, shown ✅/❌, never points. Per stage also record the harness result (`x/37`) and model time (that stage's implementation run — harness and grading time are excluded). The `Context:` line carries the model's own billion-context calls for that stage as `<n> compress · <n> decompress` — the stage's own count, never a running total. Run totals and the **final** context usage (the prompt size at the end of the last stage, never a peak) live in the Summary table's `Compress` / `Decompress` / `Final context` columns. Served context size and output cap are apparatus, not quality: they do not appear in the card. A zero-work stop does change how a stage reads, so it goes on the stage's `Flags:` line — and only when one actually happened. A genuine environment failure (dropped socket -> 0-byte patch, model server unloaded mid-run) is NOT recorded: the stage is re-run. A stage whose build is **red** cannot carry a Score-A number (`rubric.md`): write `N/G` for that stage's Score A — in the body and in the per-stage table — never a number. Its Score-B side is still a number, but over the **reduced denominator**: write `<n> / <m>` with the denominator shown (e.g. `74 / 82`; `82` is every gradeable B line, B2 and B11 being the only ungradeable ones). A red-build cell in any published table is therefore the three-part form `N/G · <n> / <m>` (e.g. `N/G · 74 / 82`) — never `/ 100` (the B denominator is below 100) and never a bare `N/G` on the B side. Green builds are unaffected.

Run provenance — the **runner hash** (`run.json.runner_sha256`), the **config hash** (`run.json.config_sha256`), the **opencode version** plus binary sha256 (`run.json.opencode`) and the **base commit** (`run.json.pins.run_base_commit`) — stays in the run's `run.json`. It is not restated in the card.

Two tables per card, at two levels of detail. The headline tables (the card header row and the Summary's first table) keep only the **final score** (`Final A/B`) and the **total model time** (the sum of the stage model times). Every per-stage figure — each stage's Score A, Score B, harness result and model time — lives in the separate **per-stage table** and in that stage's body section. Write `—` for a stage the trajectory never reached.

Maintainer spot-check corrections go bolded in the row's Notes and again in a blockquote under the header line.

Public file: no host / ssh / docker / absolute-path ops info. -->

# <model> — scores

Model: `<model family>`.

<!-- Final A/B is the card's highest level of detail: green build -> `<A> / <B>`; red build -> `N/G · <n> / <m>` (e.g. `N/G · 74 / 82`), the same three-part form as scorecard.md's per-stage cells. Never `/ 100` on a red build, and never a bare `N/G` on the B side. -->

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| <quant> | <level> | converged: stage <0\|1\|2> \| not converged | | | ✅ tscheck · ✅ lint · ✅ build | |

> <optional blockquote: retired notice / maintainer correction>

## <Quant> — <Level> reasoning

<!-- Hosted model with no quant: drop the quant half — `## <Level> reasoning` — never `## — <Level> reasoning`. -->

Parameter set: <paramset + level — stated in full here, since the header row carries only quant and level; repeat only when a later section differs>.

### Stage 0 — initial run
- Model time:
- Gates: ✅ / ❌
- Harness: x/37
- Score A: /100   Score B: /100
- Context: <n> compress · <n> decompress
- Flags:
- Findings:
  - <one finding per bullet, bold lead-in — what scored, what broke, and the line ids it moved>

### Review round 1 → Stage 1
<!-- omit this whole round if the trajectory converged at stage 0 -->
- Review prompt (verbatim — the run directory's `review-s<stage>.md`):
- Model time:      Gates:      Harness: x/37      Score A: /100   Score B: /100
- Context: <n> compress · <n> decompress
- Flags:
- Findings:
  - <one finding per bullet, bold lead-in — what scored, what broke, and the line ids it moved>

### Review round 2 → Stage 2
<!-- only if stage 1 was not converged -->
- Review prompt (verbatim — the run directory's `review-s<stage>.md`):
- Model time:      Gates:      Harness: x/37      Score A: /100   Score B: /100
- Context: <n> compress · <n> decompress
- Flags:
- Findings:
  - <one finding per bullet, bold lead-in — what scored, what broke, and the line ids it moved>

**Outcome:** converged: stage <0|1|2> | not converged — <one line>

## Summary

One row per parameter set — the outcome, the final score, the total model time, and the run totals for the model's own context calls plus the final context usage:

<!-- Final A / Final B, one column each: green build -> a number in each; red build -> `N/G` beside `<n> / <m>` with the reduced denominator (e.g. `N/G` and `74 / 82`). The card-header row above carries the same pair joined as the `Final A/B` cell. Never `/ 100` on a red build. -->

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|---|---|
| <quant> | <level> | | | | | | | <used> / <served> (<pct>%) |

Per-stage detail — one row per stage the trajectory actually ran (`—` for stages not reached):

<!-- Score A: a number, or `N/G` on a red build. Score B: a number, or `<n> / <m>` with the reduced denominator on a red build (e.g. `74 / 82` — never `/ 100`). Same rule in the stage body's `Score A: /100   Score B: /100` lines. -->

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|---|
| <quant> | 0 | | | x/37 | ✅ / ❌ | | | |
| <quant> | 1 | | | x/37 | ✅ / ❌ | | | |
| <quant> | 2 | | | x/37 | ✅ / ❌ | | | |

<bullets, one list per quant — not a paragraph: what the model got right cold (Stage 0), what the review rounds fixed (the Stage 0 -> Stage 1/2 deltas), what never converged, and the total model time (the sum of the stage model times, Stage 0 -> the stage that converged; harness and grading time are not counted — the figure measures the model producing code, not the apparatus measuring it). Keep them short enough to scan: one finding per bullet, bold lead-in, and prefer a delta or a comparison over re-stating a number the tables above already carry.>

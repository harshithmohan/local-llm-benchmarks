<!--
Scorecard template — copy to scorecards/<model>.md and fill in.

Shape: ONE CARD PER MODEL (not per model + quant) — title -> `Parameter set:` line -> optional
blockquote -> one section per parameter set / reasoning level -> ## Summary last. Keep the
section order, and keep a heading (marked "not run") rather than deleting it. Where two rigs
serve near-identical quants of one model, bench one and mark the other
"not run (duplicate of <quant>)".

ONE TRAJECTORY per model per quant/level paramset: a clean-base implementation run (Stage 0),
then up to TWO reviewer-driven repair rounds in the SAME opencode session (each followed by
re-checking gates + harness, giving Stage 1 and Stage 2). Maximum 3 stages. There are NO
repeats, NO median and NO mean — every model runs the same single trajectory, self-hosted or
cloud alike.

Converged = the build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) all pass AND the
Playwright harness (37 assertions, benchmarks/shoko-logs/harness/) is 37/37. Record the
outcome as `converged: stage 0` (green on the first run, no review needed), `converged: stage 1`,
`converged: stage 2`, or `not converged` (still failing after two review rounds — a real,
publishable result that is never re-run or averaged).

Two roles, kept separate:
- Reviewer — writes the next round's follow-up prompt. Its inputs: the ticket (`prompt.md`), the
  candidate's diff, the harness failure report (sanitized to spec titles + observed symptoms;
  never selector internals) and its own reading of the candidate's code. It must NOT read
  `reference.diff` or `rubric.md`. Fixed-shape follow-up: at most 5 findings, ordered by
  severity, symptoms and expected behaviour only — it says what does not work, never the fix; no
  code, no rubric line references, and no `file:line` (or file paths) unless absolutely required;
  for a wrong approach it describes the intended behaviour, not the exact change. Record
  each round's review text verbatim.
- Judge — grades each stage independently against `rubric.md`, blind to the
  review text and to the other stages' score sheets.

Both roles are **pinned**: the card records the reviewer's model and variant and the judge's.
The review text is what drives a repair round, so a trajectory measures the model *and* its
reviewer — a result is only comparable to another produced by the same reviewer, and a card that
does not name one is not comparable to anything.

It reports TWO independent scores per stage, never summed: **Score A** (ticket conformance,
lines A1–A21, graded from `prompt.md` only) and **Score B** (robustness & reference fidelity,
lines B1–B11). Build gates are a precondition, shown ✅/❌, never points. Per stage also record
the harness result (`x/37`), model time (that stage's implementation run — harness and grading
time are excluded), and context size. Per stage, record an output-cap note: every model is served
with an output cap, and opencode resumes a turn that stopped unimplemented **at the cap**,
nudging it to start implementing, at most twice — the runner adds no nudge of its own. A
genuine environment failure (dropped socket -> 0-byte patch, model server unloaded mid-run) is
NOT recorded: the stage is re-run. A stage whose build is **red** cannot carry a Score-A number
(`rubric.md`): write `N/G` for that stage's Score A — in the body and in the per-stage table —
never a number. Its Score-B side is still a number, but over the **reduced denominator**: write
`<n> / <m>` with the denominator shown (e.g. `74 / 82`; `82` is every gradeable B line, B2 and B11
being the only ungradeable ones). A red-build cell in any published table is therefore the
three-part form `N/G · <n> / <m>` (e.g. `N/G · 74 / 82`) — never `/ 100` (the B denominator is
below 100) and never a bare `N/G` on the B side. Green builds are unaffected.

Per parameter set, record the **runner hash** (`run.json.runner_sha256` — the runner ships no
semantic version constant), the **config hash** (`run.json.config_sha256`, the sha256 of
`shoko.config.json`), the **opencode version** plus binary sha256 (`run.json.opencode`), and the
**base commit** the run tree was built from (`run.json.pins.run_base_commit`).

Two tables per card, at two levels of detail. The headline tables (the card header row and the
Summary's first table) keep only the **final score** (`Final A/B`) and the **total model time**
(the sum of the stage model times). Every per-stage figure — each stage's Score A, Score B,
harness result and model time — lives in the separate **per-stage table** and in that stage's body
section. Write `—` for a stage the trajectory never reached.

Maintainer spot-check corrections go bolded in the row's Notes and again in a blockquote under
the header line.

Public file: no host / ssh / docker / absolute-path ops info.
-->

# <model> — scores

Model: `<model id>`. One trajectory per quant/level (Stage 0 + up to two reviewer-driven rounds). One card per model — it covers every quant of `<model>`; quants are rows, not separate cards.

Reviewer: `<reviewer model#variant>` · Judge: `<judge model#variant>` — pinned for the whole card; a trajectory is only comparable to another run with the same reviewer.

Run provenance (per parameter set): runner version `<run.json.runner_sha256, first 12>` · config hash `<run.json.config_sha256, first 12>` · opencode `<version> (<sha256, first 12)>`.

<!-- Final A/B is the card's highest level of detail: green build -> `<A> / <B>`; red build ->
`N/G · <n> / <m>` (e.g. `N/G · 74 / 82`), the same three-part form as scorecard.md's per-stage
cells. Never `/ 100` on a red build, and never a bare `N/G` on the B side. -->

| Quant | Param set | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|---|
| <quant> | <paramset, e.g. kv-q8 / w4a16 fp8 KV / Strata int8 KV> | <level> | converged: stage <0\|1\|2> \| not converged | | | ✅ tscheck · ✅ lint · ✅ build | |

> <optional blockquote: retired notice / maintainer correction>

## <Quant> — <Level> reasoning

Parameter set: <paramset + level — as in the row above; repeat only when a later section differs>.

### Stage 0 — initial run
- Model time:
- Gates: ✅ / ❌
- Harness: x/37
- Score A: /100   Score B: /100
- Flags: context size:
- Findings:

### Review round 1 → Stage 1
<!-- omit this whole round if the trajectory converged at stage 0 -->
- Review prompt (verbatim — the run directory's `review-s<stage>.md`):
- Model time:      Gates:      Harness: x/37      Score A: /100   Score B: /100
- Flags:
- Findings:

### Review round 2 → Stage 2
<!-- only if stage 1 was not converged -->
- Review prompt (verbatim — the run directory's `review-s<stage>.md`):
- Model time:      Gates:      Harness: x/37      Score A: /100   Score B: /100
- Flags:
- Findings:

**Outcome:** converged: stage <0|1|2> | not converged — <one line>

## Summary

One row per parameter set — the outcome, the final score and the total model time only:

<!-- Final A / Final B, one column each: green build -> a number in each; red build -> `N/G` beside
`<n> / <m>` with the reduced denominator (e.g. `N/G` and `74 / 82`). The card-header row above
carries the same pair joined as the `Final A/B` cell. Never `/ 100` on a red build. -->

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) |
|---|---|---|---|---|---|
| <quant> | <level> | | | | |

Per-stage detail — one row per stage the trajectory actually ran (`—` for stages not reached):

<!-- Score A: a number, or `N/G` on a red build. Score B: a number, or `<n> / <m>` with the
reduced denominator on a red build (e.g. `74 / 82` — never `/ 100`). Same rule in the stage body's
`Score A: /100   Score B: /100` lines. -->

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) |
|---|---|---|---|---|---|---|
| <quant> | 0 | | | x/37 | ✅ / ❌ | |
| <quant> | 1 | | | x/37 | ✅ / ❌ | |
| <quant> | 2 | | | x/37 | ✅ / ❌ | |

<one paragraph per quant: what the model got right cold (Stage 0), what the review rounds fixed (the Stage 0 -> Stage 1/2 deltas), what never converged, and the total model time (the sum of the stage model times, Stage 0 -> the stage that converged; harness, reviewer and judge time are not counted — the figure measures the model producing code, not the apparatus measuring it).>

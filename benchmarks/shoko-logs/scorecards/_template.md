<!-- Scorecard template — copy to `scorecards/<model>-<quant>.md` for a local GGUF or `scorecards/<model>.md` for a hosted model with no quant, and fill in.

Shape: ONE CARD PER QUANT — one file per model + quant. Name it `scorecards/<model>-<quant>.md`, the quant lowercased with underscores dropped (`ud-iq4xs`, `iq3xxs`, `apex-i-compact`, `ud-q4kxl`). Two quants of one model are two cards with two headline rows in `scorecard.md` — never two sections of one card. A quant that has not been benched has no card at all: no "not run" stubs, no placeholder headings. Where two rigs serve near-identical quants of one model (e.g. the two `qwen36` builds), bench one and give the other no card.

Order, single-level card: title -> `Model:` line -> `Parameter set:` line -> headline row -> optional blockquote -> `## Stage 0` -> `## Review round 1 → Stage 1` -> `## Review round 2 → Stage 2` -> `**Outcome:**` -> `## Summary` last. Multi-level card: the same, wrapped in one `## <level> reasoning` block per level — stages and the Summary both demoted to `### ` inside it, so a card with two levels holds two summaries.

REASONING-LEVEL HEADINGS: a model benched at, or expected to be benched at, more than one reasoning level for the same quant keeps one `## <level> reasoning` section per level (level lowercased: `default`, `high`, `xhigh`), each carrying its own `Parameter set:` line, its stages demoted to `### `, and a `### Summary` at its end (Summary always matches its stages' level). A single-level card has no level heading: stages sit at `## ` and the `Parameter set:` line carries the level. Quant never appears in a heading — it is in the title and the `Parameter set:` line.

ONE TRAJECTORY per parameter set (a single-level card, or one level section inside a multi-level card): a clean-base implementation run (Stage 0), then up to TWO review-driven repair rounds in the SAME opencode session (each followed by re-checking gates + harness, giving Stage 1 and Stage 2). Maximum 3 stages. There are NO repeats, NO median and NO mean — every model runs the same single trajectory, self-hosted or cloud alike.

Converged = the build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) all pass AND the Playwright harness (37 assertions, benchmarks/shoko-logs/harness/) is 37/37. Record the outcome as `converged: stage 0` (green on the first run, no review needed), `converged: stage 1`, `converged: stage 2`, or `not converged` (still failing after two review rounds — a real, publishable result that is never re-run or averaged).

A card records the model under test and what it produced — nothing about the apparatus used to grade it.

Each stage reports TWO independent scores, never summed: **Score A** (ticket conformance, lines A1–A21, graded from `prompt.md` only) and **Score B** (robustness & reference fidelity, lines B1–B11). Build gates are a precondition, shown ✅/❌, never points. Per stage also record the harness result (`x/37`) and model time (that stage's implementation run — harness and grading time are excluded). The `Context:` line carries the model's own billion-context calls for that stage as `<n> compress · <n> decompress` — the stage's own count, never a running total. Run totals and the **final** context usage (the prompt size at the end of the last stage, never a peak) live in the Summary table's `Compress` / `Decompress` / `Final context` columns. Served context size and output cap are apparatus, not quality: they do not appear in the card, beyond the `Parameter set:` line naming ctx and out-cap as the parameter set's identity. A zero-work stop does change how a stage reads, so it goes on the stage's `Flags:` line — and only when one actually happened. A genuine environment failure (dropped socket -> 0-byte patch, model server unloaded mid-run) is NOT recorded: the stage is re-run. A stage whose build is **red** cannot carry a Score-A number (`rubric.md`): write `N/G` for that stage's Score A — in the body and in the per-stage table — never a number. Its Score-B side is still a number, but over the **reduced denominator**: write `<n> / <m>` with the denominator shown (e.g. `74 / 82`; `82` is every gradeable B line, B2 and B11 being the only ungradeable ones). A red-build cell in any published table is therefore the three-part form `N/G · <n> / <m>` (e.g. `N/G · 74 / 82`) — never `/ 100` (the B denominator is below 100) and never a bare `N/G` on the B side. Green builds are unaffected.

Run provenance — the **runner hash** (`run.json.runner_sha256`), the **config hash** (`run.json.config_sha256`), the **opencode version** plus binary sha256 (`run.json.opencode`) and the **base commit** (`run.json.pins.run_base_commit`) — stays in the run's `run.json`. It is not restated in the card.

Two tables per card, at two levels of detail. The headline row keeps only the **final score** (`Final A/B`) and the **total model time** (the sum of the stage model times), mirroring the card's row in `scorecard.md`. Every per-stage figure — each stage's Score A, Score B, harness result and model time — lives in the separate **per-stage table** and in that stage's body section. Write `—` for a stage the trajectory never reached.

Maintainer spot-check corrections go bolded in the row's Notes and again in a blockquote under the header line.

Public file: no host / ssh / docker / absolute-path ops info. -->

# <model> · <Quant> — scores

<!-- Hosted model with no quant: `# <model> — scores` — never `# <model> · — scores`. -->

Model: `<model family>`.

<!-- The parameter set completes this card's identity: the title names model + quant, so state the quant, the served model id, the level and ctx/out-cap once here — in a multi-level card, once per level section instead of here. -->

Parameter set: <quant> (`<served model id>`), <level> reasoning level, <ctx> ctx / <out-cap> out-cap.

<!-- Hosted model: `Parameter set: no quant (hosted model, `<served model id>`), <level> reasoning level.` -->

<!-- One row per reasoning level — a single row for a single-level card. The cell carries the final score in the same form as the per-stage table below. -->

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| <quant> | <level> | converged: stage <0\|1\|2> \| not converged | | | ✅ tscheck · ✅ lint · ✅ build | |

> <optional blockquote: retired notice / maintainer correction>

<!-- Multi-level card only — one such block per level, in place of the flat stage sections below (copy their Stage 0–2 bodies and the Summary at the tail, everything demoted to `### `; every section ends with its own Summary):

## <level> reasoning

Parameter set: <quant> (`<served model id>`), <level> reasoning level, <ctx> ctx / <out-cap> out-cap.

### Stage 0 — initial run
...
### Summary
-->

## Stage 0 — initial run
- Model time:
- Gates: ✅ / ❌
- Harness: x/37
- Score A: /100   Score B: /100
- Context: <n> compress · <n> decompress
- Flags:  <!-- omit the line when no flag actually happened -->
- Findings:
  - <one finding per bullet, bold lead-in — what scored, what broke, and the line ids it moved>

## Review round 1 → Stage 1
<!-- omit this whole round if the trajectory converged at stage 0 -->
- Review prompt (verbatim — the run directory's `review-s<stage>.md`):
- Model time:      Gates:      Harness: x/37      Score A: /100   Score B: /100
- Context: <n> compress · <n> decompress
- Flags:
- Findings:
  - <one finding per bullet, bold lead-in — what scored, what broke, and the line ids it moved>

## Review round 2 → Stage 2
<!-- only if stage 1 was not converged -->
- Review prompt (verbatim — the run directory's `review-s<stage>.md`):
- Model time:      Gates:      Harness: x/37      Score A: /100   Score B: /100
- Context: <n> compress · <n> decompress
- Flags:
- Findings:
  - <one finding per bullet, bold lead-in — what scored, what broke, and the line ids it moved>

**Outcome:** converged: stage <0|1|2> | not converged — <one line>

## Summary

The card's outcome, final score, total model time, and the run totals for the model's own context calls plus the final context usage. It sits at the same heading level as the stages it closes — `## ` on a single-level card, `### ` inside a level section — so a multi-level card closes each level with its own Summary. A card gains a `Level` column here and in the per-stage table once it holds a second level section; until then it has neither:

<!-- Final A / Final B, one column each: green build -> a number in each; red build -> `N/G` beside `<n> / <m>` with the reduced denominator. The headline row carries the same pair joined as `Final A/B`. -->

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| | | | | | | <used> / <served> (<pct>%) |

Per-stage detail — one row per stage the trajectory actually ran (`—` for stages not reached):

<!-- Score A: a number, or `N/G` on a red build. Score B: a number, or `<n> / <m>` with the reduced denominator (e.g. `74 / 82`). Same rule in the stage body's `Score A: /100   Score B: /100` lines. -->

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | | | x/37 | ✅ / ❌ | | | |
| 1 | | | x/37 | ✅ / ❌ | | | |
| 2 | | | x/37 | ✅ / ❌ | | | |

<!-- Bullets, not a paragraph: what the model got right cold (Stage 0), what the review rounds fixed (the Stage 0 -> Stage 1/2 deltas), what never converged, and the total model time (the sum of the stage model times, Stage 0 -> the stage that converged; harness and grading time are not counted — the figure measures the model producing code, not the apparatus measuring it). Keep them short enough to scan: one finding per bullet, bold lead-in, and prefer a delta or a comparison over re-stating a number the tables above already carry. -->

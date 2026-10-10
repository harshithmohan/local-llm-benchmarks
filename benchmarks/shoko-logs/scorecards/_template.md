<!--
Scorecard template — copy to scorecards/<model>.md and fill in.

Shape: title -> parameter-set line -> optional blockquote -> one section per parameter set /
reasoning level -> ## Summary last. Keep the section order, and keep a heading (marked
"not run") rather than deleting it.

Variants in use:
- 2-repeat models (self-hosted): a `## <Level> reasoning` section per level, with
  `### Repeat 1 of 2` / `### Repeat 2 of 2` inside, a rubric table and `**Key findings:**`
  per repeat, then `## Summary`.
- One parameter set and no reasoning-level variation: `## Run — <YYYY-MM-DD>` in place of
  the level heading.
- opencode-go (cloud) reference models: a single run per level — `## Single run (<level>
  reasoning)` (or `## Single run` when the model exposes no levels), the `**Total ...**`
  line directly under it (no `### Repeat`), and no `## Summary` (the header line and the
  capability subtotals already carry it).

Row weights come from rubric.md (gates 1-3 = 5 pts, lines 4-25 = 95 pts). A `Pts` column
carrying the weighted points per line is an accepted variant — some cards have it, some
do not. Maintainer spot-check corrections go bolded in the row's Notes and again in a
blockquote under the header line.

Public file: no host / ssh / docker / absolute-path ops info.
-->

# <model-id> — scores

Parameter set: <paramset, e.g. kv-q8 / w4a16 fp8 KV / Strata int8 KV>. <2-repeat mean | 1 run per reasoning level (cloud)>.

> <optional blockquote: retired notice / output-limit nudge / auto-compaction / maintainer correction>

## <Level> reasoning

Parameter set: <paramset + level — only when it differs from the line above>.

### Repeat 1 of 2

**Total <n>/100** — gates 5/5 · rubric <n>/95 · <t> min · <YYYY-MM-DD>.

| # | Score | Notes |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 8 | | |
| 9 | | |
| 10 | | |
| 11 | | |
| 12 | | |
| 13 | | |
| 14 | | |
| 15 | | |
| 16 | | |
| 17 | | |
| 18 | | |
| 19 | | |
| 20 | | |
| 21 | | |
| 22 | | |
| 23 | | |
| 24 | | |
| 25 | | |

**Key findings:** <what the run got right, the load-bearing break, the misses it shares with the other repeat>.

### Repeat 2 of 2

**Total <n>/100** — gates 5/5 · rubric <n>/95 · <t> min · <YYYY-MM-DD>.

| # | Score | Notes |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 8 | | |
| 9 | | |
| 10 | | |
| 11 | | |
| 12 | | |
| 13 | | |
| 14 | | |
| 15 | | |
| 16 | | |
| 17 | | |
| 18 | | |
| 19 | | |
| 20 | | |
| 21 | | |
| 22 | | |
| 23 | | |
| 24 | | |
| 25 | | |

**Key findings:** <...>

## Summary

| Repeat | Rubric /95 | Total /100 | Run time (min) |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| **Mean** | | | |

<one paragraph: the mean total, what both repeats share, the per-repeat divergence, and the spread in points.>

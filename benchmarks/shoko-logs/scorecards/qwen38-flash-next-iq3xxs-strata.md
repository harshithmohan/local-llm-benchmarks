# qwen38-flash-next-iq3xxs-strata — scores

Line weights mirror `rubric.md` (gates 1–3 = 5 pts; lines 4–25 = 95 pts).

## Xhigh reasoning

Parameter set: Strata, int8 KV, xhigh reasoning (GSQ-RCO IQ3_XXS quant, 200k ctx,
`--prefill auto` @ 95% lend cap → 5632 chunk, MTP on).

### Repeat 1 of 2

**Total 67/100** — gates 5/5 · rubric 62/95 · 24.3 min · 2026-10-10.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | No reconnect handler resets the live tail; backlog and individual log events append in `src/core/react-query/logs/queries.ts`. |
| 5 | 1 | `Range/Read` uses ascending order, `offset`/`limit` 100, singular `level`, `message`, and `NextOffset` pagination in `src/core/react-query/logs/queries.ts`. |
| 6 | 0.5 | Key includes filter content, but hashes the level array in toggle order (`src/pages/logs/LogsPage.tsx`); it is not order-independent. |
| 7 | 0.5 | Wraps non-empty search as case-insensitive `c#:` contains, but never passes valid DSL prefixes through (`src/core/react-query/logs/queries.ts:74-77`). |
| 8 | 1 | Empty level and message filters become `undefined` (`src/core/react-query/logs/queries.ts:74-77`). |
| 9 | 1 | Trimmed, debounced search or selected levels switches between live tail and server results (`src/pages/logs/LogsPage.tsx:167-185`). |
| 10 | 0.5 | Six levels are toggleable with active styling, but chips have no tooltip (`src/pages/logs/LogsPage.tsx:377-388`). |
| 11 | 1 | Search is debounced for 250 ms and trimmed before use (`src/pages/logs/LogsPage.tsx:167-171`). |
| 12 | 1 | Clear resets search and levels; `useDebounceValue` cancels the pending timer; scroll lock is hidden while filters are active (`src/pages/logs/LogsPage.tsx:232-235,365-375`). |
| 13 | 0 | Header only says "Logs"; it does not show live-tail count or search-mode hint (`src/pages/logs/LogsPage.tsx:341-344`). |
| 14 | 0.5 | Retains the prior throttled scroll-direction heuristic; it can unlock on scroll-up but does not robustly distinguish user scroll from virtualizer/programmatic movement (`src/pages/logs/LogsPage.tsx:56-59,84-88`). |
| 15 | 0 | No live-container `scrollRect` sizing workaround is applied to the virtualizer (`src/pages/logs/LogsPage.tsx:184-191`). |
| 16 | 1 | Empty live tail renders a spinner, which disappears when rows exist (`src/pages/logs/LogsPage.tsx:273-288`). |
| 17 | 0.5 | Reaching the trailing row schedules a fetch, but invokes the debounce during render (`src/pages/logs/LogsPage.tsx:237-244`) and adds an unnecessary delay. |
| 18 | 0.5 | Concatenates pages in order and renders timestamp, level, message, and exception, but drops returned logger/caller fields (`src/pages/logs/LogsPage.tsx:181-185,237-259`). |
| 19 | 0.5 | Has a full-height initial search state and no-results Clear filters action; next-page loading is outside the virtual list rather than a phantom row (`src/pages/logs/LogsPage.tsx:263-309`). |
| 20 | 1 | Switches current-file/range download correctly and sends singular `level` and `message` params (`src/core/react-query/logs/mutations.ts:27-35`; params helper at `src/core/react-query/logs/queries.ts:74-77`). |
| 21 | 0 | Download anchor is detached and object URL is revoked synchronously (`src/core/react-query/logs/mutations.ts:16-23`). |
| 22 | 1 | Download button has a visible loading state and mutation failure shows an error toast (`src/pages/logs/LogsPage.tsx:354-360`; `src/core/react-query/logs/mutations.ts:44`). |
| 23 | 0 | Does not add or wire a `loading` prop on `IconButton`; download uses `Button` directly (`src/pages/logs/LogsPage.tsx:354-363`). |
| 24 | 0.5 | Removes the commented placeholder, but retains the legacy `logs/queries.ts` and `LogLineType`; no new unused exports/imports identified. |
| 25 | 0.5 | Defines `LogLevelValues` union for the chips, but `LogEntryType.Level` remains bare `string` instead of the union (`src/core/react-query/logs/types.ts:113-127`). |

Spot-check: all 22 line scores verified by the maintainer against `patch.diff` and cohort
precedent; no corrections. The run's implementation passed all three gates unassisted and
needed no nudge or auto-compaction.

**Key findings (r1):**

- Full read contract (5=1): `NextOffset` cursor, ascending pages, `limit` 100, singular
  `level`/`message` — plus a shared `buildLogFilterParams` helper used by both the read and
  download paths.
- Well-formed `c#:` wrap with no DSL passthrough (7=0.5), the cohort-standard position.
- Composition: `useDebounceValue` 250 ms + trim (11=1, 12=1); trailing-row pagination
  triggered from render through a 100 ms debounce (17=0.5, the `CollectionView.tsx`
  pattern); post-list spinner instead of a phantom loader row (19=0.5); scroll-lock button
  hidden under filters.
- Download: correct endpoint switch (20=1) with loading + error toast (22=1), but a
  detached anchor with synchronous `revokeObjectURL` (21=0).
- Shared cohort misses: no reconnect reset (4=0), bare header (13=0), unsorted level key
  (6=0.5), base scroll-lock heuristic (14=0.5), no `scrollRect` (15=0), no chip tooltips
  (10=0.5), Logger/Caller dropped from rows (18=0.5), legacy `logs/queries.ts` kept
  (24=0.5), `Level` bare `string` (25=0.5), `IconButton` loading absent (23=0).

### Repeat 2 of 2

**Total 68/100** — gates 5/5 · rubric 63/95 · 20.1 min · 2026-10-10.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | No reconnect handler resets the live tail; backlog and per-entry events append in `src/core/react-query/logs/queries.ts`. |
| 5 | 1 | `Range/Read` uses ascending order, `offset`/`limit` 100, singular `level`, `message`, and `NextOffset` pagination in `src/core/react-query/logs/queries.ts`. |
| 6 | 0.5 | Key includes filter content, but the level array is in toggle order (`src/pages/logs/LogsPage.tsx`); not order-independent. |
| 7 | 0.5 | Wraps non-empty search as case-insensitive `c#:` contains, but never passes valid DSL prefixes through. |
| 8 | 1 | Empty level and message filters become `undefined`. |
| 9 | 1 | Trimmed, debounced search or selected levels switches between live tail and server results. |
| 10 | 0.5 | Six levels are toggleable with active styling, but chips have no tooltip. |
| 11 | 1 | Search is debounced for 250 ms and trimmed before use. |
| 12 | 1 | `clearFilters` resets search and levels; the scroll-lock button is `disabled={filtersActive}` while filters are active (both rubric requirements met; grader's 0.5 corrected to 1). |
| 13 | 0 | Header only says "Logs"; no live-tail count or search-mode hint. |
| 14 | 0.5 | Retains the prior throttled scroll-direction heuristic; it can unlock on scroll-up but does not robustly separate user scroll from virtualizer movement. |
| 15 | 1 | Keeps the original `rowVirtualizer.scrollRect` sizing for the live container. |
| 16 | 1 | Empty live tail renders a spinner, gone once rows exist. |
| 17 | 0.5 | `handleScroll` fires a 100 ms-debounced `fetchNextPage` within 200 px of the bottom, plus an auto-fill effect; fetches do fire, but the debounce deviates from the reference's no-debounce trailing-row effect. |
| 18 | 0.5 | Concatenates pages in order and renders timestamp, level, message, exception; drops logger/caller/IDs. |
| 19 | 0.5 | Full-height initial search state and no-results Clear filters; next-page spinner sits outside the virtual list rather than a phantom row. |
| 20 | 1 | Switches current-file/range download correctly and sends singular `level` and `message` params. |
| 21 | 0 | Download anchor is detached and the object URL is revoked synchronously. |
| 22 | 1 | Download button has a visible loading state (`loading={isPending}`) and mutation failure shows an error toast. |
| 23 | 0 | No `loading` prop wired on `IconButton`. |
| 24 | 0.5 | Removes the commented placeholder, but retains the legacy `logs/queries.ts` and `LogLineType` (in use by the SignalR tail); no new unused exports/imports (grader's 0 corrected to 0.5 — it claimed a placeholder remained that the patch deletes). |
| 25 | 0.5 | `LogEntryType.Level` is the `LogLevelType` union, but the rendered `LogRowType.Level` stays bare `string`. |

Spot-check: grader scored 65/100; maintainer corrected two lines — 12 (0.5→1) and
24 (0→0.5) — bringing the rubric to 63/95 and the total to 68/100. The run passed all
three gates unassisted and needed no nudge or auto-compaction.

**Key findings (r2):**

- Same 4-file composition as r1. Keeps the original `rowVirtualizer.scrollRect` (15=1,
  where r1 scored 0).
- Pagination via a scroll handler: `handleScroll` fires a 100 ms-debounced `fetchNextPage`
  within 200 px of the bottom, plus an auto-fill effect while the list is shorter than the
  viewport (17=0.5, same as r1's render-phase trailing-row trigger).
- `LogEntryType.Level` is the `LogLevelType` union in the DTO, but the rendered
  `LogRowType.Level` is a bare `string` (25=0.5, same as r1 for a different reason).
- Download: correct endpoint switch (20=1) with `loading` + error toast (22=1), but a
  detached anchor with synchronous `revokeObjectURL` (21=0).
- `clearFilters` resets both filters and the scroll-lock button is `disabled` under filters
  (12=1).
- Shared cohort misses: no reconnect reset (4=0), bare header (13=0), unsorted level key
  (6=0.5), base scroll-lock heuristic (14=0.5), no chip tooltips (10=0.5), Logger/Caller
  dropped from rows (18=0.5), legacy `logs/queries.ts` + `LogLineType` kept (24=0.5),
  `IconButton` loading absent (23=0).

## Summary

| Reasoning | Repeat | Rubric /95 | Total /100 | Run time (min) |
|---|---|---|---|---|
| xhigh | r1 | 62 | 67 | 24.3 |
| xhigh | r2 | 63 | 68 | 20.1 |
| xhigh | **mean** | **62.5** | **67.5** | **22.2** |

Run time is wall-clock per run (fresh opencode session, start → last message), so it
includes model load. No nudges or auto-compactions in either repeat. Both repeats
recorded; this is the model's complete xhigh score.

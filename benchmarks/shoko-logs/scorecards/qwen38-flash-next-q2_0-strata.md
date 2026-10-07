# qwen38-flash-next-q2_0-strata — scores

Line weights mirror `rubric.md` (gates 1–3 = 5 pts; lines 4–25 = 95 pts).

## Low reasoning

Parameter set: Strata, int8 KV, low reasoning.

### Repeat 1 of 2

**Total 74.5/100** — gates 5/5 · rubric 69.5/95 · 17.7 min · 2026-10-07.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | SignalR appends backlog and entries only; there is no reconnect handler and no backlog/entry reset, so a reconnect cannot replace the stale tail. |
| 5 | 1 | `Range/Read`, offset paging with limit 100, `NextOffset`, `descending:false`, singular `level` + `message`. |
| 6 | 0.5 | Content-sensitive key, but the `levels` array is embedded unsorted, so toggle order changes it. |
| 7 | 0.5 | Well-formed case-insensitive `c#:` wrap with empty search omitted, but valid DSL prefixes are never passed through. |
| 8 | 1 | `buildFilterParams` supplies `undefined` for empty `level`/`message`. |
| 9 | 1 | Debounced non-empty search or any selected level switches the view from the live tail to server search. |
| 10 | 1 | Six toggleable levels with tooltips and distinct active/inactive styling. |
| 11 | 1 | `useDebounceValue(search, 250)` plus `trim()`. |
| 12 | 1 | Clear resets both filters; the scroll-lock button is disabled while filters are active. |
| 13 | 0 | Header reads only "Logs". |
| 14 | 0.5 | Base throttled scroll-direction heuristic; can unlock on virtualizer measurement scrolls. |
| 15 | 1 | `scrollRect` taken from live container dimensions (already present in the page). |
| 16 | 1 | Empty live tail renders a spinner. |
| 17 | 1 | `onScroll` proximity trigger (within 300 px of the end), no render-phase side effect and no debounce. |
| 18 | 0.5 | Pages flattened in order, but search rows render only timestamp/level/message, dropping Logger, Caller and Exception. |
| 19 | 0.5 | First-fetch "searching" state plus no-results with Clear filters; the next-page spinner sits below the virtualized list instead of being a phantom row. |
| 20 | 1 | `File/Current/Download` vs `Range/Download` switch; filtered download sends singular `level` + `message`. |
| 21 | 0.5 | Object URL with deferred revocation and a date/time filename, but the anchor is never attached to the DOM. |
| 22 | 1 | Visible `loading` on the download button plus an error toast on failure. |
| 23 | 0 | `IconButton` not extended with `loading`; the download button uses `Button`. |
| 24 | 0.5 | `LogLineType` and the commented search placeholders removed with no unused additions, but the old `logs/queries.ts` module is kept. |
| 25 | 0.5 | Event/result shapes modeled without `any`, but `LogEntryType.Level` is bare `string`. |

### Repeat 2 of 2

**Total 71.5/100** — gates 5/5 · rubric 66.5/95 · 15.7 min · 2026-10-07.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | SignalR appends backlog and entries only; there is no reconnect handler and no backlog reset, so a reconnect cannot replace the stale tail. **Spot-check 0.5 → 0.** |
| 5 | 1 | `Range/Read`, offset paging with limit `SEARCH_PAGE_SIZE` (100), `NextOffset`, `descending:false`, singular `level` + `message`. |
| 6 | 0.5 | Content-sensitive key (`[...logSearchQueryKey, request]`), but the embedded `levels` array is unsorted, so toggle order changes it. |
| 7 | 0.5 | Shared `buildLogFilterParams` forms a well-formed case-insensitive `c#:` contains and omits empty search, but valid DSL prefixes are never passed through. **Spot-check 0 → 0.5.** |
| 8 | 1 | Empty `level`/`message` omitted by the spread guards. |
| 9 | 1 | Debounced non-empty search or any selected level switches the view from the live tail to server search. |
| 10 | 1 | Six toggleable `LOG_LEVELS` chips with tooltips and distinct active/inactive styling. |
| 11 | 1 | `debounce(..., 250)` plus `trim()`. |
| 12 | 0.5 | Clear resets both filters and the scroll-lock button is disabled while filters are active, but the `useRef(debounce(...))` timer created on mount is never cancelled, so a pending commit can reapply stale text. **Spot-check 1 → 0.5.** |
| 13 | 0 | Header reads only "Logs". |
| 14 | 0.5 | Base throttled scroll-direction heuristic; can unlock on virtualizer measurement scrolls. |
| 15 | 1 | Live-container `scrollRect` applied to both the tail and search virtualizers. |
| 16 | 1 | Empty live tail renders a spinner. |
| 17 | 1 | `useEffect` on the last virtual item within 5 of the end calls `fetchNextPage`, so no render-phase side effect and no debounce. |
| 18 | 0.5 | Pages flattened in order, but search rows render only timestamp/level/message, dropping Logger, Caller and Exception. **Spot-check 1 → 0.5.** |
| 19 | 0.5 | First-fetch "searching" state plus no-results with Clear filters; the next-page spinner is a sibling div after the rows rather than a phantom virtual row. |
| 20 | 1 | `File/Current/Download` vs `Range/Download` switch via `hasFilters`; the filtered download sends singular `level` + `message`. |
| 21 | 0 | Detached anchor (never added to the DOM) and immediate `URL.revokeObjectURL`. |
| 22 | 1 | Download `IconButton` swaps to a spinning `mdiLoading` while pending; failures raise the error toast. |
| 23 | 0 | `IconButton` not extended with a `loading` prop; the icon swap lives in the page. |
| 24 | 0.5 | `LogLineType` and the commented search placeholders removed with no unused additions (`SEARCH_PAGE_SIZE` is used as the query limit), but the old `logs/queries.ts` module is kept. **Spot-check 0 → 0.5.** |
| 25 | 0.5 | `LogLevelType` union derived from `LOG_LEVELS`, no `any`, but `LogEntryType.Level` is bare `string`. |

**Key findings:**

- Both low repeats clear all three gates and discover the read contract (5=1 both: `NextOffset` cursor, ascending pages, singular `level`/`message`). Shared misses: reconnect replacement (4=0), header mode feedback (13=0), the unsorted level key (6=0.5), the base scroll-lock heuristic (14=0.5), `IconButton` loading (23=0), `Level` left a bare `string` (25=0.5), the legacy `logs/queries.ts` kept (24=0.5 both) and a well-formed `c#:` wrap with no DSL passthrough (7=0.5 both).
- r1 (74.5) uses `useDebounceValue`, which cancels the pending timer, so its Clear is correct (12=1) and it defers the object-URL revoke (21=0.5); r2 (71.5) builds a one-off `debounce()` in a ref that Clear never cancels (12=0.5) and clicks a detached anchor with an immediate revoke (21=0).
- Both map search rows down to timestamp/level/message, dropping Logger, Caller and Exception (18=0.5), and both show the next-page spinner below the virtualized list rather than as a phantom row (19=0.5).
- Five grader scores for r2 were corrected by maintainer spot-check against `patch.diff`, `patch-r3.diff`, `reference.diff` and the cohort precedent: 4 (0.5 → 0), 7 (0 → 0.5), 12 (1 → 0.5), 18 (1 → 0.5), 24 (0 → 0.5) — rubric 67 → 66.5/95, total 72 → 71.5/100.

## Medium reasoning

Parameter set: Strata, int8 KV, medium reasoning.

### Repeat 1 of 2

**Total 71.5/100** — gates 5/5 · rubric 66.5/95 · 13.4 min · 2026-10-07.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | SignalR keeps appending backlog and entries; there is no reconnect handler and no backlog reset, so a reconnect cannot replace the stale tail. |
| 5 | 1 | `Range/Read`, offset paging with limit 100, `NextOffset`, `descending:false`, singular `level` + `message`. |
| 6 | 0.5 | Content-sensitive key, but the levels array is used in toggle order, so equivalent filters hash differently. **Spot-check 0 → 0.5.** |
| 7 | 0.5 | Well-formed case-insensitive `c#:` wrap with empty search omitted, but valid DSL prefixes are never passed through. **Spot-check 0 → 0.5.** |
| 8 | 1 | Empty `level`/`message` omitted by `buildFilterParams`. |
| 9 | 1 | Trimmed debounced search or any level switches the view to the server query. |
| 10 | 1 | Six toggleable levels with tooltips and active styling. |
| 11 | 1 | `debounce(..., 250)` + trim. |
| 12 | 1 | Clear cancels the pending debounce and resets both filters; scroll-lock button disabled while filters are active. |
| 13 | 0 | Header reads only "Logs". |
| 14 | 0.5 | Base throttled scroll-direction heuristic; can unlock on virtualizer measurement scrolls. |
| 15 | 1 | `scrollRect` taken from live container dimensions (already present in the page). |
| 16 | 1 | Empty live tail renders a spinner. **Spot-check 0.5 → 1.** |
| 17 | 1 | `onScroll` proximity trigger (within 25 rows of the end), no render-phase side effect and no debounce. **Spot-check 0.5 → 1.** |
| 18 | 0.5 | Pages flattened in order, but search rows are mapped down to timestamp/level/message, dropping Logger, Caller and Exception. |
| 19 | 0.5 | First-fetch "searching" state plus no-results with Clear filters; the next-page spinner sits below the virtualized list instead of being a phantom row. |
| 20 | 1 | `File/Current/Download` vs `Range/Download` switch; filtered download sends singular `level` + `message`. |
| 21 | 0 | Detached anchor (never added to the DOM) and immediate `URL.revokeObjectURL`. |
| 22 | 1 | Visible `loading` on the button plus an error toast on failure. |
| 23 | 0 | `IconButton` not extended with `loading`; the download button uses `Button`. |
| 24 | 0 | Old `logs/queries.ts` and `LogLineType` both kept, though the commented search placeholder is gone. |
| 25 | 0.5 | Level chips use the `LogLevelType` union, but `LogEntryType.Level` is bare `string`. |

### Repeat 2 of 2

**Total 69/100** — gates 5/5 · rubric 64/95 · 12.5 min · 2026-10-07.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | Same as r1: entries are only appended; there is no reconnect handler and no backlog reset. |
| 5 | 1 | `Range/Read`, offset paging with limit 200, `NextOffset`, `descending:false`, singular `level` + `message`. |
| 6 | 0.5 | Content-sensitive key, but the `levels` array is embedded unsorted, so toggle order changes it. |
| 7 | 0 | `message: \`c#${search}\`` in both the read and download paths — the colon is missing, so it is a literal `c#foo` contains rather than a DSL `c#:` wrap, and valid prefixes do not pass through. |
| 8 | 1 | `level`/`message` omitted when their filter is empty. |
| 9 | 1 | Debounced search or any selected level switches the view to the server query. |
| 10 | 1 | Six toggleable levels with tooltips and active styling. |
| 11 | 1 | `useDebounceValue(searchInput.trim(), 250)`. |
| 12 | 1 | Clear resets both filters; the scroll-lock control is hidden while filters are active, so it is inert. **Spot-check 0.5 → 1.** |
| 13 | 0 | Header reads only "Logs". |
| 14 | 0.5 | Base throttled scroll-direction heuristic; can unlock on virtualizer measurement scrolls. |
| 15 | 1 | Live-container `scrollRect` applied to both the tail and search virtualizers. |
| 16 | 1 | Empty live tail renders a spinner. |
| 17 | 1 | `onScroll` proximity trigger (within 500 px of the end), no render-phase side effect and no debounce. |
| 18 | 1 | Pages flattened in order; timestamp/level/message/exception rendered. |
| 19 | 0.5 | First-fetch "searching" state plus no-results with Clear filters; the next-page spinner sits below the virtualized list instead of being a phantom row. |
| 20 | 1 | `File/Current/Download` vs `Range/Download` switch; filtered download sends singular `level` + `message`. |
| 21 | 0 | Detached anchor (never added to the DOM) and immediate `URL.revokeObjectURL`. |
| 22 | 1 | Visible `loading` on the download button plus an error toast on failure. |
| 23 | 0 | `IconButton` not extended with `loading`; the download button uses `Button`. |
| 24 | 0 | Old `logs/queries.ts` and `LogLineType` both kept, though the commented search placeholder is gone. |
| 25 | 0.5 | Level chips use the `LogLevelType` union, but `LogEntryType.Level` is bare `string`. |

**Key findings:**

- Both medium repeats clear all three gates and discover the read contract (5=1, `NextOffset` cursor, ascending pages, singular `level`/`message`); the shared misses are reconnect replacement (4=0), header mode feedback (13=0), `IconButton` loading (23=0), the unsorted level key (6=0.5), the base scroll-lock heuristic (14=0.5), and `Level` left as bare `string` (25=0.5).
- Both fail the DSL passthrough (7), but r1 writes a well-formed case-insensitive `c#:` contains (7=0.5) while r2 writes `c#${search}` with the colon missing in both the read and download paths (7=0).
- r1 maps search rows down to timestamp/level/message, dropping Logger, Caller and Exception (18=0.5); r2 also renders Exception (18=1). r1 keeps the scroll-lock button disabled under filters and cancels the pending debounce on clear (12=1), while r2 hides the scroll-lock control instead (12=1 after spot-check).
- Five grader scores were corrected by maintainer spot-check against `patch-r1.diff`, `patch.diff`, `reference.diff` and the cohort precedent: r1 6=0 → 0.5, 7=0 → 0.5, 16=0.5 → 1, 17=0.5 → 1; r2 12=0.5 → 1 (plus r2's line-24 note, which wrongly claimed the commented placeholder was kept).

## Xhigh reasoning

Parameter set: Strata, int8 KV, xhigh reasoning (the engine's template default when the client
sends no reasoning effort).

### Repeat 1 of 2

**Total 70.5/100** — gates 5/5 · rubric 65.5/95 · 19.8 min · 2026-10-07.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | Backlog/entry append only; no reconnect handling and no reset, so a reconnect cannot replace the stale tail. |
| 5 | 1 | `Range/Read` with offset pages, `NextOffset`, `descending:false`, singular `level` + `message`. |
| 6 | 0.5 | Content-sensitive key, but `levels` unsorted (toggle order changes it). |
| 7 | 0 | `message: `c#${search}`` — the colon is missing, so it is not a DSL `c#:` wrap and valid prefixes do not pass through. |
| 8 | 1 | Empty `level`/`message` sent as `undefined`. |
| 9 | 1 | Debounced search or any level switches the view from live tail to server search. |
| 10 | 1 | Six toggleable levels with tooltip and active styling. |
| 11 | 1 | Trimmed + 250 ms debounce. |
| 12 | 0.5 | Clear resets both filters and scroll-lock is disabled under filters, but the pending `debounce()` commit can reapply stale text after clearing. |
| 13 | 0 | Header reads only "Logs". |
| 14 | 0.5 | Delayed scroll-direction heuristic; cannot separate user from programmatic scroll. |
| 15 | 1 | Virtualizer `scrollRect` patched from live container dimensions. |
| 16 | 1 | Spinner shown whenever the live tail is empty. |
| 17 | 1 | `fetchNextPage` driven from the scroll/virtualizer path, not render phase. |
| 18 | 1 | Pages flattened in order; timestamp/level/message/exception rendered. |
| 19 | 0.5 | First-fetch and no-results/clear states present; no phantom loader row. |
| 20 | 1 | Endpoint switch correct; filtered download uses `level` + `message`. |
| 21 | 0.5 | Object URL + DOM-attached anchor, but the URL is revoked immediately after `click()`. |
| 22 | 1 | Visible `loading` on the button; failure raises the toast from the base `MutationCache.onError` (`queryClient.ts:95-100`). **Spot-check 0.5 → 1.** |
| 23 | 0 | `IconButton` not extended with `loading` (`loading` went on a regular `Button`). |
| 24 | 0.5 | `LogLineType` and the commented search placeholder removed, no unused exports, but the old `logs/queries.ts` file is kept and extended. |
| 25 | 0.5 | Types modeled without `any`, but `Level` is bare `string`, not `LogLevelType`. |

### Repeat 2 of 2

**Total 74.5/100** — gates 5/5 · rubric 69.5/95 · 21.4 min · 2026-10-07.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | Same as r1: stale tail is never reset on reconnect. **Spot-check 0.5 → 0.** |
| 5 | 1 | `Range/Read`, offset/limit 200, `NextOffset`, `descending:false`, singular `level` + `message`. |
| 6 | 0.5 | Content-sensitive key, unsorted `levels`. |
| 7 | 0.5 | Non-empty search becomes a well-formed case-insensitive `c#:` contains and empty search is omitted, but valid DSL prefixes are never passed through. |
| 8 | 1 | Empty `level`/`message` omitted (`undefined`), never empty strings. |
| 9 | 1 | Active debounced search or levels → server search; clearing → live tail. |
| 10 | 1 | Six toggleable levels, tooltips, active styling. |
| 11 | 1 | `useDebounceValue(search.trim(), 250)` — a new value cancels the pending timer, so no stale reapply. |
| 12 | 1 | Clear resets text + levels; scroll-lock button disabled while filters are active. |
| 13 | 0 | Header reads only "Logs". |
| 14 | 0.5 | Delayed scroll-direction heuristic; may trip on virtualizer-driven scroll. |
| 15 | 1 | `scrollRect` from live container dimensions. |
| 16 | 1 | Empty live tail renders a spinner. **Spot-check 0 → 1.** |
| 17 | 0.5 | Trailing sentinel row calls `fetchNextPage` from its render callback (render-phase side effect). |
| 18 | 1 | Pages flattened in order; API fields rendered. |
| 19 | 1 | First-fetch searching state + phantom loader row + no-results with Clear filters. |
| 20 | 1 | Endpoint switch correct; singular `level` + `message`. |
| 21 | 0 | Detached anchor (never appended to the DOM) **and** immediate `URL.revokeObjectURL`. |
| 22 | 1 | Visible `loading`; failure still raises the base `MutationCache.onError` toast (`.catch(console.error)` does not suppress it). **Spot-check 0.5 → 1.** |
| 23 | 0 | `IconButton` not extended with `loading`. |
| 24 | 0.5 | Removes `LogLineType` and the commented search placeholder, no unused exports; old `logs/queries.ts` kept. |
| 25 | 0.5 | Response typed, no `any`; `Level` bare `string`, not the union. |

**Key findings:**

- Both repeats clear all three gates and discover the read contract (5=1, `NextOffset` cursor, ascending pages, singular `level`/`message`); the shared misses are reconnect replacement (4=0), header mode feedback (13=0), `IconButton` loading (23=0), the unsorted level key (6=0.5), the base scroll-lock heuristic (14=0.5), and `Level` left as bare `string` (25=0.5).
- Search DSL handling is the r1 outlier: it writes `c#${search}` with no colon (7=0) where r2 forms a correct case-insensitive `c#:` contains (7=0.5).
- The rest of the spread is composition. r1 commits a `debounce()` value (12=0.5 — stale text can reapply) but paginates from the scroll path (17=1) with an attached anchor and immediate revoke (21=0.5); r2 uses `useDebounceValue` (11=1, 12=1) and the phantom loader row (19=1), but triggers `fetchNextPage` during render (17=0.5) and clicks a detached anchor with immediate revoke (21=0).
- Four grader scores were corrected by maintainer spot-check against `patch-r1.diff`, `patch.diff`, `reference.diff` and the cohort precedent: r1 22=0.5 → 1; r2 4=0.5 → 0, 16=0 → 1, 22=0.5 → 1.

## Summary

| Reasoning | Repeat | Rubric /95 | Total /100 | Run time (min) |
|---|---|---|---|---|
| low | r1 | 69.5 | 74.5 | 17.7 |
| low | r2 | 66.5 | 71.5 | 15.7 |
| **low** | **Mean** | **68** | **73** | **15.7–17.7** |
| medium | r1 | 66.5 | 71.5 | 13.4 |
| medium | r2 | 64 | 69 | 12.5 |
| **medium** | **Mean** | **65.25** | **70.25** | **12.5–13.4** |
| xhigh | r1 | 65.5 | 70.5 | 19.8 |
| xhigh | r2 | 69.5 | 74.5 | 21.4 |
| **xhigh** | **Mean** | **67.5** | **72.5** | **19.8–21.4** |

Run time is wall-clock per run (fresh opencode session, start → last message), so it includes
model load; min–max is over the two repeats. No nudges or auto-compactions in any repeat.

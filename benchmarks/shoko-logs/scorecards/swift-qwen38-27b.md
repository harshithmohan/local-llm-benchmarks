# swift-qwen38-27b — scores

Parameter set: Swift-1.5-INT4 vLLM, fp8 KV. 2-repeat mean per reasoning level.

> **Note:** the low reasoning repeat 1 run was **auto-compacted** (native compaction; a
> harness intervention, not part of the task) — see `scorecard.md` → "Auto-compactions".

## Low reasoning

Parameter set: Swift-1.5-INT4 vLLM, fp8 KV, low reasoning.

### Repeat 1 of 2 (auto-compacted)

**Total 63.0/100** — gates 5/5 · rubric 58/95 · 2026-09-27.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | SignalR appends backlog/events but adds neither automatic reconnect nor a reset before a fresh backlog, so stale entries are retained. |
| 5 | 0.5 | `Range/Read` with correct singular `level`/`message`, offset/limit, ascending order; a page shorter than 100 entries ends pagination even when `NextOffset` is non-null. |
| 6 | 1 | Selected levels sorted before entering the query key → content-sensitive, toggle-order independent. |
| 7 | 0 | Non-empty input always formatted as `c#${message}` (missing the required colon); valid DSL prefixes not passed through. |
| 8 | 1 | Empty `level`/`message` omitted from read and download requests. |
| 9 | 1 | Trimmed debounced search or any selected level switches from live tail to server results. |
| 10 | 0.5 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1 | 250 ms debounce + trim. |
| 12 | 1 | Clear filters resets search and levels; scroll-lock disabled while filters active. |
| 13 | 0 | Header only "Logs"; no live-tail count or server-search hint. |
| 14 | 0.5 | Throttled scroll comparison detects upward movement but not vs programmatic/virtualizer movement. |
| 15 | 0 | No live-container-dimension sizing or `scrollRect` workaround. |
| 16 | 1 | Spinner when the entry list is empty; clears once entries exist. |
| 17 | 1 | Scroll handler calls `fetchNextPage` near the bottom; real proximity trigger, no render-phase effect or debounce. |
| 18 | 0.5 | Pages flattened in order without slicing/dedup, but only timestamp/level/message rendered; logger/caller/exception omitted. |
| 19 | 0.5 | Full-height initial pending state and no-results Clear filters; no phantom loader row for later pages. |
| 20 | 1 | Switches `File/Current/Download` ↔ `Range/Download`; filtered requests use correctly named singular params. |
| 21 | 0.5 | Object URL + DOM-attached anchor, but synchronous revoke after click; filename lacks time. |
| 22 | 1 | Loading state + error toast. |
| 23 | 0 | `IconButton` not extended with a `loading` prop; download uses `Button`. |
| 24 | 0.5 | Old `logs/` query, `LogLineType`, and commented placeholder remain; no new unused imports/exports. |
| 25 | 0.5 | Shapes modeled without `any`; `LogEntryType.Level` typed `string`, not `LogLevelType`. |

**Key findings:**

- Correct read/download endpoints and a stable (sorted) level key, but the malformed `c#${message}` DSL breaks search and filtered downloads.
- Pagination can stop before server exhaustion; reconnect replacement, full result rendering, and `scrollRect` are missing.

### Repeat 2 of 2

**Total 66.0/100** — gates 5/5 · rubric 61/95 · 2026-09-27.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | Backlog and events append to the cache; no reconnect handler/reset, so stale entries are retained and can duplicate. |
| 5 | 1 | `Range/Read` with offset pages, `NextOffset`, `descending:false`, and correct singular params. |
| 6 | 0.5 | Key is content-sensitive but `levels.join(',')` is unsorted → toggle-order dependent. |
| 7 | 0.5 | Non-empty searches get the valid `c#:` wrapper and empty search is omitted; valid DSL input not detected/passed through. |
| 8 | 1 | Empty `message`/`level` omitted from read requests. |
| 9 | 1 | Debounced search or selected levels switch between SignalR tail and server results. |
| 10 | 0.5 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1 | 250 ms debounce + trim. |
| 12 | 1 | Clear filters resets search and levels; scroll-lock disabled while filters active. |
| 13 | 0 | Header only "Logs"; no count or mode feedback. |
| 14 | 0.5 | Throttled scroll-direction check can mistake programmatic/measurement movement for a user scroll. |
| 15 | 1 | `scrollRect` refreshed from live container dimensions. |
| 16 | 0 | Empty list shows a spinner, but no reconnect reset means the required post-reset empty state is never reached. |
| 17 | 0.5 | Pagination triggered near the end of visible results, but `fetchNextPageDebounced()` is called during render and adds an unnecessary debounce. |
| 18 | 1 | Pages flattened in order; each entry rendered once with timestamp, level, message. |
| 19 | 0.5 | Initial pending and no-results Clear filters states present; no phantom loader row. |
| 20 | 1 | Endpoint switch correct with correctly named singular params. |
| 21 | 0 | Blob and filename handled, but anchor detached and URL revoked synchronously after click. |
| 22 | 1 | Visible loading indicator + error toast. |
| 23 | 0 | `IconButton` not extended with a `loading` prop. |
| 24 | 0 | Old `logs/queries.ts` and `LogLineType` remain; placeholder removed but legacy cleanup incomplete. |
| 25 | 0.5 | Search result and `LogLevelType` modeled, but live events use legacy `LogLineType` with `Level: string`. |

**Key findings:**

- Strong read contract (5=1) but render-phase debounced pagination and a stale live spinner; DSL passthrough still missing.
- Detached anchor + immediate revoke leaves the download browser-fragile.

## Medium reasoning

Parameter set: Swift-1.5-INT4 vLLM, fp8 KV, medium reasoning.

### Repeat 1 of 2

**Total 70.0/100** — gates 5/5 · rubric 65/95 · 2026-09-27.

| # | Score | Notes |
|---|---|---|
| 4 | 0.5 | Backlog/events append, but no automatic reconnect or reset; a fresh backlog cannot replace stale entries. |
| 5 | 1 | `Range/Read` with offset pages, `NextOffset`, `descending:false`, correct singular params. |
| 6 | 0.5 | Key includes level content via `join(',')`, but the level array is unsorted → toggle-order dependent. |
| 7 | 0 | Every non-empty message wrapped as `c#:`; valid DSL prefixes not passed through. |
| 8 | 1 | Empty `level`/`message` omitted via conditional spreads. |
| 9 | 1 | Trimmed debounced search or selected levels switch live ↔ server search. |
| 10 | 0.5 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1 | 250 ms debounce + trim. |
| 12 | 1 | Clear resets search and levels; scroll-lock disabled while filters active. |
| 13 | 0 | Header only "Logs"; no live-tail count or search hint. |
| 14 | 0.5 | Throttled scroll-direction check cannot reliably distinguish user scroll from virtualizer/programmatic corrections. |
| 15 | 1 | Existing `scrollRect` workaround sets dimensions from the live container. |
| 16 | 0.5 | Empty live tail shows a spinner, but no reconnect reset for the post-reset empty state. |
| 17 | 1 | Scroll within 1000 px of the bottom invokes `fetchNextPage`, guarded while a fetch is in progress. |
| 18 | 1 | Pages concatenated in order; returned timestamp/level/message rendered without apparent drop/dup. |
| 19 | 0.5 | First pending and no-results Clear filters states present; no phantom loader row. |
| 20 | 1 | Endpoint switch with correct singular params. |
| 21 | 0.5 | Object URL + DOM-attached anchor with date/time filename, but synchronous revoke after click. |
| 22 | 1 | Loading indicator + error toast. |
| 23 | 0 | `IconButton` not extended with a `loading` prop; loading on a regular `Button`. |
| 24 | 0 | Old logs query file and `LogLineType` remain, as does the commented placeholder. |
| 25 | 0.5 | Search result types modeled, no `any`; `LogEntryType.Level` bare `string`, not the union. |

**Key findings:**

- Correct read pagination contract, endpoint switch, and loading/error feedback; DSL passthrough and reconnect reset missing.
- Smaller omissions in chip tooltips, mode-aware header, phantom loader, and typing.

### Repeat 2 of 2

**Total 78.0/100** — gates 5/5 · rubric 73/95 · 2026-09-27.

| # | Score | Notes |
|---|---|---|
| 4 | 0.5 | Backlog/events append, but no automatic reconnect or reconnect reset to replace stale tail data. |
| 5 | 1 | `Range/Read` with offset pages, `NextOffset`, ascending order, correct params. |
| 6 | 0.5 | Array key includes level content but levels unsorted → different toggle orders differ. |
| 7 | 0.5 | Ordinary text wrapped for case-insensitive contains, empty search omitted; valid DSL not passed through; emitted `c#: ` adds a leading space. |
| 8 | 1 | Conditional parameters omit empty `level`/`message`. |
| 9 | 1 | Trimmed debounced search or selected levels switch live ↔ server. |
| 10 | 0.5 | Six toggleable chips with active styling; no tooltips. |
| 11 | 1 | 250 ms debounce + trim. |
| 12 | 1 | Clear filters resets both; scroll-lock disabled while filters active. |
| 13 | 0 | Header no live-tail count or search hint. |
| 14 | 0.5 | Throttled scroll-direction check can confuse programmatic/measurement changes with user input. |
| 15 | 1 | `scrollRect` from the live container dimensions. |
| 16 | 0.5 | Empty live tail shows a spinner, but no reconnect reset for the post-reset empty state. |
| 17 | 1 | Effect invokes `fetchNextPage` as the trailing virtual range nears the end, with a concurrency guard. |
| 18 | 1 | Pages flattened in order; entries rendered without apparent drop/dup. |
| 19 | 0.5 | First-fetch and no-results states present; no phantom row for next-page loading. |
| 20 | 1 | Endpoint switch with singular param names. |
| 21 | 0.5 | Object URL + DOM-attached anchor with date/time filename, but synchronous revoke after click. |
| 22 | 1 | Visible loading state + error toast. |
| 23 | 0 | `IconButton` not extended with a `loading` prop; loading on a regular `Button`. |
| 24 | 0.5 | `LogLineType` removed and no new unused imports, but old `logs/queries.ts` path and commented placeholder remain. |
| 25 | 1 | Event/result types modeled, `Level` uses a string-literal union, no `any` leakage. |

**Key findings:**

- Best swift repeat: full read contract, effect-driven pagination, `LogLineType` removed and a level union adopted.
- Remaining gaps: DSL passthrough (leading space in the wrap), reconnect reset, tooltips, mode-aware header, phantom loader row, `IconButton` loading.

## Xhigh reasoning

Parameter set: Swift-1.5-INT4 vLLM, fp8 KV, xhigh reasoning.

### Repeat 1 of 2

**Total 74.0/100** — gates 5/5 · rubric 69/95 · 2026-09-27.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | Backlog/events append, but no automatic reconnect or reset; stale tail not replaced. |
| 5 | 1 | `Range/Read` with offset pages, `NextOffset`, limit, `descending:false`, correct singular params; empty filters omitted. |
| 6 | 0.5 | Content-sensitive key derived from selected levels, but joined in Set iteration order without sorting. |
| 7 | 0.5 | Ordinary searches sent as `c#:` and empty search omitted; no DSL-prefix recognition/passthrough. |
| 8 | 1 | Read and download requests conditionally omit empty `message`/`level`. |
| 9 | 1 | `hasFilters` switches between live tail and server-search rows. |
| 10 | 0.5 | Six toggleable level buttons with active styling; no tooltip. |
| 11 | 1 | 250 ms debounce + trim. |
| 12 | 1 | Clear filters resets search and levels; scroll-lock disabled while filters active. |
| 13 | 0 | Header only "Logs"; no live-tail count or search hint. |
| 14 | 0.5 | Delayed scroll-direction check can unlock on scroll-up but not vs programmatic/measurement movement. |
| 15 | 1 | `scrollRect` updated from live container dimensions during render. |
| 16 | 1 | Spinner whenever the tail is empty, including after an empty reset. |
| 17 | 1 | Scroll handler near the result-list end invokes `fetchNextPage()` without render-phase effect or debounce. |
| 18 | 0.5 | Pages traversed in order, but flattening deduplicates on timestamp/message (can discard distinct identical entries) and maps away other fields. |
| 19 | 0.5 | Initial pending, no-results Clear filters, and a next-page spinner; indicator not a phantom virtualizer row. |
| 20 | 1 | Mutation switches current-file ↔ range download with singular `level`/`message`. |
| 21 | 0.5 | Object URL + DOM-attached anchor and server/fallback filename, but synchronous revoke after click. |
| 22 | 1 | Visible `Button` loading state + error toast. |
| 23 | 0 | `IconButton` not extended with a `loading` prop; download uses `Button`. |
| 24 | 0.5 | Placeholder removed and additions used, but old `logs/` query module and `LogLineType` remain. |
| 25 | 1 | Search-result levels use a string-literal union; result/event shape typed without `any`. |

**Key findings:**

- Correct read/pagination contract and download endpoint switch, plus `Content-Disposition` handling; reconnect and DSL passthrough remain the largest gaps.
- Timestamp/message dedup can drop legitimate repeat entries; pagination can stall for short first pages.

### Repeat 2 of 2

**Total 72.5/100** — gates 5/5 · rubric 67.5/95 · 2026-09-27.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | Existing SignalR handlers append, but no reconnect reset; stale tail entries remain. |
| 5 | 1 | `Range/Read` with offset pages, `NextOffset`, `descending:false`, correct params. |
| 6 | 0.5 | Array-based key is content-sensitive but `criteria.levels` used unsorted → toggle-order dependent. |
| 7 | 0.5 | Ordinary terms wrapped as case-insensitive contains; every non-empty input wrapped, no DSL passthrough. |
| 8 | 1 | Empty level/message become `undefined` and are omitted. |
| 9 | 1 | `filtersActive` selects live-tail vs server-search entries. |
| 10 | 0.5 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1 | 250 ms debounce + trimmed value. |
| 12 | 1 | No-results clear action resets both filters; scroll-lock disabled while filters active. |
| 13 | 0 | Header only "Logs"; no count or mode hint. |
| 14 | 0.5 | Legacy throttled scroll-direction check cannot distinguish genuine user scroll from virtualizer corrections. |
| 15 | 0 | No live-container-dimension `scrollRect` workaround or equivalent sizing. |
| 16 | 1 | Spinner while the tail is empty; switches to rows once entries exist. |
| 17 | 1 | Scroll handler calls `fetchNextPage` at the trailing threshold, no render-phase fetch or debounce. |
| 18 | 1 | Pages flattened in page order; each row reads returned timestamp/level/message. |
| 19 | 0.5 | Full-height first-fetch searching state and no-results Clear filters; no phantom row/loader for the next page. |
| 20 | 1 | Endpoint switch with correct singular params. |
| 21 | 0 | Anchor detached and URL revoked synchronously; filenames lack a time component. |
| 22 | 1 | `loading` state + error toast. |
| 23 | 0 | No `loading` prop on `IconButton`; loading on a separate `Button`. |
| 24 | 0.5 | Old `logs/queries.ts` and `LogLineType` remain; placeholder removed, no new unused imports. |
| 25 | 0.5 | Search result types and `LogLevelType` modeled, but live SignalR path still uses `LogLineType` with `Level: string`. |

**Key findings:**

- Correct paginated read contract and endpoint switching; reusable `IconButton` untouched and `scrollRect` sizing absent.
- Reconnect replacement, DSL passthrough, order-independent filter key, and deferred blob-download lifecycle incomplete.

## Summary

| Reasoning | Repeat | Rubric /95 | Total /100 | Run time (min) |
|---|---|---|---|---|
| low | r1 (auto-compacted) | 58 | 63.0 | 13.5 |
| low | r2 | 61 | 66.0 | 11.1 |
| **low** | **Mean** | **59.5** | **64.5** | **11.1–13.5** |
| medium | r1 | 65 | 70.0 | 10.0 |
| medium | r2 | 73 | 78.0 | 7.3 |
| **medium** | **Mean** | **69** | **74.0** | **7.3–10.0** |
| xhigh | r1 | 69 | 74.0 | 8.5 |
| xhigh | r2 | 67.5 | 72.5 | 11.6 |
| **xhigh** | **Mean** | **68.25** | **73.25** | **8.5–11.6** |

Across all six repeats the common strengths are the read pagination contract (line 5) and download endpoint switch (line 20); the common gaps are DSL passthrough (line 7), reconnect replacement (line 4), header mode feedback (line 13), chip tooltips (line 10), the phantom next-page loader row (line 19), and `IconButton` loading (line 23). Medium reasoning was the strongest variant by mean total (74.0); low lagged on the malformed `c#` DSL (7=0 in r1), stop-early pagination (5=0.5), and the render-phase pagination regression in r2 (17=0.5).

# mimo-v2.6-flash — scores

Parameter set: opencode-go (no reasoning levels). Cloud reference model — **1 run
only** (no repeat-mean; see README → "Run naming and repeats").

## Single run

**Total 67.5/100** — gates 5/5 · rubric 62.5/95 · 2026-09-28. Run time **33.0 min**
(13:16:08Z–13:49:08Z). **No output-limit nudge, no auto-compaction.** Patch 467 lines
across 5 files: `src/pages/logs/LogsPage.tsx`, `src/core/react-query/logs/queries.ts`,
new `src/core/react-query/logs/helpers.ts`, new `src/core/react-query/logs/mutations.ts`,
new `src/core/react-query/logs/types.ts`.

Capability subtotals: Discovery & server-contract **50%** · Implementation **73%** ·
Integration & wiring **74%** · Build hygiene **100%** · Code quality **25%**.

> **Maintainer corrections (spot-check).** The grader printed **59.5/100 (54.5/95)**, but
> its own line scores sum to **62.5/100** — the stated subtotal was a summation error.
> Two lines were corrected against the patch:
> - **#7 → 0.5** (was 0). The helper sends `` message = `c#:${search}` `` — the `c#:` wrap
>   **with** the colon is a valid case-insensitive contains, the same behavior deepseek
>   (7=0.5) and qwen3.8-flash (7=0.5) received. Only the DSL passthrough
>   prefix-check half is missing → half credit. (0 is reserved for the malformed
>   missing-colon `c#${x}` wrap, e.g. qwen38-27b r2 / swift r1.)
> - **#24 left at 0**, but the grader's reason was wrong: the commented-out search
>   placeholder **was** removed (patch removes the `{/* <Input … placeholder="Search
>   Logs..." */}` block). The zero is sustained on the rubric's primary requirement —
>   the reference's old `logs/` query file and `LogLineType` are **not** removed.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0 | 0 | SignalR appends backlog + individual `Log` events, but no reconnect handling/reset — stale tail after reconnect. |
| 5 | 0.5 | 5 | `Range/Read` with `offset`/`limit`/`descending:false`, singular `level`+`message`, `NextOffset` paging — but `getNextPageParam` declares exhaustion on `Entries.length < 200`, so a short page stops paging even when `NextOffset` is non-null. |
| 6 | 0.5 | 1.5 | Level array is content-sensitive in the key but not sorted — toggle order changes the key. |
| 7 | 0.5 | 5 | `` `c#:${search}` `` wrap (case-insensitive contains, correct colon) for every nonempty search; **no DSL passthrough** prefix check. Corrected 0→0.5 by maintainer (see above). |
| 8 | 1 | 5 | `level`/`message` omitted when empty. |
| 9 | 1 | 7 | Nonempty trimmed debounced search or any selected level switches to server search. |
| 10 | 0.5 | 2 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1 | 3 | 250 ms debounce + trim. |
| 12 | 1 | 3 | Clear filters resets search + levels; scroll-lock control disabled while filtering. |
| 13 | 0 | 0 | Header bare "Logs"; no live count / server-search hint. |
| 14 | 0.5 | 2 | Delayed scroll-direction heuristic can react to programmatic / virtualizer scroll corrections. |
| 15 | 1 | 1 | Virtualizer `scrollRect` refreshed from live container dimensions. |
| 16 | 1 | 3 | Spinner while live tail is empty; gone once entries exist. |
| 17 | 0.5 | 3 | `fetchNextPage` is scheduled as a **render-time** side effect (debounced callback on the trailing virtual row) — works, but render-phase + needless debounce. |
| 18 | 1 | 5 | Search pages concatenated in order, rendered from returned fields, no drops/dupes. |
| 19 | 1 | 4 | First-fetch full-height searching state, trailing loader row, no-results + Clear Filters. |
| 20 | 1 | 6 | Endpoint switch `File/Current/Download` ↔ `Range/Download`; singular `level` + `message` names correct. |
| 21 | 0.5 | 1.5 | Object URL + DOM-attached anchor + `Content-Disposition`/date-time filename, but URL revoked **synchronously** after `click()`. |
| 22 | 1 | 4 | Visible loading state on the button + error toast. |
| 23 | 0 | 0 | `IconButton` not extended with `loading`; the download sidesteps via `<Button>`. |
| 24 | 0 | 0 | Commented placeholder removed and no unused exports/imports, but the old `logs/` query file was **extended** and `LogLineType` retained instead of removed. |
| 25 | 0.5 | 1.5 | Filter levels use a union, results modeled without `any`; `LogEntryType` inherits bare `Level: string` from `LogLineType`. |

**Key findings:**

- Solid, end-to-end wiring for a no-reasoning model: correct read + download endpoints
  and param names, live tail kept running, working infinite scroll, six level chips,
  debounced search, loading/empty states, and `IconButton`-free download button.
- Trips the benchmark discriminator: **no DSL passthrough** (7=0.5), and pagination both
  stops on short pages (5=0.5) and runs as a render-phase debounced side effect (17=0.5).
- Versus the earlier sample: most wiring was kept, but pagination now runs as a
  render-phase debounced side effect (17=0.5), legacy types are retained (24=0), and no
  `IconButton` loading was added (23=0).

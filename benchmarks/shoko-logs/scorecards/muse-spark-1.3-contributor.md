# muse-spark-1.3-contributor — scores

Parameter set: opencode-go. Cloud reference model — **1 run per reasoning level** (no
repeat-mean; see README → "Run naming and repeats"). One level tested: **xhigh**.

## Single run (xhigh reasoning)

**Total 66.0/100** — gates 5/5 · rubric 61.0/95 · 2026-09-28. Run time **11m 57s**
(14:46:16Z–14:58:13Z). **No output-limit nudge, no auto-compaction.** Patch 466 lines
across 4 files: modified `src/core/react-query/logs/queries.ts`,
`src/core/types/api/common.ts` (removed `LogLineType`), `src/pages/logs/LogsPage.tsx`;
new `src/core/react-query/logs/types.ts`.

Capability subtotals: Discovery & server-contract **50%** · Implementation **66%** ·
Integration & wiring **72%** · Build hygiene **100%** · Code quality **50%**.

> **Maintainer corrections (spot-check).** Two lines were corrected against the patch:
> - **#7 → 0.5** (was 0). The query sends `` message: search === '' ? undefined :
>   `c#:${search}` `` — a non-empty-guarded `c#:` wrap, i.e. a valid case-insensitive
>   contains, the same partial-credit behavior deepseek/qwen3.8-flash/mimo received.
>   Only the DSL passthrough prefix-check half is missing → half credit.
> - **#16 → 1** (was 0.5). The live view renders an `mdiLoading` spinner whenever
>   `logLines.length === 0`, which satisfies the empty-tail requirement; the grader
>   docked it for the (separately-scored) missing reconnect reset, which the cohort does
>   not double-count (deepseek/glm/mimo all scored 16=1 with 4=0).
> All other line scores verified; the sheet's arithmetic was self-consistent
> (54.5/95 + 5 gates = 59.5 before these two fixes).

| # | Score | Pts | Notes |
|---|---|---|---|
| 1 | 1 | 2 | `pnpm tscheck` clean. |
| 2 | 1 | 1 | `pnpm lint` clean (dprint + oxlint + stylelint). |
| 3 | 1 | 2 | `pnpm build` succeeds. |
| 4 | 0 | 0 | No automatic reconnect / reconnect reset — a fresh backlog appends to stale tail data. |
| 5 | 0.5 | 5 | `Range/Read`, ascending, offset/limit, singular `level`+`message` — but stops on a short page even when `NextOffset` is non-null. |
| 6 | 1 | 3 | Content-sensitive comma-joined level key normalized in `LOG_LEVELS` order — toggle-order independent. |
| 7 | 0.5 | 5 | Non-empty-guarded `` `c#:${search}` `` wrap (case-insensitive contains); **no DSL passthrough** prefix check. Corrected 0→0.5. |
| 8 | 1 | 5 | Empty `level`/`message` passed as `undefined` → omitted. |
| 9 | 1 | 7 | Debounced search or any selected level switches live tail ↔ server search. |
| 10 | 0.5 | 2 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1 | 3 | Trimmed + 250 ms debounced search. |
| 12 | 1 | 3 | Clear filters resets both; scroll-lock button disabled in search mode. |
| 13 | 0 | 0 | Header remains "Logs"; no live count / search hint. |
| 14 | 0.5 | 2 | Throttled `scrollTop` comparison can unlock the tail but cannot distinguish user input from virtualizer/programmatic corrections. |
| 15 | 1 | 1 | Virtualizer `scrollRect` updated from live container dimensions. |
| 16 | 1 | 3 | `mdiLoading` spinner rendered while the live tail is empty. Corrected 0.5→1. |
| 17 | 0.5 | 3 | Trailing-row effect invokes `fetchNextPage`, but via a needless debounce and without a virtual phantom loader row. |
| 18 | 0.5 | 2.5 | Pages flattened in order without duplication, using returned timestamp/level/message; the row omits other returned fields (logger/caller/exception) the reference renders. |
| 19 | 0.5 | 2 | First-fetch searching state + no-results/Clear filters, but next-page loading is a spinner after the list, not a phantom virtual row. |
| 20 | 1 | 6 | `File/Current/Download` unfiltered ↔ `Range/Download` filtered; singular `level`+`message` names correct. |
| 21 | 0.5 | 1.5 | Object URL + DOM-attached anchor, but revokes **synchronously** after click and uses a fixed (not date-time) filename. |
| 22 | 1 | 4 | Visible loading state on the button + error toast. |
| 23 | 0 | 0 | `IconButton` not extended with `loading`; download uses `Button`. |
| 24 | 0.5 | 1.5 | Removed `LogLineType` + commented placeholder, no unused additions, but keeps the old `src/core/react-query/logs/queries.ts` file. |
| 25 | 0.5 | 1.5 | Event/result DTOs modeled, no `any`; `LogEntryType.Level` stays bare `string`, not `LogLevelType`. |

**Key findings:**

- Build-clean, broad delivery: correct read + download contract (endpoint switch,
  singular `level`/`message`, ascending reads), stable sorted query key, 250 ms debounce,
  six level chips, live/search switching, flattened result pages, spinner + toast.
- Trips the discovery discriminator: no DSL passthrough (7=0.5) and pagination stops on
  short pages (5=0.5); no reconnect reset (4=0).
- Rendering is thinner than the reference (no logger/caller/exception in the row, 18=0.5)
  and pagination is debounced without a phantom loader row (17=0.5, 19=0.5); download
  revokes synchronously (21=0.5); `IconButton` loading absent (23=0).

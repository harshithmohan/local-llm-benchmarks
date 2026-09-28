# deepseek-v4.1-flash — scores

Parameter set: opencode-go, **high reasoning level** (`--variant high`; its default is
high). Cloud reference model — **1 run only** (no repeat-mean; see README → "Run naming
and repeats").

## Single run (high reasoning)

**Total 71.5/100** — gates 5/5 · rubric 66.5/95 · 2026-09-28. Run time **4m 43s**
(13:59:21Z–14:04:04Z — notably fast, ~199 tok/s). **No output-limit nudge, no
auto-compaction.** Patch 470 lines across 3 tracked files (+3 new): new
`src/core/types/api/logs.ts`, new `src/core/react-query/logs/mutations.ts`, new
`src/pages/logs/LogLevelChips.tsx`, plus modified `src/core/react-query/logs/queries.ts`,
`src/core/types/api/common.ts`, `src/pages/logs/LogsPage.tsx`.

Capability subtotals: Discovery & server-contract **50%** · Implementation **71%** ·
Integration & wiring **82%** · Build hygiene **100%** · Code quality **50%**.

> **Maintainer correction (spot-check).** Line **#14 → 0.5** (grader scored 0). The patch
> keeps the base `throttle`+`setTimeout` `checkScrollDirection` scroll-lock verbatim
> (only guarded with `if (scrollToBottom)`), the same retained base mechanism the
> model's own 2026-09-19 run and the glm/mimo runs received 0.5 for. The grader's
> rationale ("does not guarantee the lock behavior") applies equally to those, so 0 is
> inconsistent. All other line scores verified against the patch; the sheet's arithmetic
> is self-consistent (its 64.5/95 + 5 gates = 69.5 before the #14 fix).

| # | Score | Pts | Notes |
|---|---|---|---|
| 1 | 1 | 2 | `pnpm tscheck` clean. |
| 2 | 1 | 1 | `pnpm lint` clean (dprint + oxlint + stylelint). |
| 3 | 1 | 2 | `pnpm build` succeeds (Vite warns the runtime-resolved `Theme.css` is absent at build time — non-fatal). |
| 4 | 0 | 0 | Backlog + per-entry append kept, but no reconnect handler/reset — stale tail after reconnect. |
| 5 | 0.5 | 5 | `Range/Read` with `offset`/`limit`/`descending:false`, singular `level`+`message`, `NextOffset` — but `getNextPageParam` stops whenever `Entries.length < 100`, even if `NextOffset` is non-null. |
| 6 | 0.5 | 1.5 | Level array content-sensitive in the key but not sorted — toggle order changes the key. |
| 7 | 0.5 | 5 | Empty search omitted, but **no DSL passthrough** and nonempty input is sent as case-sensitive `` `c:${search}` `` rather than case-insensitive `c#:`. |
| 8 | 1 | 5 | Empty `message`/`level` → `undefined`, omitted from requests. |
| 9 | 1 | 7 | Trimmed/debounced search or any level switches live tail ↔ server search. |
| 10 | 0.5 | 2 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1 | 3 | 250 ms debounce + trim. |
| 12 | 1 | 3 | Clear filters resets both; scroll-lock button disabled while filtering. |
| 13 | 0 | 0 | Header only "Logs"; no live-count / server-search hint. |
| 14 | 0.5 | 2 | Base throttled snapshot scroll-lock retained (see correction note) — unlocks in the common case, fragile on programmatic/virtualizer scrolls. |
| 15 | 1 | 1 | `scrollRect` updated from live container dimensions. |
| 16 | 1 | 3 | Live spinner while the tail has no entries. |
| 17 | 1 | 6 | Scroll handler fetches next page within 600 px of the bottom — no debounce, no render-phase side effect. |
| 18 | 1 | 5 | Pages flattened in order, each entry rendered once from returned fields. |
| 19 | 0.5 | 2 | Full-height first-fetch state + no-results/Clear filters, but the next-page spinner sits outside the virtualized list (no phantom loader row). |
| 20 | 1 | 6 | `File/Current/Download` unfiltered ↔ `Range/Download` filtered; `level`/`message` names correct. |
| 21 | 1 | 3 | Object URL + DOM-attached anchor + date-time filename + **deferred** (`setTimeout`) revoke. |
| 22 | 1 | 4 | `Button` visible loading spinner + error toast. |
| 23 | 0 | 0 | `IconButton` not extended with `loading`; download uses `Button`. |
| 24 | 0.5 | 1.5 | Commented search placeholder removed and added exports used, but the old `logs/queries.ts` path remains and `LogLineType` was relocated (to `types/api/logs.ts`), not removed. |
| 25 | 0.5 | 1.5 | Search/result types modeled, no `any`; but `LogLineType.Level` stays bare `string`, not `LogLevelType`. |

**Key findings:**

- Fast, broad delivery: correct read contract, endpoint switching, empty-param omission,
  working infinite scroll (600 px trigger, no debounce), full blob download handling
  (DOM attach + deferred revoke + date-time filename), spinner + toast, and a dedicated
  `LogLevelChips` component.
- Trips the discovery discriminator: DSL grammar is **not** implemented and default
  search is case-sensitive `c:` (7=0.5); pagination stops on short pages (5=0.5);
  no reconnect reset (4=0).
- Download is now fully correct (21=1) but the query key lost its canonical ordering
  (6: 1→0.5) and pagination moved to the scroll handler with a short-page stop (5: 1→0.5).

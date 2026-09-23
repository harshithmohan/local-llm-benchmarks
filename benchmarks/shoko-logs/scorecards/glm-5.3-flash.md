# glm-5.3-flash — scores

Parameter set: opencode-go. Two reasoning levels tested, each a single discovery run:
**high** and **max**. (The very first glm run — 70.5/100, also high — was discarded at
the user's request and replaced by the high run below.)

## Discovery — single run (high reasoning)

**Total 66.5/100** — gates 5/5 · rubric 61.5/95 · 2026-09-23. Replacement run (prior 70.5 discarded); orchestrator spot-checked (no `c#` anywhere; `anchor.download=''` + sync revoke + no `appendChild`; `fetchNextPage` in scroll handler; live empty state regressed) — all confirmed. Patch 399 lines, 4 files (stat.txt shows 2 — new files untracked at stat time).

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3 | SignalR subscription + GetBacklog append + per-entry `Log` append kept; no `onreconnected` reconnect reset. |
| 5 | 1.0 | 9 | `Range/Read`, `offset: pageParam`, `limit: 500`, `descending:false`, `NextOffset ?? undefined`; `level`(singular)/`message`/`offset`/`limit`/`descending` all correct. |
| 6 | 0.5 | 1.5 | Content-sensitive `levels.join(',')` key (no Set hashing); **not sorted** → toggle order changes the cache key. |
| 7 | 0 | 0 | **No DSL handling at all** — raw trimmed `message` sent (queries.ts:40); no `c#:` wrap, no passthrough; case-sensitive search. |
| 8 | 1.0 | 5 | `level`/`message` via `\|\| undefined` → omitted, never empty strings. |
| 9 | 1.0 | 6 | `isFilterActive` (debounced+trimmed) switches line source + render branch. |
| 10 | 0.5 | 2 | Six levels, toggleable, active styling; no tooltip (raw `<button>`). |
| 11 | 1.0 | 3 | `useDebounceValue(searchInput, 250)` then `.trim()`. |
| 12 | 0.5 | 1.5 | `clearFilters` resets both ✓; scroll-lock IconButton not disabled while filters active. |
| 13 | 0 | 0 | Header is just `Logs` — no live-count / server-search hint. |
| 14 | 1.0 | 6 | Kept base throttle scroll-lock; unlocks on scroll-up, stays locked through programmatic `scrollToIndex` (flakiness noted). |
| 15 | 1.0 | 3 | scrollRect workaround present inline. |
| 16 | 0 | 0 | Live-view empty state shows "No results found." — the initial-load spinner was regressed/removed. |
| 17 | 1.0 | 5 | `fetchNextPage` invoked in `handleScroll` near bottom (<400px); not render-phase, no debounce. |
| 18 | 1.0 | 4 | Full-height searching; "Loading more…" during `isFetchingNextPage`; "No results found." + Clear filters. |
| 19 | 1.0 | 6 | `Range/Download` vs `File/Current/Download` switch; `level` (singular) + `message` names correct. |
| 20 | 0 | 0 | No DOM attach, **synchronous** revoke, `anchor.download=''` (no filename) — broken in Firefox, wrong filename everywhere. |
| 21 | 0.5 | 2 | `disabled` + opacity (no spinner); error toast ✓. |
| 22 | 0 | 0 | IconButton `loading` prop not added (IconButton.tsx untouched). |
| 23 | 1.0 | 3 | No leftover placeholder, no unused exports/imports; kept `logs/queries.ts` + `LogLineType` (both still used). |
| 24 | 0.5 | 1.5 | Types modeled, no `any`; `LogEntryType.Level` bare `string`; Logger/Caller/ThreadID/ProcessID required. |

**Key findings:**

- Data layer solid (5, 9, 11, 17, 19 full; loader row 18; clean dead-code 23) — but **no DSL handling at all** (7=0) and **download broken** (20=0: no DOM attach + sync revoke + empty filename).
- Live-tail initial spinner regressed (16=0), no reconnect reset (4), unsorted key (6=0.5), no IconButton loading (22=0).
- Textbook "green gates ≠ working feature": 61.5/95 rubric despite a fully passing build.

## Discovery — single run (max reasoning)

**Total 70/100** — gates 5/5 · rubric 65/95 · 2026-09-23. Fresh oracle session; orchestrator spot-checked (no `c#` anywhere; sorted `.sort()` at L188; render-phase `fetchNextPageDebounced` at L347; deferred revoke via `setTimeout` but no `appendChild`; IconButton.tsx untouched) — all confirmed. Patch 384 lines, 2 files.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3 | Backlog + per-entry append kept; `onreconnected` tail reset absent. |
| 5 | 1.0 | 9 | `level` (singular), `message`, `offset`, `limit`, `descending:false` all correct; `NextOffset ?? undefined` pagination. |
| 6 | 1.0 | 3 | `selectedLevels` kept `.sort()`ed in `toggleLevel` — order-independent key (fixed vs high run's 0.5). |
| 7 | 0 | 0 | **No DSL handling at all** — raw `message` (queries.ts:89, mutations.ts:27); no `c#:` wrap, no passthrough; case-sensitive search. |
| 8 | 1.0 | 5 | Empty `message`/`level` omitted (`\|\| undefined`) in both query and download. |
| 9 | 1.0 | 6 | `hasFilters` switches the single virtualizer's data source (live ↔ search). |
| 10 | 0.5 | 2 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1.0 | 3 | `useDebounceValue(search, 250)` + `.trim()`. |
| 12 | 0.5 | 1.5 | `clearFilters` resets both; scroll-lock IconButton has no `disabled={hasFilters}`. |
| 13 | 0 | 0 | Header bare "Logs" — no mode hint. |
| 14 | 0.5 | 3 | Kept the throttle+`setTimeout` snapshot lock; not reliable through programmatic scroll/measurement corrections. |
| 15 | 1.0 | 3 | Inline `rowVirtualizer.scrollRect` workaround preserved. |
| 16 | 1.0 | 3 | Empty-tail spinner gated to `!hasFilters && logLines.length === 0` (restored vs high run's 0). |
| 17 | 0.5 | 2.5 | Fetch invoked on the trailing phantom row, but as a **render-phase side effect** (`fetchNextPageDebounced` inside `.map()`, L347) + needless 100 ms debounce. |
| 18 | 1.0 | 4 | First-fetch searching state; phantom loader row; "No results found." + Clear filters. |
| 19 | 1.0 | 6 | Endpoint switch correct; `level`/`message` names correct. |
| 20 | 0.5 | 2.5 | Object URL + **deferred revoke** (`setTimeout`) + date+time filename (fixed vs high run's 0), but anchor never DOM-attached. |
| 21 | 1.0 | 4 | Real spinner (`isDownloading ? mdiLoading : mdiDownload`) + `toast.error` (fixed vs high run's disabled-only). |
| 22 | 0 | 0 | IconButton not given a `loading` prop; download sidesteps via icon-swap + `disabled`. |
| 23 | 1.0 | 3 | Placeholder removed; no dead file; all imports used. |
| 24 | 0.5 | 1.5 | Types modeled, no `any`; Logger/Caller/ThreadID/ProcessID required; live tail still `LogLineType.Level: string`. |

**Key findings:**

- +3.5 over the high run: deferred revoke + date+time filename (20), real spinner + toast (21), sorted key (6), restored empty-tail spinner (16).
- Traded even elsewhere: pagination trigger went clean-scroll-handler → render-phase debounced (17: 1→0.5); scroll-lock unchanged.
- Still 0 on DSL both times — the grammar is missed regardless of reasoning level.

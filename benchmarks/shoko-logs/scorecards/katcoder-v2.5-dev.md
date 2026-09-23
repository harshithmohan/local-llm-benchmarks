# katcoder-v2.5-dev — scores

Parameter set: katcoder apex-i compact (262k ctx, default reasoning; no reasoning_effort variants — KAT templates take `enable_thinking`/`preserve_thinking` only).

## Discovery — repeat 1 of 2

**Total 64.5/100** — gates 5/5 · rubric 59.5/95 · 2026-09-23. Orchestrator spot-checked (no `c#:` in patch; `fetchNextPage` in scroll effect; scrollRect workaround deleted; sync `revokeObjectURL`; no `loading` prop) — all confirmed.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3/6 | Backlog append + per-entry append preserved, but no `onreconnected` tail reset. |
| 5 | 1 | 9/9 | `Range/Read` pagination correct: `offset`/`limit:200`/`descending:false`, `getNextPageParam` → `NextOffset`, `level` singular. |
| 6 | 0.5 | 1.5/3 | Content-sensitive key, Set→array, but `Array.from(activeLevels)` insertion-ordered, not sorted. |
| 7 | 0 | 0/10 | **No DSL handling at all** — `message` sent raw (queries.ts:90); no `c#:` wrap, no passthrough. |
| 8 | 1 | 5/5 | Empty `message`/`level` omitted, never sent as empty strings. |
| 9 | 1 | 6/6 | `hasActiveFilters` correctly switches live ↔ search. |
| 10 | 0.5 | 2/4 | Six levels, toggleable, active styling — no tooltip; chips gated behind `hasActiveFilters`. |
| 11 | 1 | 3/3 | `useDebounceValue(search.trim(), 250)`. |
| 12 | 0.5 | 1.5/3 | `clearFilters` resets both; scroll-lock hidden (not disabled) while filters active. |
| 13 | 0 | 0/1 | Header bare "Logs" — no live-count / server-search hint. |
| 14 | 0.5 | 3/6 | Kept old `throttle`+`setTimeout` snapshot approach, not bottom-distance check. |
| 15 | 0 | 0/3 | Inline `scrollRect` workaround **removed** and never replaced — TanStack #634 regression. |
| 16 | 1 | 3/3 | Live spinner gated on `logLines.length === 0` (initial only). |
| 17 | 1 | 5/5 | `fetchNextPage` invoked via scroll listener (<200px from bottom), not render-phase, no debounce. |
| 18 | 0.5 | 2/4 | Searching + no-results/clear states present; **no phantom loader row**. |
| 19 | 1 | 6/6 | Endpoint switch (Range vs File/Current) + `level`/`message` correct names. |
| 20 | 0.5 | 2.5/5 | Object URL + DOM anchor; but **sync** revoke and static `shoko-logs.txt` filename (no date/time). |
| 21 | 1 | 4/4 | `Button loading={isDownloading}` spinner + `toast.error` on failure. |
| 22 | 0 | 0/3 | `IconButton` never gains `loading` prop — sidestepped via `Button`. |
| 23 | 0.5 | 1.5/3 | Placeholder removed; but `LogSearchFilters` unused export; `LogLineType` kept alongside `LogEntryType`. |
| 24 | 0.5 | 1.5/3 | Types + optional fields modeled; but `Level` bare `string`, `NextOffset?` loose, `as unknown as Blob` cast. |

**Key findings:**

- Solid API integration + search plumbing (working infinite scroll, endpoint switch, correct contract), completely missing DSL (7=0, 10 pts).
- r1 regressions: **chicken-and-egg level chips** (render only when `hasActiveFilters` → level-only filtering unreachable), deleted scrollRect workaround, scroll listener bound to a stale element after view switch, `new Blob([...])` double-wrap cast.

## Discovery — repeat 2 of 2

**Total 66.5/100** — gates 5/5 · rubric 61.5/95 · 2026-09-23. Note: the first eval's lint gate failed on a transient oxlint flake (`Cannot find module 'react-use-measure'` ×39, all in files the patch never touched); lint passed on re-run, gates re-recorded 5/5. Orchestrator spot-checked the load-bearing claims — all confirmed.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3/6 | Backlog + per-entry append kept; no `withAutomaticReconnect`/`onreconnected` tail reset. |
| 5 | 1 | 9/9 | `Range/Read` with `offset/limit/descending:false`, `NextOffset ?? undefined`, all param names correct. |
| 6 | 0 | 0/3 | Query key `['logs','search', search, levels]` with raw `string[]` — toggle order changes the key, not sorted/stable. |
| 7 | 0 | 0/10 | **No DSL handling at all** — raw `search.trim()` as `message`; no `c#:` wrap, no passthrough. |
| 8 | 1 | 5/5 | `message`/`level` omitted when empty. |
| 9 | 1 | 6/6 | `hasFilters` switch logic correct (but behaviorally dead — see findings). |
| 10 | 0.5 | 2/4 | Six levels, toggleable, active styling; no tooltip; chips unreachable (gated behind `levels.length > 0`). |
| 11 | 1 | 3/3 | `debounce(..., 250)` + trim at use sites. |
| 12 | 1 | 3/3 | `clearFilters` resets both; scroll-lock `disabled={hasFilters}`. |
| 13 | 0 | 0/1 | Header bare "Logs". |
| 14 | 0.5 | 3/6 | Kept base scrollTop-snapshot heuristic; no bottom-distance check. |
| 15 | 1 | 3/3 | Inline `scrollRect` workaround preserved (r1 had deleted it — regression fixed). |
| 16 | 1 | 3/3 | Empty-tail spinner gated to `!hasFilters && logLines.length === 0`. |
| 17 | 1 | 5/5 | `fetchNextPage` in `handleScroll` (<200px from bottom); not render-phase, no debounce. |
| 18 | 0.5 | 2/4 | Searching + no-results/Clear states present; no phantom loader row. |
| 19 | 1 | 6/6 | Endpoint switch + `level`/`message` correct names. |
| 20 | 0 | 0/5 | `createObjectURL(data.data)` — axios interceptor already unwrapped, so `data.data` is `undefined` → throws in `onSuccess`; anchor never DOM-attached; sync revoke; no date/time filename. |
| 21 | 1 | 4/4 | `Button loading={isPending}` spinner + `toast.error`. |
| 22 | 0 | 0/3 | `IconButton` untouched; download sidesteps via `Button`. |
| 23 | 1 | 3/3 | Old `logs/queries.ts` + `LogLineType` reused (not dead); placeholder removed; no unused exports. |
| 24 | 0.5 | 1.5/3 | Types modeled, no `any`; but `Level` bare `string`, event fields required (not optional). |

**Key findings:**

- **CRITICAL — circular filter gate**: the search Input is `disabled` whenever `!hasFilters`, and `hasFilters` only becomes true once search is non-empty or a level is active → provably always false; server search, level filtering, and filtered download can never be triggered.
- r2 restored the scrollRect workaround (15: 0→1) and fixed scroll-lock (12: 0.5→1), but shipped the circular gate + `createObjectURL(data.data)` blob misread (20: 0.5→0) and dropped sorting (6: 0.5→0).
- The circular gate isn't captured by any single rubric line — search/level/download are behaviorally dead end-to-end despite lines 5/9/17/19 scoring on code.

## Discovery — variant summary

| Repeat | Rubric /95 | Total /100 |
|---|---|---|
| r1 | 59.5 | 64.5 |
| r2 | 61.5 | 66.5 |
| **Mean** | **60.5** | **65.5** |

Both repeats: full server-contract discovery (line 5 = 9/9), DSL 0, IconButton sidestep (22=0), no reconnect reset, no header hint, snapshot scroll lock, no phantom loader row, tooltip missing. Divergence: r1 broke composition via a chicken-and-egg chip gate + deleted workaround; r2 via an input-level deadlock + a blob misread. Consistent KAT pattern — solid API discovery + correct primitives, broken composition.

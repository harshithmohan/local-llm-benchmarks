# katcoder-v2.5-dev — scores

Run on the **moe-cache fork** (cache 80, 262k ctx, MTP on) on 2026-09-28.

## Run — 2026-09-28

Served as `atlantis/katcoder-apex-i-compact` on the GenerelSchwerz moe-cache fork engine.
No nudges, no auto-compactions.

### Repeat 1 of 2

**Total 66.5/100** — gates 5/5 · rubric 61.5/95 · 2026-09-28 · wall 16m41s.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0 | 0/6 | No reconnect/`onreconnected` reset; a fresh backlog appends to a stale tail. |
| 5 | 1 | 10/10 | `Range/Read`, offset/limit, `NextOffset`, ascending, singular `level` + `message`. |
| 6 | 0.5 | 1.5/3 | Content-sensitive key, but levels not sorted (toggle order changes the key). |
| 7 | 0 | 0/10 | Raw `search.trim()` as `message`; no DSL passthrough, no case-insensitive wrap. |
| 8 | 1 | 5/5 | Empty message/levels omitted. |
| 9 | 1 | 7/7 | Search mode when debounced query or any level active; clearing returns to live. |
| 10 | 1 | 4/4 | Six toggleable levels, each with tooltip + active styling. |
| 11 | 1 | 3/3 | Trimmed + 250 ms debounce. |
| 12 | 1 | 3/3 | Clear resets text+levels; scroll lock disabled under filters. |
| 13 | 0 | 0/1 | Header static "Logs". |
| 14 | 0 | 0/4 | 1 s-snapshot + 50 ms compare; unreliable, cannot tell user vs programmatic scroll. |
| 15 | 1 | 1/1 | Live virtualizer `scrollRect` set from container dimensions. |
| 16 | 1 | 3/3 | Live spinner whenever tail empty. |
| 17 | 1 | 6/6 | Effect near trailing entries calls `fetchNextPage`; not render-phase. |
| 18 | 1 | 5/5 | Pages flattened in order; timestamp/level/message rendered. |
| 19 | 0.5 | 2/4 | First-fetch + no-results/clear present; loader `h-64` not full-height; no phantom row. |
| 20 | 1 | 6/6 | Endpoint switch correct; filtered `level`/`message`; extra `format=simple` on unfiltered. |
| 21 | 0.5 | 1.5/3 | Object URL + DOM anchor, but sync revoke and static filename. |
| 22 | 0.5 | 2/4 | Error toast present; no visible busy indicator. |
| 23 | 0 | 0/1 | `IconButton` not extended with `loading`. |
| 24 | 0 | 0/3 | Legacy `logs/queries.ts` + `LogLineType` retained. |
| 25 | 0.5 | 1.5/3 | Fields modeled; `Level` bare string, not `LogLevelType`. |

### Repeat 2 of 2

**Total 66/100** — gates 5/5 · rubric 61/95 · 2026-09-28 · wall 11m52s.

| # | Score | Pts | Notes |
|---|---|---|---|
| 1 | 1 | 2/2 | `pnpm tscheck` clean. |
| 2 | 1 | 1/1 | `pnpm lint` clean (dprint/oxlint/stylelint). |
| 3 | 1 | 2/2 | `pnpm build` succeeded. |
| 4 | 0 | 0/6 | No reconnect handler/reset; stale tail keeps old entries. |
| 5 | 1 | 10/10 | `Range/Read`, offset/limit, `NextOffset`, `descending:false`, singular `level`+`message`. |
| 6 | 0.5 | 1.5/3 | Set->string key is content-sensitive but unsorted (toggle order changes it). |
| 7 | 0.5 | 5/10 | Valid DSL prefix passes through + empty search omitted, but plain terms not wrapped as case-insensitive contains; invalid prefix not normalized. |
| 8 | 1 | 5/5 | Undefined message/level omitted, never empty strings. |
| 9 | 1 | 7/7 | Debounced non-empty search or levels -> server search; clearing -> live tail. |
| 10 | 0.5 | 2/4 | Six toggleable levels, active styling; no tooltip. |
| 11 | 1 | 3/3 | Trimmed + 250 ms debounce. |
| 12 | 0.5 | 1.5/3 | `clearFilters` resets both, but clear only rendered on empty results; scroll-lock not disabled. |
| 13 | 0 | 0/1 | Header static "Logs". |
| 14 | 0.5 | 2/4 | Delayed compare can detect scroll-up but cannot distinguish user vs programmatic. |
| 15 | 1 | 1/1 | `scrollRect` from live container dimensions. |
| 16 | 1 | 3/3 | Live spinner whenever tail empty. |
| 17 | 0 | 0/6 | `checkLoadMore` in a `useRef` initializer captures initial `isSearchMode===false` -> early return blocks every later-page fetch. |
| 18 | 1 | 5/5 | Pages flattened in order; no apparent drop/duplicate. |
| 19 | 0.5 | 2/4 | First-search + no-results/clear present; no phantom loader row. |
| 20 | 0.5 | 3/6 | Param names correct; unfiltered -> current file, but filtered download also hits `File/Current/Download` instead of `Range/Download`. |
| 21 | 0 | 0/3 | Uses `window.open`, not fetch+blob+DOM anchor with deferred revoke. |
| 22 | 0.5 | 2/4 | Error toast; pending only disables the button (no visible busy indicator). |
| 23 | 0 | 0/1 | `IconButton` not extended with `loading`. |
| 24 | 0.5 | 1.5/3 | Removed obsolete commented placeholder, no unused imports/exports, but old `logs/` file + `LogLineType` remain. |
| 25 | 0.5 | 1.5/3 | Response typed, no `any`; `Level` bare string, not the union. |

### Summary

| Repeat | Rubric /95 | Total /100 | Wall |
|---|---|---|---|
| r1 | 61.5 | 66.5 | 16m41s |
| r2 | 61 | 66 | 11m52s |
| **Mean** | **61.25** | **66.25** | — |

**Key findings:** solid server-contract discovery both repeats (line 5 full), gates clean
both; misses DSL (r1 0 / r2 0.5), reconnect reset (4=0 both), header hint (13=0 both),
chip tooltips, and `IconButton` loading. Each repeat carries one load-bearing wiring break:
r1's unreliable snapshot-based scroll lock (14=0) and sync-revoke download (21=0.5); r2's
`useRef`-captured `checkLoadMore` making later pages unreachable (17=0) plus filtered
download hitting the wrong endpoint (20=0.5). Consistent KAT pattern: correct primitives +
contract discovery, fragile composition.


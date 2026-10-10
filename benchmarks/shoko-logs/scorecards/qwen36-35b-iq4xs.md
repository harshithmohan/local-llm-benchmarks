# qwen36-35b-iq4xs — scores

Parameter set: default (kv-q8). 2-repeat mean.

> Implementation runs used `limit.output` 16384. On **repeat 1** the model spent its
> entire output budget on a planning chain-of-thought and made **no edits** on the cold
> attempt; the patch was produced only after one nudge ("stop reasoning, implement").
> **Repeat 2** needed no nudge. The nudge is a harness intervention, not part of the task.

## Run — 2026-09-27

### Repeat 1 of 2 (nudged)

**Total 54.5/100** — gates 5/5 · rubric 49.5/95 · 26.0 min · 2026-09-27.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0 | 0/6 | No reconnect handler resets the tail; `GetBacklog` + `Log` append, so a reconnect backlog can duplicate stale lines. |
| 5 | 1 | 10/10 | `Range/Read`, offset pages, `NextOffset`, ascending order, correct `level`/`message`/`offset`/`limit`/`descending` names. |
| 6 | 0.5 | 1.5/3 | Content-sensitive key, but `Array.from(activeLevels)` preserves toggle order instead of sorting. |
| 7 | 0 | 0/10 | Always wraps nonempty input as case-sensitive `c:`; DSL not passed through. |
| 8 | 1 | 5/5 | `message`/`level` added only when nonempty. |
| 9 | 0.5 | 3.5/7 | Filters switch views, but mode uses immediate search text, not the debounced value. |
| 10 | 0.5 | 2/4 | Six toggleable levels + active styling; no tooltip. |
| 11 | 0 | 0/3 | 250 ms timer updates a ref without a render/query update; value not trimmed when stored. |
| 12 | 0.5 | 1.5/3 | Clear filters resets text, debounce ref, levels; scroll-lock not disabled while filtering. |
| 13 | 0 | 0/1 | Header stays "Logs"; no count or server-search hint. |
| 14 | 0.5 | 2/4 | Throttled scroll-direction check is heuristic, not a reliable user-scroll detector. |
| 15 | 0 | 0/1 | No live-dimension `scrollRect` workaround. |
| 16 | 0.5 | 1.5/3 | Spinner for empty tail; reconnect does not reset the tail. |
| 17 | 1 | 6/6 | Trailing-edge scroll listener calls `fetchNextPage` from an effect-installed handler. |
| 18 | 1 | 5/5 | Pages flattened in order and rendered from fetched timestamp/level/message. |
| 19 | 0.5 | 2/4 | "No results" + Clear present; first-fetch condition inverted (no searching state while fetching); no phantom loader row. |
| 20 | 0.5 | 3/6 | Filtered requests use `level`/`message`, but downloads always call `Range/Download` even with no filters. |
| 21 | 0.5 | 1.5/3 | Object URL + DOM anchor, but revoked synchronously after click. |
| 22 | 0.5 | 2/4 | Error toast present; download state only disables the button (no visible busy indicator). |
| 23 | 0 | 0/1 | `IconButton` gains no `loading` prop. |
| 24 | 0.5 | 1.5/3 | Commented placeholder removed, but old `logs/queries.ts` and `LogLineType` remain. |
| 25 | 0.5 | 1.5/3 | Result shape modeled; both log level fields bare `string`; no `any` leakage. |

**Key findings:** read contract fully correct (5=10/10) and pagination path invoked
(17=6/6), but the debounce ref is never wired to a query/render update (9, 11) and DSL is
absent (7=0). No reconnect reset; download save flow incomplete.

### Repeat 2 of 2 (clean)

**Total 47.5/100** — gates 5/5 · rubric 42.5/95 · 16.1 min · 2026-09-27.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3/6 | SignalR append intact, but no reconnect reset (fresh backlog can duplicate stale entries). |
| 5 | 0.5 | 5/10 | Correct endpoint/params/`NextOffset`/ascending, but the active query reads `res.data` though `@/core/axios` already unwraps it; a correct hook is defined but unused. |
| 6 | 0.5 | 1.5/3 | Content-sensitive array key, but unsorted → toggle order changes the key. |
| 7 | 0 | 0/10 | No DSL recognition; ordinary text not wrapped as case-insensitive contains. |
| 8 | 1 | 5/5 | Empty `level`/`message` → `undefined`, omitted from requests. |
| 9 | 1 | 7/7 | Active search/level filters select server search; none select the live tail. |
| 10 | 0.5 | 2/4 | Six toggleable levels + active styling; no tooltip. |
| 11 | 0.5 | 1.5/3 | 250 ms debounce and request-time trim; stored value not trimmed, whitespace can still activate search. |
| 12 | 0.5 | 1.5/3 | No-results action clears both; no general clear control; scroll lock not disabled while filtering. |
| 13 | 0 | 0/1 | No count or server-search hint. |
| 14 | 0.5 | 2/4 | Upward-scroll heuristic can't distinguish user from programmatic/measurement scrolls. |
| 15 | 1 | 1/1 | Virtualizer receives live container dimensions via the `scrollRect` workaround. |
| 16 | 0.5 | 1.5/3 | Empty-tail spinner present, but reconnect does not reset the tail. |
| 17 | 0 | 0/6 | `getNextPageParam` defined, but nothing invokes `fetchNextPage` near the trailing row. |
| 18 | 0 | 0/5 | Flatten/render path present, but the `res.data` access conflicts with response unwrapping → entries not rendered reliably. |
| 19 | 0.5 | 2/4 | First-fetch/no-results UI + trailing loader coded; broken result handling makes the loader unreachable. |
| 20 | 1 | 6/6 | Switches current-file vs range-download endpoints; singular `level` + `message` for filtered downloads. |
| 21 | 0 | 0/3 | No success handler creates/clicks an anchor or revokes a URL. |
| 22 | 0.5 | 2/4 | Download button busy state present; failures not surfaced with an error toast. |
| 23 | 0 | 0/1 | `IconButton` not extended; page uses `Button` directly. |
| 24 | 0 | 0/3 | Old `logs/queries.ts` path and `LogLineType` remain; only the commented placeholder was removed. |
| 25 | 0.5 | 1.5/3 | Result shape + optional fields modeled; `LogLineType.Level` stays `string` rather than the `LogLevelType` union. |

**Key findings:** read + download request parameters are correct (8=5/5, 20=6/6) and view
switching works (9=7/7), but the active query mishandles the unwrapped axios response
(5, 18) and never calls `fetchNextPage` (17=0). DSL absent (7=0). No download save flow
(21=0).

## Capability rollup

| Dimension | r1 | r2 | Mean |
|---|---:|---:|---:|
| Discovery & server-contract (20) | 50.0% | 25.0% | 37.5% |
| Implementation (28) | 39.3% | 42.9% | 41.1% |
| Integration & wiring (41) | 62.2% | 58.5% | 60.4% |
| Build hygiene (5) | 100% | 100% | 100% |
| Code quality (6) | 50.0% | 25.0% | 37.5% |
| **Total /100** | 54.5 | 47.5 | **51.0** |

## Summary

| Repeat | Rubric /95 | Total /100 | Run time (min) |
|---|---|---|---|
| 1 (nudged) | 49.5 | 54.5 | 26.0 |
| 2 (clean) | 42.5 | 47.5 | 16.1 |
| **Mean** | **46.0** | **51.0** | **16.1–26.0** |

Run time is wall-clock per run (fresh opencode session, start → last message); repeat 1
includes the nudge. Min–max is over the two repeats.

Both runs nailed the request-contract naming but missed the DSL entirely (7=0 both) and
left one fatal end-to-end break each: r1's debounce ref never triggers a query/render, so
the search wiring is dead; r2's active query mishandles the unwrapped axios response and
never pages. Neither produces a working download save flow. Build gates pass in both —
build hygiene does not catch these runtime data-flow breaks. Spread 7 pts.

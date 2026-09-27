# qwen36-35b-iq4xs — scores

Parameter set: default (kv-q8). 2-repeat mean.

## Repeat 1 of 2

**Total 60.5/100** — gates 5/5 · rubric 55.5/95 · 2026-09-19. Re-weighted re-grade (gates 25→5, rubric 75→95): no fraction changed vs the old grading, only point values.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3/6 | SignalR backlog append + per-entry append intact, but no reconnect reset (`useLogsSubscription` untouched). |
| 5 | 1 | 9/9 | Paginated `Range/Read` with `offset`, `NextOffset`→next / null→exhausted, `descending:false`; param names all correct. |
| 6 | 0.5 | 1.5/3 | Content-sensitive key, Set never hashed — but `Array.from(set)` unsorted → toggle order changes the key. |
| 7 | 0 | 0/10 | No DSL handling at all — no mode-char regex, no `c#:` wrap, no `toServerSearch`. |
| 8 | 1 | 5/5 | Empty `level`/`message` omitted — never sent as empty strings. |
| 9 | 1 | 6/6 | `isSearching` (debounced, trimmed) switches live↔search. |
| 10 | 0.5 | 2/4 | Six levels, toggleable, active styling — no tooltip. |
| 11 | 1 | 3/3 | 250 ms debounce; value trimmed at use. |
| 12 | 1 | 3/3 | `clearFilters` resets both; scroll-lock hidden (not `disabled`) while filters active — functionally equivalent. |
| 13 | 0 | 0/1 | Header is just `Logs`; no mode subtitle. |
| 14 | 0.5 | 3/6 | Base throttle+`setTimeout` scrollTop heuristic retained; not a bottom-distance check. Moot: live view renders 0 rows. |
| 15 | 0 | 0/3 | scrollRect workaround removed — no replacement hook. |
| 16 | 1 | 3/3 | Spinner shown only when `logLines.length === 0` (initial state). |
| 17 | 0.5 | 2.5/5 | `fetchNextPage` invoked, but via IntersectionObserver callback that ignores `isIntersecting` and fires on initial observe → eager fetch. |
| 18 | 0.5 | 2/4 | Searching + no-results/Clear present; no phantom loader row. |
| 19 | 0.5 | 3/6 | Always `Range/Download`, never `File/Current/Download`; names correct but `limit:100` + `format:'Simple'` leak in. |
| 20 | 0.5 | 2.5/5 | Object URL + DOM anchor + local `YYYYMMDD-HHmmss` filename, but synchronous `revokeObjectURL`. |
| 21 | 1 | 4/4 | `Button loading` real spinner + `onError` toast. |
| 22 | 0 | 0/3 | `IconButton` not modified; patch uses `Button` directly. |
| 23 | 0.5 | 1.5/3 | Placeholder removed; unused export `LogSearchQueryResult`. |
| 24 | 0.5 | 1.5/3 | Types modeled, no `any`; but `Level: string` and event fields required. |

**Key findings:**

- **Critical:** a single virtualizer bound to search-result count (`count: searchEntries.length`) leaves the live tail rendering zero rows.
- Nailed the discovery crux (line 5 = 9/9) but missed DSL (7=0), eager pagination, no endpoint switch.

## Repeat 2 of 2

**Total 62/100** — gates 5/5 · rubric 57/95 · 2026-09-19.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3/6 | Live tail retained (backlog + per-entry append), but no `onreconnected` reset. |
| 5 | 1 | 9/9 | `Range/Read` infinite query: `offset` pageParam, `limit:100`, `descending:false`, `level` singular + `message` correct; `getNextPageParam` = `NextOffset`. |
| 6 | 0.5 | 1.5/3 | Set→array derived, not hashed — but unsorted → toggle order changes key. |
| 7 | 0 | 0/10 | No DSL handling — search passed raw as `message`. |
| 8 | 1 | 5/5 | `message`/`level` emit `undefined` when empty. |
| 9 | 1 | 6/6 | `hasFilters` switches live↔search and gates `enabled`. |
| 10 | 0.5 | 2/4 | Six levels, toggleable, active styling + close icon — no tooltip. |
| 11 | 1 | 3/3 | 250 ms debounce of `search.trim()`. |
| 12 | 0.5 | 1.5/3 | `handleClearFilters` resets both; scroll-lock only rendered when `hasFilters` and never disabled — inverted. |
| 13 | 0 | 0/1 | Header shows only "Logs"; no mode hint. |
| 14 | 0.5 | 3/6 | Retained snapshot scroll lock; unreliable under active logging; lock button removed from live mode. |
| 15 | 1 | 3/3 | `rowVirtualizer.scrollRect` patched from live container. |
| 16 | 1 | 3/3 | Empty-tail spinner gated on `logLines.length === 0`. |
| 17 | 0 | 0/5 | `fetchNextPage` never invoked — `SearchVirtualizer` uses `count: results.length` (no sentinel), so the `if (!row)` fetch branch is dead. Only first 100 rows. |
| 18 | 0.5 | 2/4 | Searching + no-results/Clear ✓; phantom loader row is dead code (same count bug). |
| 19 | 1 | 6/6 | `File/Current/Download` vs `Range/Download` switch; `level` + `message` correct. |
| 20 | 0.5 | 2.5/5 | Object URL + DOM-attached anchor; synchronous revoke; no date+time filename. |
| 21 | 0.5 | 2/4 | `disabled` only (no spinner); error toast ✓. |
| 22 | 0 | 0/3 | `IconButton.tsx` untouched; `Button.loading` exists in base but unused. |
| 23 | 1 | 3/3 | Placeholder removed; old file/`LogLineType` reused; no unused exports. |
| 24 | 0.5 | 1.5/3 | Optional fields + result type modeled, no `any` — but `Level` bare `string`. |

**Key findings:**

- **Critical (different from r1):** live tail works, but infinite scroll is dead (`fetchNextPage` unreachable → capped at 100 rows).
- API discovery nailed again (line 5=9/9); DSL 0 again. Endpoint switching (19) now correct.
- Level chips unreachable to initiate (render only when `hasFilters` already true).

## Summary

| Repeat | Rubric /95 | Total /100 |
|---|---|---|
| 1 | 55.5 | 60.5 |
| 2 | 57 | 62 |
| **Mean** | **56.25** | **61.25** |

Both runs nailed API discovery (line 5=9/9) and missed DSL entirely (7=0); they diverged on the critical render bug (r1: live tail renders zero rows; r2: live tail works but infinite scroll dead) and endpoint switching (r1 absent 0.5, r2 correct 1). Spread 1.5 pts.

Pattern: data-layer contract solid in both runs (line 5 = 9/9); DSL absent (7=0); one fatal end-to-end wiring bug per run. The model implements spec'd local mechanics well but repeatedly fails the end-to-end loop (fetch→save blob, page 1→page 2).

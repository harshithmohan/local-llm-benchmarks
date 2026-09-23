# qwen36-35b-iq4xs — scores

Parameter set: default (kv-q8). The only model run on all
three variants (discovery ×2, api-summary ×2, full-spec ×2).

## Discovery — repeat 1 of 2

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

## Discovery — repeat 2 of 2

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

## Discovery — variant summary

| Repeat | Rubric /95 | Total /100 |
|---|---|---|
| 1 | 55.5 | 60.5 |
| 2 | 57 | 62 |
| **Mean** | **56.25** | **61.25** |

Both runs nailed API discovery (line 5=9/9) and missed DSL entirely (7=0); they diverged on the critical render bug (r1: live tail renders zero rows; r2: live tail works but infinite scroll dead) and endpoint switching (r1 absent 0.5, r2 correct 1). Spread 1.5 pts.

## API-summary — repeat 1 of 2

**Total 64.5/100** — gates 5/5 · rubric 59.5/95 · 2026-09-19.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3 | Backlog append + per-entry append preserved, but no reconnect reset. |
| 5 | 1 | 9 | `Range/Read` with `offset`/`limit`/`descending:false`; `NextOffset`→next / null→exhausted; param names all correct. |
| 6 | 1 | 3 | `levelsKey = params.levels?.sort().join(',')` — sorted, order-independent. |
| 7 | 0 | 0 | No DSL handling at all: no `hasDslPrefix` regex, no `c#:` wrap. Raw trimmed text sent as `message`. |
| 8 | 1 | 5 | `message`/`level` only added when non-empty. |
| 9 | 1 | 6 | `hasFilters` switches live↔search; infinite query `enabled: hasFilters`. |
| 10 | 0.5 | 2 | Six levels, toggleable, active styling — no tooltip. |
| 11 | 0.5 | 1.5 | `useDebounceValue(search, 250)` — debounced but **not** trimmed; whitespace-only input activates filters. |
| 12 | 0.5 | 1.5 | `clearFilters` resets both; scroll-lock `IconButton` NOT `disabled` while filters active. |
| 13 | 0 | 0 | Header bare `Logs` text. |
| 14 | 0.5 | 3 | Kept `throttle`+`setTimeout(50ms)` snapshot; no bottom-distance check. |
| 15 | 1 | 3 | Inline `scrollRect` patch present. |
| 16 | 0 | 0 | Empty-tail spinner never renders: `!liveQuery.isSuccess` always false (`initialData: []` ⇒ `isSuccess` true). |
| 17 | 1 | 5 | `fetchNextPage()` in `handleScroll` on bottom-distance <100px; not render-phase, no debounce. |
| 18 | 0.5 | 2 | Searching + no-results/Clear ✓; no phantom loader row. |
| 19 | 1 | 6 | Endpoint switch + `level`/`message` correct names. |
| 20 | 0.5 | 2.5 | Object URL + DOM anchor; synchronous revoke; date-only UTC filename. |
| 21 | 1 | 4 | `Button loading` spinner + `toast.error`. |
| 22 | 0 | 0 | `IconButton` untouched; download uses `Button`. |
| 23 | 0.5 | 1.5 | Placeholder removed, no unused exports; but `LogLineType` retained and `fetchingRef` dead. |
| 24 | 0.5 | 1.5 | Types modeled, no `any`; but `LogEventType.Level` bare `string`. |

**Key findings:**

- Worked end-to-end this time: scroll-triggered pagination (17 full), endpoint switch (19 full), sorted key (6 full) — the API-summary appendix carried the "easy API points."
- Still missed DSL entirely (7=0, grammar in-prompt), no reconnect reset, live spinner dead (16=0), whitespace-only search activates filters (11=0.5).

## API-summary — repeat 2 of 2

**Total 52.5/100** — gates 5/5 · rubric 47.5/95 · 2026-09-19. Widest repeat-to-repeat spread in the benchmark (12 pts).

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3.0/6 | Backlog + per-entry append; no reconnect reset; `useLogsQuery` switched to non-reactive `queryClient.getQueryData` → live updates never re-render. |
| 5 | 0.5 | 4.5/9 | Correct params, but the first page's `useQuery` result is **discarded** (never merged into `allEntries`) → query never drives results. |
| 6 | 0.5 | 1.5/3 | Content-sensitive key but **not sorted** (`levels: [...activeLevels]`). |
| 7 | 0 | 0/10 | **No DSL handling at all.** Raw `message: search.trim()` sent. |
| 8 | 1 | 5/5 | Empty params omitted. |
| 9 | 1 | 6/6 | `hasFilters` switches live↔search. |
| 10 | 0.5 | 2/4 | Six levels, active ring styling — no tooltip. |
| 11 | 1 | 3/3 | `useDebounceValue(search.trim(), 250)`. |
| 12 | 0.5 | 1.5/3 | `clearFilters` resets both; scroll-lock has no `disabled={hasFilters}`. |
| 13 | 0 | 0/1 | Header bare "Logs". |
| 14 | 0.5 | 3/6 | Kept snapshot approach; not robust to programmatic scroll/corrections. |
| 15 | 0 | 0/3 | scrollRect patch **removed**; no replacement. |
| 16 | 1 | 3/3 | Empty-tail spinner gated on `logLines.length === 0` (gating correct; staleness is the line-4 reactivity bug). |
| 17 | 0 | 0/5 | `loadMore` never reachable: render-phase `fetchNextPageDebounced()` on last virtual item, but `allEntries` never populates (first page discarded). |
| 18 | 0.5 | 2/4 | Searching + no-results/Clear present; no phantom loader row; states functionally wrong (always "No results"). |
| 19 | 1 | 6/6 | Endpoint switch correct; `level`(singular) + `message` correct. (Dead because line 20 never saves the blob.) |
| 20 | 0 | 0/5 | Blob handling broken: `createObjectURL(response.data as Blob)` — interceptor already unwrapped, so `response.data` is `undefined` → throws; filtered download only toasts, never saves. |
| 21 | 1 | 4/4 | `Button loading` spinner + `onError` toast. |
| 22 | 0 | 0/3 | `IconButton` unchanged. |
| 23 | 0.5 | 1.5/3 | Placeholder removed; new dead surface (`Chip` props unused, `firstPageQuery` data discarded). |
| 24 | 0.5 | 1.5/3 | Types modeled with `Level` union + optional fields; `any` leakage via `as unknown as` casts. |

**Key findings:**

- Three fatal wiring bugs: (1) first page fetched then discarded → search never surfaces a result; (2) `getQueryData` non-reactive live tail; (3) blob handling broken on both download paths (misread of the axios unwrap interceptor).
- The `as Blob` cast hid the blob bug from the type checker; rubric line 20 (revoke timing/filename) under-prices it.

## API-summary — variant summary

| Repeat | Rubric /95 | Total /100 |
|---|---|---|
| 1 | 59.5 | 64.5 |
| 2 | 47.5 | 52.5 |
| **Mean** | **53.5** | **58.5** |

Both runs got the server contract right (line 5 correct pagination + param names) and missed DSL entirely (7=0 in all four runs so far). Diverged sharply on end-to-end wiring: r1 worked (scroll handler pagination, endpoint switch, sorted key), r2 shipped three fatal bugs.

## Full-spec — repeat 1 of 2

**Total 73/100** — gates 5/5 · rubric 68/95 · 2026-09-19.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3/6 | Backlog + per-entry append retained, but no reconnect reset. |
| 5 | 1 | 9/9 | `Range/Read`, `offset`/`limit`/`descending:false`, `level`(singular) + `message` correct; `NextOffset → next page`. |
| 6 | 1 | 3/3 | `levelParam = [...activeLevels].sort().join(',')` — stable, order-independent. |
| 7 | 0.5 | 5/10 | DSL regex `/^[c=^$~*](!#\|#!)?#:.*$/` **requires `#`**, so bare mode-char DSL and negate-only get re-wrapped. Wrap + empty-skip correct. |
| 8 | 1 | 5/5 | Empty params omitted. |
| 9 | 1 | 6/6 | `hasFilters` switches live↔search. |
| 10 | 0.5 | 2/4 | Six levels, toggleable, active styling — no tooltip. |
| 11 | 0.5 | 1.5/3 | Debounce (250 ms) + trim, but wired to **download only** — search uses `rawSearch`, fires per keystroke. |
| 12 | 0.5 | 1.5/3 | `clearFilters` resets `rawSearch`+`activeLevels` but **not `debouncedSearch`**; scroll-lock hidden, not disabled. |
| 13 | 0 | 0/1 | Header just "Logs". |
| 14 | 1 | 6/6 | Correct bottom-distance check replacing the snapshot hack; stays locked through programmatic scroll. |
| 15 | 1 | 3/3 | `scrollRect` patched from live container. |
| 16 | 0 | 0/3 | Empty-tail spinner **removed**. |
| 17 | 1 | 5/5 | `fetchNextPage` from a scroll listener (within 100px of bottom) in an effect — no render-phase side effect. |
| 18 | 0.5 | 2/4 | Searching ✓, no-results + Clear ✓; no phantom loader row. |
| 19 | 1 | 6/6 | Endpoint switch + `level`/`message` correct names. |
| 20 | 1 | 5/5 | Object URL + DOM-anchored `<a>` + deferred revoke (`setTimeout(…,5000)`) + local `YYYY-MM-DD_HH-mm-ss` filename — all four. |
| 21 | 0.5 | 2/4 | `loading` spinner ✓; no error toast (comment claims "handled by mutation onError" that doesn't exist). |
| 22 | 0 | 0/3 | `IconButton` untouched. |
| 23 | 0.5 | 1.5/3 | Placeholder removed; `LogLineType` retained; unnecessary exports `wrapSearchExpression` + `LogsSearchResult`. |
| 24 | 0.5 | 1.5/3 | Optional fields ✓; `Level: string` (no union); `as unknown as` casts. |

**Key findings:**

- Best run at the time: bottom-distance scroll lock (14 full), deferred revoke + timestamped filename (20 full), scroll-triggered pagination (17 full) — several in-prompt edge behaviors implemented.
- Still: DSL regex over-strict (requires `#`), search not actually debounced, no reconnect reset, no error toast, no phantom loader row, no IconButton loading.

## Full-spec — repeat 2 of 2

**Total 71/100** — gates 5/5 · rubric 66/95 · 2026-09-19.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3/6 | Subscription + per-entry append intact; GetBacklog changed to *replace*; no reconnect reset. |
| 5 | 1 | 9/9 | `Range/Read` with all correct params; `getNextPageParam` = `NextOffset`; `initialPageParam:0`. |
| 6 | 1 | 3/3 | `['logs-search', wrappedMessage, levelParam]`; `levels = Array.from(Set).sort()` — sorted, order-independent. |
| 7 | 0.5 | 5/10 | DSL regex `^[c=^$~*][!#]?[!#]?:.+$` allows `!!`/`##` (violates ≤1 each) → server 400s; `.+$` forces non-empty. Core `c#:` wrap correct. |
| 8 | 1 | 5/5 | Empty params never sent. |
| 9 | 1 | 6/6 | `hasFilters` switches live↔search. |
| 10 | 1 | 4/4 | Six levels, toggleable, `tooltip={level}`, active styling (all `mdiMagnify` — poor UX). |
| 11 | 1 | 3/3 | `throttle(...,250)` + trim at use sites. |
| 12 | 0.5 | 1.5/3 | Clear-filters only in no-results state; no toolbar clear; scroll-lock not `disabled`. |
| 13 | 0 | 0/1 | Header literally `Logs`. |
| 14 | 1 | 6/6 | Bottom-distance check `scrollHeight - scrollTop - clientHeight > 1` replaces the snapshot hack. |
| 15 | 1 | 3/3 | scrollRect patched on both virtualizers (inline). |
| 16 | 1 | 3/3 | Spinner gated on `logLines.length === 0`. |
| 17 | 0 | 0/5 | `fetchNextPage`/`hasNextPage` never referenced (grep 0 hits). Infinite scroll never fetches page 2. |
| 18 | 0.5 | 2/4 | Searching + no-results/Clear ✓; phantom loader dead (footer, not virtual row). |
| 19 | 0.5 | 3/6 | Always `Range/Download` — no endpoint switch; names correct but message raw. |
| 20 | 0 | 0/5 | Mutation fetches a blob and does **nothing** with it — no createObjectURL/anchor/revoke/filename. Download non-functional. |
| 21 | 0.5 | 2/4 | `loading` spinner ✓; no `onError`/toast. |
| 22 | 1 | 3/3 | `loading?: boolean` added to IconButtonProps and wired to Button (first run to touch IconButton). |
| 23 | 1 | 3/3 | `LogLineType` removed (renamed `LogEventType`); placeholder removed; no unused exports. |
| 24 | 0.5 | 1.5/3 | Types modeled with optional fields, no `any`; but `Level: string` bare, forced `row.Level as LogLevel` casts. |

**Key findings:**

- Added `IconButton.loading` (22 full) + clean `LogEventType` rename (23 full) — the only run to touch IconButton.
- But three highest-impact behaviors broken/absent: infinite scroll dead (17=0), download fetches a blob and discards it (20=0), no endpoint switch (19=0.5), reconnect handling missing.

## Full-spec — variant summary

| Repeat | Rubric /95 | Total /100 |
|---|---|---|
| 1 | 68 | 73 |
| 2 | 66 | 71 |
| **Mean** | **67** | **72** |

Tightest variant (2-pt spread). Both runs implemented the in-prompt local mechanics well (bottom-distance scroll lock, deferred revoke + timestamped filename in r1; IconButton.loading + LogEventType rename in r2) but swapped which core loop survives: r1 had working pagination + broken DSL-wrap regex, r2 had dead download + dead infinite scroll. The model implements spec'd *local* mechanics well but repeatedly fails to wire the *end-to-end* loop (fetch→save blob, page 1→page 2).

## Overall

| Variant | Mean /100 |
|---|---|
| discovery | 61.25 |
| api-summary | 58.5 |
| full-spec | 72 |
| **Overall** | **63.9** |

Pattern: data-layer contract solid in all 6 runs (line 5 ≈ full); DSL nearly absent (0 in 4 runs, 0.5×2 under full-spec); one random fatal end-to-end wiring bug per run. Full-spec is its best variant — it executes explicit instructions reliably, which is why it's the natural pipeline *implementer* candidate.

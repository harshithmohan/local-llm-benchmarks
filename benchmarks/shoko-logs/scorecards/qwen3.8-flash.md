# qwen3.8-flash — scores

Parameter set: opencode-go, xhigh reasoning level (its default is xhigh). Single run.

## Discovery — single run

**Total 74.5/100** — gates 5/5 · rubric 69.5/95 · 2026-09-19. Fresh-session grade; orchestrator spot-checked the load-bearing claims (always-`c#:` wrap, render-phase `fetchNextPageDebounced`, endpoint switch, detached anchor + deferred revoke, `LogLineType` removed, no error toast) — all confirmed.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3.0 / 6 | Backlog append + per-entry append present, but no `onreconnected` reset — reconnect re-appends GetBacklog to stale entries. |
| 5 | 1 | 9.0 / 9 | `Range/Read` with `offset`/`limit`/`descending:false`; `getNextPageParam` = `NextOffset ?? undefined`; `level` (singular) + `message` correct. |
| 6 | 1 | 3.0 / 3 | Levels rebuilt from canonical `logLevels` order — toggle order irrelevant; stable, content-sensitive key. |
| 7 | 0.5 | 5.0 / 10 | Default case-insensitive contains (`c#:`) + empty-omission correct, but **no full-grammar passthrough regex** — typed DSL literalized. |
| 8 | 1 | 5.0 / 5 | Empty `levels`/`search` omitted via conditional spread. |
| 9 | 1 | 6.0 / 6 | `filtersActive` switches `entries`/`body` between live and search. |
| 10 | 0.5 | 2.0 / 4 | Six levels, toggleable, active styling — but **no tooltip**. |
| 11 | 1 | 3.0 / 3 | `useDebounceValue(search, 250)` + `.trim()` at read. |
| 12 | 1 | 3.0 / 3 | `clearFilters` resets both; scroll-lock conditionally hidden (functionally equivalent to `disabled`). |
| 13 | 0 | 0.0 / 1 | Header shows only "Logs"; no live-tail line count / server-search hint. |
| 14 | 0.5 | 3.0 / 6 | Kept legacy throttle+50ms-snapshot scroll lock; racy with streaming + programmatic `scrollToIndex`. |
| 15 | 1 | 3.0 / 3 | Inline `rowVirtualizer.scrollRect` patch present. |
| 16 | 1 | 3.0 / 3 | Empty-tail spinner gated to `entries.length===0` in the non-search branch. |
| 17 | 0.5 | 2.5 / 5 | Next page **is** fetched (phantom row → `fetchNextPageDebounced()`), but as a **render-phase side effect** + 50ms debounce. |
| 18 | 1 | 4.0 / 4 | Full-height "Searching…" on first fetch; phantom loader row; "No results" + Clear Filters. |
| 19 | 1 | 6.0 / 6 | `File/Current/Download` ↔ `Range/Download` switch; `level` singular + `message` correct. |
| 20 | 0.5 | 2.5 / 5 | Object URL + deferred revoke (1000ms `setTimeout`), but anchor **never appended to DOM** and no local date+time filename. |
| 21 | 0.5 | 2.0 / 4 | `loading` spinner, but **no error toast** (mutation has no `onError`). |
| 22 | 0 | 0.0 / 3 | `IconButton.tsx` unmodified — no `loading` prop; download uses `Button`. |
| 23 | 1 | 3.0 / 3 | `LogLineType` removed from `api/common.ts`; placeholder replaced; no unused imports. |
| 24 | 0.5 | 1.5 / 3 | Types modeled, no `any`; but `Level` bare `string` and `Logger/Caller/ThreadID/ProcessID` required, not optional. |

**Key findings:**

- Clean data layer + endpoint switch; canonical-order key; search-view states incl. phantom row; `LogLineType` removed.
- Genuine discovery: identified `c#:`, the `format=Json` serialization value, and the `apikey` header without an API summary.
- Notable divergence: downloads use raw `fetch` (not axios) to preserve the server's `Content-Disposition` filename.
- Gaps: no DSL passthrough (7=0.5), render-phase `fetchNextPageDebounced` (17=0.5), detached anchor + no date+time filename (20=0.5), no error toast (21=0.5).

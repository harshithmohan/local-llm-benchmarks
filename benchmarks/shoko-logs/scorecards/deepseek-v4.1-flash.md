# deepseek-v4.1-flash — scores

Parameter set: opencode-go, **high reasoning level** (its default is high). Single run.

## Discovery — single run

**Total 77/100** — gates 5/5 · rubric 72/95 · 2026-09-19. Fresh-session grade; orchestrator spot-checked the load-bearing claims (order-independent key, always-`c#:` wrap, trailing-row `fetchNextPage`, both download endpoints, `disabled={hasFilters}`, sync revoke without DOM attach) — all confirmed.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3 / 6 | Backlog append + per-entry append kept (pre-existing), but no `onreconnected` tail reset / no `withAutomaticReconnect` — reconnect duplicates stale backlog. |
| 5 | 1 | 9 / 9 | `Range/Read` with `offset`/`limit`/`descending:false`; `getNextPageParam: NextOffset ?? undefined`; param names `level`(singular)/`message`/`offset`/`limit`/`descending` all correct. |
| 6 | 1 | 3 / 3 | `normalizeLevels` canonicalizes to `LOG_LEVELS` order → order-independent, content-sensitive key (equivalent to reference `.sort()`). |
| 7 | 0.5 | 5 / 10 | DSL grammar **discovered** (comment in helpers.ts) but **not implemented**: `buildLogFilterParams` always wraps `c#:` and never passes valid DSL through. Correct `c#:` default + empty→undefined, but regex/fuzzy/negate input silently literalized. |
| 8 | 1 | 5 / 5 | Empty `level`/`message` → `undefined`, never sent as `''`. |
| 9 | 1 | 6 / 6 | `hasFilters` switches `logLines` between tail and search, gates query via `enabled`. |
| 10 | 0.5 | 2 / 4 | Six toggleable levels with active styling but **no tooltip** on chips. |
| 11 | 1 | 3 / 3 | `useDebounceValue(search.trim(), 250)`. |
| 12 | 1 | 3 / 3 | `clearFilters` resets search + levels; scroll-lock `IconButton` has `disabled={hasFilters}`. |
| 13 | 0 | 0 / 1 | Header is a static "Logs" title — no live-tail count / server-search hint. |
| 14 | 0.5 | 3 / 6 | Keeps base snapshot/throttle machinery (`throttle(1000)` + `setTimeout(50)`) with a `!hasFilters` guard — unlocks in the common case but is the fragile approach the rubric flags. |
| 15 | 1 | 3 / 3 | Inline `scrollRect` patch retained. |
| 16 | 1 | 3 / 3 | Spinner shown only when `logLines.length===0` (initial live-tail state). |
| 17 | 1 | 5 / 5 | `useEffect` on trailing virtual row invokes `fetchNextPage()`; no render-phase side effect, no debounce. |
| 18 | 0.5 | 2 / 4 | Full-height searching + "No results"/Clear present, but **no phantom loader row** (`count: logLines.length`, no +1). |
| 19 | 1 | 6 / 6 | Endpoint switch `File/Current/Download` vs `Range/Download` on `hasFilters`; `level`(singular)+`message` correct. |
| 20 | 0.5 | 2.5 / 5 | Immediate `revokeObjectURL` after `click()` (no DOM attach, no deferred revoke); date-only filename for current-file download. |
| 21 | 1 | 4 / 4 | `loading={isDownloading}` → Button spinner; `toast.error` on failure. |
| 22 | 0 | 0 / 3 | `IconButton` untouched — no `loading` prop (download uses a plain `Button`). |
| 23 | 1 | 3 / 3 | No dead code; `LogLineType` still used; placeholder removed; no unused exports. |
| 24 | 0.5 | 1.5 / 3 | Result types modeled (`NextOffset: number\|null`), no `any`; but `Level` stays bare `string`, Logger/Caller/ThreadID/ProcessID not modeled. |

**Key findings:**

- Strongest discovery run to date: data layer, param naming, endpoint switching, empty-param omission, key stability, debounce, and next-page fetch trigger all correct.
- The one real miss is the discovery discriminator (line 7): the grammar was found and even documented in a code comment, but the passthrough regex was never written — every search is forced through `c#:`.
- `normalizeLevels` is a clean order-independent canonicalization (arguably nicer than the reference's inline `.sort()`).

# mimo-v2.6-flash — scores

Parameter set: opencode-go (no reasoning levels). Single run.

## Discovery — single run

**Total 79/100** — gates 5/5 · rubric 74/95 · 2026-09-23. Fresh oracle session; orchestrator spot-checked claims and corrected one line (see below).

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0.5 | 3.0 | Backlog append + per-entry append intact (queries.ts:40–58), but no `onreconnected` tail reset — stale backlog duplicates on reconnect. |
| 5 | 1.0 | 9.0 | `Range/Read` with `offset`/`limit`(500≤1000)/`descending:false`; `getNextPageParam` → `NextOffset ?? undefined`. Params `level`/`message` correct. |
| 6 | 1.0 | 3.0 | `levels` kept in canonical `LOG_LEVELS` order by `toggleLevel` re-filter — order-independent key. |
| 7 | 0.5 | 5.0 | Correct `c#:` wrap + empty-omission; **no passthrough** (no mode-char/`!`/`#` regex). Corrected 0→0.5 by orchestrator for cross-run consistency (the patch's `c#:` wrap WITH colon is behaviorally identical to deepseek/qwen3.8/27B-r2; 0 is reserved for the malformed missing-colon wrap). |
| 8 | 1.0 | 5.0 | `level`/`message` only added when non-empty. |
| 9 | 1.0 | 6.0 | `filtersActive` = trimmed-debounced search or any level; switches view. |
| 10 | 0.5 | 2.0 | Six levels, toggleable, active styling — raw `<button>` with **no tooltip**. |
| 11 | 1.0 | 3.0 | `useDebounceValue(search, 250)` + `.trim()`. |
| 12 | 1.0 | 3.0 | `clearFilters` resets search+levels; scroll-lock `disabled={filtersActive}`. |
| 13 | 0.0 | 0.0 | Header bare "Logs" — no live-tail count / server-search hint. |
| 14 | 0.5 | 3.0 | Kept base throttle+`setTimeout` snapshot; no bottom-distance check; can spurious-unlock. |
| 15 | 1.0 | 3.0 | Inline scrollRect workaround retained. |
| 16 | 1.0 | 3.0 | Live empty spinner gated `!filtersActive && length===0` (initial-only). |
| 17 | 1.0 | 5.0 | `fetchNextPage` via scroll-handler bottom-distance trigger <500px, not render-phase; 100 ms debounce is a smell, not a break. |
| 18 | 1.0 | 4.0 | Full-height searching; `isFetchingNextPage` loader; no-results + Clear filters. |
| 19 | 1.0 | 6.0 | Endpoint switch `File/Current/Download` ↔ `Range/Download`; `level`+`message` names correct. |
| 20 | 0.5 | 2.5 | Object URL + date+time filename, but **immediate `revokeObjectURL`** after `click()` and anchor **never appended to DOM**. |
| 21 | 1.0 | 4.0 | `<Button loading>` spinner + `toast.error` on failure. |
| 22 | 0.0 | 0.0 | `IconButton.tsx` untouched — no `loading` prop; download sidesteps via `<Button>`. |
| 23 | 1.0 | 3.0 | Placeholder removed; old `logs/` + `LogLineType` still used; no unused exports/imports. |
| 24 | 0.5 | 1.5 | Types modeled, no `any`; but `LogEntryType.Level: string` (not union) and `Logger/Caller/ThreadID/ProcessID` required. |

**Key findings:**

- New #1 (79). Coherent single-file implementation: correct endpoint/param discovery, live tail kept running, working infinite scroll + download.
- Trips the benchmark discriminator (no DSL passthrough, 7=0.5), plus immediate revoke + no DOM attach, racy snapshot scroll-lock, no IconButton `loading`, no header hint.
- Notables: avoided the `data.data` blob misread (consumes the unwrapped Blob directly); canonical level ordering gives a clean query key; no render-phase side effects or composition deadlocks.

# qwen3.8-flash — scores

Parameter set: opencode-go, **xhigh reasoning level** (`--variant xhigh`; its default).
Cloud reference model — **1 run only** (no repeat-mean; see README → "Run naming and
repeats").

## Single run (xhigh reasoning)

**Total 72/100** — gates 5/5 · rubric 67/95 · 2026-09-28. Run time **10m 22s**
(14:15:40Z–14:26:02Z). **No output-limit nudge, no auto-compaction.** Patch 406 lines:
modified `src/core/react-query/logs/queries.ts`, `src/pages/logs/LogsPage.tsx`; new
`src/core/react-query/logs/types.ts`, `src/core/react-query/logs/mutations.ts`.

Capability subtotals: Discovery & server-contract **75%** · Implementation **61%** ·
Integration & wiring **82%** · Build hygiene **100%** · Code quality **25%**.

> **Maintainer correction (spot-check).** The grader printed **75/100 (70/95)**; its line
> scores are internally consistent. One line was corrected against the patch:
> **#4 → 0** (was 0.5). The SignalR subscription appends backlog + per-entry `Log`, but
> there is **no reconnect handling at all** (base builder has no `withAutomaticReconnect`,
> no `onreconnected` reset) — the same situation scored **0** for deepseek-v4.1-flash,
> glm-5.3-flash, and mimo-v2.6-flash. Line #24's stated reason was also wrong (the
> commented search placeholder **is** removed), but its 0 stands: the old `logs/`
> query file and `LogLineType` are retained.
> Corrected: rubric 67/95, total **72/100**; Integration & wiring 89% → **82%**.

| # | Score | Pts | Notes |
|---|---|---|---|
| 4 | 0 | 0 | Backlog + per-entry append kept, but no reconnect handling/reset — stale tail after reconnect (corrected 0.5→0; see note). |
| 5 | 1 | 10 | `Range/Read` with `offset`/`limit`/`descending:false`, singular `level`+`message`; `getNextPageParam: lastPage => lastPage.NextOffset ?? undefined` (correct `NextOffset` cursor, null exhausts). |
| 6 | 0.5 | 1.5 | Level array is content-sensitive in the key but not sorted — toggle order changes the key. |
| 7 | 0.5 | 5 | `` `c#:${search}` `` wrap (case-insensitive contains) + empty omission, but **no DSL passthrough** prefix check. |
| 8 | 1 | 5 | Empty `message`/`level` conditionally omitted. |
| 9 | 1 | 7 | Debounced search text or any selected level switches live tail ↔ server search. |
| 10 | 0.5 | 2 | Six toggleable levels with active styling; no tooltip. |
| 11 | 1 | 3 | 250 ms debounce + trim. |
| 12 | 1 | 3 | Clear filters resets both; scroll-lock control disabled while filtering. |
| 13 | 0 | 0 | Header bare "Logs"; no live count / server-search hint. |
| 14 | 0.5 | 2 | Base throttled scrollTop-decrease check retained; can mistake programmatic/measurement scrolls for user input. |
| 15 | 1 | 1 | Virtualizer `scrollRect` updated from live container dimensions. |
| 16 | 1 | 3 | Spinner while the live tail is empty; gone once rows arrive. |
| 17 | 1 | 6 | Effect on the last visible virtual item (trailing 25 rows) invokes `fetchNextPage` — not render-phase, not debounced. |
| 18 | 1 | 5 | Pages flattened in order; each entry rendered once from returned timestamp/level/message. |
| 19 | 0.5 | 2 | First-fetch + no-results/Clear-filters states present, but the next-page loader sits below the list (no phantom virtual row). |
| 20 | 1 | 6 | `File/Current/Download` unfiltered ↔ `Range/Download` filtered; singular `level`/`message` names correct. |
| 21 | 0 | 0 | Date-time filename, but anchor **detached** and object URL revoked **synchronously** after `click()` — both wrong. |
| 22 | 1 | 4 | Visible loading state on the button + error toast. |
| 23 | 0 | 0 | `IconButton` not extended with `loading`; download uses `Button` directly. |
| 24 | 0 | 0 | Commented placeholder removed, but the old `logs/queries.ts` path and `LogLineType` are retained. |
| 25 | 0.5 | 1.5 | Response shape typed, no `any`; `Level` is bare `string`, not the `LogLevelType` union. |

**Key findings:**

- Strongest integration of the cloud set: correct `NextOffset` cursor (5=1, the only cloud
  run to get the read contract fully right), trailing-viewport effect pagination with no
  render-phase side effect or debounce (17=1), correct endpoint switch (20=1), flattened
  rendering (18=1), debounce + trim (11=1).
- Trips the discovery discriminator: **no DSL passthrough** — always-`c#:` wrap (7=0.5) —
  and no reconnect handling (4=0).
- Download is broken in practice: detached anchor + synchronous revoke (21=0).
- Legacy `logs/` query file and `LogLineType` kept (24=0); no `IconButton` loading (23=0).

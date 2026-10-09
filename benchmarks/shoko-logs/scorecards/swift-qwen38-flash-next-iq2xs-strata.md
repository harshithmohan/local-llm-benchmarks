# swift-qwen38-flash-next-iq2xs-strata — scores

Line weights mirror `rubric.md` (gates 1–3 = 5 pts; lines 4–25 = 95 pts). Model = `swift-qwen38-flash-next-iq2xs-strata` (Strata pack engine, Swift-1.5 IQ2_XS fine-tune). Grader `opencode-go/gpt-6-luna`, static against the exported patch; the line scores below carry maintainer spot-checks applied against the recorded cohort precedent in `scorecards/qwen38-flash-next-q2_0-strata.md`.

> **Retired 2026-10-09.** The checkpoint was dropped from the serving configuration on these
> results, so its rows were removed from `scorecard.md`; this file is the surviving record. See
> [models/rig1-3060/archive/swift-qwen38-flash-next.md](../../../models/rig1-3060/archive/swift-qwen38-flash-next.md).

## Low reasoning

Parameter set: Strata pack engine, Swift-1.5 IQ2_XS pack, int8 KV, low reasoning.

### Repeat 1 of 2

**Total 61.5/100** — gates 5/5 · rubric 56.5/95 · 23.4 min · 2026-10-09.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | No reconnect reset — the SignalR path appends backlog and entries only, so a reconnect cannot replace the stale tail. |
| 5 | 1 | `Range/Read` + `NextOffset` cursor, `descending:false`, singular `level`/`message`. |
| 6 | 0.5 | Level filter is a `Set` joined in insertion order → order-sensitive `queryKey`. |
| 7 | 0 | DSL written as `` `c#${debouncedSearch}` `` — the terminating `:` is missing, so even the contains wrap is malformed. |
| 8 | 1 | Empty `level`/`message` omitted from the request. |
| 9 | 1 | Debounced non-empty search or any selected level switches live tail → server search. |
| 10 | 0.5 | Six toggleable level chips with active styling, but no tooltip. |
| 11 | 1 | Trimmed + ~250 ms debounce (`useDebounceValue`). |
| 12 | 1 | Clear resets both filters; the scroll-lock control is hidden while filters are active, so it cannot act (inert). **Spot-check 0.5 → 1.** |
| 13 | 0 | Static `Logs` header; no mode/count hint. |
| 14 | 0.5 | Scroll-lock is a throttled scroll-direction heuristic that cannot separate user scrolls from virtualizer measurement. |
| 15 | 1 | `scrollRect` sized from live container dimensions (pre-existing workaround). |
| 16 | 1 | Empty live tail renders a spinner — a pure function of the empty tail, so it also covers a post-reconnect reset. **Spot-check 0.5 → 1.** |
| 17 | 0.5 | `fetchNextPage` invoked during row render (plus a needless debounce) rather than from an effect/trailing row. |
| 18 | 0.5 | Pages flattened in order, but search rows render only TimeStamp/Level/Message — Logger, Caller and Exception dropped. **Spot-check 1 → 0.5.** |
| 19 | 0.5 | First-fetch "searching" and no-results/Clear states present; the next-page spinner is a sibling element, not a phantom row. |
| 20 | 1 | `File/Current/Download` unfiltered, `Range/Download` + singular `level`/`message` when filtered. |
| 21 | 0 | `downloadBlob` clicks a detached anchor then revokes the object URL synchronously — both required safeguards missing. |
| 22 | 1 | Visible download loading state + error toast. |
| 23 | 0 | Download uses a plain `Button`; no `IconButton` `loading` prop. |
| 24 | 0 | Old `logs/queries.ts` and `LogLineType` both retained (the commented placeholder was in fact deleted; the grader's claim that it was kept is wrong) — the reference deletes that file. |
| 25 | 0.5 | Search `Level` typed as the level union, but `LogLineType.Level` stays a bare `string`. |

**Key findings:** the server read contract (`Range/Read`, `NextOffset`, singular `level`) and the download endpoint switch are discovered cleanly, and pagination/concatenation work. The run is a single in-file rewrite of `LogsPage.tsx` plus `logs/{types,queries,mutations}.ts`; it does not adopt the reference's component split (`LogRow`/`LogSearchView`/`LogLiveView`) and keeps the legacy `logs/queries.ts`/`LogLineType`. The DSL colon is missing, so the wrap is malformed; reconnect handling is absent.

### Repeat 2 of 2

**Total 66.5/100** — gates 5/5 · rubric 61.5/95 · 19.2 min · 2026-10-09.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | No reconnect handler/reset; stale tail entries survive a reconnect and the fresh backlog is appended. |
| 5 | 1 | `Range/Read` with `offset`/`limit`, `descending:false`, singular `level`/`message`, `NextOffset` pagination. |
| 6 | 0.5 | Key includes filter content, but the `levels` array is embedded unsorted → toggle-order dependent. |
| 7 | 0.5 | Well-formed case-insensitive `c#:` contains with empty search omitted, but valid user DSL prefixes are never passed through. **Spot-check 0 → 0.5.** |
| 8 | 1 | Empty `level`/`message` omitted via conditional spreads. |
| 9 | 1 | `filtersActive` switches live tail ↔ server results. |
| 10 | 0.5 | Six toggleable levels with active styling, but no tooltip. |
| 11 | 1 | Trimmed + 250 ms debounce. |
| 12 | 1 | Clear resets both filters; the scroll-lock control is not rendered while filters are active. |
| 13 | 0 | Static `Logs` header. |
| 14 | 0.5 | Throttled scroll-direction heuristic; cannot reliably separate user input from programmatic scroll. |
| 15 | 1 | Live-container `scrollRect`. |
| 16 | 1 | Empty-tail spinner while the tail has no entries. |
| 17 | 0.5 | Render-phase `fetchNextPage` behind an extra ~50 ms debounce; no trailing-row trigger. |
| 18 | 0.5 | Pages flattened in order, but rows render only timestamp/level/message (Logger/Caller/Exception dropped). **Spot-check 1 → 0.5.** |
| 19 | 0.5 | First-fetch/no-results/Clear states present; no phantom next-page row. |
| 20 | 1 | Endpoint switch correct; filtered download uses singular `level`/`message`. |
| 21 | 0 | Detached anchor + immediate `URL.revokeObjectURL`. |
| 22 | 1 | Visible loading state; failure surfaces the error toast from the global mutation handler. |
| 23 | 0 | No `IconButton` `loading` prop. |
| 24 | 0 | Old `logs/queries.ts` and `LogLineType` retained rather than removed (the primary dead-code requirement). |
| 25 | 0.5 | Search result/filter types modeled, but `Level` remains a bare `string`. |

**Key findings:** the same data-layer contract as r1 (read pagination, endpoint switch, filter omission) with the search flow wired end to end. It differs from r1 by forming a well-formed `c#:` contains and by hiding (rather than disabling) the scroll lock. Shared misses: reconnect replacement, header mode feedback, the phantom loader row, browser-safe download, and the legacy `logs/queries.ts`/`LogLineType`.

## Medium reasoning

Parameter set: Strata pack engine, Swift-1.5 IQ2_XS pack, int8 KV, medium reasoning.

### Repeat 1 of 2

**Total 42/100** — gates 4/5 · rubric 38/95 · 21.5 min · 2026-10-09.

`pnpm tscheck` and `pnpm build` passed; `pnpm lint` failed at `dprint check` (two unformatted files), so oxlint/stylelint never ran and the gate subtotal is 4/5.

| # | Score | Notes |
|---|---|---|
| 4 | 0.5 | Retains backlog/per-entry append handling, but adds no reconnect reset. |
| 5 | 1 | `Range/Read` offset pages, `NextOffset`, ascending, and the correct `level`/`message`/`offset`/`limit`/`descending` names. |
| 6 | 0.5 | Query key keys on the unsorted level array. |
| 7 | 0.5 | Search always becomes a well-formed `c#:<input>` contains, but valid DSL prefixes are never passed through. **Spot-check 0 → 0.5.** |
| 8 | 1 | Empty `level`/`message` omitted from both read and download requests. |
| 9 | 0 | `LogsPage` unchanged; there is no active-filter state or live/search switch. |
| 10 | 0 | No level chips added. |
| 11 | 0 | No debounced search input added. |
| 12 | 0 | No clear-filters action or filter-aware scroll-lock handling added. |
| 13 | 0 | Header unchanged. |
| 14 | 0.5 | Existing throttled scroll-direction check. |
| 15 | 1 | Existing virtualizer `scrollRect` from live container dimensions. |
| 16 | 1 | Existing live view shows a spinner for an empty tail. |
| 17 | 0 | No search view invokes `fetchNextPage` — defining the infinite query does not fetch later pages. |
| 18 | 0 | The query maps pages but no component concatenates or renders them. |
| 19 | 0 | No search loading, next-page loader, or no-results UI. |
| 20 | 1 | Download selects current-file vs range and sends the required singular `level`/`message`. |
| 21 | 0 | Download anchor detached, object URL revoked immediately. |
| 22 | 0 | No button wiring, visible busy state or error toast. |
| 23 | 0 | No `IconButton` `loading` prop. |
| 24 | 0 | Old `LogLineType` and logs query kept, and the patch adds unused exports (`LOG_LEVELS` plus the new query/mutation hooks). |
| 25 | 0.5 | Search result shape modeled, but `LogEntryType.Level` is a bare `string`. |

**Key findings:** the run is an unintegrated data-layer scaffold — it gets the read contract, filter omission and download endpoint right, but never touches `LogsPage`, so the entire search surface (9–13, 17–19, 22) scores zero and the new hooks are dead code. Lint also fails on formatting, costing the second gate point.

### Repeat 2 of 2

**Total 71/100** — gates 5/5 · rubric 66/95 · 18.2 min · 2026-10-09.

| # | Score | Notes |
|---|---|---|
| 4 | 0.5 | Existing SignalR handlers append backlog/entries, but there is no reconnect reset. |
| 5 | 1 | `Range/Read`, `offset`/`limit`, `descending:false`, singular `level`/`message`, `NextOffset` pagination. |
| 6 | 0.5 | Content-sensitive key part, but the levels array is not sorted → toggle-order dependent. |
| 7 | 0.5 | Always wraps non-empty input as a well-formed `c#:` contains; never passes through valid DSL prefixes. **Spot-check 0 → 0.5.** |
| 8 | 1 | Empty levels/message sent as `undefined`, i.e. omitted. |
| 9 | 1 | Debounced non-empty search or selected levels activate server search; otherwise the live tail. |
| 10 | 0.5 | Six toggleable levels with active styling, but no tooltip. |
| 11 | 1 | Trimmed + 250 ms debounce. |
| 12 | 1 | Clear resets search and levels; scroll lock is disabled while filters are active. |
| 13 | 0 | Header only `Logs`. |
| 14 | 0.5 | Throttled scroll-direction detection. |
| 15 | 1 | Live-container `scrollRect`. |
| 16 | 1 | Empty tail renders a spinner, including an empty reset. |
| 17 | 0.5 | Next pages fetched at the last result row, but from a debounced render-phase call rather than a trailing virtual row. |
| 18 | 0.5 | Pages concatenated in order, but search rows omit Logger, Caller and Exception. **Spot-check 1 → 0.5.** |
| 19 | 0.5 | Full-height initial-search and no-results/Clear states present; the next-page spinner sits below the list rather than as a phantom row. |
| 20 | 1 | Endpoint switch + correct singular `level`/`message`. |
| 21 | 0.5 | Object URL with deferred revoke, but the anchor is never attached to the DOM. |
| 22 | 1 | Visible loading state + error toast. |
| 23 | 0 | Download uses `Button`; no `IconButton` `loading` prop. |
| 24 | 0 | Commented placeholder removed and no new unused imports, but the legacy `logs/queries.ts` and `LogLineType` are retained rather than removed. **Spot-check 0.5 → 0.** |
| 25 | 0.5 | Result/event types modeled with no `any`, but `Level` remains a bare `string`. |

**Key findings:** the most complete search wiring of the medium pair — filter state, view switching, disabled scroll lock, download endpoint choice and loading/error feedback are all connected and all three gates pass. The shared misses are DSL passthrough, reconnect replacement, an order-independent filter key, a phantom loader row, and full download safety (detached anchor).

## Xhigh reasoning

Parameter set: Strata pack engine, Swift-1.5 IQ2_XS pack, int8 KV, xhigh reasoning.

A first xhigh attempt was cut short by an infrastructure fault before it wrote any patch and produced an empty export; it was discarded and the level re-run. Only the two completed repeats below are recorded.

### Repeat 1 of 2

**Total 66.5/100** — gates 5/5 · rubric 61.5/95 · 16.5 min · 2026-10-09.

| # | Score | Notes |
|---|---|---|
| 4 | 0.5 | Backlog/entry append only; no reconnect reset. |
| 5 | 1 | `Range/Read` with `offset`/`limit`, `NextOffset` null-exhaustion, `descending:false`, singular `level`/`message`. |
| 6 | 0.5 | Content-sensitive key, but the `levels` array is unsorted. |
| 7 | 0.5 | Non-empty text wrapped as a case-insensitive contains with empty search omitted, but valid DSL is never passed through. |
| 8 | 1 | `buildLogFilterParams` omits empty `level`/`message`. |
| 9 | 1 | Trimmed/debounced search or any level activates server search; otherwise the live tail. |
| 10 | 1 | Six levels, tooltips and active/inactive styling. |
| 11 | 1 | Trimmed + 250 ms debounce. |
| 12 | 1 | Clear resets both filters; the scroll-lock button is disabled while filters are active. |
| 13 | 0 | Header only `Logs`. |
| 14 | 0.5 | Delayed `scrollTop` comparison; cannot guard against programmatic/measurement scrolls. |
| 15 | 1 | Live-container `scrollRect`. |
| 16 | 1 | Spinner whenever the live tail is empty. |
| 17 | 0.5 | Scroll-proximity `fetchNextPage` with a needless 50 ms debounce rather than a trailing virtual row. |
| 18 | 0.5 | Pages flattened in order, but only TimeStamp/Level/Message are rendered. **Spot-check 1 → 0.5.** |
| 19 | 0.5 | First-fetch/search-empty and next-page spinner present, but the loader is not a phantom row. |
| 20 | 0.5 | Correct endpoint switch with singular `level`/`message`, but sends an extra `format: 'simple'` even on the unfiltered `File/Current/Download` request, which the contract says takes no params. |
| 21 | 0 | Detached anchor plus synchronous revoke. |
| 22 | 0.5 | Visible `Button` loading state, but no error toast on failure. |
| 23 | 0 | No `IconButton` `loading` prop. |
| 24 | 0 | Legacy `LogLineType` and `logs/queries.ts` retained rather than removed. **Spot-check 0.5 → 0.** |
| 25 | 0.5 | Filter levels union-typed and result shape modeled, but event/result `Level` is a bare `string`. |

**Key findings:** the best-structured low-miss run — it adds a shared `logs/helpers.ts` (filter params), six tooltip chips and a disabled scroll lock. It loses points on DSL passthrough, reconnect reset, the phantom loader row, browser-safe download, an unnecessary download `format` param, and leaving the legacy type/file in place.

### Repeat 2 of 2

**Total 71.5/100** — gates 5/5 · rubric 66.5/95 · 18.2 min · 2026-10-09.

| # | Score | Notes |
|---|---|---|
| 4 | 0 | Live SignalR subscription left without a reconnect reset, so stale tail entries are not replaced by the fresh backlog. |
| 5 | 1 | `useLogSearchQuery` sends `offset`/`limit`/`descending:false` and singular `level`/`message`; `NextOffset` drives pagination. |
| 6 | 0.5 | Key includes level contents but uses the unsorted array → toggle-order dependent. |
| 7 | 0.5 | `buildLogFilterParams` always wraps non-empty text as a well-formed `c#:${search}` contains; valid DSL prefixes are not recognised. **Spot-check 0 → 0.5.** |
| 8 | 1 | Omits `level`/`message` when empty. |
| 9 | 1 | `filtersActive` switches displayed entries between server results and the live tail. |
| 10 | 1 | Six level buttons with tooltip and active/inactive styling. |
| 11 | 1 | Trimmed + 250 ms debounce. |
| 12 | 1 | Clear resets both filters; the scroll-lock control is hidden while filters are active (inert). **Spot-check 0.5 → 1.** |
| 13 | 0 | Static `Logs` header; no mode/count hint. |
| 14 | 0.5 | Throttled scroll-direction detection. |
| 15 | 1 | `scrollRect` from live container dimensions. |
| 16 | 1 | Empty tail shows a spinner. **Spot-check 0.5 → 1.** |
| 17 | 1 | An effect fetches the next page when the virtualizer range nears the last five entries — no render-phase side effect and no needless debounce. |
| 18 | 0.5 | Pages flattened in order, but rows render only TimeStamp/Level/Message (`patch.diff:306-308`). **Spot-check 1 → 0.5.** |
| 19 | 0.5 | Initial pending and no-results/Clear states present; no phantom loader row. |
| 20 | 1 | Unfiltered `File/Current/Download`; filtered `Range/Download` with singular `level`/`message`. |
| 21 | 0 | `downloadBlob` clicks a detached anchor and revokes the object URL synchronously (`src/core/util.ts`). |
| 22 | 1 | Visible loading state + error toast. |
| 23 | 0 | Download uses `Button`; no `IconButton` `loading` prop. |
| 24 | 0 | Commented placeholder removed and no new unused exports, but the legacy `logs/queries.ts` and `LogLineType` remain. **Spot-check 0.5 → 0.** |
| 25 | 0.5 | Search levels union-typed and no `any`, but `LogEntryType.Level` is a bare `string`. |

**Key findings:** the cleanest pagination of the pair — 17=1 from an effect on the virtualizer range, with tooltip chips, trim/download feedback and correct endpoint switching. It still misses DSL passthrough, reconnect replacement, the phantom loader row and full download safety, and it renders only three of the log fields.

## Summary

| Reasoning | Repeat | Rubric /95 | Total /100 | Run time (min) |
|---|---|---|---|---|
| low | r1 | 56.5 | 61.5 | 23.4 |
| low | r2 | 61.5 | 66.5 | 19.2 |
| **low** | **Mean** | **59** | **64** | **19.2–23.4** |
| medium | r1 | 38 | 42 | 21.5 |
| medium | r2 | 66 | 71 | 18.2 |
| **medium** | **Mean** | **52** | **56.5** | **18.2–21.5** |
| xhigh | r1 | 61.5 | 66.5 | 16.5 |
| xhigh | r2 | 66.5 | 71.5 | 18.2 |
| **xhigh** | **Mean** | **64** | **69** | **16.5–18.2** |

Run time is wall-clock per run (fresh opencode session, start → last message), so it includes model load; min–max is over the two repeats. No output-limit nudges or auto-compactions in any repeat.

Maintainer spot-checks corrected 16 grader line calls across the six repeats, per the cohort precedent: the well-formed `c#:` contains without DSL passthrough is half credit (line 7: low r2, medium r1, medium r2, xhigh r2), a hidden scroll-lock control is inert and scores full (line 12: low r1, xhigh r2), an empty-tail spinner is a pure function of the empty tail (line 16: low r1, xhigh r2), search rows that render only timestamp/level/message lose half of the rendering line (line 18: low r1, low r2, medium r2, xhigh r1, xhigh r2), and keeping `LogLineType`/`logs/queries.ts` fails the dead-code line (line 24: medium r2, xhigh r1, xhigh r2). medium r1's lint failure is a genuine gate miss (4/5), not a spot-check.

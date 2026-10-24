# Qwen3.6-35B-A3B — scores

Model: `Qwen3.6-35B-A3B`.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| UD-IQ4_XS | default | not converged (11/37) | 29 / 42 | 28.4 | ✅ tscheck · ✅ lint · ✅ build | Filter mode never engaged at any stage; live-tail container had zero height throughout |

## UD-IQ4_XS — default reasoning

Parameter set: UD-IQ4_XS GGUF (`qwen36-35b-ud-iq4xs`), default reasoning level.

### Stage 0 — initial run
- Model time: 15.8 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 10/37
- Score A: 31.5 / 100   Score B: 52.5 / 100
- Context: 5 compress · 2 decompress
- Findings:
  - **Wrong response shape.** The shared request helper already returns the payload and the model unwrapped it a second time, so both search pages and downloads resolved to `undefined` — one cause behind most of the A side.
  - **Double SignalR subscription.** The tail subscribed twice, appending the backlog twice (A1, A19 zero; B2 zero on strict-mode duplicates).
  - **Download never fired.** It gated on `isSuccess` instead of fetching on press (A11–A13 zero).
  - **No expression wrapping.** Plain terms went out unwrapped, missing the `c#:` prefix on all four wrap cases (A18 zero).
  - **Right cold.** DSL heads passed through verbatim (A17 full), text search did switch the view (A2 half), and pagination limits and ordering were correct wherever a request was actually issued.
  - **Discovery held.** No invented endpoint and no reference reading — the sibling server checkout was read correctly.

### Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Keep exactly one live connection for the tail and on reconnect replace the stale entries with the fresh backlog without showing anything twice and without dropping entries that arrive around the reconnect, so the live view stays correct and following new entries keeps working.
  >    Append each backlog entry once and keep appending new arrivals after the reset.
  > 2. Keep the search input, all level filter options, the download control and the scroll lock visible in every state of the logs page including live, loading, empty and failure, and make any active filter such as text alone or a single level selection switch away from the live tail to the server-backed search with filtering done on the server, so filtering is always reachable and behaves the same everywhere.
  >    The scroll lock belongs to the live tail only, so while filters are active it must stay visible but unusable, and a genuine user scroll away from the bottom must release following without programmatic scrolling re-engaging it.
  > 3. Send trimmed search values using the exact parameter shapes the server accepts with empty values omitted, page by feeding each returned continuation marker into the next request until exhausted and joining all pages oldest to newest with seamless loading while scrolling, and ignore or cancel stale in-flight replies when inputs change, so results are complete and newer results are never overwritten by older replies.
  >    While the first fetch is in flight show a loading state, when results are empty and nothing is loading show an empty state that looks different from loading with a way to clear the filters, and when the request fails show a visible failure state that looks different from empty.
  > 4. Treat blank input as no search, pass recognized filter expressions through exactly as typed, and wrap all other ordinary text including strings containing colons or malformed expression heads as a single case-insensitive substring match, so user expressions are honoured and plain terms still match without surprises.
  >    Send the trimmed form so surrounding spaces never reach the server.
  > 5. Make the download control fetch directly when pressed, using the current file with no filters and the filtered range with the same active level and search values when filters are present, show a working state while the download is in flight, report failures with an error toast, and keep the generated download alive until the browser has taken it, so downloads always fire and failures are visible.
- Model time: 4.9 min   Gates: ✅ / ✅ / ✅   Harness: 12/37   Score A: 35 / 100   Score B: 43.5 / 100
- Context: none — stage 0's folding left it under the threshold all round
- Findings:
  - **Search path came alive.** Chips and debounced text both drove `hasFilters` into the server view, with clear returning to the tail (A2 full), and debounce plus trimming landed (B11 full).
  - **Double-unwrap fixed only on the list path.** Download stayed unrouted (A11 zero) and pagination still never rendered a second page (A6 zero).
  - **Second subscription survived.** A1 and B2 stayed zero on duplicate rendering.
  - **Repair-round damage.** A freshly exported `downloadLogs` was never imported (B10 zero) and the query key carried an insertion-ordered level array (B1 zero).

### Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

  > 1. Use server responses directly without unwrapping them a second time, because the shared request helper already returns the payload and an extra unwrap turns every search page and every download into undefined so nothing renders and files come back empty.
  >   Fixing this one handling restores the search list, page joining, and file contents.
  > 2. Keep exactly one live connection for the view and make reconnect replace the stale tail with the fresh backlog without stranding old entries and without dropping entries that arrive around the reset, because duplicate connections double every entry and a clear plus replace loses the window around reconnect.
  > 3. Send the active search text and active levels on every server search and on filtered downloads using only shapes the server accepts, page with the returned cursor until it ends, and join pages seamlessly oldest to newest with stable ordering of levels, because filtering and paging currently never produce rows.
  > 4. Treat typed filter expressions as pass-through as written while wrapping ordinary text including colon bearing literals and malformed heads as ordinary case-insensitive substring search, keeping blank input on the live tail, because plain terms currently go out unwrapped and miss.
  > 5. Cancel or ignore stale reads so an older response never overwrites newer results, keep loading and empty and failure visibly distinct with a way to clear filters on empty, show working state during download with failures as an error toast, and keep the scroll lock active only for the live tail.
- Model time: 7.7 min   Gates: ✅ / ✅ / ✅   Harness: 11/37   Score A: 29 / 100   Score B: 42 / 100
- Context: 5 compress · 0 decompress
- Findings:
  - **Subscription finally fixed.** A1 went full and A19 improved to half.
  - **Filter switch regressed.** Text no longer switched the view (A2 zero), so loading, empty and clear-filters states were never observably entered (A8–A10 zero) and the filtered download range never issued (A11–A13 zero).
  - **Wrapper inverted.** `#c:` reversed instead of `c#:`, with `cfoo:bar` passing through as an expression head (A18 zero).
  - **Zero-height container unaddressed.** All five B2 follow tests failed.
  - **Cancellation still absent** (A20 zero), and a second unused export appeared (B10 zero).

**Outcome:** not converged — 11/37 after two repair rounds, with all three builds green and the ticket's server-discovery work correct throughout; the failures are behavioural (filter switch, expression wrapping, download routing, follow/scroll), not environmental.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|---|---|
| UD-IQ4_XS | default | not converged (11/37) | 29 | 42 | 28.4 | 10 | 2 | 51,167 / 262,144 (20%) |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|---|
| UD-IQ4_XS | 0 | 31.5 | 52.5 | 10/37 | ✅ / ✅ / ✅ | 15.8 | 5 | 2 |
| UD-IQ4_XS | 1 | 35 | 43.5 | 12/37 | ✅ / ✅ / ✅ | 4.9 | 0 | 0 |
| UD-IQ4_XS | 2 | 29 | 42 | 11/37 | ✅ / ✅ / ✅ | 7.7 | 5 | 0 |

- **Discovery was solved cold.** Stage 0 found the real `Logging` controller and hub in the sibling server checkout and built the read parameters, the pagination cursor and the DSL pass-through from source — no invented endpoint, no reference-copying.
- **Stage 0 failed on its own side of the wire, from one cause.** It subscribed the tail twice and unwrapped an already-unwrapped payload; that single double-unwrap sits behind eleven zeros, and the download never fired because it gated on `isSuccess`.
- **Review round 1 fixed the named cause, and cost B.** The list path recovered (A2, B11 full; +1 assertion, +3.5 A) but download stayed dead, a new unused export appeared, and the level array went into the query key unordered — Score B fell 9 points.
- **Review round 2 repaired the subscription and broke the wrapper.** A1 went full, then the expression wrapper inverted (`#c:` instead of `c#:`), which took the filter switch and everything downstream of it with it; the harness ended one assertion below stage 1.
- **The coached number is the least informative one.** Stage 2 is the post-coaching cell; the cold stage is the one that describes the model.
- **Score B is not monotonic, and this run shows it cleanly.** Stage 0 holds the best B of the trajectory, so the B side must be read per stage, never as progress.
- **Time shape.** The initial stage bought the only stable part of the result; the two repair rounds at roughly half its time each moved A +3.5 then −6 and B −9 then −1.5.
- **Not environmental.** Gates green at all three stages, patches 28–30 KB, every turn ended `finish=stop` — the failures are behavioural, so the result stands as recorded.

# swift-qwen38-27b — scores

Model: `swift-qwen38-27b` (Swift-1.5-INT4-fast — a Swift-1.5 fine-tune of Qwen3.8-27B, dense hybrid SSM+attention, served at ctx 176128), run at reasoning level `xhigh`. One trajectory (Stage 0 + two reviewer-driven rounds). One card per model.

Reviewer: `opencode-go/muse-spark-1.3-contributor#xhigh` · Judge: `opencode-go/muse-spark-1.3-contributor#xhigh` — pinned for the whole card; a trajectory is only comparable to another run with the same reviewer.

| Quant | Param set | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|---|
| Swift-1.5-INT4-fast | fp8 KV, ctx 176128, 4 MTP drafts, int8 act | xhigh | not converged (34/37) | 84 / 66.5 | 65.8 | ✅ tscheck · ✅ lint · ✅ build | The three residual harness failures are the search-list continuation (A6/A7, one root cause) and the reconnect-window merge (A19) |

> The first Stage-0 attempt (a ~60-minute run with zero edits) is **not recorded**: the client connection dropped mid-run (`HTTP 499` on the session wait endpoint) and the run ended with the tree untouched. This is a genuine environment failure, not a model result, so the stage was re-run per protocol.

## Swift-1.5-INT4-fast — xhigh reasoning

Parameter set: `swift-qwen38-27b`, reasoning level `xhigh`, served at ctx 176128 (fp8 KV, 4 MTP drafts, INT8 activation), headless provider injected with `limit.context` 176128 and the 32768 output cap, run in an isolated base-commit checkout beside a sibling ShokoServer.

### Stage 0 — initial run
- Model time: 40.4 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 29/37
- Score A: 76.5 /100   Score B: 46.5 /100
- Flags: context: injected 176128 ctx / 32768 out, requests peaked at ~41k tokens in use
- Findings: cold, the model built the whole surface in a single `LogsPage` — live tail, server-backed filtered search, paginated infinite scroll, filter-aware download, DSL pass-through, reconnect handling, cancellation and failure states — and scored A 76.5: full on the tail, the search contract (`Range/Read` with singular `level`, `message`/`offset`/`limit`/`descending=false`), the chip filters, the loading/empty/clear states, the scroll-lock, both download endpoints and their busy/toast affordances, DSL passthrough, cancellation and the read-failure state, plus the three static lines except A14. It lost A6 and A7 entirely (the scroll-proximity + 100 ms-debounced `fetchNextPage` never fired a next-page fetch under the harness, so page 2 never loads and its concatenation is unobservable), A14 (the object-URL was revoked synchronously after the click, which can abort the save), half of A18 (the plain-term wrap keyed on `value.includes(':')` rather than a grammar check, so `http://x`, `a:b` and `cfoo:bar` were passed through as expressions instead of wrapped) and half of A19 (the reconnect path replaced the tail wholesale, dropping an entry that arrived in the reset/replay window). Score B 46.5: full for the live-dimension `scrollRect` workaround, export hygiene and the debounced/trimmed input, halved for the order-dependent query key, the throttle-based scroll-lock release, the initial-only empty spinner and the tooltip-less chips, and zero for the phantom loader row, the mode-blind header, the un-extended `IconButton` and the string-typed `Level`.

### Review round 1 → Stage 1
- Review prompt (verbatim, round 1):
  > Follow-up for the logs work — at most five issues, most severe first. Each item describes observed symptoms and the expected behaviour.
  >
  > 1. Scrolling a filtered search to the end never loads more results. Only the first page of the server search ever appears, even when the server indicates more pages remain, so the second page never joins the first and long result sets stay truncated. Expected behaviour is that moving toward the end of a filtered search pulls the next page using the paging cursor returned with the previous page, pages join seamlessly in oldest to newest order with no dropped or duplicated rows, and paging stops when the server signals there is nothing further.
  >
  > 2. Ordinary search text that happens to contain a colon is sent as if it were a structured filter expression. A web address, a plain word pair joined by a colon, and a malformed expression head are all passed through as written instead of being treated as ordinary text. Expected behaviour is that only genuine filter-expression syntax is passed through as written, all other non-blank input is treated as an ordinary case-insensitive substring search, and empty or blank input means no search filter at all.
  >
  > 3. A live entry arriving in the window around a dropped and re-established live connection is lost. The fresh backlog correctly replaces the stale pre-disconnect entries, but an entry that arrives during the reset and replay interval never appears in the tail. Expected behaviour is that the fresh backlog replaces the now-stale entries while entries arriving around the reconnect are still preserved, with the rest of the view kept consistent through the transition.
  >
  > 4. The scroll-to-bottom follow does not honor genuine user intent. A genuine user scroll upward while following the live tail does not release the follow without snapping back to the bottom, and once released, programmatic movement of the viewport re-engages the follow on its own. Expected behaviour is that a genuine user scroll away from the bottom releases the follow and the viewport stays where the user left it, programmatic scrolling never re-engages a released follow, and the lock control itself stays unavailable while filters are active.
  >
  > 5. A triggered download can be cancelled before the browser saves it. The download button correctly shows busy state and failures surface an error notice, but the temporary download resource is released immediately after the click, so in some browsers the file save is aborted or comes out empty. Expected behaviour is that with no filters the current server log file downloads, with filters the matching range downloads under the same level and search filters as the search view, and every started download reliably completes and saves.
- Model time: 10.5 min      Gates: ✅ tscheck · ✅ lint · ✅ build      Harness: 33/37      Score A: 78 /100   Score B: 45 /100
- Flags: context: injected 176128 ctx / 32768 out, requests peaked at ~65k tokens in use
- Findings: the round fixed three of the five findings — the scroll-lock release now uses a bottom-distance threshold with programmatic-scroll immunity (B2 full), the download revoke is deferred 1 s so the save completes (A14 full), and the DSL wrap boundary now handles the malformed head (`cfoo:bar` wrapped, A18 full). But it inverted the pass-through regex (flags before the mode character), so every flag-bearing expression (`c#:error` → `c#:c#:error`) is double-wrapped: A17 fell from full to zero and A18 rose to full, a net +1.5 on Score A. Pagination still never fired (A6/A7 zero) and the reconnect merge still dropped the window entry (A19 half), so the harness moved only to 33/37. The round also introduced new unused exports, so B10 fell from full to zero; B1, B4, B5, B6, B7, B8, B9 were unchanged. Score A 78 (A6/A7 zero, A17 zero, A19 half), Score B 45.

### Review round 2 → Stage 2
- Review prompt (verbatim, round 2):
  > Follow-up review — filtered search and live tail recovery
  >
  > The live tail, filter switching, empty and error states, and download selection all behave as intended. The items below are ordered by severity. Each describes an observed symptom and the behaviour that is expected instead.
  >
  > 1. Scrolling toward the end of a filtered search never loads further results. Only the first page ever appears, so long result sets cannot be browsed and later pages are never shown. Expected: scrolling toward the end pulls in the next page, pages join up seamlessly oldest to newest, and fetching stops once there is nothing more to show.
  >
  > 2. A log entry arriving around a connection drop and reconnect can disappear from the live tail. The fresh backlog correctly replaces stale pre-disconnect entries, but an entry that arrived in the gap is missing afterwards. Expected: the fresh backlog replaces the stale entries while entries that arrived around the reconnect are preserved, with no stranded stale entries and no dropped fresh ones.
  >
  > 3. A typed search expression that combines a match mode with a case-insensitivity marker is not honoured as written. It arrives at the server wrapped a second time as ordinary text instead of passing through unchanged. Expected: an expression the user typed is passed through as written, ordinary text is treated as an ordinary case-insensitive substring search, and empty or blank input counts as no search.
  >
  > 4. While additional filtered results are being fetched after scrolling, there is no visible indication that more rows are on the way. Expected: loading more rows shows a visible loading-more affordance that is distinct from the initial search loading indicator and from the empty-results state.
  >
  > 5. Selecting the same set of level filters in a different toggle order behaves as a different search. Expected: the same active filter set produces the same search regardless of the order in which the filters were toggled.
- Model time: 15.0 min      Gates: ✅ tscheck · ✅ lint · ✅ build      Harness: 34/37      Score A: 84 /100   Score B: 66.5 /100
- Flags: context: injected 176128 ctx / 32768 out, requests peaked at ~44k tokens in use
- Findings: the round fixed the DSL inversion (the pass-through head regex is now mode-first, `c#:error` verbatim, A17 full back), the toggle-order instability (levels are normalised to declaration order before the query key and the `level` parameter, B1 full), the missing loading-more affordance (a distinct "Loading more…" footer now renders, B5 half) and the reconnect merge (backlog merged with dedupe/sort, but the harness race still drops the window entry, A19 stays half). It also restored export hygiene (B10 full) and widened the type modelling (B9 half, from zero). Pagination still produced zero next-page fetches (A6/A7 zero), so the harness reached only 34/37. Score A 84 (A6/A7 zero, A19 half, every other runtime and static line full), Score B 66.5.

**Outcome:** not converged — gates green but the harness stopped at 34/37 (29 → 33 → 34) after two review rounds. The residual failures are the search-list continuation (A6 zero, A7 zero as its cascade — one root cause) and the reconnect-window merge (A19 half). Score A climbed 76.5 → 78 → 84 and Score B 46.5 → 45 → 66.5.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) |
|---|---|---|---|---|---|
| Swift-1.5-INT4-fast | xhigh | not converged (34/37) | 84 | 66.5 | 65.8 |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) |
|---|---|---|---|---|---|---|
| Swift-1.5-INT4-fast | 0 | 76.5 | 46.5 | 29/37 | ✅ | 40.4 |
| Swift-1.5-INT4-fast | 1 | 78 | 45 | 33/37 | ✅ | 10.5 |
| Swift-1.5-INT4-fast | 2 | 84 | 66.5 | 34/37 | ✅ | 15.0 |

At xhigh, the model produced a strong ticket implementation but never closed it. Stage 0 built the full surface in one pass — 76.5 on Score A with only narrow misses — but its one structural defect, a pagination trigger that never fires (scroll proximity plus a debounce that the harness's virtualized list never trips), survived all three stages and cost A6 and A7 outright; the reconnect-window merge was likewise never fully fixed, holding A19 at half. The two repair rounds were mostly productive on the ancillary surfaces: round 1 fixed the download revoke and the DSL wrap boundary but inverted the pass-through regex (A17 zero, A18 full, a small net gain) and introduced unused exports; round 2 undid the inversion, made the level query key order-independent, added the loading-more footer and restored export hygiene, taking Score A to 84 and Score B to 66.5 — its largest gains. The remaining Score-B gap is production polish: no phantom-row loader, a mode-blind header, an un-extended `IconButton`, tooltip-less chips, a string-typed `Level` and no post-reconnect empty window. Total model time 65.8 min across three stages; harness, reviewer and judge time are not counted — the figure measures the model producing code, not the apparatus measuring it.

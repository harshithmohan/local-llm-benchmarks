# Qwen3.8-Flash-Next · UD-IQ4_XS — scores

Model: `Qwen3.8-Flash-Next`.

Parameter set: UD-IQ4_XS (`qwen38-flash-next-ud-iq4_xs-speedy`), xhigh reasoning level, 204800 ctx / 32768 out-cap.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| UD-IQ4_XS | xhigh | not converged (34/37) | 84 / 56 | 43.2 | ✅ tscheck · ✅ lint · ✅ build | pagination never requested page two and the reconnect reset-window arrival survived both repair rounds; A rose 77 → 84 while B ended below its cold stage |

## Stage 0 — initial run
- Model time: 30.8 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 31/37
- Score A: 77 / 100   Score B: 61.5 / 100
- Context: 4 compress · 0 decompress
- Findings:
  - **The ticket core landed cold.** Live tail, filter switch and clear, six chips, loading/empty/error states, both download routes, DSL pass-through, stale-read cancellation and the retry state all passed (A1–A4, A8–A13, A15–A18, A20–A21), with 31/37 on the first turn.
  - **Pagination never left page one.** No fetch followed the scroll to the end (A6), so the concatenation check cascaded to zero (A7).
  - **The read contract sent empty filters.** A5 zero: `buildLogsParams` sent `level` as an empty string instead of omitting it, failing the singular-name contract test.
  - **The download URL was revoked too early.** A14 zero: `revokeObjectURL` ran immediately after `anchor.click()`, with no DOM append or delay.
  - **Reconnect replaced the tail but dropped the boundary entry.** A19 half: the fresh backlog replaced the stale tail, but an arrival inside the reset window was lost.
  - **Static polish cost B.** Order-dependent query key (B1 0.5), a follow that only half worked (B2 0.5), the loading-more spinner outside the virtualized list (B5 0.5), no chip tooltips (B6 0.5), a static header (B7 0), an unextended `IconButton` (B8 0), and a bare-string `Level` (B9 0.5).

## Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Omit the level filter when no levels are selected and omit the message filter when the search text is blank, keeping singular names with descending off plus offset and limit for paging, because sending empty values breaks the server expectation and empty input must mean inactive.
  > 2. Move the next page trigger out of render into scroll handling or an effect that watches near end rows, passing the continuation marker from the previous response as the next offset and stopping when it is absent with pages joined oldest to newest, because the current render time check never fires so later pages never load.
  > 3. Merge the fresh backlog delivered on reconnect with entries that arrived around the drop by matching identity and timestamp order, discarding stale pre disconnect entries while preserving in window arrivals, because wholesale replacement loses messages that arrived during the reset window.
  > 4. Release the stick to bottom lock on genuine user upward wheel movement and do not reengage it on program driven scrolling, keeping the lock inactive while filters are active, because the current guard only listens while already locked and misses the release gesture.
  > 5. Keep the generated download link attached to the document until after the click has been handled and delay resource cleanup, showing working state while the download is in flight with an error toast on failure, because immediate cleanup can invalidate the download before the browser starts it.
- Model time: 7.4 min   Gates: ✅ / ✅ / ✅   Harness: 33/37   Score A: 80 / 100   Score B: 56 / 100
- Context: 1 compress · 0 decompress
- Findings:
  - **Two contract fixes landed.** A5 and A14 went full — empty filters are omitted, and the object URL now outlives the click. A 77 → 80.
  - **Pagination replaced a dead trigger with an early exit.** The new `getNextPageParam` stops on a short page before the null `NextOffset`, so A6/A7 stayed zero.
  - **Reconnect fell before it recovered.** A19 0.5 → 0: both reconnect tests failed, with stale entries stranded and the window entry dropped.
  - **B2 went full; B3 went to zero.** The follow now releases on a real wheel-up and ignores programmatic scrolling, but `scrollRect` is frozen while filtering, so the virtualizer uses a stale size. B 61.5 → 56.
  - **Static B losses held.** B7, B8 and the half-point B1/B5/B6/B9 gaps were unchanged.

## Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

  > 1. Continue paging through filtered results using only the empty continuation marker from the server to stop, and request each following page with the exact offset the server just returned, because stopping early on a short page prevents the second page from ever loading and leaves combined ordering unobservable.
  > 2. Request the next filtered page directly when scrolling toward the end of the list while more pages remain, without extra debounce delay or visibility blocking that can suppress the request, and keep the loading indicator inside the scrolling flow so reaching the end stays possible, because the expected follow up request after scrolling to the end currently never happens.
  > 3. On every fresh backlog delivered for the live tail, replace the displayed tail with exactly that backlog and discard all prior entries, then keep appending new arrivals normally, including arrivals around the reconnect moment, because keeping and resorting a window of old entries leaves one stale entry stranded and drops one arrival inside the reset window.
  > 4. Accept typed filter expressions that carry both modifiers together in either order as pass through expressions, while still wrapping ordinary text as a case insensitive contains search and ignoring empty input, because dual modifier expressions are currently wrapped and misinterpreted.
- Model time: 5.0 min   Gates: ✅ / ✅ / ✅   Harness: 34/37   Score A: 84 / 100   Score B: 56 / 100
- Context: 0 compress · 0 decompress
- Findings:
  - **Reconnect replacement landed; the window entry still dropped.** A19 0 → 0.5: the fresh backlog now replaces the stale tail, but an arrival during the reset/replay window is still lost — the round-2 note ordered wholesale replacement, and the stage did exactly that.
  - **Pagination never fetched page two.** A6/A7 stayed zero for the third stage; the scroll handler's threshold and guards never produced a second request.
  - **B held at 56.** B3 stayed zero (the filtered view keeps the stale `scrollRect`), B7/B8 stayed zero, and the B1/B5/B6/B9 halves were unchanged.
  - **Scope stayed clean.** The patch touched only Shoko-WebUI paths; no outside-tree reads or `../` references.

**Outcome:** not converged — 34/37 after two repair rounds; the next-page trigger and the reconnect-window arrival survived all three stages, while the repair rounds bought Score A at the cost of part of Score B.

## Summary

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| not converged (34/37) | 84 | 56 | 43.2 | 5 | 0 | 52,586 / 204,800 (25.7%) |

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | 77 | 61.5 | 31/37 | ✅ / ✅ / ✅ | 30.8 | 4 | 0 |
| 1 | 80 | 56 | 33/37 | ✅ / ✅ / ✅ | 7.4 | 1 | 0 |
| 2 | 84 | 56 | 34/37 | ✅ / ✅ / ✅ | 5.0 | 0 | 0 |

- **The cold stage was the strongest B.** 77 A / 61.5 B at 31/37 — the ticket core, states, download routes, DSL and cancellation landed without coaching, with only pagination, the empty-filter contract, the download lifetime and the reconnect boundary missing.
- **Repair rounds bought A, not B.** A climbed 77 → 80 → 84 and the harness 31 → 33 → 34, while B fell 61.5 → 56 in round one and stayed there.
- **Pagination never moved.** A6/A7 zero at every stage: no second-page fetch ever fired, so the concatenation check had nothing to observe.
- **Reconnect needed round two for replacement, never fixed the window.** A19 0.5 → 0 → 0.5; the reset-window arrival was still dropped at stage 2.
- **Cost.** 43.2 min of model time, 30.8 of it the initial stage.

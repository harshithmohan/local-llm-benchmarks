# Qwen3.8-Flash-Next — scores

Model: `Qwen3.8-Flash-Next`.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| IQ3_XXS | xhigh | not converged (33/37) | 91 / 87.5 | 252.9 | ✅ tscheck · ✅ lint · ✅ build | Best cold stage recorded (30/37); pagination duplication and the reconnect window survived both repair rounds |

## IQ3_XXS — xhigh reasoning

Parameter set: IQ3_XXS (`qwen38-flash-next-iq3xxs-strata`), xhigh reasoning level.

### Stage 0 — initial run
- Model time: 112.8 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 30/37
- Score A: 79 / 100   Score B: 66 / 100
- Context: 5 compress · 3 decompress
- Findings:
  - **Nearly the whole ticket landed cold.** A1–A5 (live tail, filter switch, blank input, chips, read contract), A8–A13 (loading/empty/error states and both download routes), A15–A18, A20 and A21 all full, with 30/37 on the first turn.
  - **Pagination never asked for page two.** No fetch followed the scroll to the end, so A6 scored zero and A7's concatenation check cascaded to zero with it.
  - **Reconnect dropped the boundary entry.** Both A19 tests failed: the stale tail was not replaced and an arrival inside the reset window was lost, because arrivals were compared as truncated display timestamps.
  - **The follow never worked in either direction.** B2 zero on all three subtests — a wheel-up did not release the follow, a programmatic scroll re-engaged it, and the lock control was removed while filtering instead of left visible and disabled.
  - **Four static misses.** A14 revoked the object URL immediately after click, B7 left the header at a static `Logs`, B8 never extended the shared icon control, B5 put the loading-more spinner outside the measured list, and B9 kept `Level` as a bare `string`.
  - **Discovery and scope held.** Every endpoint, parameter name and the DSL pass-through were derived from the sibling server checkout, and the patch touched only web-client paths.

### Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Repair continuation of server search results so scrolling near the end reliably requests the next chunk using the continuation value supplied with the previous response and stops only when the server signals no more data.
  >   Keep requesting while the rendered content does not fill the viewport and render the loading more indicator as part of the scrollable flow so measurement stays correct.
  >   Without this the view never asks for a second page and later rows never appear with pages never joining oldest to newest.
  > 2. Fix live tail recovery on reconnect so the fresh replayed backlog replaces stale pre disconnect entries while preserving entries that arrived around the reconnect window.
  >   Compare full precision times rather than truncated display strings and treat same moment arrivals as newer than the backlog, because truncation makes distinct arrivals look equal and drops the boundary entry while leaving stale rows above the fresh backlog.
  > 3. Keep the scroll to bottom lock control always visible and make it inactive while filters are active instead of removing it, and suspend automatic following while filtered.
  >   Make release respond promptly to genuine user upward movement while ignoring programmatic movement, because the control currently disappears when filtering and a released state still scrolls to the bottom while programmatic movement incorrectly reengages following.
  > 4. Keep the temporary download storage alive until the browser has taken ownership of the file instead of releasing it immediately after activation, while keeping the working indication and the failure notification.
  >   Immediate release can cancel the file before it is saved.
  > 5. Show search context in the header area alongside the title, use the shared icon control family with loading support for the download action, model the entry level with the shared level union already used for the filter chips, and keep the continuation spinner inside the measured list.
  >   Without this the header stays static, the download uses a different control, the level remains an unconstrained string, and the spinner sits outside the list flow.
- Model time: 29.7 min   Gates: ✅ / ✅ / ✅   Harness: 31/37   Score A: 87 / 100   Score B: 89 / 100
- Context: 1 compress · 0 decompress
- Findings:
  - **Six of the nine stage-0 gaps closed in one round.** A6, A14, B5, B7, B8 and B9 went full — the cursor fetch, the deferred object-URL release, the spinner inside the virtualized list, the header count, the icon control and the level union.
  - **Pagination fetched, then duplicated.** A6 full but A7 stayed zero: page two arrived and the boundary row rendered twice (five rows against four expected).
  - **The reconnect note missed its own target.** A19 zero again on both tests — the display-truncation comparison the note named was left in place.
  - **The scroll lock was untouched.** B2 zero for the second time on all three subtests.
  - **Repair-round additions stayed clean.** B1 and B10 held at full — no unordered query key, no new dead export — with all three gates green.

### Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

  > 1. Ensure concatenated search pages contain each server entry exactly once in order, without repeating the boundary entry and without counting the trailing status row as an entry, so scrolling through results shows a seamless oldest to newest sequence.
  > 2. On reconnect, discard pre-disconnect tail entries that are already covered by the fresh backlog while preserving only entries strictly newer than the entire backlog, handling empty backlogs and equal timestamps so no stale entry remains above the fresh window and no arrival around the reset is lost, keeping subsequent live appends working.
  > 3. Fix the follow-the-tail release so a genuine user upward scroll immediately releases the lock even when automatic scrolling recently ran, while automatic scrolling itself never toggles the lock, so the view stays where the user left it until they re-engage it and does not jump back to the bottom.
  > 4. Keep the scroll lock control rendered, visible and disabled with an explanatory hint while search filters are active, restoring its normal enabled behavior when filters clear, since the lock applies only to the live tail.
- Model time: 110.5 min   Gates: ✅ / ✅ / ✅   Harness: 33/37   Score A: 91 / 100   Score B: 87.5 / 100
- Context: 5 compress · 2 decompress
- Findings:
  - **Two lines moved, one slipped.** A19 went 0 → 0.5 (the fresh backlog now replaces the stale tail) and B2 went 0 → 0.5 (release and stay-locked hold), but B7 fell 1 → 0 because the header count survived only in search mode — A +4, B −1.5.
  - **Duplication outlived a note that named it.** A7 zero for the third time at five rendered rows against four expected, so the boundary entry was still appended twice.
  - **The window entry is still filtered out.** A19's remaining failure is the equal-timestamp arrival: a strict `>` comparison drops it (expected one, received zero).
  - **The lock control is still not found by the harness.** The tooltip moved onto a wrapper element, so the visible-but-disabled control has no button-level hint — the same missing-element failure as stage 0.
  - **Programmatic scrolling still re-engages the follow**, landing three pixels off the bottom.

**Outcome:** not converged — 33/37 after two repair rounds, with the trajectory's strongest stage still the cold one on the B side; the four remaining failures are behavioural (page boundary duplication, reconnect equality, follow re-engagement, lock visibility), not environmental.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|---|---|
| IQ3_XXS | xhigh | not converged (33/37) | 91 | 87.5 | 252.9 | 11 | 5 | 102,996 / 204,800 (50%) |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|---|
| IQ3_XXS | 0 | 79 | 66 | 30/37 | ✅ / ✅ / ✅ | 112.8 | 5 | 3 |
| IQ3_XXS | 1 | 87 | 89 | 31/37 | ✅ / ✅ / ✅ | 29.7 | 1 | 0 |
| IQ3_XXS | 2 | 91 | 87.5 | 33/37 | ✅ / ✅ / ✅ | 110.5 | 5 | 2 |

- **The cold stage is the result.** 30/37 on the first turn — the ticket core, the states, the download routes, the DSL pass-through and the cancellation all correct without coaching — with only pagination, reconnect and the follow/lock control missing.
- **Repair rounds bought A, not B.** A climbed 79 → 87 → 91 and the harness 30 → 31 → 33, while B peaked in the middle round at 89 and ended below it.
- **Pagination duplication outlived both notes.** A7 zero at every stage, at five rendered rows against four expected, even after the second note described the boundary entry exactly.
- **Reconnect needed the second note to move at all.** Stage 1 changed nothing (A19 zero); stage 2 landed replacement but kept a strict `>` that drops the equal-timestamp arrival.
- **The lock control never appeared to the harness.** B2 was zero then half, with the same missing-element failure at all three stages — the hint ended up on a wrapper rather than the control.
- **Stage 2 traded B for A.** A19 and B2 each gained half a point while B7 lost its header count outside search mode, so the last round is the weaker B cell.
- **Cost.** 252.9 min of model time across the trajectory, 112.8 of it the initial stage — about nine times the qwen36 trajectory's 28.4 min, for 30/37 cold against 10/37.

# Swift-1.5 Qwen3.8-Flash-Next · IQ3_XXS — scores

Model: `Swift-1.5-Qwen3.8-Flash-Next` (GSQ-RCO IQ3_XXS, Strata on Rig 1).

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| IQ3_XXS | xhigh | converged: stage 2 | 100 / 64.5 | 88.1 | ✅ tscheck · ✅ lint · ✅ build | Cold stage already ticket-complete except the download lifetime; the reconnect race took two rounds |

## xhigh reasoning

Parameter set: IQ3_XXS (`swift-flash-next-iq3xxs-strata`), xhigh reasoning level, 204800 ctx / 32768 out-cap.

### Stage 0 — initial run
- Model time: 64.3 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 33/37
- Score A: 95 / 100   Score B: 66 / 100
- Context: 2 compress · 0 decompress
- Findings:
  - **Eighteen of twenty A lines landed cold.** Read contract, DSL pass-through, `NextOffset` pagination, server-side chips, the three distinct states, cancellable reads and the lock semantics all cleared their own harness tests on the first turn.
  - **The download was the one unforced A error.** A14: `saveBlob` called `URL.revokeObjectURL` immediately after `anchor.click`, so the object URL did not outlive the browser claiming the file — the same single miss the base model recorded.
  - **The reconnect window was the real gap.** A19 half: the merge kept the fresh backlog but dropped an entry that arrived during the reset/replay window (`Expected: 1; Received: 0`), which is also what cost B2 both follow specs and B4 its post-reconnect reset.
  - **Polish held B at 66.** Static `Logs` header with no live count or search hint (B7 zero), `IconButton` never gained a loading prop (B8 zero), bare-string `Level` instead of the shared union (B9 half), unsorted level array in the query key (B1 half), chips with active styling but no tooltips (B6 half).
  - **Scope held.** Only web-client paths were touched; the sibling server checkout appears solely as the API the model had to discover.

### Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Preserve a live entry that arrives between clearing the tail for a reconnect and applying the fresh replayed backlog so it is kept in order rather than dropped and the view stays consistent through the reconnect.
  > 2. Make a genuine user upward scroll gesture release the automatic follow and leave the viewport where the user placed it instead of jumping back to the bottom.
  > 3. Allow only an explicit user action on the lock control to turn follow back on after it was released so automatic movement of the list does not turn follow back on by itself.
  > 4. Keep the scroll lock control visible at all times and make it inactive while search or level filters are active then return it to usable state when returning to the live tail since locking belongs to the live tail only.
  > 5. Delay cleanup of the temporary download address until the browser has started the save so the requested content persists long enough to be stored instead of being cancelled by immediate cleanup while showing busy state during the wait and keeping the existing failure notice.
- Model time: 13.3 min   Gates: ✅ / ✅ / ✅   Harness: 34/37   Score A: 92 / 100   Score B: 60 / 100
- Context: 1 compress · 0 decompress
- Findings:
  - **Both follow specs closed, the reconnect regressed further.** A19 fell from half to zero: `queries.ts:54-70` merged by formatted text and timestamp, so a stale entry survived and the racing entry was still lost — one new failure (`fresh backlog replaces stale entries`) on top of the original.
  - **The lock fix made the control unfindable.** B2's third spec still failed because the disabled state swapped the tooltip to `Scroll lock is a live-tail feature` with `opacity-50`, which took the control out of the harness's reach even though the lock itself behaved.
  - **A lost 3 and B lost 6** — the repair round traded a regression in the reconnect merge and the download-clearing behaviour for the two scroll-follow fixes.

### Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

  > 1. Reset the live tail to exactly the fresh backlog delivered on reconnect, discarding all entries held from before the disconnect, then append only entries that arrived after the snapshot without duplication, because stale entries must not remain above the fresh backlog and racing entries must not be lost.
  >   Comparison by formatted text alone can keep a stale entry and drop a racing one when timestamps collide, so order the result by snapshot membership and arrival rather than by text equality.
  > 2. Keep the scroll lock control present and visible with an unusable appearance while any filter is active, restoring interactive behavior when filters clear, because the lock applies to the live tail only yet must stay easy to find during filtering.
  >   Ensure the disabled state does not remove the control from layout or change its accessible name in a way that makes it unfindable.
- Model time: 10.5 min   Gates: ✅ / ✅ / ✅   Harness: 37/37   Score A: 100 / 100   Score B: 64.5 / 100
- Context: 2 compress · 0 decompress
- Findings:
  - **Reconnect went to a replace, not a merge.** Ordering by snapshot membership and arrival instead of text equality closed both `reconnect.a19` specs, and the disabled lock kept its layout and accessible name, closing the last `b2` spec — 37/37 and A 100.
  - **B recovered only part of the stage-1 loss.** B1, B6, B7, B8 and B9 stayed exactly where they were — the notes never asked for sorting, tooltips, a header count, an `IconButton` loading prop or the level union.
  - **B10 fell to zero as collateral.** `LogsDownloadArgsType` was exported from `mutations.ts` and never imported, which the stage-1 run did not do.
  - **The cheapest round of the three.** 10.5 min against 64.3 and 13.3, patch 6 files +516/−94.

**Outcome:** converged: stage 2 — 37/37 with A 100 and B 64.5 after two review rounds.

### Summary

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| converged: stage 2 | 100 | 64.5 | 88.1 | 5 | 0 | 66,699 / 204,800 (33%) |

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | 95 | 66 | 33/37 | ✅ / ✅ / ✅ | 64.3 | 2 | 0 |
| 1 | 92 | 60 | 34/37 | ✅ / ✅ / ✅ | 13.3 | 1 | 0 |
| 2 | 100 | 64.5 | 37/37 | ✅ / ✅ / ✅ | 10.5 | 2 | 0 |

- **Ticket conformance was never the problem.** A 95 on the cold turn with only the download lifetime and the reconnect race outstanding, and A 100 by stage 2.
- **The reconnect merge was the only genuinely hard part.** Two rounds and two different failure modes — a dropped racing entry, then a stale entry kept by text equality — closed only once the tail was rebuilt from the snapshot.
- **A repair round can go backwards.** Stage 1 cost A −3 and B −6 because the merge regressed while the scroll fixes landed; the run needed the second round, not just the first.
- **B is the static-fidelity score, and it barely moved.** 66 → 60 → 64.5 across three stages: header count (B7), `IconButton` loading (B8), chip tooltips (B6), level union (B9) and query-key ordering (B1) were never named by a reviewer note, so no round was going to earn them.
- **Fastest of the recorded trajectories per stage.** 88.1 min total against 252.9 for the base Qwen3.8-Flash-Next at the same harness, with the cold stage 43% shorter (64.3 vs 112.8) and one extra round instead of two.

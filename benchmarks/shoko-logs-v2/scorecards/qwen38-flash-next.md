# qwen38-flash-next — scores (v2)

Model: `qwen38-flash-next-iq3xxs-strata` (Qwen3.8-Flash-Next, 512-expert GSQ-RCO `IQ3_XXS`, ~75.8 GB two-shard build with a separate MTP head), self-hosted by Strata at context 200000 and run at reasoning level `xhigh`. One trajectory per quant/level (Stage 0 + up to two reviewer-driven rounds). One card per model — it covers every quant of `qwen38-flash-next`; quants are rows, not separate cards.

Reviewer: `opencode-go/muse-spark-1.3-contributor#xhigh` · Judge: `opencode-go/muse-spark-1.3-contributor#xhigh` — pinned for the whole card; a trajectory is only comparable to another run with the same reviewer.

| Quant | Param set | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|---|
| IQ3_XXS | Strata int8 KV, ctx 200000, `--expert-cache auto`, `--prefill auto` (lend 95%), MTP `--spec 4` | xhigh | converged: stage 2 | 99.5 / 84 | 76.6 | ✅ tscheck · ✅ lint · ✅ build | No output-cap nudge and no zero-work stop in any stage; harness 33/37 → 0/37 → 37/37 |

> Stage 1's 0/37 is a genuine candidate regression, not an environment failure, and the trajectory is recorded as run: that round renamed the page title away from the reference's plain `Logs`, which the suite's page-open check matches exactly, so every spec — the live-tail test included — failed at page open with `element(s) not found` and Score A collapsed to its three static lines. Stage 2 restored a stable `Logs` title with the mode moved into the count line underneath, and the suite went 37/37.

> Level `xhigh` is the model's declared top reasoning-effort variant, selected with `#xhigh`; the effort reaches the served engine on the wire as `reasoning_effort: xhigh`. Context was injected at 200000 (the served ceiling) with a 32768 output cap, matching the benchmark's nudge rule.

## IQ3_XXS — xhigh reasoning

Parameter set: Strata, context 200000, int8 KV, `--expert-cache auto`, `--prefill auto` at the 95% lend setting, MTP `--spec 4`, reasoning level `xhigh`. Self-hosted on Rig 1's RTX 3060 (~35 t/s decode), so the stage timings are dominated by engine throughput rather than by the harness's fixtures.

### Stage 0 — initial run
- Model time: 45.1 min (no nudge, no zero-work stop; the served entry's cold load falls inside this window)
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 33/37
- Score A: 91 /100   Score B: 61 /100
- Flags: nudges: none; zero-work stop: no; context: served and injected 200000, output cap 32768
- Findings: cold, the model built the whole surface in one pass — live tail, server-backed filtered search with paginated infinite scroll, filter-aware downloads, DSL pass-through and wrapping, reconnect recovery, and cancellation with failure surfacing — scoring A 91. It was full on the tail, the chips, the `Range/Read` parameter contract, pagination, both download endpoints and the busy state, DSL pass-through, cancellation and the three static lines. It lost A7 (search rows rendered the raw ISO stamp while the tail formatted its rows — the search path never ran entries through the same formatter) and half of A19 (the reconnect merge compared formatted second-precision stamps with a strict `>`, dropping an entry that landed in the reconnect window). Score B 61: full for the live `scrollRect` sizing, the tail spinner, chip active styling and tooltips, export hygiene and the deferred-revoke download; half for the 1 s-throttled scroll-follow release (both behavioural B2 tests failed) and for the post-reconnect spinner, the loading-more affordance sitting outside the virtualized list, the chip-tooltip clause and the bare-`string` level typing; zero for the header mode/count and the `IconButton` loading extension.

### Review round 1 → Stage 1
- Review prompt (verbatim, round 1):
  > Follow-up: search display, reconnect handling, and scroll locking need fixes
  >
  > 1. Search results show timestamps in a raw machine form while the live feed shows readable dates and times, so a search row does not display its time the way a live row does. Instead, every row in the filtered results should present its timestamp in the same readable date-and-time form as the live feed.
  > 2. A log entry arriving right around the moment the live feed drops and replays its backlog goes missing from the view. Instead, nothing arriving around a reconnect should be lost: the replayed backlog should replace the stale entries while entries from the reconnect window are kept.
  > 3. Scrolling up with the wheel while locked to the bottom does not release the bottom lock, and automatic movements of the list can switch a released lock back on. Instead, a genuine user scroll up should release the lock and it should stay released until the user turns it back on, with automatic list movements never re-engaging it.
  > 4. The header shows the same bare title whether the page is showing the live feed or filtered server results, with no count and no indication of which mode is on screen. Instead, it should convey how much is being shown in the live mode and make clear when the visible rows are filtered server results.
  > 5. When the next page of filtered results is loading, the loading indicator appears detached below the scrolling rows rather than as the final row within them. Instead, the loading of additional pages should be indicated by a trailing row inside the scrolling list itself.
- Model time: 19.4 min      Gates: ✅✅✅      Harness: 0/37      Score A: 3 /100   Score B: 60 /100
- Flags: nudges: none; zero-work stop: no; context: served 200000, output cap 32768
- Findings: the round addressed all five findings — search rows ran through the tail's shared formatter, the reconnect merge was rewritten around an entry-identity key plus a backlog-window check, the throttled scroll release became an 8 px wheel-up delta with a 100 ms auto-scroll guard, the header gained a mode/count, and the loading-more affordance became a trailing virtual row — but renaming the title to `Live Logs` / `Search Results` broke the harness's page-open check, and all 37 specs failed at page open. Every runtime line therefore zeroed and Score A fell to its three static lines. Score B 60 is a static reading of a view nothing could exercise: full on query-key stability, the phantom loader row and the mode header, halves on the post-reconnect spinner, chip tooltips and level typing, and zero on the `IconButton` extension and both behavioural lines (the scroll-lock and input-discipline tests could not run).

### Review round 2 → Stage 2
- Review prompt (verbatim, round 2):
  > The logs page loads and shows entries, but a few behaviours are off:
  >
  > 1. The page header no longer reads Logs. With no filters it shows a live-mode label instead, and with filters it swaps to a search-mode label. The header is expected to keep a stable Logs title in both modes, with the current mode communicated separately alongside it, for example in the count line underneath.
  > 2. A failed download is silent. When the download request fails nothing visible tells the user it failed. A failed download is expected to surface a visible error toast so the user knows it did not go through.
  > 3. Reconnecting leaves stale content on screen. When the live connection drops and reconnects, the old entries stay painted through the gap before the fresh backlog arrives. The view is expected to reset to its loading appearance across the reconnect, then show the fresh backlog replacing the stale entries, with entries that arrived around the reconnect still accounted for.
  > 4. Downloading does not save a file in Firefox. The download works in Chrome but nothing is saved in Firefox. The download control is expected to trigger a file save in every browser.
  > 5. The level chips give no hover hint about what they do. Hovering a chip is expected to describe whether it will show or hide that level, in addition to the active styling that is already there.
- Model time: 12.1 min      Gates: ✅✅✅      Harness: 37/37      Score A: 99.5 /100   Score B: 84 /100
- Flags: nudges: none; zero-work stop: no; context: served 200000, output cap 32768
- Findings: the round restored the stable `Logs` title and moved mode plus an abbreviated count into the line underneath, surfaced a failure toast on a failed download, reset the view across the reconnect gap before the fresh backlog lands, appended the download anchor to the DOM before clicking so it saves in Firefox, and gave the level chips hover hints. The suite went fully green (37/37) and Score A reached 99.5 — the only docked half-point is the dead-code line, for retaining the old query file and its type alongside the new `logs/` module. Score B 84 leaves two fidelity gaps: the download busy state still reuses the shared `Button` loading instead of extending `IconButton`, and the level type is still a bare `string`. The reconnect path is arguably stronger than the reference — it preserves racing live entries by identity and chronological splice rather than resetting wholesale.

**Outcome:** converged at stage 2 — gates green and the harness at 37/37 after two review rounds (33/37 → 0/37 → 37/37). Score A 91 → 3 → 99.5 and Score B 61 → 60 → 84; the stage-1 dip is the title-rename regression, fixed in stage 2 by keeping the reference's `Logs` heading and reporting the mode separately.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) |
|---|---|---|---|---|---|
| IQ3_XXS | xhigh | converged: stage 2 | 99.5 | 84 | 76.6 |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) |
|---|---|---|---|---|---|---|
| IQ3_XXS | 0 | 91 | 61 | 33/37 | ✅ | 45.1 |
| IQ3_XXS | 1 | 3 | 60 | 0/37 | ✅ | 19.4 |
| IQ3_XXS | 2 | 99.5 | 84 | 37/37 | ✅ | 12.1 |

Cold, the model built the full ticket surface in a single pass and scored A 91, with only the search-row timestamp formatting outright wrong and the reconnect merge half-detected — among the strongest cold conformance recorded so far. Its first repair round fixed every review finding but renamed the page title away from the reference's `Logs`, which broke the harness's page-open check and produced the trajectory's 0/37; the second round restored the stable title and closed the loop at 37/37 with A 99.5. Its ceiling is production fidelity, not correctness: Score B 84 keeps the reference's `IconButton` busy-state extension and the `LogLevelType` union unfilled, so the A/B gap (99.5 vs 84) is exactly the "built the ticket" versus "built it like the reference" separation v2 measures. Total model time 76.6 min across three stages (Stage 0 carries the served entry's cold load); harness, reviewer and judge time are not counted — the figure measures the model producing code, not the apparatus measuring it.

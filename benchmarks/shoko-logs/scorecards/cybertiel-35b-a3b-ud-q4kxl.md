# Cyber-Tiel-Coder-35B-A3B · UD-Q4_K_XL — scores

Model: `Cyber-Tiel-Coder-35B-A3B` (UD-Q4_K_XL GGUF, llama-swap entry `cybertiel-35b-q4kxl` on Rig 2, moe-cache fork, expert cache 192, 250 W cap).

Parameter set: UD-Q4_K_XL (`cybertiel-35b-q4kxl`), default reasoning level, 262144 ctx / 32768 out-cap.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| UD-Q4_K_XL | default | not converged (31/37) | 83 / 66 | 33.8 | ✅ tscheck · ✅ lint · ✅ build | Strongest cold stage in the cohort (29/37, A 83 / B 57.5) and the cleanest DSL handling recorded, then +2 tests in round one and **zero edits in round two** — the final A/B is a second reading of stage-1 code |

## Stage 0 — initial run
- Model time: 24.6 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 29/37
- Score A: 83 / 100   Score B: 57.5 / 100
- Context: 2 compress · 0 decompress
- Findings:
  - **Best cold stage recorded on this ticket.** 29/37 with A 83 / B 57.5 in one pass, against KAT-Coder's 8.5 / 28.5 deadlock and Qwen3.6-35B's 31.5 / 52.5 — and the two things that cost KAT-Coder two rounds were right first time here: the server expression grammar was detected and passed through verbatim, and plain input was wrapped as `c#:` with malformed heads wrapped rather than leaked.
  - **Filtered paging never left page one.** A6 saw a single read with no follow-up after the scroller reached its end, so A7's two-page concatenation had nothing to observe — two [R] lines, one missing effect.
  - **The reconnect reset dropped the racing entry.** The fresh backlog replaced stale rows correctly but the entry landing inside the reset window was lost — A19 half, one failing test.
  - **Search fired per keystroke.** Three keystrokes produced three reads with intermediate values, so B11 lost both its tests.
  - **The scroll lock was wrong in three separate ways.** Wheel-up never released follow, a programmatic scroll re-engaged a released follow, and the lock control was absent rather than visible-but-disabled while filtering — B2 at half.
  - **Five more lines failed statically with the harness green.** A14 revoked the object URL synchronously after `click`, B5 had no loading-more affordance, B7 left the header a static "Logs", B8 never extended `IconButton` for loading, B9 kept `LogLineType.Level` a bare string.
  - **Scope held.** Five `Shoko-WebUI` files, +422/−89, nothing outside the web client.

## Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Make the filtered view load more history as the user scrolls toward the end, sending one follow up request per page with the continuation marker from the prior response and joining pages in order with no drops or repeats, stopping when no further pages remain, and show a loading more indicator distinct from the initial searching indicator and the empty results view with a way to clear filters.
  >   Keep the first page behavior unchanged while ensuring later pages appear seamlessly oldest to newest.
  > 2. Preserve entries that arrive during a live connection drop and replay so the fresh backlog replaces stale entries without losing or duplicating the entries around the reconnect, keeping order and the rest of the view consistent.
  >   The live tail must continue to append new arrivals across the reconnect.
  > 3. Coalesce rapid typing in the search field into a single server request for the settled trimmed value instead of one request per keystroke, ignoring stale responses when inputs change, and surface search failures as a visible error distinct from empty results.
  >   Blank input must remain the live tail.
  > 4. Keep the scroll to bottom lock working for the live tail only, with the control remaining visible but unusable while filters are active and usable again afterward, so a genuine user scroll upward releases follow without snapping back and automatic movement never reengages a released follow.
  >   Entering the filtered view must not keep follow engaged.
- Model time: 8.7 min   Gates: ✅ / ✅ / ✅   Harness: 31/37   Score A: 79 / 100   Score B: 49 / 100
- Context: 1 compress · 0 decompress
- Findings:
  - **The cheapest real repair in the cohort.** +11/−5 in `LogsPage.tsx` bought both B11 tests — a 250 ms `useDebounceValue` and a trimmed value — plus a loading-more affordance: 29 → 31, the only movement the trajectory ever made.
  - **A and B both fell while the build stayed green.** A 83 → 79 and B 57.5 → 49, because the stage-1 sheet grades from the harness report where stage 0 reasoned statically: A19 dropped from half to zero once the window-entry test was read as a failure, and B2 dropped from half to zero on its three tests.
  - **Pagination was attempted and still never fired.** The follow-up effect exists but no second read reached the server, so A6 and A7 stayed at zero.
  - **Four of the five notes went unaddressed.** The reconnect merge (note 2), the scroll-lock intent (note 3), the download release (note 4) and most of the fidelity list (note 5) were untouched; B3 stayed zero for the search virtualizer's missing `scrollRect` workaround.

## Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

  > 1. Make the filtered results list load additional pages as the user scrolls toward the end, joining every page seamlessly oldest to newest and stopping when history is exhausted, because at present only the first page ever shows.
  >   Keep the scroll listener stable across renders and gate follow-up fetches on whether more data remains and no fetch is already in flight.
  > 2. Preserve live entries that arrive between a disconnect and the replayed backlog on reconnect, merging those in-between entries with the fresh backlog instead of discarding them, because the current reset replaces everything and loses messages from the gap.
  >   Keep the rest of the live view consistent through the reset so no stale pre-disconnect entries remain stranded above the fresh data.
  > 3. Make the scroll-to-bottom lock respond only to genuine user intent and stay out of the filtered view, releasing when the user scrolls up and never re-engaging on programmatic scrolling, because the lock currently does not release correctly.
  >   Keep the lock control visible but unusable while filters are active and restore it when filters clear.
  > 4. Delay cleanup of the temporary download link until the browser has had a chance to start the download, because revoking it synchronously cancels the file before it can be saved.
  >   Keep showing working progress while the download is in flight and keep surfacing failures as an error toast.
  > 5. Bring the filtered list and surrounding chrome up to the same fidelity as the live tail, giving both lists the same sizing workaround for the virtualized scroller, showing continued loading as a row inside the list rather than outside it, restoring a loading indication across reconnect gaps, and making the header reflect whether the user is watching the live tail or a server search, because the two modes currently look and behave inconsistently.
- Model time: 0.6 min   Gates: ✅ / ✅ / ✅   Harness: 31/37   Score A: 83 / 100   Score B: 66 / 100
- Context: 0 compress · 0 decompress
- Flags: zero-work stop — the repair turn made no edits (0.6 min, one file read)
- Findings:
  - **The round produced no code at all.** `patch-s2.diff` is byte-identical to `patch-s1.diff` (`cmp`), via a 34-second turn that read `./Shoko-WebUI/src/pages/logs/LogsPage.tsx` once and stopped — the trace records `finish=stop touched=False`. The model announced "Let me make the changes for stage 2" and made none.
  - **The same code scored 4 A points and 17 B points higher.** Identical patch, identical 31/37, and the sheet moved B3 0 → 1, B4 0.5 → 1, A19 0 → 0.5. That is judge variance on unchanged input, not a repair — the recorded A 83 / B 66 is a second reading of stage-1 code.
  - **The three defect clusters were named in both notes and fixed in neither.** Pagination still fetched one page (A6/A7), the reconnect window still dropped its entry (A19), and all three scroll-lock behaviours still failed (B2).
  - **Everything else stayed green.** Gates clean, the DSL and wrap rules still passed, and the harness held at 31/37 with the same six failures as stage 1.

**Outcome:** not converged — 31/37 with A 83 and B 66 after two review rounds, the second of which changed nothing.

## Summary

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| not converged (31/37) | 83 | 66 | 33.8 | 3 | 0 | 58,990 / 262,144 (23%) |

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | 83 | 57.5 | 29/37 | ✅ / ✅ / ✅ | 24.6 | 2 | 0 |
| 1 | 79 | 49 | 31/37 | ✅ / ✅ / ✅ | 8.7 | 1 | 0 |
| 2 | 83 | 66 | 31/37 | ✅ / ✅ / ✅ | 0.6 | 0 | 0 |

- **The strongest cold stage in the cohort, and the least repaired.** 29/37 with A 83 / B 57.5 in one pass — the DSL grammar and the `c#:` wrap that cost KAT-Coder both repair rounds were correct here on the first try — but the trajectory added two tests in round one and nothing after.
- **Where it stops is consistent: three clusters, named in both notes.** Filtered pagination (A6/A7), the reconnect-window entry (A19), and scroll-lock semantics (B2) account for all six remaining failures at every stage after the first.
- **Round two was empty, so its scores measure the judge, not the model.** A byte-identical patch moved A 79 → 83 and B 49 → 66, with B3, B4 and A19 flipping on their own. That is the one place in the cohort where a score change cannot be attributed to code at all.
- **Fast where it counted, then flat.** 24.6 of the 33.8 minutes went into the cold stage that got it to 29/37; the remaining 9.3 minutes bought two tests, and the last 0.6 bought none.
- **Static-only gaps stayed static.** The synchronous `revokeObjectURL` (A14), the unextended `IconButton` (B8) and the bare-string `Level` (B9) were flagged in all three sheets and never touched. The second note did name the static header (B7) and the in-list loading row, but it produced no edits, so nothing moved either way.

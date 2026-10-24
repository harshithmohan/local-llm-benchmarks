# MiMo-V2.6-Flash — scores

Model: `MiMo-V2.6-Flash`.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| — | default | not converged (34/37) | 92 / 72.5 | 47.7 | ✅ tscheck · ✅ lint · ✅ build | Cold stage already ticket-solid at A 80; the reconnect reset and the filtered lock control survived both rounds |

## Default reasoning

Parameter set: no quant (hosted model, `mimo-v2.6-flash`), default reasoning level.

### Stage 0 — initial run
- Model time: 36.8 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 30/37
- Score A: 80 / 100   Score B: 44.5 / 100
- Context: 4 compress · 0 decompress
- Findings:
  - **The cold stage missed the two mechanics the ticket spells out.** A6 and A7 both zero: filtered pagination never fetched a second page, so concatenation had nothing to join — seven harness failures, three of them pagination-shaped.
  - **Download shipped with no state and a self-destroying link.** A13 zero (no busy indication, no error toast) and A14 zero (`URL.revokeObjectURL` called synchronously after the click, so the URL did not outlive the browser taking the file).
  - **Reconnect half-worked.** A19 at 0.5: the fresh backlog did replace stale entries, but the entry arriving inside the reset/replay window was dropped.
  - **The follow control was the largest B cluster.** B2 zero across all three specs — wheel-up release, programmatic re-engagement and the lock control staying visible-but-unusable under an active filter.
  - **Cache identity and header polish went unbuilt.** B1 zero (query key and level param preserved toggle order instead of a canonical sorted key), B7 zero (header stayed a static `Logs`), B8 zero (the shared icon control gained no loading prop).
  - **Fidelity lines landed at half.** B9 0.5 (`Level` stayed a bare string), B5 0.5 (loading-more affordance in the header, not a phantom row inside the virtualizer), B6 0.5 (chips styled, no tooltips), B4 0.5 (initial empty-tail spinner only, none after a reconnect).

### Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Make filtered search pagination reliably fetch the next page as the user scrolls toward the end and join all pages seamlessly oldest to newest without drops or duplicates, stopping only when the server indicates no more data, because filtered results currently stall after the first page.
  >   Keep already loaded rows on screen while the next page loads and guard against duplicate in flight requests for the same continuation marker.
  > 2. Give the download control a visible busy state while the download is in flight and surface download failures as an error toast, keeping the generated download link alive until the browser has taken it, because failures are currently silent with no working indication and early cleanup can prevent the download from completing.
  >   Keep downloading the current file when no filter is active and the filtered range otherwise, using the same level and search values as the visible results.
  > 3. Preserve entries that arrive during the reconnect reset window by merging the replayed backlog with recent live entries and removing only true duplicates, rather than discarding everything at or after the oldest replayed timestamp, because the current cutoff drops entries that arrive around the reconnect while still needing to clear stale pre disconnect entries stranded above the fresh backlog.
  >   Keep the rest of the view consistent through the reset so the live tail continues to append normally afterward.
  > 4. Keep the scroll to bottom lock control always visible but unusable while any filter is active, with automatic following disabled in that mode and restored after clearing, because removing the control entirely breaks expectations and following currently stays engaged when it should be off.
  >   Make a genuine user scroll up release the follow without snapping back to the bottom and ensure programmatic scrolling does not re engage a released follow, while still following new live entries when the follow is engaged.
  > 5. Make the filtered search identity independent of the order in which level filters were toggled by using a canonical sorted order for both caching and the server request, with the search text trimmed and debounced before use, because the same set toggled in a different order currently looks like a different search.
  >   Complete the surrounding polish so loading and empty and error states stay visually distinct, with the incremental loading indicator inside the results area and a live count and search hint in the header and a loading capable download control and descriptive labels for the level choices.
- Model time: 5.2 min   Gates: ✅ / ✅ / ✅   Harness: 32/37   Score A: 84 / 100   Score B: 78.5 / 100
- Context: none — the stage never folded
- Findings:
  - **Round 1 bought the most, and it was B.** 44.5 → 78.5: download gained a busy state and error toast and kept its object URL alive (A13, A14 full), the follow released on a genuine wheel-up, and the toggle-order cache key was canonicalised (B1 full).
  - **Pagination did not move at all.** A6 still zero — no next-page fetch after scrolling to the end — and A7 fell with it, so the same two harness specs failed a second time.
  - **The lock control was removed rather than disabled.** B2 0.5: programmatic scrolling still re-engaged a released follow, and the filtered-mode control never rendered at all.
  - **Cheap round.** 5.2 min against the cold stage's 36.8, patch 4 files +363/−79, all gates green.

### Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

  > 1. Make scrolling near the end of filtered results reliably load the next page and join pages oldest to newest with no missing or repeated rows.
  >   Keep a single in flight guard so one scroll gesture triggers one request, pass the continuation value from the previous response unchanged into the next request, keep loading while that value is present and stop when it is absent, and keep loading when the current content is too short to scroll so short first pages still grow.
  > 2. Keep live entries that arrive around a reconnection while replacing stale pre disconnect entries with the fresh backlog.
  >   Do not filter or order by the displayed second precision timestamp and do not treat equal timestamps plus identical text as duplicates when they are distinct arrivals, and after a reconnect keep any newer arrivals that are not part of the replay while discarding only entries fully covered by the replay, then keep ordering consistent for the rest of the view.
  > 3. Make the follow lock respond only to deliberate user action and stay released until the user re engages it.
  >   Ignore position changes caused by automatic movement to new rows when deciding whether follow is engaged, require an explicit user scroll to the bottom or an explicit toggle press to re engage after a release, and keep the toggle as the single source of truth so automatic movement never flips a released state back on.
  > 4. Keep the scroll lock control always present and visibly disabled while filters are active, then make it usable again when filters clear.
  >   Render the same control in both modes without changing its identity or hiding it behind a different label, only switch its enabled state, and ensure filtering never enables automatic following while still allowing the user to clear filters and return to the live tail.
- Model time: 5.6 min   Gates: ✅ / ✅ / ✅   Harness: 34/37   Score A: 92 / 100   Score B: 72.5 / 100
- Context: none — the stage never folded
- Findings:
  - **Pagination finally closed.** A6 and A7 both pass: the scroll-end fetch reuses the previous `NextOffset` unchanged and stops when it is null, taking the harness to 34/37 and A to 92.
  - **The reconnect fix inverted instead of resolving.** A19 fell 0.5 → 0 — `GetBacklog` merged uncovered stale entries where it should have reset, so stale rows survived the reconnect and both specs now expect zero and see one.
  - **Two lines never converged.** The visible-but-unusable lock under an active filter (B2 0.5) and the reconnect reset (A19 zero) were each named in both review prompts.
  - **The polish lines stayed put.** B8 zero (the shared icon control was never extended), B5 0.5 (affordance outside the virtual rows), B9 0.5 (bare `Level` string), B4 0.5 (no reset spinner, because the reset never empties the tail).
  - **B slipped 6 points while A rose 8.** The round traded a merge for a reset and lost the half-credit A19 had been carrying; B2's half was the only B line it moved.

**Outcome:** not converged — 34/37 after two rounds, with the reconnect reset and the filtered lock control still red.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|---|---|
| — | default | not converged (34/37) | 92 | 72.5 | 47.7 | 4 | 0 | 69,959 / 1,048,576 (7%) |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|---|
| — | 0 | 80 | 44.5 | 30/37 | ✅ / ✅ / ✅ | 36.8 | 4 | 0 |
| — | 1 | 84 | 78.5 | 32/37 | ✅ / ✅ / ✅ | 5.2 | 0 | 0 |
| — | 2 | 92 | 72.5 | 34/37 | ✅ / ✅ / ✅ | 5.6 | 0 | 0 |

- **The cold stage was already ticket-solid.** A 80 on the first turn — the misses were the two runtime mechanics the ticket spells out (no second page fetched, no download busy state, a blob URL revoked before the browser claimed it), not the read contract or the DSL handling.
- **Round 1 was the B round: +34** (44.5 → 78.5) from download state/lifetime and most of the follow behaviour, while pagination did not move at all.
- **Round 2 was the A round: +8** (84 → 92) by closing pagination, and it cost 6 B points as the reconnect fix changed failure mode rather than resolving.
- **Two lines never converged** — the reconnect reset (A19 zero, merged stale rows) and the visible-but-unusable lock under a filter (B2 half) — both named in both review prompts.
- **The polish tail never moved**: the icon control's loading prop (B8 zero), the phantom continuation row (B5 half), a `LogLevelType` union (B9 half) and the reset spinner (B4 half) sat at the same values from stage 0 to stage 2.
- **47.7 min total**, 36.8 of it the cold stage; the two repair rounds together cost 10.8 — the cheapest repair pair recorded so far.
- **Context was never the constraint.** All 4 folds fell in stage 0 and the run finished at 69,959 of a 1,048,576-token window (7%), the widest served window on any card.

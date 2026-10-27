# KAT-Coder-V2.5-Dev — scores

Model: `KAT-Coder-V2.5-Dev` (APEX-I-Compact GGUF, llama-swap entry `katcoder-apex-i-compact` on Rig 2, moe-cache fork).

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| APEX-I-Compact | default | not converged (23/37) | 74.5 / 32 | 22.3 | ✅ tscheck · ✅ lint · ✅ build | Cold stage deadlocked the filter UI at 5/37; each round repaired real ground, and the DSL wrap colon, the pagination cursor and the reconnect window still failed at stage 2 |

## Default reasoning

Parameter set: APEX-I-Compact (`katcoder-apex-i-compact`), default reasoning level, 262144 ctx / 32768 out-cap.

### Stage 0 — initial run
- Model time: 8.9 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 5/37
- Score A: 8.5 / 100   Score B: 28.5 / 100
- Context: 1 compress · 0 decompress
- Findings:
  - **A deadlock at the first render made the whole ticket unreachable.** `LogsPage.tsx` rendered the search input and all six level chips behind `hasFilters` — the control that can only become true *by* using them — so no filter could ever be activated and the server search view was never entered. One cause behind A2–A12, A17–A21 and B11.
  - **The search read unwrapped the wrong envelope level.** `search.ts` read `response.Entries` where the helper already returns `response.data`, so every fetch threw even if it had been reached.
  - **The rest of the omitted ticket landed with it.** No DSL detection or `c#:` wrap, `SearchView` a plain `entries.map` with the sentinel outside the scroller, the download object URL revoked synchronously after `anchor.click`, and the reconnect an atomic replace with no window buffering.
  - **The opening was wasted on guessed absolute paths.** The first two tool calls (`read ./..`, `glob **/*`) errored and the next few greps named paths that do not exist, before a `pwd && ls -la` put it on the real tree.
  - **Scope held.** The patch touched four `Shoko-WebUI` files (+387/−64) and nothing outside the web client.

### Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Always show the search box and all six level selectors even when no filter is active, so the user can start a search from the live view, because hiding them until filters exist makes filtering unreachable and the live view can never switch to search.
  >   Keep the current live tail as the default and switch to the server search view whenever a search string or any level is active, switching back when cleared.
  > 2. Repair the server search fetch so results can actually render, because the current unwrapping reads the wrong envelope level and every request fails and no text driven read or page ever appears.
  >   Send levels sorted and deduplicated with a stable request identity plus a short debounce on typing, and cancel or ignore stale in flight requests so only the newest filter set ever paints.
  > 3. Honour the server filter expression syntax by passing valid expressions through exactly as typed while wrapping ordinary text as a case insensitive substring search, because sending raw text breaks both expression searches and plain searches.
  >   Treat empty or blank input as no search and treat colon bearing literals and malformed heads as ordinary text rather than expressions.
  > 4. Make the search view page seamlessly from oldest to newest with the next page trigger inside the scrolling area using the existing long list pattern with stable unique keys, because a trigger outside the scroller plus a plain list means the next page is never fetched.
  >   Show distinct first load, empty with a clear filters action, and error with a clear filters action states, and keep the scroll to bottom control visible but disabled while filtered since it belongs to live only.
  > 5. Keep downloaded content alive until the browser has taken it by releasing the object link asynchronously after the click, and preserve entries that arrive around a reconnect by merging the fresh backlog window instead of atomically replacing, because immediate release corrupts the file and atomic replace drops window entries and strands stale rows.
  >   Keep the busy indicator during download with an error toast on failure, matching the same level plus message filters as the search view and falling back to the current file with no filters.
- Model time: 11.2 min   Gates: ✅ / ✅ / ✅   Harness: 18/37   Score A: 45.5 / 100   Score B: 33 / 100
- Context: 2 compress · 0 decompress
- Findings:
  - **The deadlock broke and most of the ticket became reachable.** Search and chip paths switched views, blank input stayed on the tail, the lock showed disabled while filtered, both download endpoints and their params landed, and A19's replace half arrived — 5/37 → 18/37, A 8.5 → 45.5.
  - **The DSL wrap used the wrong modifier.** `wrapAsExpression` emitted `ci:` where the contract is `c#:`, and the validator accepted any middle characters, so `cfoo:bar` passed through unwrapped — all four A18 tests failed and B11 with them.
  - **Filter parameters were dropped on follow-on reads.** The search effect called `runFetch(0, messageParam)` without levels and `loadMore` called `runFetch(nextOffset, undefined, undefined)` without either, and `Number(data.NextOffset)` turned the end-of-list `null` into `0`, so A4–A7 and the pagination chain failed.
  - **Reconnect went the other way.** `queries.ts` merged by timestamp instead of resetting, keeping stale rows above the fresh window and still losing the racing entry.
  - **B barely moved (+4.5).** Chatty query-key identity, no follow behaviour, no search virtualizer, chips without tooltips and a static header were all untouched by the note.

### Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

  > 1. Wrap ordinary text as a case insensitive contains expression using the hash modifier and treat malformed heads with extra letters as ordinary text to be wrapped rather than passing them through as written because plain terms currently use the wrong form and invalid heads leak through.
  > 2. Attach the active level choices and the settled search text to every read including follow on pages and preserve the empty end of list marker instead of converting it to zero while letting a level chip alone enter the server search view because filtered paging currently drops filters and stalls and chip only filtering never reaches the server.
  > 3. Discard the stale live tail when the fresh backlog arrives on reconnect instead of merging by timestamp while still keeping entries that arrive around the reconnect window and keeping later live appends working because stale rows currently survive above the fresh window and window entries are lost.
  > 4. Abort or ignore stale in flight reads when inputs change including the debounce window so an older response never paints over newer filter results and always send current filters on retry because a slow earlier read currently overwrites newer output.
  > 5. Show a searching indicator while the first fetch is loading distinct from the empty results state with a way to clear filters and render paged results in the virtualized list with the near end trigger inside the scroller plus a loading more affordance while keeping the scroll lock visible but unusable during filtering and fixing release on user scroll up because loading feedback and endless scrolling and follow behavior are currently broken.
- Model time: 2.2 min   Gates: ✅ / ✅ / ✅   Harness: 23/37   Score A: 74.5 / 100   Score B: 32 / 100
- Context: 0 compress · 0 decompress
- Findings:
  - **A17 and the read contract closed; the wrap colon did not.** `isValidExpression` now matched the real grammar and valid expressions passed through verbatim, but `wrapAsExpression` still returned `` `c#${text}` `` — `c#err` instead of `c#:err` — so all four A18 wrap tests kept failing and dragged B11 with them.
  - **The cursor stayed broken in the other direction.** `Number(data.NextOffset)` still mapped the `null` end marker to `0` and `hasNextPage` to `Boolean(0)`, so paging over-fetched (8 rows where 2 were expected, 4 where 1) and A6 stalled at half.
  - **Search rows skipped `formatTimestamps`.** The list rendered raw ISO `TimeStamp` values, so A7's `YYYY-MM-DD HH:mm:ss` pattern failed even though the live tail formatted correctly.
  - **The reconnect lost the window entry, not the stale one.** Replacing the tail fixed the stale rows but `setQueryData` still dropped the entry that arrived around the reset — A19 half, B4 half.
  - **B fell 1 point.** Pagination's `getNextPageParam` and the loading-more affordance moved B5 to half, but the search virtualizer never gained the live tail's `scrollRect` workaround, which cost B3 outright.
  - **Cheapest round of the three and mostly unscored.** 2.2 min for +35/−28 across two files: A +29 for +8 patch lines, B −1, no new gates.

**Outcome:** not converged — 23/37 with A 74.5 and B 32 after two review rounds.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|---|---|
| APEX-I-Compact | default | not converged (23/37) | 74.5 | 32 | 22.3 | 3 | 0 | 54,581 / 262,144 (21%) |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|---|
| APEX-I-Compact | 0 | 8.5 | 28.5 | 5/37 | ✅ / ✅ / ✅ | 8.9 | 1 | 0 |
| APEX-I-Compact | 1 | 45.5 | 33 | 18/37 | ✅ / ✅ / ✅ | 11.2 | 2 | 0 |
| APEX-I-Compact | 2 | 74.5 | 32 | 23/37 | ✅ / ✅ / ✅ | 2.2 | 0 | 0 |

- **One render-level mistake cost almost the whole ticket.** Stage 0 was not a partial implementation but an unreachable one: gating the controls on `hasFilters` left A2–A12 and A17–A21 with no runtime evidence, so 8.5 is a floor set by a single condition, not a measure of how much code the model wrote.
- **The repair rounds did what the loop is for.** 5 → 18 → 23 of 37, A 8.5 → 45.5 → 74.5, all three gates green every stage: the reviewer's symptom-only notes walked it back to a mostly correct ticket in 13.4 minutes of model time.
- **Three defects survived both rounds, all one-liners.** The missing colon in the `c#:` wrap, `Number(null)` in the cursor and the dropped reconnect-window entry are single-token bugs the notes named in plain language twice; the model re-read them and did not change them.
- **B never converged with A.** 28.5 → 33 → 32 — the polish the ticket omits (header count, chip tooltips, `IconButton` loading, the level union, a stable query key, the search `scrollRect`) was invisible to every review note, and the one B line that moved down (B3) moved because a new virtualizer was added without the workaround the live tail already had.
- **Fastest trajectory recorded here.** 22.3 min of model time against 252.9 for Qwen3.8-Flash-Next and 88.1 for Swift-1.5 at the same harness, with the whole three-stage run costing under an hour of wall time.

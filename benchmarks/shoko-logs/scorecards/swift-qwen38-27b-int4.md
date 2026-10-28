# Swift-1.5-Qwen3.8-27B · INT4 — scores

Model: `Swift-1.5-Qwen3.8-27B` (Swift-1.5-INT4-fast GPTQ, llama-swap entry `swift-qwen38-27b-256k` on Rig 2, HyperQwen vLLM 0.31.0, KVarN k4v2 KV).

Parameter set: Swift-1.5-INT4-fast (`swift-qwen38-27b-256k`), default reasoning level, 262144 ctx / 32768 out-cap.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| INT4 | default | not converged (36/37) | 96 / 66.5 | 97.3 | ✅ tscheck · ✅ lint · ✅ build | One test short of convergence — the reconnect window entry — after a stage 0 that was red on lint; the best non-converged final recorded |

## Stage 0 — initial run
- Model time: 48.7 min
- Gates: ✅ tscheck · ❌ lint · ✅ build
- Harness: 24/37
- Score A: N/G   Score B: 43 / 82
- Context: 1 compress · 1 decompress
- Findings:
  - **The DSL wrapper omitted the colon.** All four `dsl.a17-a18` tests failed because ordinary text was wrapped as `c#` + value instead of `c#:` + value — `Received: "a:b"` where `"c#:a:b"` was expected, and the same for `http://x` and `cfoo:bar`. One character, four tests, from the first stage.
  - **Search rows rendered raw instants.** A7 failed on `2026-01-02T03:04:05.000Z…`: search entries bypassed the live tail's timestamp formatting, so the joined rows could not match the expected `YYYY-MM-DD HH:MM:SS` shape.
  - **The build was red before the judge saw it.** `pnpm lint` still failed after the normalizer on a redundant type assertion the next note named outright; scored against a red build the sheet's 73.5 is not publishable, so the stage carries `N/G`.
  - **The reconnect window entry was dropped.** The fresh backlog replaced the stale tail correctly, but the entry arriving inside the reset window was lost: A19 half — the same half-point every run on this ticket leaves behind.
  - **The scroll lock failed in three ways at once.** Wheel-up never released follow, a programmatic scroll re-engaged it, and the control stayed enabled while filtering: B2 zero. The searching state was missing (A8 half) and the lock check inside the states spec failed with it (A10 half).
  - **B11 failed twice over.** No debounce and an untrimmed value — `Received: "c#  err  "` — so both the settled-value and the trimmed-value tests failed.
  - **Statics:** A14 revokes the object URL on click; B7 keeps a static header, B8 never extends `IconButton`, B9 leaves `Level` a bare string, B1 joins levels unsorted, B4 has no reconnect-reset spinner, B5 puts the loader outside the list, B6 ships no chip tooltips.
  - **Narrowest scope in the cohort: three files.** `src/core/react-query/logs/queries.ts`, `src/core/types/api/common.ts`, `src/pages/logs/LogsPage.tsx` — +339/−74, with the log types going into the shared `common.ts` and no `logs/mutations.ts` or `logs/types.ts` at all.

## Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

> 1. Normalize the search text before sending it to the server and settle rapid typing to a single final request, trimming surrounding whitespace first, wrapping ordinary text as a case insensitive substring filter with the documented hash colon prefix, and passing through only recognized filter expressions exactly as typed while wrapping web addresses and bare word colon word pairs and malformed heads as ordinary text, because untrimmed and miswrapped values are rejected or misinterpreted and intermediate keystrokes cause extra requests.
> 2. Format timestamps from the server backed search the same way as live rows into a human readable year month day hour minute second form, because search rows currently display raw instants while live rows are formatted, which breaks concatenation order and readability.
> 3. Preserve log entries that arrive around a reconnect reset by merging the replayed backlog with entries received in the reset window instead of blindly replacing, deduplicating and keeping oldest to newest order and keeping the rest of the view consistent, because blind replacement drops the window entry and leaves stale entries stranded.
> 4. Tie the scroll to bottom behavior strictly to the live tail, keeping the lock control visible but disabled while any filter is active, releasing follow on genuine user wheel up without snapping back to the bottom, ignoring programmatic scrolling while released, showing a distinct searching indicator while the first fetch is in flight separate from the empty state with a way to clear filters, and showing load more progress inside the list flow, because the current lock stays usable during filtering and scroll handling reengages incorrectly and loading and empty look alike.
> 5. Remove the redundant type assertion flagged by automated checks, make the level filter order independent by sorting before joining so the cached query identity is stable, keep long lists virtualized, and delay releasing the temporary download link until after the download has started so the resource outlives the click, because these issues break the automated checks and cause unstable caching and failed downloads.

- Model time: 40.4 min   Gates: ✅ / ✅ / ✅   Harness: 29/37   Score A: 79 / 100   Score B: 59.5 / 100
- Context: 0 compress · 0 decompress
- Findings:
  - **Green again, five tests the better.** 24 → 29: timestamps now formatted (A7), the searching state present (A8), the lock disabled under filters (A10), and all three scroll-lock behaviours fixed (B2 0 → 1). The lint error went with the type assertion.
  - **The colon survived the repair.** Debounce and trim arrived — the value sent is the settled trimmed term — but the wrapper still emitted `c#` instead of `c#:`, so all four DSL tests failed again (A18 zero) and both B11 tests failed on `c#err` rather than on its timing. Five tests were one character away.
  - **The reconnect got worse by following the note.** Told to replace rather than carry, `mergeBacklog` appended the stale entries after the fresh backlog: both A19 tests failed and the half-point became zero.
  - **Patch +421/−89 over the same three files.**

## Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

> 1. Correct the ordinary text branch of the search message builder so plain terms and values that merely resemble expressions are wrapped as a case-insensitive contains filter with the trailing colon present, while genuine filter expressions still pass through exactly as typed and blank input still means no search, because the current wrapping omits the colon and the server does not recognize the result as the intended substring search.
>    This also repairs the settled and trimmed search values sent after typing, which must carry the same corrected prefix.
> 2. Change the live tail update on backlog delivery so the fresh replayed backlog replaces the previously held entries instead of being kept with all old entries carried after it, retaining only entries that arrived around the reconnect window and are absent from the fresh backlog without duplication and preserving oldest to newest order, because carrying all stale entries forward leaves pre-disconnect rows stranded above the fresh backlog and breaks continuity through reconnects.

- Model time: 8.2 min   Gates: ✅ / ✅ / ✅   Harness: 36/37   Score A: 96 / 100   Score B: 66.5 / 100
- Context: 0 compress · 0 decompress
- Findings:
  - **One character bought six of the seven tests.** The ordinary-text branch now emits `c#:`; the four DSL tests and both B11 tests passed in a round that added a single line (+421/−89 → +422/−89) and took 8.2 minutes. The seventh is the reconnect-replacement test, which came with the same merge change. 29 → 36.
  - **One test short of convergence, and it is the cohort's recurring one.** The only remaining failure is `reconnect.a19`'s window entry — dropped in all three stages here and left unfixed by every run on this ticket. A19 scores half.
  - **The reconnect replacement itself now holds.** The fresh backlog replaces the stale tail; only the entry landing inside the reset window is lost, which is why the note's second half is the one piece still open.
  - **The statics never moved.** A14, B7 and B8 stayed at zero and B4, B5, B6, B9 stayed at half across all three sheets, each named in both notes.

**Outcome:** not converged — 36/37 with A 96 and B 66.5, one assertion short: the reconnect-window entry survived every round, as it has for every run on this ticket.

## Summary

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| not converged (36/37) | 96 | 66.5 | 97.3 | 1 | 1 | 139,528 / 262,144 (53%) |

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | N/G | 43 / 82 | 24/37 | ✅ / ❌ / ✅ | 48.7 | 1 | 1 |
| 1 | 79 | 59.5 | 29/37 | ✅ / ✅ / ✅ | 40.4 | 0 | 0 |
| 2 | 96 | 66.5 | 36/37 | ✅ / ✅ / ✅ | 8.2 | 0 | 0 |

- **The colon decided the trajectory.** `c#` instead of `c#:` cost four DSL tests and both B11 tests in stage 0, survived the first repair re-emitted without the colon, and one line in stage 2 took the run from 29 to 36.
- **One assertion from convergence, and it is the one nobody has passed.** The reconnect-window entry is the sole remaining failure; the other seven runs on this ticket leave the same line ungraded or half.
- **The cheapest closing round in the cohort.** 8.2 of 97.3 minutes for a seven-test jump, against 48.7 minutes for the cold stage that scored 24/37.
- **The narrowest scope recorded.** Three files, +422/−89, with the log query and types layer rebuilt inside `queries.ts` and `common.ts` rather than the `logs/` module files every other run touched.
- **The first red stage on this ticket.** Lint failed after normalization on a shape-only assertion, which is why stage 0 reads `N/G · 43 / 82` rather than the sheet's 73.5 — the only stage in the published cards with a ❌ gate.

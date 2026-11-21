# Claude Haiku 5.5 — scores

Model: `Claude Haiku 5.5`.

Parameter set: no quant (hosted model, `claude-haiku-5-5`), xhigh reasoning level.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| — | xhigh | converged: stage 1 | 100 / 79.5 | 21.6 | ✅ tscheck · ✅ lint · ✅ build | Converged in one round; B 79.5 held by four static polish gaps |

## Stage 0 — initial run
- Model time: 12.2 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 32/37
- Score A: 99 / 100   Score B: 58 / 100
- Context: 1 compress · 0 decompress
- Findings:
  - **A14 was the only A miss.** `saveBlob` created the object URL, clicked, and revoked it in the same task (`mutations.ts:9-16`), so the download could not outlive the click.
  - **All five harness failures were B checks** — two B11 coalescing specs (three reads for one typing burst; an intermediate value reached the server) and three B2 lock specs (wheel-up release, programmatic re-engage, and the visible-but-disabled control were all absent).
  - **The lock control and header had no implementation.** B2 zero on three subchecks, B7 zero on a static `Logs` title, B8 zero on `IconButton` (no loading prop, download relied on `Button` only).
  - **B5, B6, B9 and B11 met exactly half** — loading-more affordance outside the virtual rows, no chip tooltips, bare-string `Level`, and trim without coalescing.
  - **Everything runtime-observable passed cold** — A19's reconnect merge, the DSL pass-through/wrapping, cancellation, pagination and the distinct error state were full on the first turn.

## Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Coalesce fast typing in the search box into a single server search so intermediate keystrokes do not each trigger a request and only the settled trimmed value is sent, because per-keystroke reads overload the service and send superseded text.
  >    Show typed characters immediately while delaying only the query sent to the server, and treat blank input as no search so the live tail stays up.
  > 2. Make a genuine user scroll upward release the automatic follow of the live tail, while motion caused by the view itself leaves a released follow off, because the current delayed direction check misses real wheel movement and lets programmatic jumps change the state.
  >    Listen for user-initiated scrolling directly and ignore position changes that the view produced itself.
  > 3. Keep the scroll lock affordance mounted and visible while filters are active but marked unusable with a hint that it belongs to the live tail only, because hiding it removes the expected control and breaks keyboard access.
  >    Restore full interactivity automatically when filters clear.
  > 4. Keep the temporary download address alive until the browser has taken the file instead of releasing it in the same task as the click, because immediate release can cancel the save.
  >    Preserve the existing busy indication while the download is in flight and keep the failure message for errors.
  > 5. Make the header and list chrome reflect live versus search mode with a visible count or hint and keep any loading-more indicator outside the virtualized rows so the row count stays exact, because a static title and in-list spinners confuse the mode and disturb virtualization.
  >    Keep active filter choices visually distinct with accessible names and explanatory hints about the search behavior.
- Model time: 9.4 min   Gates: ✅ / ✅ / ✅   Harness: 37/37   Score A: 100 / 100   Score B: 79.5 / 100
- Context: 2 compress · 0 decompress
- Findings:
  - **Round 1 cleared every named gap.** A14 full (the object URL is revoked after 40 s), B2 full (user-only unlock, programmatic scroll immunity, visible-but-disabled control under a filter), B11 full (300 ms debounce on the settled trimmed value) and B7 full (header tail count vs server-search hint).
  - **Harness 32 → 37, A 99 → 100, B 58 → 79.5** — one repair pass, no further rounds.
  - **Four statics held B at 79.5**: B8 zero (`IconButton` gained only an `aria` prop, no loading prop), B5 0.5 (distinct loading-more affordance but in the header, not a phantom row), B6 0.5 (no chip tooltips), B9 0.5 (`LogLineType.Level` still a bare string).
  - **Patch 7 files +436/−95 in 9.4 min**, under the cold stage's 12.2.

**Outcome:** converged — stage 1; A 100 / B 79.5, harness 37/37.

## Summary

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| converged: stage 1 | 100 | 79.5 | 21.6 | 3 | 0 | 111,816 / 1,000,000 (11%) |

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | 99 | 58 | 32/37 | ✅ / ✅ / ✅ | 12.2 | 1 | 0 |
| 1 | 100 | 79.5 | 37/37 | ✅ / ✅ / ✅ | 9.4 | 2 | 0 |

- **Converged in one repair round.** The cold stage was already ticket-complete at A 99 — the only A miss was the synchronous object-URL revoke (A14) — and every harness failure was a B check, not a ticket requirement.
- **Round 1 was broad and effective**: search coalescing (B11), the whole lock cluster (B2), the header mode (B7) and the download lifetime (A14) all closed in one pass, taking the harness from 32 to 37.
- **B 79.5 is reference polish, not broken behavior** — the four deductions are static: the loading-more affordance sits in the header instead of a phantom row (B5 half), chips have no tooltips (B6 half), `IconButton` never gained a loading prop (B8), and `LogLineType.Level` stayed a bare string (B9 half).
- **21.6 min total**, 12.2 cold + 9.4 repair; 3 context folds, 0 decompressions; finished at 111,816 of a 1,000,000-token window (11%).

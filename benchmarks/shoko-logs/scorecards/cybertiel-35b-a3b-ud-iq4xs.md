# Cyber-Tiel-Coder-35B-A3B · UD-IQ4_XS — scores

Model: `Cyber-Tiel-Coder-35B-A3B` (UD-IQ4_XS GGUF, llama-swap entry `cybertiel-35b-iq4xs` on Rig 1, moe-cache fork, expert cache 76).

Parameter set: UD-IQ4_XS (`cybertiel-35b-iq4xs`), default reasoning level, 262144 ctx / 32768 out-cap.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| UD-IQ4_XS | default | not converged (31/37) | 84 / 60 | 161.6 | ✅ tscheck · ✅ lint · ✅ build | Lands on the same 31/37 as UD-Q4_K_XL with a different six: pagination was repaired in round two, the reconnect window and the scroll lock never were |

## Stage 0 — initial run
- Model time: 39.9 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 23/37
- Score A: 68.5 / 100   Score B: 51.5 / 100
- Context: 1 compress · 0 decompress
- Findings:
  - **Cold stage: 23/37, A 68.5 / B 51.5.** Clearly ahead of KAT-Coder's deadlocked first pass (8.5 / 28.5) and as clearly behind UD-Q4_K_XL on the same ticket (83 / 57.5); the server-contract side of the ticket was already right.
  - **Filtered paging never left page one.** No `NextOffset`-driven follow-up fetch was observed, so A6 scored zero and A7's concatenation had nothing to join — the same single missing effect that cost the larger quant two rounds.
  - **The text classifier was half right.** Plain input was wrapped as `c#:` correctly, but colon-bearing literals and malformed heads were passed through raw instead of wrapped (A18 half).
  - **Cancellation did not exist.** `QueryFn` ignored the abort signal, so a slow earlier response could paint over newer filter results — A20 zero — and the download URL was revoked synchronously after `click`, so the file did not outlive the click (A14 zero).
  - **The reconnect reset dropped the racing entry.** The fresh backlog did replace the stale tail, but the entry landing inside the reset window was lost: A19 half.
  - **The scroll lock held follow and failed everything else.** Wheel-up never released it, programmatic movement re-engaged it, and the control was absent while filtering: B2 half. The search virtualizer also lacked the live-dimension `scrollRect` workaround (B3 zero).
  - **Six fidelity lines failed statically.** No chip tooltips (B6), a static "Logs" header with no mode reflection (B7), `IconButton` never extended for loading (B8), `Level` left a bare string (B9), an order-dependent query key (B1), one request per keystroke (B11).
  - **Scope held.** Five `Shoko-WebUI` files, +351/−67, nothing outside the web client.

## Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

> 1. Coalesce rapid typing into a single settled server search and make in-flight reads cancellable so a slow earlier response can never overwrite newer filter results, keeping only the latest filter values in flight.
>    Wait briefly after the last keystroke before sending, trim surrounding whitespace, and forward the cancellation signal through the data fetching layer so superseded reads are aborted or ignored and do not render.
> 2. Tighten the search text classifier so only input whose head matches the documented filter expression grammar passes through verbatim, while all other nonblank input including web addresses and ordinary text that happens to contain a colon and malformed heads is sent as an ordinary case-insensitive substring search, with empty or blank input meaning no text filter.
>    Keep valid expressions unchanged and ensure colon-bearing literals are wrapped rather than treated as expressions.
> 3. Repair paged search loading and appending so the first fetch shows a searching indicator that is visibly distinct from the empty-results state, a failed read shows a distinct error state with retry, and the empty state offers a way to clear filters.
>    Fetch each following page using the offset returned for the next page until the server reports no further offset, join all pages in order oldest to newest without drops or duplicates, and ensure the scrolling list measures its container in all browsers so rows are visible and the near-end trigger fires reliably even when content fits without scrolling.
> 4. Make reconnect recovery lossless by treating the replayed backlog as authoritative for stale content while merging in entries that arrived around the disconnect and replay window without loss or duplication, then continue appending new live entries normally and keep the rest of the view consistent.
>    Do not leave pre-disconnect entries stranded above the fresh backlog and do not discard window entries by unconditional replacement.
> 5. Fix the scroll to bottom lock so only a genuine user scroll away from the bottom releases it, programmatic movement while released never reengages it, and only an explicit user action reenables it, with the control remaining visible but inactive while filters are active and usable again after clearing.
>    Keep the lock enforced for the live tail only and off while filtered results are shown.

- Model time: 103.3 min   Gates: ✅ / ✅ / ✅   Harness: 28/37   Score A: 71 / 100   Score B: 54.5 / 100
- Context: 5 compress · 2 decompress
- Findings:
  - **The heaviest stage in the cohort: 103.3 minutes.** Five compressions and two decompressions to file inside one repair turn — four times the wall time of the entire UD-Q4_K_XL trajectory, and 64% of this run's total model time.
  - **It bought five tests and the debounce.** B11 moved to one request per settled value (debounce plus trim), the search virtualizer gained the `scrollRect` workaround (B3 zero → one), and the classifier stopped leaking malformed heads (A18 half → one): 23 → 28.
  - **Pagination was attempted and stayed dead, now for a stated reason.** `SearchResults`' `parentRef` was never attached, so the near-end trigger had no scroll element to observe and no second read reached the server — A6 and A7 both zero.
  - **The reconnect got worse.** `mergeBacklog` appended instead of replacing, so stale pre-disconnect rows stayed above the fresh backlog and the window entry was still dropped: A19 half → zero. B4 also fell to half, because a merge that never empties can never show its spinner.
  - **Note 1's cancellation and the download lifetime were both ignored.** The abort signal was still unwired (A20 zero) and `createObjectURL` was still revoked synchronously (A14 zero), though the note named both in its first and third items.
  - **Patch grew without widening.** +459/−88, the same five files.

## Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

> 1. Give the filtered search list its own scrollable viewport of bounded height and attach the virtualized list to that viewport so scrolling near the end triggers the next page and pages concatenate oldest to newest, stopping only when no further cursor is returned.
> 2. On live connection replay discard the stale pre-disconnect tail and replace it with the fresh backlog while preserving any entry that arrived during the reset window so nothing stale remains above the replay and nothing in flight is lost, keeping the rest of the view consistent.
> 3. Guard filtered requests so that when filter inputs change the previous in-flight response is cancelled or ignored and never paints over newer results, showing only the latest filter set.
> 4. Show a distinct loading indication while the first filtered fetch is in flight that is visibly different from the empty-results state which must offer a way to clear filters, keeping the scroll lock disabled while filters are active.
> 5. Make the scroll-to-bottom lock release on a genuine user scroll upward away from the bottom and ensure automatic programmatic scrolling neither releases nor re-engages the lock, so the live tail stays put when the user has scrolled up and resumes only on explicit re-enable.

- Model time: 18.3 min   Gates: ✅ / ✅ / ✅   Harness: 31/37   Score A: 84 / 100   Score B: 60 / 100
- Context: 0 compress · 0 decompress
- Findings:
  - **Pagination finally fired.** The search list got its own bounded scroll viewport — +5 lines in `LogsPage.tsx` — so the near-end trigger had a scroll element: A6 zero → one and the fetched pages concatenated in order. 28 → 31.
  - **A7 stayed zero on formatting, not on paging.** The joined rows rendered the raw ISO string (`2026-01-02T03:04:05.000Z…`) instead of the `\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}` pattern the assertion expects.
  - **The reconnect window failed both tests again.** A stale/live merge still dropped the entry arriving inside the reset window: A19 zero for the second stage running.
  - **The scroll lock stayed half.** Follow still pinned new rows and the control stayed visible-disabled under filters, but both wheel-up tests — release on genuine scroll, no re-engagement on programmatic scroll — still failed: B2 half.
  - **The static list never moved.** A14, B7, B8, B9, B6, B4, B1 and A8 were flagged in all three sheets (B4 and A8 in the last two) and none was touched.
  - **One turn hit the 32,768 output cap** (`finish=length`, 32,768 output tokens) mid-stage; the model resumed and the stage closed at +464/−88 across the same five files.

**Outcome:** not converged — 31/37 with A 84 and B 60 after two review rounds: round two repaired pagination, while the reconnect window and the scroll lock survived both rounds untouched.

## Summary

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| not converged (31/37) | 84 | 60 | 161.6 | 6 | 2 | 80,003 / 262,144 (31%) |

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | 68.5 | 51.5 | 23/37 | ✅ / ✅ / ✅ | 39.9 | 1 | 0 |
| 1 | 71 | 54.5 | 28/37 | ✅ / ✅ / ✅ | 103.3 | 5 | 2 |
| 2 | 84 | 60 | 31/37 | ✅ / ✅ / ✅ | 18.3 | 0 | 0 |

- **Same harness total as the larger quant, a different six.** Both Cyber-Tiel runs stop at 31/37, but UD-IQ4_XS repairs pagination in round two and leaves the timestamp format broken, while UD-Q4_K_XL never fires a second page at all.
- **The quants separate before any review.** Cold stage 23/37 with A 68.5 / B 51.5 against UD-Q4_K_XL's 29/37 with A 83 / B 57.5 — a 14.5 A-point gap on identical inputs — and the gap closes to one point by the final sheet.
- **Round one took 103.3 of the 161.6 minutes** for the biggest single-round gain in the cohort (+5 tests), then round two bought three more in 18.3 minutes.
- **Three clusters never moved:** the reconnect-window entry (A19 zero in every sheet), the scroll-lock semantics (B2 half in every sheet), and the static fidelity list (A14, B7, B8, B9 flagged three times, never touched).

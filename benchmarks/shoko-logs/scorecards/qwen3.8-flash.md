# Qwen3.8 Flash — scores

Model: `Qwen3.8 Flash`.

Parameter set: no quant (hosted model, `qwen3.8-flash`), xhigh reasoning level.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| — | xhigh | not converged (35/37) | 92 / 71.5 | 33.2 | ✅ tscheck · ✅ lint · ✅ build | Cold stage already ticket-solid at A 91; both reconnect specs survived both repair rounds |

## Stage 0 — initial run
- Model time: 22.5 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 32/37
- Score A: 91 / 100   Score B: 60.5 / 100
- Context: 3 compress · 0 decompress
- Findings:
  - **The cold stage missed two runtime mechanics.** A14 zero (`saveBlob` revoked the object URL immediately after the click, so the download could not complete) and A19 zero (both reconnect specs: stale entries not replaced, the in-window entry dropped); the other three harness failures were the B2 lock specs, not A lines.
  - **The follow control was the whole B2 cluster.** B2 zero: no release on a deliberate wheel-up, programmatic scrolling re-engaged the follow, and the control was removed rather than shown disabled while filtering.
  - **The polish tail went unbuilt.** B7 zero (static `Logs` header), B8 zero (the shared icon control gained no loading prop), B1 0.5 (the cache key preserved toggle order), B6 0.5 (no chip tooltips), B9 0.5 (`Level` stayed a bare string).
  - **Everything else passed cold** — search/filter switching, server-side level chips, cursor pagination and concatenation, download endpoint selection, DSL pass-through/wrapping, cancellation and the distinct error state were all full.

## Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Replace stale live entries with the fresh replayed backlog when the connection recovers, keeping entries that arrived around the reset so none are lost or duplicated and later live entries keep appending in order.
  > 2. Keep the temporary download link alive until the browser has taken over the download instead of releasing it right after activation, because immediate release prevents the download from completing.
  > 3. Release the stick to bottom mode when the user deliberately scrolls upward away from the bottom, and leave the viewport where the user put it instead of pulling it back down.
  > 4. Ensure only a deliberate user action reengages the stick to bottom mode after it was released, so automatic list updates and program driven scrolling never turn it back on by themselves.
  > 5. Keep the stick to bottom control visible but unusable while filters are active instead of removing it, and return it to usable state when filters are cleared.
- Model time: 6.6 min   Gates: ✅ / ✅ / ✅   Harness: 35/37   Score A: 92 / 100   Score B: 65.5 / 100
- Context: none — the stage never folded
- Findings:
  - **Round 1 closed the download lifetime and the entire lock cluster.** A14 full (the object URL now outlives the browser taking the file) and B2 full (wheel-up release, programmatic scrolls stay locked, the control visible-but-disabled under a filter): harness 32 → 35.
  - **Reconnect failed again.** A19 zero: the merge kept stragglers by display timestamp, so stale entries stayed above the fresh backlog and the in-window entry was still dropped.
  - **B4 slipped half.** The initial empty-tail spinner survived, but no reset spinner appeared after a reconnect — 1 → 0.5.
  - **Cheap round.** 6.6 min against the cold stage's 22.5; patch 7 files +393/−98, all gates green.

## Review round 2 → Stage 2
- Review prompt (verbatim — `review-s1.md`):

  > 1. Make the fresh backlog received after a reconnect replace the previous live tail instead of merging with it, so entries from before the disconnect do not remain stranded above the fresh entries.
  >   Keep only live entries that arrived during the reconnect window and are missing from the fresh backlog, joining them after the fresh entries in oldest to newest order.
  > 2. Ensure a live entry that arrives while the backlog reset and replay is in progress is never dropped and that later live entries continue to append normally.
  >   Deduplicate the racing live entry against the fresh backlog by full identity so it is kept when absent and skipped only when truly already present.
  > 3. Perform all recency and identity comparisons for the reconnect merge on raw unformatted timestamps and complete entry identity, not on display formatted values.
  >   Truncating timestamps to display precision collapses distinct moments and causes stale entries to be kept and window entries to be mistaken for duplicates.
  > 4. Keep the rest of the view coherent across the reconnect by clearing any empty loading indicator once the fresh backlog arrives and leaving the scroll to bottom lock tied only to the live tail.
- Model time: 4.1 min   Gates: ✅ / ✅ / ✅   Harness: 35/37   Score A: 92 / 100   Score B: 71.5 / 100
- Context: none — the stage never folded
- Findings:
  - **The reconnect rewrite changed failure mode, not outcome.** A19 stayed zero: the backlog now replaces the tail outright, but the racing window entry is still dropped (received 1, expected ≥ 2) and the replacement is not observed.
  - **B recovered the B4 half** — the spinner now clears when the fresh backlog arrives — taking B 65.5 → 71.5.
  - **Five B lines sat still from stage 0 to stage 2**: B7 zero (static header), B8 zero (the icon control never gained a loading prop), B1 0.5 (order-dependent query key), B6 0.5 (no tooltips), B9 0.5 (bare-string `Level`).
  - **Cheapest round.** 4.1 min; patch 7 files +408/−99; gates green; harness unchanged at 35/37.

**Outcome:** not converged — 35/37 after two rounds, with both `reconnect.a19` specs still red.

## Summary

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| not converged (35/37) | 92 | 71.5 | 33.2 | 3 | 0 | 79,906 / 1,000,000 (8%) |

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | 91 | 60.5 | 32/37 | ✅ / ✅ / ✅ | 22.5 | 3 | 0 |
| 1 | 92 | 65.5 | 35/37 | ✅ / ✅ / ✅ | 6.6 | 0 | 0 |
| 2 | 92 | 71.5 | 35/37 | ✅ / ✅ / ✅ | 4.1 | 0 | 0 |

- **The cold stage was already ticket-solid.** A 91 on the first turn — the only A misses were the download lifetime (A14) and the reconnect pair (A19); search, pagination, DSL, cancellation and error states all passed cold.
- **Round 1 was the B round (+5)** as the lock cluster (B2) and the download lifetime (A14) closed, taking the harness from 32 to 35; B4 lost its half on the way.
- **Round 2 traded a merge for a reset without closing the reconnect.** A19 stayed zero through both repair texts, and the in-window entry is still dropped after the replay.
- **The polish tail never moved**: the header mode (B7), the shared icon control's loading prop (B8), chip tooltips (B6 half), `LogLevelType` (B9 half) and the canonical cache key (B1 half) sat at stage-0 values through both rounds.
- **33.2 min total**, 22.5 of it the cold stage; the two repair rounds together cost 10.7.
- **Context was never the constraint.** All 3 folds fell in stage 0 and the run finished at 79,906 of a 1,000,000-token window (8%).

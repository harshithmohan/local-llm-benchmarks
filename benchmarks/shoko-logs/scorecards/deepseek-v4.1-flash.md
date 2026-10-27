# DeepSeek V4.1 Flash — scores

Model: `DeepSeek V4.1 Flash`.

| Quant | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|
| — | high | converged: stage 1 | 100 / 71 | 19.8 | ✅ tscheck · ✅ lint · ✅ build | Converged in one round; the cold stage was already ticket-complete at A 99 |

## high reasoning

Parameter set: no quant (hosted model, `deepseek-v4.1-flash`), high reasoning level.

### Stage 0 — initial run
- Model time: 16.5 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 33/37
- Score A: 99 / 100   Score B: 62 / 100
- Context: 4 compress · 1 decompress
- Findings:
  - **The ticket landed cold, in full.** A 99 with every runtime A line credited by its own harness test — read contract, DSL pass-through versus wrap, `NextOffset` pagination, reconnect merge, cancellable reads and the three distinct states all correct without a note.
  - **The only A miss was the download's lifetime.** A14: `saveBlob` called `URL.revokeObjectURL` synchronously after the click, so the object URL did not outlive the browser taking the file.
  - **Both behavioural gaps were exactly the unstated lines.** All four harness failures were B11's two debounce specs (three requests for three keystrokes, three values sent instead of the settled one) and B2's two follow specs (wheel-up release, programmatic re-engagement).
  - **Polish held B at 62.** Header stayed a static `Logs` (B7 zero), the shared icon control was never extended (B8 zero), the loading-more affordance sat outside the virtualized rows (B5 half), chips had active styling but no tooltips (B6 half), and a reconnect never reset the tail to the empty spinner (B4 half).
  - **Scope held.** Only web-client paths were touched, and the sibling server checkout appears only as an API reference comment.

### Review round 1 → Stage 1
- Review prompt (verbatim — `review-s0.md`):

  > 1. Add a short debounce to the search box so rapid keystrokes coalesce into a single server-backed search using only the settled final text, because each keystroke currently triggers its own request and intermediate values can overwrite newer results.
  >   Keep blank input meaning no search and keep trimming surrounding whitespace before deciding whether a search is active.
  > 2. Make the scroll to bottom lock release on a genuine user scroll upward and never change on programmatic scrolling, keeping the view where the user left it after release, because the current scroll handler misses quick wheel movements and lets automatic scrolling reassert the lock.
  > 3. Keep the temporary download link alive until the browser has claimed the file before releasing its underlying resource, because releasing it synchronously after the click can invalidate the download before it starts.
- Model time: 3.3 min   Gates: ✅ / ✅ / ✅   Harness: 37/37   Score A: 100 / 100   Score B: 71 / 100
- Context: none — the stage never folded
- Findings:
  - **All three notes closed in one round.** A 250 ms `useDebounceValue` coalesced keystrokes to the settled value (B11 full), the wheel handler released on `deltaY` and ignored programmatic scroll (B2 full), and the blob release moved behind the load (A14 full) — 37/37 and A 100.
  - **B moved +9 and stopped.** The remaining halves and zeros are polish the note never named: header count and mode hint (B7 zero), icon-control loading prop (B8 zero), phantom continuation row inside the virtualizer (B5 half), chip tooltips (B6 half), and the empty-spinner reset on reconnect (B4 half).
  - **The repair round was cheap.** 3.3 min against the initial stage's 16.5, patch 5 files +411/−92, all gates green.

**Outcome:** converged: stage 1 — 37/37 with A 100 and B 71 after a single review round.

### Summary

| Outcome | Final A /100 | Final B /100 | Total model time (min) | Compress | Decompress | Final context |
|---|---|---|---|---|---|---|
| converged: stage 1 | 100 | 71 | 19.8 | 4 | 1 | 54,377 / 1,000,000 (5%) |

| Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) | Compress | Decompress |
|---|---|---|---|---|---|---|---|
| 0 | 99 | 62 | 33/37 | ✅ / ✅ / ✅ | 16.5 | 4 | 1 |
| 1 | 100 | 71 | 37/37 | ✅ / ✅ / ✅ | 3.3 | 0 | 0 |
| 2 | — | — | — | — | — | — | — |

- **The cold stage was already ticket-complete.** A 99 on the first turn, with the single miss being a download URL released before the browser claimed the file.
- **The unstated behaviours were the whole gap.** Debounce coalescing and the follow release/re-engage accounted for every harness failure at stage 0, and both closed from one note each.
- **One round converged the run** at 37/37 with A 100 — the fastest trajectory recorded, 19.8 min against 28.4 (Qwen3.6-35B-A3B) and 252.9 (Qwen3.8-Flash-Next).
- **B is where the headroom is.** It finished at 71 with five polish gaps the note never asked for, so the B side measures what the ticket left unstated rather than what the model failed to do.
- **Cheap repair.** The review round cost 3.3 min against the initial stage's 16.5 and moved A +1, B +9, harness 33 → 37.

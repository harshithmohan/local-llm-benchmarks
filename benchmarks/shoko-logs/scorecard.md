# Consolidated score card — shoko-logs

Two **independent 0–100 scores per stage, never summed** (see `README.md` → "Scoring" and `rubric.md`): **Score A** = ticket conformance (only what `prompt.md` asks for), **Score B** = robustness & reference fidelity (behaviors the ticket leaves unstated). Build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) are a **precondition**, not points — a stage carries a score only if all three pass, and the per-stage gate results are in the card.

Which runs count:

- **One trajectory per model per parameter set** — a clean-base implementation run (**stage 0**) plus up to two reviewer-driven repair rounds in the **same** session (**stages 1** and **2**). No repeats, no median.
- **Outcome** is `converged: stage 0|1|2`, or **`not converged`** = still red after two rounds — with the trajectory's **final harness result** in parentheses (`n/37`), so a run one assertion short and a run still in the red read differently at a glance. *Converged* means the gates pass **and** the runtime harness passes in full (37/37 today). "Not converged" is a published result, never re-run or averaged (see README → "Method").

Per-model breakdown in `scorecards/<model>.md` (one card per model, a row per quant, one block per stage); the run directory (under the bench root) is deleted once recorded — the scorecards are the persistent record. The tables below carry each stage's Score A/B, the **final harness result** and the **total model time**; per-stage harness results and per-stage model times live in the card.

Each per-stage cell reads **`<A> / <B>`** — that stage's Score A and Score B. On a **red build** the two sides are written differently, because the Score-B side already contains a slash: a red-build cell is **`N/G · <n> / <m>`** (e.g. `N/G · 74 / 82`), i.e. `N/G` for Score A and a `<n> / <m>` total with the reduced denominator for Score B. A red-build cell is **never `/ 100`** (the B denominator is below 100 — `82` today), and a bare `N/G` is **wrong on the B side**. Green builds are unaffected: their cells stay `<A> / <B>`.

The **model is the unit**: each card covers all of a model's quants, and near-identical quants across rigs are collapsed — bench one and mark the other `— (not run: duplicate of <quant>)` rather than benching both.

### Local (self-hosted) models

| Model | Quant | Level | Outcome | Stage 0 A / B | Stage 1 A / B | Stage 2 A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|---|
| qwen36-35b-a3b | UD-IQ4_XS | default | not converged (23/37) | 15.5 / 25 | 55.5 / 19.5 | 67.5 / 30.5 | 26.3 | Stage 2's first turn ended with zero edits and was resumed once; the host's billion-context plugin made 8 `compress` calls, peaking at ~120k tokens of context and ending at ~36k |
| katcoder-v2.5-dev | APEX-I-Compact | default | not converged (15/37) | 31 / 37.5 | 37.5 / 37.5 | 38 / 37.5 | 21.8 | The host's billion-context plugin made 5 `compress` calls, peaking at ~127k tokens of context and ending at ~41k |
| qwen38-flash-next | IQ3_XXS | xhigh | not converged (36/37) | 78 / 58.5 | 92 / 64 | 96 / 100 | 94.2 | Served by Strata at ctx 200000 with MTP; measured on the revised harness whose page-open gate no longer depends on the page title text; the last round's reconnect merge drops a live entry that shares the backlog cutoff timestamp; stage 0 carries the served entry's cold load |
| swift-qwen38-27b | Swift-1.5-INT4-fast | xhigh | not converged (34/37) | 76.5 / 46.5 | 78 / 45 | 84 / 66.5 | 65.8 | Served at ctx 176128 (fp8 KV, 4 MTP drafts, int8 act); the persistent miss is the search-list continuation — a pagination trigger that never fires under the harness, costing A6 outright and A7 as its cascade at every stage — plus the reconnect-window merge held at A19 half; the first Stage-0 attempt (client connection dropped mid-run, zero edits, tree untouched) is an environment failure and is not recorded, and the stage was re-run |

### opencode-go (cloud) models

| Model | Quant | Level | Outcome | Stage 0 A / B | Stage 1 A / B | Stage 2 A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | — | high | converged: stage 2 (37/37) | 89 / 62.5 | 90 / 65.5 | 100 / 84 | 27.6 | The first Stage-0 attempt was void — the checkout exposed the merged upstream implementation through its git history — so this is the clean re-run in an isolated checkout; the host's billion-context plugin made 7 `compress` calls; the trajectory ended at ~86k tokens of context |

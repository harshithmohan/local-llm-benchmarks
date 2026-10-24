# Consolidated score card — shoko-logs

Two **independent 0–100 scores per stage, never summed** (see `README.md` → "Scoring" and `rubric.md`): **Score A** = ticket conformance (only what `prompt.md` asks for), **Score B** = robustness & reference fidelity (behaviors the ticket leaves unstated). Build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) are a **precondition**, not points — a stage carries a score only if all three pass, and the per-stage gate results are in the card.

> **No results recorded yet for the current harness.** The runner, the harness and the scoring were rewritten in place (v2 → the Python runner, `expected_total: 37` pinned); results produced before that rewrite were measured against a different ticket, harness and denominator and are withdrawn rather than carried over. They remain readable in git history under the old paths, and they are **not comparable** to anything recorded here.

Which runs count:

- **One trajectory per model per parameter set** — a clean-base implementation run (**stage 0**) plus up to two reviewer-driven repair rounds in the **same** session (**stages 1** and **2**). No repeats, no median.
- **Outcome** is `converged: stage 0|1|2`, or **`not converged`** = still red after two rounds — with the trajectory's **final harness result** in parentheses (`n/37`), so a run one assertion short and a run still in the red read differently at a glance. *Converged* means the gates pass **and** the runtime harness passes in full (37/37 today). "Not converged" is a published result, never re-run or averaged (see README → "Method").

Per-model breakdown in `scorecards/<model>.md` (one card per model, a row per quant, one block per stage); the run directory (under the bench root) is deleted once recorded — the scorecards are the persistent record. The tables below carry each stage's Score A/B, the **final harness result** and the **total model time**; per-stage harness results and per-stage model times live in the card.

Each per-stage cell reads **`<A> / <B>`** — that stage's Score A and Score B. On a **red build** the two sides are written differently, because the Score-B side already contains a slash: a red-build cell is **`N/G · <n> / <m>`** (e.g. `N/G · 74 / 82`), i.e. `N/G` for Score A and a `<n> / <m>` total with the reduced denominator for Score B. A red-build cell is **never `/ 100`** (the B denominator is below 100 — `82` today), and a bare `N/G` is **wrong on the B side**. Green builds are unaffected: their cells stay `<A> / <B>`.

The **model is the unit**: each card covers all of a model's quants, and near-identical quants across rigs are collapsed — bench one and mark the other `— (not run: duplicate of <quant>)` rather than benching both.

### Local (self-hosted) models

| Model | Quant | Level | Outcome | Stage 0 A / B | Stage 1 A / B | Stage 2 A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | No runs recorded on the current harness |

### opencode-go (cloud) models

| Model | Quant | Level | Outcome | Stage 0 A / B | Stage 1 A / B | Stage 2 A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | No runs recorded on the current harness |

## Nudges

Models are served with an output cap (see README → Protocol → "Output limit and nudges"). A reasoning model can spend the whole budget on a planning chain-of-thought and end the turn with nothing implemented, stopping **at the cap**. That run is resumed with a nudge to start implementing, **at most five times per stage**. A nudge is an **intervention, not part of the task** — record the stage it happened in and how many nudges it took, here and in the card, so that stage's number is read with the help in mind.

A turn that ends unimplemented **without** hitting the cap is resumed the same way, but it is **not a nudge** and is not listed here: it is recorded in the card's stage flags as a **zero-work stop**.

| Model | Quant | Level | Stage | Nudges | Note |
|---|---|---|---|---|---|

The table lists only stages that needed a nudge — a turn that stopped **at the cap** with nothing implemented. Stages that ran without one, and stages whose extra run came from a zero-work stop rather than a cap, are not listed here. A stage that was still unimplemented after five nudges is listed with the count and stands as recorded.

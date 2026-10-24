# Consolidated score card — shoko-logs

Two **independent 0–100 scores per stage, never summed** (see `README.md` → "Scoring" and `rubric.md`): **Score A** = ticket conformance (only what `prompt.md` asks for), **Score B** = robustness & reference fidelity (behaviors the ticket leaves unstated). Build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) are a **precondition**, not points — a stage carries a score only if all three pass, and the per-stage gate results are in the card.

> **Recording on the current harness restarts here.** The runner, the harness and the scoring were rewritten in place (v2 → the Python runner, `expected_total: 37` pinned); results produced before that rewrite were measured against a different ticket, harness and denominator and are withdrawn rather than carried over. They remain readable in git history under the old paths, and they are **not comparable** to anything recorded here.

Which runs count:

- **One trajectory per model per parameter set** — a clean-base implementation run (**stage 0**) plus up to two review-driven repair rounds in the **same** session (**stages 1** and **2**). No repeats, no median.
- **Outcome** is `converged: stage 0|1|2`, or **`not converged`** = still red after two rounds — with the trajectory's **final harness result** in parentheses (`n/37`), so a run one assertion short and a run still in the red read differently at a glance. *Converged* means the gates pass **and** the runtime harness passes in full (37/37 today). "Not converged" is a published result, never re-run or averaged (see README → "Method").

Per-model breakdown in `scorecards/<model>.md` (one card per model, a row per quant, one block per stage); the run directory (under the bench root) is deleted once recorded — the scorecards are the persistent record. The tables below carry each stage's Score A/B, the **final harness result** and the **total model time**; per-stage harness results and per-stage model times live in the card.

Each per-stage cell reads **`<A> / <B>`** — that stage's Score A and Score B. On a **red build** the two sides are written differently, because the Score-B side already contains a slash: a red-build cell is **`N/G · <n> / <m>`** (e.g. `N/G · 74 / 82`), i.e. `N/G` for Score A and a `<n> / <m>` total with the reduced denominator for Score B. A red-build cell is **never `/ 100`** (the B denominator is below 100 — `82` today), and a bare `N/G` is **wrong on the B side**. Green builds are unaffected: their cells stay `<A> / <B>`.

The **model is the unit**: each card covers all of a model's quants, and near-identical quants across rigs are collapsed — bench one and mark the other `— (not run: duplicate of <quant>)` rather than benching both.

### Local (self-hosted) models

| Model | Quant | Level | Outcome | Stage 0 A / B | Stage 1 A / B | Stage 2 A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | UD-IQ4_XS | default | not converged (11/37) | 31.5 / 52.5 | 35 / 43.5 | 29 / 42 | 28.4 | [card](scorecards/qwen36-35b-ud-iq4xs.md) — filter mode never engaged at any stage |

### opencode-go (cloud) models

| Model | Quant | Level | Outcome | Stage 0 A / B | Stage 1 A / B | Stage 2 A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | No runs recorded on the current harness |

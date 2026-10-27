# Consolidated score card — shoko-logs

Two **independent 0–100 scores per stage, never summed** (see `README.md` → "Scoring" and `rubric.md`): **Score A** = ticket conformance (only what `prompt.md` asks for), **Score B** = robustness & reference fidelity (behaviors the ticket leaves unstated). Build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) are a **precondition**, not points — a stage carries a score only if all three pass, and the per-stage gate results are in the card.

> **Recording on the current harness restarts here.** The runner, the harness and the scoring were rewritten in place (v2 → the Python runner, `expected_total: 37` pinned); results produced before that rewrite were measured against a different ticket, harness and denominator and are withdrawn rather than carried over. They remain readable in git history under the old paths, and they are **not comparable** to anything recorded here.

Which runs count:

- **One trajectory per model per parameter set** — a clean-base implementation run (**stage 0**) plus up to two review-driven repair rounds in the **same** session (**stages 1** and **2**). No repeats, no median.
- **Outcome** is `converged: stage 0|1|2`, or **`not converged`** = still red after two rounds — with the trajectory's **final harness result** in parentheses (`n/37`), so a run one assertion short and a run still in the red read differently at a glance. *Converged* means the gates pass **and** the runtime harness passes in full (37/37 today). "Not converged" is a published result, never re-run or averaged (see README → "Method").

Per-parameter-set breakdown in `scorecards/<model>-<quant>.md` (one card per model + quant; one headline row per reasoning level; one block per stage, nested per level section in a multi-level card); the run directory (under the bench root) is deleted once recorded — the scorecards are the persistent record. The tables below carry each stage's Score A/B, the **final harness result** and the **total model time**; per-stage harness results and per-stage model times live in the card.

Each per-stage cell reads **`<A> / <B>`** — that stage's Score A and Score B. On a **red build** the two sides are written differently, because the Score-B side already contains a slash: a red-build cell is **`N/G · <n> / <m>`** (e.g. `N/G · 74 / 82`), i.e. `N/G` for Score A and a `<n> / <m>` total with the reduced denominator for Score B. A red-build cell is **never `/ 100`** (the B denominator is below 100 — `82` today), and a bare `N/G` is **wrong on the B side**. Green builds are unaffected: their cells stay `<A> / <B>`.

The **parameter set is the unit**: each card covers one quant of one model, and near-identical quants across rigs are collapsed — bench one and give the other no card.

### Local (self-hosted) models

| Model | Quant | Level | Outcome | Stage 0 A / B | Stage 1 A / B | Stage 2 A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | UD-IQ4_XS | default | not converged (11/37) | 31.5 / 52.5 | 35 / 43.5 | 29 / 42 | 28.4 | [card](scorecards/qwen36-35b-ud-iq4xs.md) — filter mode never engaged at any stage |
| Qwen3.8-Flash-Next | IQ3_XXS | xhigh | not converged (33/37) | 79 / 66 | 87 / 89 | 91 / 87.5 | 252.9 | [card](scorecards/qwen38-flash-next-iq3xxs.md) — pagination duplication and the reconnect window survived both repair rounds |
| Swift-1.5 Qwen3.8-Flash-Next | IQ3_XXS | xhigh | converged: stage 2 | 95 / 66 | 92 / 60 | 100 / 64.5 | 88.1 | [card](scorecards/swift-qwen38-flash-next-iq3xxs.md) — cold stage ticket-complete except the download lifetime; the reconnect race took two rounds |
| KAT-Coder-V2.5-Dev | APEX-I-Compact | default | not converged (23/37) | 8.5 / 28.5 | 45.5 / 33 | 74.5 / 32 | 22.3 | [card](scorecards/katcoder-v2.5-dev-apex-i-compact.md) — a cold `hasFilters` gate deadlocked the whole filter UI; the `c#:` wrap colon, the cursor and the reconnect window survived both rounds |
| Cyber-Tiel-Coder-35B-A3B | UD-Q4_K_XL | default | not converged (31/37) | 83 / 57.5 | 79 / 49 | 83 / 66 | 33.8 | [card](scorecards/cybertiel-35b-a3b-ud-q4kxl.md) — strongest cold stage of the cohort; round two made no edits at all, so the final A/B re-reads stage-1 code |

### opencode-go (cloud) models

| Model | Quant | Level | Outcome | Stage 0 A / B | Stage 1 A / B | Stage 2 A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash | — | high | converged: stage 1 | 99 / 62 | 100 / 71 | — | 19.8 | [card](scorecards/deepseek-v4.1-flash.md) — converged in one round; B 71 held by polish the note never named |
| MiMo-V2.6-Flash | — | default | not converged (34/37) | 80 / 44.5 | 84 / 78.5 | 92 / 72.5 | 47.7 | [card](scorecards/mimo-v2.6-flash.md) — the reconnect reset and the filtered lock control survived both rounds |

# Consolidated score card (v2) — shoko-logs

Two **independent 0–100 scores per stage, never summed** (see `README.md` → "Why v2" and `rubric.md`): **Score A** = ticket conformance (only what `prompt.md` asks for), **Score B** = robustness & reference fidelity (behaviors the ticket leaves unstated). Build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) are a **precondition**, shown `✅/❌`, not points.

Which runs count:

- **One trajectory per model per parameter set** — a clean-base implementation run (**stage 0**) plus up to two reviewer-driven repair rounds in the **same** session (**stages 1** and **2**). No repeats, no median.
- **Outcome** is `converged: stage 0|1|2`, or **`not converged`** = still red after two rounds. *Converged* means the gates pass **and** the runtime harness passes in full (37/37 today). "Not converged" is a published result, never re-run or averaged (see README → "Method").
- A stage that needed a nudge is flagged in the card so its number is read with that help in mind.

Per-model breakdown in `scorecards/<model>.md` (one card per model, a row per quant, one block per stage); run artifacts under `runs/<model>/` are deleted once recorded — the scorecards are the persistent record. The tables below keep the **final score** and the **total model time** only; per-stage scores, harness results and per-stage model times live in the card.

The **model is the unit**: each card covers all of a model's quants, and near-identical quants across rigs are collapsed — bench one and mark the other `— (not run: duplicate of <quant>)` rather than benching both.

### Local (self-hosted) models

| Model | Quant | Level | Outcome | Gates | Final A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|
| qwen36-35b-a3b | UD-IQ4_XS | default | not converged | ✅✅✅ | 67.5 / 30.5 | 26.3 | Stage 2's first turn ended with zero edits (a zero-work stop, not an output-cap nudge — this trajectory hit no cap) and was resumed once |

### opencode-go (cloud) models

| Model | Quant | Level | Outcome | Gates | Final A / B | Total model time (min) | Notes |
|---|---|---|---|---|---|---|---|
_No runs recorded yet._

## Nudges

Models are served with an output cap (see README → Protocol → "Output limit and nudges"). A reasoning model can spend the whole budget on a planning chain-of-thought and end the turn with nothing implemented, stopping **at the cap**. That run is resumed with a nudge to start implementing, **at most five times per stage**. A nudge is an **intervention, not part of the task** — record the stage it happened in and how many nudges it took, here and in the card, so that stage's number is read with the help in mind.

A turn that ends unimplemented **without** hitting the cap is resumed the same way, but it is **not a nudge** and is not listed here: it is recorded in the card's stage flags as a **zero-work stop**.

| Model | Quant | Level | Stage | Nudges | Note |
|---|---|---|---|---|---|

The table lists only stages that needed a nudge — a turn that stopped **at the cap** with nothing implemented. Stages that ran without one, and stages whose extra run came from a zero-work stop rather than a cap, are not listed here. A stage that was still unimplemented after five nudges is listed with the count and stands as recorded.

# shoko-logs — two-score coding benchmark

Two independent scores for the same task. This directory is self-contained.

## Scoring

Two **independent 0–100 scores, never summed** (that sum is exactly the conflation it removes):

- **Score A — Ticket conformance.** Only behaviors `prompt.md` explicitly requests. Judged at runtime by the harness wherever a line is `[R]`, otherwise by static inspection of the patch. The headline "did the model build the ticket" number.
- **Score B — Robustness & reference fidelity.** Behaviors the ticket deliberately leaves unstated: reference-level polish a production implementation has anyway. In scope, not extra credit — they measure whether the model applies them **without being told**, and the run's target is the reference. A low Score B never depresses Score A. The "how close to production-grade" number.
- **Build gates are a precondition, not points.** `pnpm tscheck` / `pnpm lint` / `pnpm build` must pass for a run to carry a Score-A number at all (a red build means the runtime checks cannot run). Report gates `✅/❌`; they carry no weight.

Every line is scored 0 / half / full, and **a half is not a judgement call**: it is available only where the line's own text in [`rubric.md`](rubric.md) states a half criterion — every other line is binary, so two independent judge passes on the same patch cannot disagree about partial credit. The line lists (A1–A21, B1–B11) are in [`rubric.md`](rubric.md).

## Task summary

Given to the model as a ticket, never as a reference implementation — one ticket covering all five features, every behaviour graded in Score A:

1. **Server-side log search** — keep the SignalR live tail as the default view; when any filter is active (debounced search text or level chips), switch to a server-backed search over the full log history with paginated infinite scroll, level chips filtered server-side, loading/empty states, and a clear-filters action.
2. **Log download** — download button: current log file when no filters are active, filtered range when they are; loading state on the button, error toast on failure.
3. **DSL-aware search** — recognize the server's filter-expression prefix grammar and pass DSL input through unchanged; wrap only plain input as a case-insensitive contains.
4. **Automatic reconnect recovery** — on SignalR reconnect, reset the tail to the fresh backlog without dropping entries that arrived around the reconnect.
5. **Cancellation and failure handling** — changing filters cancels or ignores the in-flight request; a failed read shows a visible error state distinct from the empty state.

## Prompt

Delivered as a ticket with no API reference: the model must read the sibling **ShokoServer** checkout to find the endpoint paths, query parameters, response shapes, and the filter expression syntax before writing any fetch calls — a pure discovery test (*can the model find what it needs in an unfamiliar codebase and build it?*). The ticket is [`prompt.md`](prompt.md).

## Method — one trajectory, up to two repair rounds

Each model gets **one trajectory per parameter set**: a clean-base implementation run (**stage 0**), then up to **two** reviewer-driven repair rounds in the **same** session (**stages 1** and **2**). There are no repeats and no median — the trajectory *is* the result.

A stage is **green** when it matches the reference implementation: the build gates pass and the runtime harness passes in full (37/37 today — the runner checks the report's own total against the pinned `expected_total`, so a suite that loses tests is not green, and it stops the run on a failure bullet `lines.json` does not key). The harness covers the ticket behaviours **and** the two behavioural Score-B lines, because convergence is measured against the reference — not against Score A alone. A trajectory is reported as `converged: stage 0` (green first try), `converged: stage 1`, `converged: stage 2`, or **`not converged`** — still red after two rounds. "Not converged" is a published result, not a failed sample: it is never re-run, averaged, or discarded.

**Green is a gates-plus-harness claim, not a full-rubric claim.** 3 of Score A's 100 points are `[S]` (static), so the harness cannot see them: a converged trajectory can still leave a static ticket item unmet (download-save mechanics, virtualized rendering, dead-code hygiene). The same holds on the B side — only B2 and B11 are behavioural, so the other nine B lines are invisible to the harness and a converged stage can still carry B gaps. Read the stage's Score A and Score B for those — convergence says the build works and the asserted behaviours hold, not that every line scored full. Score B is also **not monotonic**: a repair round rewrites files, so a later stage can score lower on B than stage 0 did — read B per stage, never as progress.

This is why the loop replaced repeats: a user does not send the same prompt three times and take a median. They look at the result, say what is wrong, and let the model try again. **Rounds to green** and the **total model time** it took to get there are the discriminating numbers; the score at the final stage is the least interesting one, because once coached everyone converges. The single exception is a genuine environment failure — a dropped socket that exports a 0-byte patch, or the model server being unloaded mid-run. That is the rig failing, not the model: re-run that stage.

The **reviewer** is the automated stand-in for the human in that loop: it sees the ticket, the candidate's diff, the sanitized harness report, the judge's score sheet for that stage, and the candidate tree, and writes a short, symptom-only follow-up prompt. The judge's sheet is what a human reviewer would have — a per-line account of what scored and why, naming the file and line where each problem lives — and the reviewer's job is to turn that, plus its own reading of the code, into plain language. It is where the details the ticket omits live: a debounce interval, a trim, a convention the codebase already establishes are the kind of thing a human says on seeing the code, so they belong to the review round, not the ticket. The constraint is on what it *writes*, not on what it may know: it states what does not work, never the fix, and carries no `file:line` into the follow-up even though the sheet it read is full of them. It works without `reference.diff` and `rubric.md` — the sheet already carries the rubric-level findings, so the reviewer can raise them without reading the reference implementation and copying it.

## Protocol

The runner drives every step non-interactively — `prepare` and `run`.

1. **Prepare — the runner's `prepare`.** The runner clones `Shoko-WebUI` and `ShokoServer` from GitHub into `~/.cache/shoko`, then builds the run's tree itself: a history-free copy of those checkouts (`Shoko-WebUI` with a single commit on branch `bench/shoko-logs`, `ShokoServer` as files only) plus the run's state, all under a bench root outside this repo. The source checkouts are never clean-tree-checked or branched, and the runner never touches them.
2. **Implement — runner-owned.** The run is never driven by hand: the runner hands the ticket in `prompt.md` to a model in a headless `build` agent session, launched as a plain host process and reaching the model directly — the implement role's `--endpoint` becomes its provider base URL. Always use the `build` agent: the default `orchestrator` agent delegates to subagents and can finish without implementing. The harness never drives opencode; it only exercises the finished run. The runner records the session id and continues that same session for the repair rounds.

   **The checkout must not expose the reference implementation — git history included.** This is a discovery test: the model is meant to find the endpoint paths, the query parameters and the filter-expression grammar in the sibling ShokoServer source, not to be handed the answer. If the checkout the run works in can reach the merged upstream implementation of this ticket — through its own history, another branch, a remote-tracking ref, a stash, or a second checkout sitting inside the working directory — a model can read it, or check it out wholesale, and skip the task entirely. Such a stage is **void**, however good its numbers look: it measures retrieval, not implementation, and it lands at or near the reference's own score. Hand the implementation run a checkout whose history stops at the base commit and which carries no other reachable refs, and treat any stage whose tree matches the reference as suspect. The judge and reviewer are already barred from `reference.diff`; the implementation run must be too. The runner applies this structurally — the run tree is history-free, with a single ref, no remotes, no stash, no alternates, and a tree hash equal to the base.
3. **Normalize — runner-owned, always, immediately after the model returns.** In the checkout the runner runs `pnpm dprint:fix && pnpm oxlint:fix`. This is the only mechanical intervention the protocol makes, and it is deliberate: the fixers are deterministic and behaviour-preserving, and a formatting slip is not what the benchmark measures. It is **not** a repair round and never counts as help. Only what the fixers cannot fix is a real gate failure — anything still failing `pnpm lint` after this is a genuine failure, and is raised in the next review round. A lint or formatting failure on its own never invalidates a stage: the rest of the run is still graded normally.
4. **Export — runner-owned.** The runner writes that stage's cumulative patch to `patch-s<stage>.diff` and its `stat-s<stage>.txt`, **after** the normalize step so the patch matches the graded tree. The exported patch is the record of the stage; whether a stage is void (the rule under step 2) is a human check on that patch, not something the runner decides.
5. **Gates — runner-owned.** `pnpm tscheck` / `pnpm lint` / `pnpm build` are a precondition, not points; the runner records the gates for the score sheet and for the judge.
6. **Harness — runner-owned.** [`harness/`](harness/) exercises the run at runtime for the `[R]`-marked Score-A lines. The runner points it at the checkout with `SHOKO_WEBUI_DIR` and at the run directory with `HARNESS_REPORT`, and keeps a sanitized failure report plus a raw log per stage. It grades the step green only on the report's **own** numbers: the report's total must equal the pinned `expected_total` in `shoko.config.json` (37) and every one of those tests must have passed — a suite that loses tests (a spec file that fails to load, so the report says 30/30) is **not** green. It also validates every failure bullet's key against [`harness/lines.json`](harness/lines.json); a bullet the file does not key stops the run (`harness-report-unmapped`), because a failure the runner cannot place is not gradeable. Setup and usage are in [`harness/README.md`](harness/README.md).
7. **Judge — runner-owned.** The runner judges the exported patch against `rubric.md` in a headless opencode session running the configured judge model, scoring **Score A and Score B independently** (one sheet per stage, each score written without letting the other anchor it — the sheet shape is at the end of `rubric.md`). The judge works **blind**, so the runner stages into the pass's working directory exactly what it may read — the ticket, the rubric, this stage's patch and stat, the recorded `gates.json`, this stage's sanitized harness report as `harness.json`, and a read-only copy of the candidate tree — and nothing else is reachable from it: no `score-s*.md`, no `review-s*.md`, no raw harness log, no other stage's artifacts. The failure mode is real: an unbounded judge will read an earlier stage's score sheet and the review text and anchor on them. `[R]` lines are decided **solely** by the harness report, with no cascade credit. The gates are the runner's recorded `gates.json` — the judge reads that file rather than re-running the gates. The judge writes its score sheet in the shape at the end of `rubric.md`. **Invoke the judge and the reviewer as headless opencode processes — never as opencode subagents.** A subagent inherits the parent session's model when no model is passed, so such a lane silently runs on the orchestrator's own model instead of the configured judge model.
8. **Repair rounds — runner-owned, only when a stage is not green.** A stage is **green** when the three gates pass and the harness passes in full (37/37 today). If stage 0 is not green, a **reviewer** writes a follow-up prompt and the runner sends it into the **same** session; the work after that round is stage 1, and a second round may follow as stage 2 — **two rounds maximum**. The reviewer sees the ticket, the candidate's diff, the sanitized harness failure report (spec titles and observed symptoms, never selector internals; the raw log is still written for humans but is **not** given to the reviewer), the judge's score sheet for that stage (a per-line account of what scored and why, naming the file and line where each problem lives), and the candidate tree. **The judge runs first**: the review round is written from the sheet, so the judge completes before the review begins. The sheet is the reviewer's full information, exactly as a human reviewer's would be; the constraint is on what it *writes*, not on what it may know. It must still **not** read `reference.diff` or `rubric.md` — the sheet carries the rubric-level findings, and the reference implementation is not something a reviewer would have in hand. The reviewer has no browser tool, so its own review is of the code and the diff — the harness is the runtime evidence; do not ask it to boot the app. This is where a human reviewer's judgement lives: details the ticket deliberately omits — a debounce interval, a trim, a convention the codebase already establishes — may be raised here. Its prompt is fixed-shape: at most five findings, ordered by severity, written as symptoms and expected behaviour only. It states **what** does not work, never the fix: no code, no rubric line numbers, and no file paths or `file:line` references — the sheet it read is full of them, and translating them into plain language is part of the job. Each round then repeats the normalize → export → gates → harness → judge sequence with the new stage number. The judge runs **before** the reviewer, because the reviewer reads the judge's sheet; the judge itself must not see the review text or another stage's score sheet. A trajectory still red after two rounds is recorded **not converged** — that is the result, not a sample to re-run or average.
9. **Verify the pass.** The runner never trusts a pass's exit status: what it requires is the artifact on disk — `score-s<stage>.md` from the judge, `review-s<stage>.md` from the reviewer. A pass can exit cleanly having written nothing (observed 2026-10-13 — a judge ended right after reading a few files). The runner re-runs that pass once; if it still produces nothing the run stops rather than grading against a missing sheet. No score is ever fabricated, and no artifact is ever hand-edited into place.
10. **Record — human-owned.** The run's facts are the run directory's own artifacts: the per-stage patches and stats, `gates-s<stage>.json`, the sanitized harness reports, the score sheets, and the review texts, plus `run.json` (pins) and `state.json`. The run directory lives under the bench root, outside this repo; the runner writes those artifacts as it goes, and a human writes the repository's scorecard row from them. `run` exits `0` when the trajectory converged and `4` when it ended not converged (`10` is a failed precondition, `70` an internal failure).

Never let the run's branch outlive the run: results live in the exported patch, not in git.

### Reasoning level

A reasoning level is part of the **parameter set**, not the model id, and it is selected with a `#<level>` suffix on the model the runner is given for the implement step: `<model>#low`. The suffix picks a *variant* declared on the model entry of the injected opencode provider — the level itself is a setting inside that variant:

```json
"models": {
  "<model>": {
    "name": "<Model>",
    "limit": { "context": <served ctx>, "output": <served output cap> },
    "variants": [
      { "id": "low",  "settings": { "reasoningEffort": "low" } },
      { "id": "high", "settings": { "reasoningEffort": "high" } }
    ]
  }
}
```

The settings key is camelCase `reasoningEffort`; the OpenAI-compatible provider maps it to the request's `reasoning_effort` field. Hosted providers ship their own effort variants (so `#xhigh` needs no declaration); a self-served model needs each level declared in the injection, and a model with no effort setting is run with no suffix and recorded as `default`. Every level is a **separate section** in the card, with its own headline row — the parameter set differs, so the trajectories are not comparable to each other.

### Output limit

Every model is served with an output cap. A reasoning model can spend the whole budget on a planning chain-of-thought and end the turn with the work unimplemented — the plan is complete, no tool was called, and the run stopped **at the cap**. opencode continues such a turn in the **same** session on its own; the runner never intervenes. Whatever the turn reaches is what the stage records — no stage is re-run to look for a better sample.

### Context management

The implement session runs with the host's opencode configuration as it stands: the runner scrubs `OPENCODE_CONFIG*`, `OPENCODE_PORT`, `OPENCODE_SESSION_ID` and `OPENCODE_TERMINAL` only (recorded as `child_env` in `run.json`), so every plugin the host loads is loaded for the run too. That includes **[billion-context](https://github.com/ranxianglei/billion-context)**, which gives the model `compress`, `decompress` and `acp_status` tools — it can fold consumed conversation into a summary it writes itself, restore a folded range, and read its own context status.

That is the model's decision, not the runner's: nothing folds the conversation for it, and how it manages its own history is part of what the benchmark observes. The card records the call counts per stage (`Context:` line and the per-stage table in Summary) with the run totals and the final context usage in the headline row. The plugin is not pinned by the benchmark — the run uses whatever the host has loaded — so counts are comparable within a host's configuration, not across configurations.

### Reliability

Judging is blind; what the run keeps fixed is the sampling:

- **One trajectory, no repeats.** See "Method" above. The reported numbers are the trajectory's own stage scores, not a median of independent runs.
- **"Not converged" stands.** A trajectory still red after two repair rounds is recorded `not converged`. It is not re-run to look for a better sample, and it is never averaged with a converged one.

### Runs and recording

Run names are the served model id, e.g. `qwen36-35b-iq4xs` (without a rig prefix — models are assumed identical across rigs). Each model gets **one trajectory**: one run tree per run; per stage one patch export (`patch-s<stage>.diff`), one raw harness log (humans only), one sanitized harness report (the reviewer's input), and one score sheet (`score-s<stage>.md`), plus the review text that opened the stage (`review-s<stage>.md`, stages 1 and 2 only). The last stage's sheet is also copied to `score.md` as the run's final result — the converging stage, or stage 2 when the trajectory does not converge. All of it lives in the run's state under the bench root, **outside this repository** — the repo's `scorecards/` is the persistent record.

- **One card per model + quant.** Results are grouped by parameter set: `scorecards/<model>-<quant>.md`, one quant of one model per card, one headline row in `scorecard.md`; unbenched quants get no card, and near-identical quants across rigs (e.g. the two `qwen36` builds) are collapsed — bench one, give the other no card. Level sections, hosted-model filenames and the card shape are in `scorecards/_template.md` — copy it once per parameter set. **A human writes the card row** from the run's recorded state; the runner's card draft is the input to that edit, not the published record.
- The parameter set the model was served with (e.g. `kv-q8`, or `kv-q4` when re-testing with a different cache) is recorded in the card's `Parameter set:` line, not in the run name — it can be arbitrarily long, so the filename carries only the short quant slug.
- **A frontier judge and reviewer are recommended.** The judge must read a whole patch against every rubric line, and the reviewer must turn that sheet into a usable repair note, so an underpowered model silently caps the trajectory's ceiling. The benchmark pins no model of its own: `--judge` and `--reviewer` are required and are chosen per run.
- **House setting for the numbers in this repo.** Runs published here use `opencode-go/muse-spark-1.3-contributor#xhigh` for **both** the judge and the reviewer — the same model at the `xhigh` reasoning level, passed as `--judge opencode-go/muse-spark-1.3-contributor#xhigh --reviewer opencode-go/muse-spark-1.3-contributor#xhigh`. The scorecard records the model under test and what it produced, nothing about the grading apparatus.
- Record each stage's **model time** — that stage's implementation run, i.e. the model's own session segment producing that stage's patch, start → finish from the run log — in the card's per-stage table (`scorecards/<model>-<quant>.md`), and the **total model time** (the sum of those times, stage 0 through the stage that converged, or through stage 2 for a `not converged` trajectory) in the card's headline row and the `scorecard.md` row. The headline tables carry the **final score** and the total model time only; per-stage scores and timings go in the per-stage table. Harness, reviewer and judge time are **not** part of any recorded figure: the timing measures the model producing code, not the apparatus measuring it. Model time includes model load.
- **Delete the run dir after recording.** Once the trajectory's stages (and any review text worth keeping) are recorded in `scorecards/<model>-<quant>.md`, the run tree and its state are removed — the scorecards are the persistent record, not the run artifacts. Review the patch before deleting; nothing survives in the state directory.

## Layout

```
shoko-logs/
  README.md            this file
  rubric.md            Score A (A1-A21), Score B (B1-B11), gates
  prompt.md            the ticket (search, download, DSL, reconnect, cancellation/failure)
  reference.diff       reference implementation (combined upstream diff)
  shoko.py             runner: prepare / run (stdlib-only)
  shoko_pipeline.py    the stage loop: implement → normalize → gates → harness → judge → review
  shoko_proc.py        host-process spawn (opencode invocation, streaming, timeouts)
  shoko_stream.py      NDJSON event-stream parsing
  shoko.config.json    committed pins, timeouts and permissions
  prompts/             hash-pinned prompt templates (judge, reviewer)
  harness/             runtime assertions for the [R] Score-A lines (see harness/README.md)
    lines.json         authoritative test-title -> rubric-line mapping
  scorecards/
    _template.md       per-parameter-set scorecard shape
  scorecard.md         consolidated two-score table
```

The benchmark is self-contained apart from its two source checkouts: `reference.diff` is a local copy, and the runner clones `Shoko-WebUI` and `ShokoServer` from GitHub into `~/.cache/shoko` (reused across runs, fetched to refresh).

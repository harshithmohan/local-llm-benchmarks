# shoko-logs (v2) — two-score coding benchmark

Supersedes v1's single-score scheme (the sibling `shoko-logs` benchmark): same task, but two independent scores instead of one conflated number. This directory is self-contained.

## Why v2

v1 reported a single 100-point number that mixed two different things — **ticket conformance** (did the model build what the ticket asked for) and **reference fidelity** (did it match the hidden reference's production-grade behaviors). Of v1's 95 rubric points, ~24 were earned by essentially nobody (DSL passthrough 10, reconnect reset 6, scroll-lock 4, dead-code 3, header 1) and ~25 by essentially everybody (the read contract, chips, debounce, clear, endpoint switch, loading) — leaving only ~46 points of real separation, all in scattered half-points. Cohort spread was 51–75. The one headline number was therefore misleading: a run was docked for missing behaviors the ticket never asked for, while a plain-but-conformant implementation and a polished one could land at the same total. v2 splits the two concerns into two independent scores and moves the signal to the behaviors that actually differ.

## Scoring

Two **independent 0–100 scores, never summed** (that sum is exactly the conflation v2 removes):

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

A stage is **green** when it matches the reference implementation: the build gates pass and the runtime harness passes in full (37/37 today). The harness covers the ticket behaviours **and** the two behavioural Score-B lines, because convergence is measured against the reference — not against Score A alone. A trajectory is reported as `converged: stage 0` (green first try), `converged: stage 1`, `converged: stage 2`, or **`not converged`** — still red after two rounds. "Not converged" is a published result, not a failed sample: it is never re-run, averaged, or discarded.

**Green is a gates-plus-harness claim, not a full-rubric claim.** 3 of Score A's 100 points are `[S]` (static), so the harness cannot see them: a converged trajectory can still leave a static ticket item unmet (download-save mechanics, virtualized rendering, dead-code hygiene). The same holds on the B side — only B2 and B11 are behavioural, so the other nine B lines are invisible to the harness and a converged stage can still carry B gaps. Read the stage's Score A and Score B for those — convergence says the build works and the asserted behaviours hold, not that every line scored full. Score B is also **not monotonic**: a repair round rewrites files, so a later stage can score lower on B than stage 0 did — read B per stage, never as progress.

This is why the loop replaced repeats: a user does not send the same prompt three times and take a median. They look at the result, say what is wrong, and let the model try again. **Rounds to green** and the **total model time** it took to get there are the discriminating numbers; the score at the final stage is the least interesting one, because once coached everyone converges. The single exception is a genuine environment failure — a dropped socket that exports a 0-byte patch, or the model server being unloaded mid-run. That is the rig failing, not the model: re-run that stage.

The **reviewer** is the automated stand-in for the human in that loop: it sees the ticket, the candidate's diff, the sanitized harness report, the judge's score sheet for that stage, and the candidate tree, and writes a short, symptom-only follow-up prompt. The judge's sheet is what a human reviewer would have — a per-line account of what scored and why, naming the file and line where each problem lives — and the reviewer's job is to turn that, plus its own reading of the code, into plain language. It is where the details the ticket omits live: a debounce interval, a trim, a convention the codebase already establishes are the kind of thing a human says on seeing the code, so they belong to the review round, not the ticket. The constraint is on what it *writes*, not on what it may know: it states what does not work, never the fix, and carries no `file:line` into the follow-up even though the sheet it read is full of them. It works without `reference.diff` and `rubric.md` — the sheet already carries the rubric-level findings, so the reviewer can raise them without reading the reference implementation and copying it.

## Protocol

1. `./run.sh setup` — verifies a clean tree, creates branch `bench/shoko-logs-v2` from the base commit, and prints the headless command for the implementation step. Point `run.sh` at the Shoko-WebUI checkout via `SHOKO_WEBUI_DIR` (or edit the top of `run.sh`); ShokoServer must sit beside it (siblings under one parent), which is what the prompt points to.
2. **Implement — headless.** The run is never driven by hand: the ticket in `prompt.md` is given to a model in a headless `build` agent session. A run works in the process cwd, so `cd` to the parent that holds **both** checkouts first, and pass `--standalone` when the provider is injected with `OPENCODE_CONFIG_CONTENT` (the shared background service ignores the inline config) and `--auto` (a headless session cannot answer the edit permission prompt):

       cd <parent dir holding Shoko-WebUI and ShokoServer> && \
         opencode run --standalone --auto --agent build --thinking -m <model> \
           "$(cat <benchmark dir>/prompt.md)"

   The directory must be the parent that holds **both** checkouts: the model has to read the sibling ShokoServer source, and headless opencode auto-rejects reads outside its working directory. Always use the `build` agent: the default `orchestrator` agent delegates to subagents and can finish without implementing. The harness never drives opencode; it only exercises the finished run. **Record the session id** — the repair rounds continue this same session. `opencode session list` prints it (the list is scoped to the cwd the session ran in), or pin it up front with `--session <id>` (`opencode run --session <id>` creates the session if that id does not exist).
3. **Normalize — always, immediately after the model returns.** In the checkout:

       cd <Shoko-WebUI checkout> && pnpm dprint:fix && pnpm oxlint:fix

   This is the only mechanical intervention the protocol makes, and it is deliberate: the fixers are deterministic and behaviour-preserving, and a formatting slip is not what the benchmark measures. It is **not** a repair round and never counts as help. Only what the fixers cannot fix is a real gate failure — anything still failing `pnpm lint` after this is a genuine failure, and is raised in the next review round. A lint or formatting failure on its own never invalidates a stage: the rest of the run is still graded normally.
4. `./run.sh eval <run-name> [stage]` — exports that stage's cumulative patch to `runs/<run-name>/patch-s<stage>.diff` (stage defaults to 0), **after** the normalize step so the patch matches the graded tree. Then run the gates in the checkout (`pnpm tscheck` / `pnpm lint` / `pnpm build`) and record them for the score sheet. The checkout is left on the bench branch with the changes applied.
5. **Run the harness.** [`harness/`](harness/) exercises the run at runtime for the `[R]`-marked Score-A lines and emits per-assertion pass/fail to feed the score sheet. Point it at the checkout with `SHOKO_WEBUI_DIR` and pass `HARNESS_REPORT=../runs/<run-name>/harness-s<stage>.report.md` so the sanitized failure report lands beside the raw log; keep the raw Playwright output per stage as `runs/<run-name>/harness-s<stage>.log`. Setup and usage are in [`harness/README.md`](harness/README.md).
6. **Judge — two score sheets.** Judge the exported patch against `rubric.md` with a headless opencode session running the configured judge model (`<judge-model>`), scoring **Score A and Score B independently** (two score sheets; never let one anchor the other). Use the `build` agent, and run opencode from a directory that contains the checkout, its sibling ShokoServer, and this benchmark dir (their common parent) so the judge can read `rubric.md`/`reference.diff`/the server source and run the gates in the checkout. The judge writes `runs/<run-name>/score-s<stage>.md` in the shape at the end of `rubric.md`. cwd is that common parent; `--auto` approves the gate commands and the score-file write, and add `--standalone` if the judge provider is injected inline:

       cd <common parent dir> && \
         opencode run --standalone --auto --agent build --thinking -m <judge-model> \
           "Judge <benchmark dir>/runs/<run-name>/patch-s<stage>.diff against <benchmark dir>/rubric.md, using <benchmark dir>/reference.diff as the reference and <benchmark dir>/runs/<run-name>/harness-s<stage>.report.md for the [R] lines (harness/README.md maps tests to lines; [R] lines are decided solely by that report, with no cascade credit). Read nothing else — not any score-s*.md, not any review-s*.md, not the run log, not the raw harness logs, not another stage's artifacts. The build gates are a maintainer-verified precondition (you may re-run pnpm tscheck / pnpm lint / pnpm build in <Shoko-WebUI checkout>). Score Score A and Score B independently and write the score sheet to <benchmark dir>/runs/<run-name>/score-s<stage>.md."

   The working directory must be the common parent; if it were the checkout alone, reads of the rubric and the sibling ShokoServer are auto-rejected in headless mode.

   The judge works **blind**, so the command must say what it may not read — the failure mode is real: an unbounded judge prompt will read an earlier stage's score sheet and the review text and anchor on them. Give it an explicit read list (the rubric, `reference.diff`, this stage's patch, this stage's sanitized harness report, `harness/README.md` for the test→line mapping, and the candidate tree) and forbid the rest (any `score-s*.md`, any `review-s*.md`, the run log, the raw harness logs, other stages' artifacts). Also state that `[R]` lines are decided **solely** by the harness report with no cascade credit, and that the gates were verified by the maintainer (so the judge need not re-run them, though it may). **Invoke the judge and the reviewer as headless `opencode run` processes — never as opencode subagents.** A subagent inherits the parent session's model when no model is passed, so such a lane silently runs on the orchestrator's own model instead of `<judge-model>`.

   **Verify the pass before trusting it.** Three checks, all cheap, all against the run's own log. They apply to the reviewer pass in step 7 too:
   - *Which model actually ran.* Headless opencode prints a banner naming the model it is using (`> build · muse-spark-1.3-contributor`); confirm it names `<judge-model>`. A mis-dispatched pass is invisible in the sheet itself — the banner is the only thing that reveals it.
   - *Which files it actually read.* The log lists every read; confirm the judge read only the permitted set. A judge that read an earlier stage's score sheet or the review text has anchored on it: discard that sheet and re-run, never hand-edit it.
   - *Whether the artifact was actually written.* A pass can produce a complete score sheet or review in its streamed output while its `write` call comes out mangled and never executes (`<atem:function_calls>` in place of a real call), so no `score-s<stage>.md` / `review-s<stage>.md` appears on disk. Confirm the file exists; if it does not, recover the text from the run's streamed output — do not re-run a pass that already produced its answer.
   - A pass that stopped **early** leaves nothing to recover: no artifact on disk and no sheet in the streamed output either (observed 2026-10-13 — a judge ended right after reading a few files). Re-run that pass. Never hand-edit an artifact into place.
   - If **no artifact was written** and the log ends in `Error: The request contains invalid parameters.` immediately after a `⚙ compress` tool call, that is a provider/tool incompatibility, not a judgement — re-run the pass.
7. **Repair rounds — only when a stage is not green.** A stage is **green** when the three gates pass and the harness passes in full (37/37 today). If stage 0 is not green, a **reviewer** writes a follow-up prompt and it is sent into the **same** session; the work after that round is stage 1, and a second round may follow as stage 2 — **two rounds maximum**. The reviewer sees the ticket, the candidate's diff, the sanitized harness failure report (`runs/<run-name>/harness-s<stage>.report.md` — spec titles and observed symptoms, never selector internals; the raw `harness-s<stage>.log` is still written for humans but is **not** given to the reviewer), the judge's score sheet for that stage (`runs/<run-name>/score-s<stage>.md` — a per-line account of what scored and why, naming the file and line where each problem lives), and the candidate tree. **The judge runs first**: the review round is written from the sheet, so steps 5–6 complete before step 7 begins. The sheet is the reviewer's full information, exactly as a human reviewer's would be; the constraint is on what it *writes*, not on what it may know. It must still **not** read `reference.diff` or `rubric.md` — the sheet carries the rubric-level findings, and the reference implementation is not something a reviewer would have in hand. The reviewer has no browser tool, so its own review is of the code and the diff — the harness is the runtime evidence; do not ask it to boot the app. This is where a human reviewer's judgement lives: details the ticket deliberately omits — a debounce interval, a trim, a convention the codebase already establishes — may be raised here. Its prompt is fixed-shape: at most five findings, ordered by severity, written as symptoms and expected behaviour only. It states **what** does not work, never the fix: no code, no rubric line numbers, and no file paths or `file:line` references — the sheet it read is full of them, and translating them into plain language is part of the job. When something is implemented the wrong way, it describes the intended behaviour or concept, not the exact change. Record the review text verbatim in `runs/<run-name>/review-s<stage>.md`. The reviewer runs headlessly from the common parent, e.g.

       cd <common parent dir> && \
         opencode run --standalone --auto --agent build --thinking -m <reviewer-model> \
           "Read <benchmark dir>/prompt.md, the candidate patch <benchmark dir>/runs/<run-name>/patch-s<stage>.diff, the sanitized harness report <benchmark dir>/runs/<run-name>/harness-s<stage>.report.md (spec titles and observed symptoms only; do not read the raw harness-s<stage>.log), and the judge's score sheet <benchmark dir>/runs/<run-name>/score-s<stage>.md — that sheet names the file and line where each problem lives; use it as your evidence, but keep its file:line detail out of what you write. Inspect the candidate tree in <Shoko-WebUI checkout> by reading files — do not run git; shell git commands are denied in headless runs. Write at most five findings, severity-ordered, as symptoms and expected behaviour only — say what does not work, never the fix; no code, no rubric line numbers, and no file paths or file:line references; for a wrong approach describe the intended behaviour, not the exact change — to <benchmark dir>/runs/<run-name>/review-s<stage>.md. Do not read <benchmark dir>/reference.diff or <benchmark dir>/rubric.md."

   The follow-up prompt handed to the model is that review text, sent into the **same** session with the id recorded at step 2:

       cd <parent dir holding both checkouts> && \
         opencode run --standalone --auto --agent build --thinking -m <model> --session <session id> \
           "$(cat <benchmark dir>/runs/<run-name>/review-s<stage>.md)"

   Each round then repeats steps 3–7 with the new stage number — normalize, export, gates, harness, judge (step 6), then the next review (step 7). The judge runs **before** the reviewer, because the reviewer reads the judge's sheet; the judge itself must not see the review text or another stage's score sheet. A trajectory still red after two rounds is recorded **not converged** — that is the result, not a sample to re-run or average.
8. `./run.sh cleanup <run-name>` — returns to `master`, deletes the branch, and removes `runs/<run-name>/`. The score recorded in `scorecards/<model>.md` is the only surviving artifact (see "Runs and recording").

Never let the branch outlive the run: results live in the exported patch, not in git.

### Reasoning level

A reasoning level is part of the **parameter set**, not the model id, and it is selected with a `#<level>` suffix on the model in step 2: `-m <model>#low`. The suffix picks a *variant* declared on the model entry of the injected opencode provider — the level itself is a setting inside that variant:

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

The settings key is camelCase `reasoningEffort`; the OpenAI-compatible provider maps it to the request's `reasoning_effort` field. Hosted providers ship their own effort variants (so `#xhigh` needs no declaration); a self-served model needs each level declared in the injection, and a model with no effort setting is run with no suffix and recorded as `default`. Every level is a **separate row** in the card — the parameter set differs, so the trajectories are not comparable to each other.

### Output limit and nudges

Every model is served with an output cap. A reasoning model can spend the entire budget on a planning chain-of-thought and end the turn with the work unimplemented — the plan is complete, no tool was called, and the run stopped **at the cap** (`finishReason: length`). That turn is resumed in the **same** session and nudged to stop reasoning and start implementing, then the gates run — and **whatever the cap is, it is not a fixed number**, so the rule keys on the cap being hit, never on a value:

    cd <parent dir holding both checkouts> && \
      opencode run --standalone --auto --agent build --thinking -m <model> --session <session-id> \
        "You have already reasoned enough; stop planning and implement the ticket now, \
         then run pnpm tscheck / lint / build."

Use that wording verbatim: the nudge is a fixed part of the protocol, so the *wording* of the intervention is identical across models — the *number* each model needs is not, which is why it is recorded.

A stage gets **at most five nudges** — and a nudge counts only when the turn stopped **at the output cap**. One nudge is often not enough: the truncated turn is resent, but the model re-derives its plan instead of continuing it, so a model that keeps re-emitting a plan can need several resume-and-nudge cycles. Re-check the candidate tree after each one (`git status --porcelain` in the checkout) and stop as soon as it is no longer untouched. If nothing has been implemented after the fifth, stop there — the stage stands as it stands and is recorded as it stands, and it is never re-run to look for a better sample.

A turn that ends unimplemented **without** hitting the cap (`finishReason: stop`, zero edits, tree untouched) is resumed the same way, but it is **not a nudge** and must not be counted as one. Record it in the stage's flags as a zero-work stop: that keeps the extra run visible without inflating the nudge count.

Resume from the **same cwd as the implementation step** — the parent holding both checkouts, so the model can still read the sibling ShokoServer source. `--session <session-id>` resolves the session by id; the cwd is what keeps the sibling reads legal. A degenerate repetition loop in the reasoning channel counts as this case too: the turn ends with `finish: "length"` and no tool call, so the run stopped unimplemented at the cap. The nudge is an **intervention, not part of the task**: record the stage it happened in **and how many nudges it took** — in `scorecard.md` (→ "Nudges") and in `scorecards/<model>.md` — so that stage's number is read with the help in mind. It is not a repair round: it is the same stage, rescued from a provider limit.

### Reliability

Judging is still blind and still double-checked; what changed is the sampling:

- **One trajectory, no repeats.** See "Method" above. The reported numbers are the trajectory's own stage scores, not a median of independent runs.
- **Blind double pass.** Re-judge a sample of stages (a second judge pass with no access to the first score sheet) and record the disagreement per line; a stage whose A/B lines the two passes disagree on is reported with that spread noted, never silently averaged.
- **"Not converged" stands.** A trajectory still red after two repair rounds is recorded `not converged`. It is not re-run to look for a better sample, and it is never averaged with a converged one.
- **Record the help.** Output-cap nudges inside a stage are recorded as a flag on that stage, with the count (see the section above), so a coached stage is never read as a clean one and how much help it took stays visible.

### Runs and recording

Run names are the served model id, e.g. `qwen36-35b-iq4xs` (without a rig prefix — models are assumed identical across rigs). Each model gets **one trajectory**: one branch per run; per stage one patch export (`patch-s<stage>.diff`), one raw harness log (`harness-s<stage>.log`, humans only), one sanitized harness report (`harness-s<stage>.report.md`, the reviewer's input), and one score sheet (`score-s<stage>.md`), plus the review text that opened the stage (`review-s<stage>.md`, stages 1 and 2 only); the run dir `runs/<model>/` is reused for every stage.

- **One card per model.** Results are grouped by model, not by model + quant, matching the model cards elsewhere in the repo: `scorecards/<model>.md` covers every quant of that model (one section per parameter set / level), and its headline rows land in `scorecard.md`. Where two rigs serve near-identical quants of one model (e.g. the two `qwen36` builds), bench one and mark the other `not run (duplicate of <quant>)` instead of benching both. The scorecard shape is in `scorecards/_template.md` — copy it once per model.
- The parameter set the model was served with (e.g. `kv-q8`, or `kv-q4` when re-testing with a different cache) is recorded in the scorecard, not in the run name — it can be arbitrarily long; the quant/paramset is a row in the card, not a separate card.
- **Pin the reviewer and the judge.** The card records the reviewer's model and variant and the judge's, next to the parameter set. The review text drives the repair rounds, so a trajectory measures the model **and** its reviewer: it is comparable only to another run with the same reviewer, and a card that names neither is not comparable to anything.
- Record each stage's **model time** — that stage's implementation run, i.e. the model's own session segment producing that stage's patch, start → finish from the run log — in the card's per-stage table (`scorecards/<model>.md`), and the **total model time** (the sum of those times, stage 0 through the stage that converged, or through stage 2 for a `not converged` trajectory) in the card's headline row and the `scorecard.md` row. The headline tables carry the **final score** and the total model time only; per-stage scores and timings go in the per-stage table. Harness, reviewer and judge time are **not** part of any recorded figure: the timing measures the model producing code, not the apparatus measuring it. Model time includes model load and any nudge.
- **Delete the run dir after recording.** Once the trajectory's stages (and any review text worth keeping) are recorded in `scorecards/<model>.md`, remove `runs/<model>/` — the scorecards are the persistent record, not the run artifacts. Review the patch before deleting; nothing survives in `runs/`.

## Layout

```
shoko-logs-v2/
  README.md            this file
  rubric.md            Score A (A1–A21), Score B (B1–B11), gates
  prompt.md            the ticket (search, download, DSL, reconnect, cancellation/failure)
  reference.diff       reference implementation (combined upstream diff)
  run.sh               runner: setup / eval / cleanup
  harness/             runtime assertions for the [R] Score-A lines (see harness/README.md)
  scorecards/
    _template.md       per-model scorecard shape
  scorecard.md         consolidated two-score table
```

The benchmark is self-contained: `reference.diff` and `run.sh` are local copies, and nothing is read from a sibling directory.

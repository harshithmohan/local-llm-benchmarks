# shoko-logs — realistic coding benchmark

A real-world coding task benchmark: from a clean base, reproduce the two upstream
Shoko-WebUI changes that rewrote the logs page with server-side search
([#1465](https://github.com/ShokoAnime/Shoko-WebUI/pull/1465)) and added log download
([#1468](https://github.com/ShokoAnime/Shoko-WebUI/pull/1468)). Unlike the timing
prompts in `test-prompts.md`, this is an agentic coding benchmark — it measures
whether a model can implement a non-trivial frontend feature against a real backend
API it must discover or parse.

- Source repo: [ShokoAnime/Shoko-WebUI](https://github.com/ShokoAnime/Shoko-WebUI).
- Base commit: [`a715a49c4feb1b9d32c21b6691f652b298632b14`](https://github.com/ShokoAnime/Shoko-WebUI/commit/a715a49c4feb1b9d32c21b6691f652b298632b14) (the commit before both changes).
- Reference implementation: the combined diff of
  [`9a411aa`](https://github.com/ShokoAnime/Shoko-WebUI/commit/9a411aaf86a7ec5b14eb5585754e8ac21f9d5a59) +
  [`05f8dc6`](https://github.com/ShokoAnime/Shoko-WebUI/commit/05f8dc6bef4e181f4bb1c22687cfcbf3b843bd0a),
  stored here as `reference.diff`.
- The backend (ShokoServer) is a sibling checkout; its logging API already exposes
  everything the frontend needs. The server is the source of truth for the API.

## Task summary

Given to the model as a ticket, never as a reference implementation:

1. **Server-side log search** — keep the SignalR live tail as the default view; when
   any filter is active (debounced search text or level chips), switch to a
   server-backed search over the full log history with paginated infinite scroll,
   level chips filtered server-side, loading/empty states, and a clear-filters action.
2. **Log download** — download button: current log file when no filters are active,
   filtered range when they are; loading state on the button, error toast on failure.

## Prompt

Delivered as a ticket with no API reference: the model must read the sibling ShokoServer
checkout to find the endpoint paths, query
parameters, response shapes, and the filter DSL grammar before writing any fetch calls.
This makes it a pure discovery test — *can the model find what it needs in an unfamiliar
codebase and build it?* — closest to real agentic coding, with no spec handed over. The
single prompt is [`prompt.md`](prompt.md).

## Scoring

Per run, a single 100-point rubric (`rubric.md`): the build gates (`pnpm tscheck` 2,
`pnpm lint` 1, `pnpm build` 2) plus 95 points across seven behavior aspects (data layer,
search integration, page composition, live view, search view, download, code quality),
each scored 0 / half / full against `reference.diff`. The repo has no tests (`vitest`
runs an empty suite), so the gates are build hygiene only and carry little weight. The
grader model runs the gates and produces the score sheet (see Protocol); the maintainer
spot-checks the line scores against the exported patch.

Recorded per run: gate results, rubric score, wall-clock run time, whether an
output-limit nudge or an auto-compaction was needed (see "Output limit and nudges" and
"Auto-compaction"), notes.

## Protocol

1. `./run.sh setup` — verifies a clean tree, creates branch `bench/shoko-logs`
   from the base commit, and prints the prompt for the implementation step.
   Point `run.sh` at the Shoko-WebUI checkout via `SHOKO_WEBUI_DIR` (or edit the top
   of `run.sh`); ShokoServer must sit beside it (siblings under one parent), which is
   what the prompt points to.
2. **Implement.** The implementation runs by giving a model the prompt, either
   interactively (start opencode in the checkout, select the model under test, paste
   `prompt.md`) or headlessly. The headless command depends on the OpenCode major
   version:

   - **OpenCode v2** — a run works in the process cwd, so `cd` to the parent first. Pass
     `--standalone` when the provider is injected with `OPENCODE_CONFIG_CONTENT` (the
     shared background service ignores the inline config) and `--auto` (a headless
     session cannot answer the edit permission prompt):

         cd <parent dir holding Shoko-WebUI and ShokoServer> && \
           opencode run --standalone --auto --agent build -m <model> \
             "$(cat <shoko-logs dir>/prompt.md)"

   - **OpenCode v1** — the working directory is passed with `--dir`:

         opencode run --agent build --model <model> --dir <parent dir holding \
           Shoko-WebUI and ShokoServer> "$(cat <shoko-logs dir>/prompt.md)"

   In both versions the directory must be the parent that holds **both** checkouts: the
   model has to read the sibling ShokoServer source, and headless opencode auto-rejects
   reads outside its working directory. Always use the `build` agent: the default
   `orchestrator` agent delegates to subagents and can finish without implementing. The
   harness itself never drives opencode; it only exports the patch after the model stops.
3. `./run.sh eval <run-name>` — exports the patch to `runs/<run-name>/`. No gates here:
   the grader runs them (next step). The checkout is left on the bench branch with the
   changes applied for the grader.
4. **Rubric eval — grader model.** Grade the exported patch with a headless opencode
   session running the configured grader model (`<grader-model>`). Use the `build`
   agent: the default `orchestrator` agent delegates to subagents and can return
   without producing a score sheet. Run opencode from a directory that contains the
   checkout, its sibling ShokoServer, and this benchmark dir (e.g. their common parent)
   so the grader can read `rubric.md`/`reference.diff`/the server source and still run
   the gates in the checkout.

   - **OpenCode v2** — cwd is the common parent; `--auto` approves the gate commands and
     the score-file write, and add `--standalone` if the grader provider is injected
     inline:

         cd <common parent dir> && \
           opencode run --standalone --auto --agent build -m <grader-model> \
             "Run the build gates in <Shoko-WebUI checkout> (pnpm tscheck, pnpm lint, pnpm build), then grade <shoko-logs dir>/runs/<run-name>/patch.diff against <shoko-logs dir>/rubric.md using <shoko-logs dir>/reference.diff as the reference implementation; write the score sheet to <shoko-logs dir>/runs/<run-name>/score.md."

   - **OpenCode v1**:

         opencode run --agent build --model <grader-model> --dir <common parent dir> \
           "Run the build gates in <Shoko-WebUI checkout> (pnpm tscheck, pnpm lint, \
            pnpm build), then grade <shoko-logs dir>/runs/<run-name>/patch.diff against \
            <shoko-logs dir>/rubric.md using <shoko-logs dir>/reference.diff as the \
            reference implementation; write the score sheet to \
            <shoko-logs dir>/runs/<run-name>/score.md."

   The grader runs the gates, reads `rubric.md`, `reference.diff`, and the run's patch,
   and writes `runs/<run-name>/score.md` in the format at the end of `rubric.md`. If
   you instead run it with the working directory (v2) or `--dir` (v1) set to the checkout
   alone, add `--auto` or stage the two rubric files into the checkout — reads outside
   the working directory are auto-rejected in headless mode.
5. After review, `./run.sh cleanup <run-name>` — returns to `master`, deletes the
   branch, and removes `runs/<run-name>/`. The score recorded in
   `scorecards/<model>.md` is the only surviving artifact (see "Run naming and
   repeats").

Never let the branch outlive the run: results live in the exported patch, not in git.

### Output limit and nudges

Serve every model under test with `limit.output` **16384**. Reasoning models can spend the
entire output budget on a planning chain-of-thought and stop at the cap with the ticket
unimplemented (`finishReason: length`, zero edits — the model reasoned a full plan but
never called a tool). When a run hits the cap this way, resume the **same** session and
nudge it to stop reasoning and start implementing, then run the gates:

    cd <Shoko-WebUI checkout> && opencode run -s <session-id> \
      "You have already reasoned enough; stop planning and implement the ticket now, \
       then run pnpm tscheck / lint / build."

Resume from the checkout directory itself: v1 reports "Session not found" if `--dir` is
passed to a resume, and in v2 the session is resolved from the cwd (add
`--standalone --auto`, as in the implementation step). The nudge is a **harness
intervention, not part of the task**: record every nudged run in `scorecard.md`
(→ "Output-limit nudges") and in `scorecards/<model>.md`, so nudged runs are only ever
compared against other nudged runs.

### Auto-compaction

A run can also hit the provider's size limit: opencode then compacts the session and
continues, so the model resumes from a summarized context rather than its full history
(the session may go on to report completion after the compaction). Like a nudge, this is
a **harness intervention, not part of the task** — record every auto-compaction (which
repeat, and that it recovered) in `scorecard.md` (→ "Auto-compactions") and in
`scorecards/<model>.md`, so compacted runs are only compared against other compacted runs.

### Run naming and repeats

Run names are the served model id, e.g. `qwen36-35b-iq4xs` (without a rig prefix —
models are assumed identical across rigs). Each model gets **2 repeats**; the score is
the mean of the 2 repeat totals. **opencode-go reference models are the exception:
1 run only** (cost), so their score is a single sample — no repeat-mean.

- The parameter set the model was served with (e.g. `kv-q8`, or `kv-q4` when
  re-testing with a different cache) is recorded in the scorecards, not in the run
  name — it can be arbitrarily long. Per-model detail goes in
  `scorecards/<model>.md` (one section per parameter set, labeled with the paramset);
  the headline row lands in `scorecard.md`. The scorecard shape (headings, rubric
  table, key findings, summary) is in `scorecards/_template.md` — copy it for a new
  model.
- Every repeat gets its own branch, patch export, and grading (the grader runs the
  gates); the run dir `runs/<model>/` is reused for each repeat.
- Record each repeat's **wall-clock run time** (session start → finish, as reported by
  the harness) in `scorecards/<model>.md`; the per-parameter-set **min–max** across
  repeats goes in the `scorecard.md` row's notes. Run time includes model load and, for
  nudged runs, the nudge.
- **Delete the run dir after recording the score.** Once a repeat's score (and any
  reviewer notes worth keeping) is recorded in `scorecards/<model>.md`, remove
  `runs/<model>/` — the scorecards are the persistent record, not the run artifacts.
  Review the patch before deleting; nothing survives in `runs/`.

## Results

Canonical results live in [scorecard.md](scorecard.md) — one row per model +
parameter set, the mean score across repeats (see "Run naming and repeats" above), with
per-capability subtotals (see `rubric.md` → "Capability dimensions and rollup").
Per-repeat rubric breakdown is in `scorecards/<model>.md`; run artifacts under
`runs/` are deleted once their scores are recorded.

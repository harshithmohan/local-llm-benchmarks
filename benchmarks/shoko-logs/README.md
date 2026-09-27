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

Delivered as a ticket with no API reference: the model must read the ShokoServer source
(`../ShokoServer` relative to the checkout) to find the endpoint paths, query
parameters, response shapes, and the filter DSL grammar before writing any fetch calls.
This makes it a pure discovery test — *can the model find what it needs in an unfamiliar
codebase and build it?* — closest to real agentic coding, with no spec handed over. The
single prompt is [`prompt.md`](prompt.md).

## Scoring

Per run, three layers (`rubric.md` has the full breakdown, 100 points):

1. **Automatic gates** — `pnpm tscheck` (2), `pnpm lint` (1), `pnpm build` (2).
   The repo has no tests (`vitest` runs an empty suite), so typecheck/lint/build are
   the only mechanical gates — they are build hygiene only and carry little weight.
2. **Rubric vs reference** — 95 points across seven behavior aspects (data layer,
   search integration, page composition, live view, search view, download, code
   quality), scored 0 / half / full per line against `reference.diff`.
3. **Maintainer review** — eyeball the exported patch; gate + rubric numbers are
   advisory until reviewed.

Recorded per run: gate results, rubric score, notes.

## Protocol

1. Pick the model in opencode (via the LiteLLM gateway).
2. `./run.sh setup` — verifies a clean tree, creates branch `bench/shoko-logs`
   from the base commit, and prints the prompt to paste into an opencode session
   started in the Shoko-WebUI checkout. Point `run.sh` at that checkout via
   `SHOKO_WEBUI_DIR` (or edit the top of `run.sh`); ShokoServer sits at
   `../ShokoServer` relative to the checkout, which is what the prompt points to.
3. Let the model work.
4. `./run.sh eval <run-name>` — runs the three gates (each pass/fail recorded
   independently), exports the patch to `runs/<run-name>/`.
5. Grade with `rubric.md`; save scores as `runs/<run-name>/score.md`.
6. After review, `./run.sh cleanup <run-name>` — returns to `master`, deletes the
   branch, and removes `runs/<run-name>/`. The score recorded in
   `scorecards/<model>.md` is the only surviving artifact (see "Run naming and
   repeats").

Never let the branch outlive the run: results live in the exported patch, not in git.

### Run naming and repeats

Run names are the served model id, e.g. `qwen36-35b-iq4xs` (without a rig prefix —
models are assumed identical across rigs). Each model gets **2 repeats**; the score is
the mean of the 2 repeat totals. **opencode-go reference models are the exception:
1 run only** (cost), so their score is a single sample — no repeat-mean.

- The parameter set the model was served with (e.g. `kv-q8`, or `kv-q4` when
  re-testing with a different cache) is recorded in the scorecards, not in the run
  name — it can be arbitrarily long. Per-model detail goes in
  `scorecards/<model>.md` (one section per parameter set, labeled with the paramset);
  the headline row lands in `scorecard.md`.
- Every repeat gets its own branch, gates run, and grading; the run dir
  `runs/<model>/` is reused for each repeat.
- **Delete the run dir after recording the score.** Once a repeat's score (and any
  reviewer notes worth keeping) is recorded in `scorecards/<model>.md`, remove
  `runs/<model>/` — the scorecards are the persistent record, not the run artifacts.
  Review the patch before deleting; nothing survives in `runs/`.

## Results

Canonical results live in [scorecard.md](scorecard.md) — one row per model +
parameter set, the mean score across repeats (see "Run naming and repeats" above).
Per-repeat rubric breakdown is in `scorecards/<model>.md`; run artifacts under
`runs/` are deleted once their scores are recorded.

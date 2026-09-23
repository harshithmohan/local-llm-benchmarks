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

## Context variants

| Variant | Prompt file | API context given |
|---|---|---|
| discovery | `prompt-discovery.md` | Ticket only; the model must read the ShokoServer source to find endpoints, params, and the filter DSL grammar |
| api-summary | `prompt-api-summary.md` | Ticket + endpoint list, params, response shapes, DSL grammar summary |
| full-spec | `prompt-full-spec.md` | Ticket + full behavioral spec including every edge case the reference implementation had to get right (query-key stability, param omission, DSL prefix regex, pagination triggers, scroll-lock logic, blob handling) |

The ticket body is identical in all three; only the API reference appendix differs.

**What each variant measures** (discovery is mandatory; api-summary and full-spec are optional diagnostics — run them when you want to isolate a failure mode):

- **discovery** — the headline number: *can the model find what it needs in an unfamiliar codebase and build it?* Closest to real agentic coding (no spec, must explore). A low score here reads as a weak explorer.
- **api-summary** (optional) — *given the API contract, can it implement?* Removes the research burden. Comparing against discovery separates "couldn't find the API" from "couldn't implement with the API known". For most models expect ≥ discovery; if a model scores below discovery (as qwen36-35b did), the summary hurt more than it helped — a signal in itself.
- **full-spec** (optional) — upper-bound control: *given a complete spec with every edge case spelled out, can it follow the spec?* Exposes whether a model's gap is information gathering (recovers strongly under full-spec) or implementation ability (stays low). It does not re-test discovery; it tells you whether the discovery variant's losses were research failures or implementation failures.

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

Recorded per run: variant, gate results, rubric score, notes.

## Protocol

1. Pick the model in opencode (via the LiteLLM gateway) and a variant.
2. `./run.sh setup <variant>` — verifies a clean tree, creates branch `bench/shoko-logs`
   from the base commit, and prints the prompt to paste into an opencode session
   started in the Shoko-WebUI checkout. Point `run.sh` at that checkout via
   `SHOKO_WEBUI_DIR` (or edit the top of `run.sh`); ShokoServer sits at
   `../ShokoServer` relative to the checkout, which is what the discovery prompt
   points to.
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

Run names follow `<model>/<variant>`, e.g. `qwen36-35b-iq4xs/discovery`:

- **model** is the served model id (without a rig prefix — models are assumed
  identical across rigs).
- **discovery is mandatory** (2 repeats); **api-summary and full-spec are optional**
  diagnostics (2 repeats each when run). A variant's score is the mean of its
  2 repeat totals; the Overall score is the mean of the variant means that were
  run (discovery-only → Overall = the discovery mean). Every repeat gets its own
  branch, gates run, and grading; the run dir `runs/<model>/<variant>/` is reused
  for each repeat. **opencode-go reference models are the exception: 1 run only** (cost),
  so their score is a single sample — no repeat-mean.
- The parameter set the model was served with (e.g. `kv-q8`, or `kv-q4` when
  re-testing with a different cache) is recorded in the scorecards, not in the run
  name — it can be arbitrarily long. Per-model detail goes in
  `scorecards/<model>.md` (one section per parameter set, labeled with the paramset);
  the headline row lands in `scorecard.md`.
- **Delete the run dir after recording the score.** Once a repeat's score (and any
  reviewer notes worth keeping) is recorded in `scorecards/<model>.md`, remove
  `runs/<model>/<variant>/` — the scorecards are the persistent record, not the run
  artifacts. Review the patch before deleting; nothing survives in `runs/`.

## Results

Canonical results live in [scorecard.md](scorecard.md) — one row per model +
parameter set, per-variant mean totals (see "Run naming and repeats" above).
Per-repeat rubric breakdown is in `scorecards/<model>.md`; run artifacts under
`runs/` are deleted once their scores are recorded.

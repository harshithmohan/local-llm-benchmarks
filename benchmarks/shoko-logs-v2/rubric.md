<!-- v2 design note: this file replaces v1's single 100-point rubric. It exists because the
v1 cohort showed the task is NOT saturated (spread 51-75) but the ONE headline number mixed
two different things: fulfilling the ticket, and replicating the hidden reference. Of v1's 95
rubric points, ~24 were earned by essentially nobody (DSL passthrough 10, reconnect reset 6,
scroll-lock 4, dead-code 3, header 1) and ~25 by essentially everybody (read contract, chips,
debounce, clear, endpoint switch, loading) — leaving only ~46 points of real separation, all in
scattered half-points. v2 splits the score in two and — since the iterative measurement loop
(README.md -> "Method") repairs a run only against what the ticket asks — puts every behaviour
we intend to grade in ONE ticket (prompt.md): the search/download features plus DSL-aware
search, reconnect recovery and cancellation/failure handling. Those three were a separate
"stretch" ticket in an earlier draft; they are now ticket requirements graded in Score A, so a
missing one surfaces in the next review round instead of being ungradeable. The ticket states
outcomes, not mechanisms: details a human would never say out loud — a debounce interval, a
trim, a library name, a copy string — are deliberately left out, and the conventions a developer
is expected to pick up from the codebase are graded in Score B (B11) instead. Every Score A line
is a behaviour the reference implementation itself exhibits, so the reference scores 100 on both
scores — a requirement the reference does not meet is not a ticket line (an earlier draft's
"discoverable syntax affordance" was dropped for exactly that reason: it graded a behaviour with
no reference exemplar; the cancellation line A20 is likewise scoped to the read path, because the
reference's download path has no stale-result guard).

Amendment (2026-10-13, A10/B2): the ticket's "off while filters are active" reads as absent, but
the reference keeps the scroll-to-bottom control on screen while merely disabling it, so that
visible-but-unusable quality is graded in B2 (removing the control is the wrong answer) while A10
accepts either state - absent or disabled - and still requires the control to be usable again in
the live tail once the filters are cleared. -->

# Rubric (v2) — shoko-logs

Score every line 0 / half / full. Score A and Score B are **independent 0–100 scores and are never summed** — that sum is exactly the conflation v2 removes. A line's points are listed in the tables below.

- **Score A — Ticket conformance.** Only behaviors `prompt.md` explicitly requests. Graded at runtime by the harness (`harness/`) wherever a line is marked **[R]**; otherwise by static inspection of the patch. This is the headline "did the model build the ticket" number.
- **Score B — Robustness & reference fidelity.** Behaviors the ticket deliberately does **not** state: reference-level polish that a production implementation has anyway. They are in scope, not extra credit — the run's target is the reference, and these are what a competent engineer applies without being told. A low Score B must never depress Score A. This is the "how close to production-grade" number. Most B lines are graded by static inspection of the patch; **B2 and B11 are behavioural** and are asserted at runtime by the harness (see the note under the table).
- **Build gates are a precondition, not points.** `pnpm tscheck` / `pnpm lint` / `pnpm build` are run **after** the protocol's normalize step (`pnpm dprint:fix && pnpm oxlint:fix`, README → Protocol step 3), so only what the deterministic fixers cannot repair counts. A failing gate never voids the stage: a red `build` blocks the runtime `[R]` lines (the harness cannot exercise the app), but the `[S]` lines and all of Score B are still graded from the patch, and a `lint` failure on its own leaves every line gradeable — it is recorded as a gate `❌` and raised in the next review round. Report gates as `✅/❌` in the score sheet; they carry no weight, because every v1 model passed them (zero separation).

Grade against the server contract below and the run's patch. Do **not** let a green build anchor line scores. **Score A** grades the observable outcome, not the reference's structure — a different approach that behaves correctly scores full. **Score B** is explicitly reference fidelity, so a B line may name the reference's mechanism (a specific component extension, a specific workaround); that is what the score is for.

## Server contract (ground truth; do not re-open the controller for grading)

- Read endpoint `Range/Read`: `level` (singular — `levels` is ignored), `message`, `logger`, `caller`, `exception`, `offset`, `limit` (≤1000), `descending` (defaults `true`; ascending requires `descending=false`). `message`/`logger`/`caller`/`exception` accept the DSL.
- Download: `Range/Download` (filtered) and `File/Current/Download` (unfiltered), same filter params, no paging.
- Pagination: response field `NextOffset`; non-null = next offset, `null` = exhausted.
- DSL grammar: mode char first (`c` contains, `=` equals, `^` starts-with, `$` ends-with, `~` fuzzy, `*` regex), then ≤1 `!` and ≤1 `#` in either order, then `:`. Bare value = case-sensitive contains; `c#:` = case-insensitive contains; `#` is ignored for `~`/`*`.

## Score A — Ticket conformance (100)

Every line is something `prompt.md` states. `[R]` = asserted by the runtime harness; `[S]` = graded from the patch when the harness cannot exercise it. An `[R]` line is decided **only** by its harness test: if that test fails, the line scores 0, and the judge may not credit it on the grounds that the failure is another line's cascade — a behaviour that cannot be observed because a prerequisite is broken is not met. The per-line note may name the cascade.

| # | Behavior (ticket) | Pts | Verify |
|---|---|---:|---|
| A1 | Live tail is the default view: SignalR subscription appends the connect backlog (`GetBacklog`) and each new entry (`Log`). | 5 | [R] |
| A2 | Any active filter (non-empty search **or** ≥1 level chip) switches to the server-search view; clearing filters switches back to the live tail. | 5 | [R] |
| A3 | Empty or blank input is not a search filter (the view stays on the live tail). | 2 | [R] |
| A4 | Six level chips (Trace…Critical), multi-select, filtering applied **server-side** (no client-side level filtering of the fetched history). | 4 | [R] |
| A5 | Read request contract: `Range/Read` with the exact param names `level` (singular), `message`, `offset`, `limit`, `descending=false` (ascending); empty `level`/`message` omitted, never sent as empty strings. | 6 | [R] |
| A6 | Pagination: next page is fetched automatically as the user scrolls toward the end, driven by the `NextOffset` cursor (next request uses the returned offset; `null` = exhausted, stop); pages arrive ascending, oldest→newest. Zero if no next-page fetch is ever invoked. | 7 | [R] |
| A7 | Result rendering: fetched pages concatenate in order with no dropped or duplicated entries; each row renders at least timestamp, level, and message from the returned fields. | 5 | [R] |
| A8 | First-fetch in-flight state, and an empty result with nothing loading shows an empty state distinct from "still loading" plus a Clear-filters action. | 4 | [R] |
| A9 | Clear-filters resets both the search text and the level chips. | 3 | [R] |
| A10 | While filters are active the scroll-to-bottom lock is not usable - disabled or absent both satisfy this - and it is usable again in the live tail once the filters are cleared. | 3 | [R] |
| A11 | Download: no filters → the server's current log file; any filter → the filtered range using the same level/search filters. | 4 | [R] |
| A12 | Download request contract: unfiltered hits `File/Current/Download`; filtered hits `Range/Download` with `level` (singular) + `message` correctly named. Wrong/absent param name = half at most. | 4 | [R] |
| A13 | Download button shows a visible busy indicator while in flight; a failure produces an error toast. | 3 | [R] |
| A14 | Download actually saves in a browser: the click triggers a real, completed file download — whatever resource it hands the browser must outlive the download (an immediately-revoked URL, or a no-op, fails). | 1 | [S] |
| A15 | The results list is virtualized — long lists are not rendered whole. | 1 | [S] |
| A16 | Dead code the change obsoletes is removed (old log query file/types, any leftover search placeholder). | 1 | [S] |
| A17 | **DSL pass-through**: a search expression that matches the server's prefix grammar is recognized and sent **unchanged** (the flags belong to the expression, not to a wrapping layer) — e.g. `^:GET /api` reaches `message` verbatim. The colon is what engages the grammar: a colon-less string (`^GET /api`) is a bare literal and is wrapped. The ticket states only that expressions must be honoured; the grammar itself must be **discovered from the server source**. | 17 | [R] |
| A18 | **DSL wrap rule**: only plain, non-DSL input is wrapped as a case-insensitive contains (`c#:`); input already in the grammar is passed through, not wrapped. A string that merely contains a colon is plain input, not an expression: a colon-bearing literal (`http://x`, `a:b`) and a malformed head (`cfoo:bar`) are both wrapped. (Whether anything is sent at all for blank input is A3.) | 8 | [R] |
| A19 | **Reconnect recovery**: on SignalR reconnect the tail resets so the fresh backlog replaces stale entries **without dropping entries that arrived around the reconnect** (any race-free ordering). | 8 | [R] |
| A20 | **Cancellation**: changing the filters cancels or ignores the in-flight search/read request — a stale response never renders over newer results. | 6 | [R] |
| A21 | **Failure surfacing**: a failed read/search request produces a visible error state distinct from the "no results" empty state (download failures keep their toast — A13). | 3 | [R] |
| | **Score A total** | **100** | |

## Score B — Robustness & reference fidelity (100)

Unstated in the ticket by design — in scope, not extra credit. These are the behaviors that separated v1's top runs from production grade, graded on their own so they cannot cap Score A.

| # | Behavior | Pts |
|---|---|---:|
| B1 | Level filter derived into a **stable, content-sensitive, order-independent** query key (sorted; a Set hashed directly, or toggle-order-significant, is half). | 11 |
| B2 | Scroll lock (behavioral): unlocks on a genuine user scroll-up and **stays locked** through programmatic `scrollToIndex` and virtualizer measurement corrections. Re-engagement is **explicit** (the lock control) — a released follow is not silently re-engaged by scrolling back to the bottom. Grade the outcome; the bottom-distance check is one valid mechanism. While filters are active the control stays visible and merely unusable - removing it from the screen is the wrong answer. | 11 |
| B3 | Virtualizer sized from live container dimensions (the `scrollRect` workaround), not a snapshot. | 11 |
| B4 | Empty-tail spinner: shown while the live tail has no entries — including just after a reconnect reset — and gone once entries exist. | 12 |
| B5 | Phantom loader row for a subsequent page (distinct from the first-fetch full-height state). | 9 |
| B6 | Level chips carry tooltips **and** active styling (active styling only = half). | 9 |
| B7 | Header reflects mode (live-tail count vs. server-search hint). | 7 |
| B8 | The shared `IconButton` gains a `loading` prop wired to the button (rewards the component extension, not merely a spinner). | 7 |
| B9 | Typing quality: event/level/result types model the real API/event shape; `Level` is the `LogLevelType` union (not bare `string`); no `any` leakage. Grade against the DTO. | 9 |
| B10 | No **newly-added** unused exports (lint does not catch unused exports — check manually). Removal of code the change obsoletes is A16, not here. | 7 |
| B11 | **Search-input discipline** (behavioral): rapid typing coalesces — a request per keystroke is a fail — and the value sent is trimmed. The interval itself is not pinned: the app's own search inputs vary. | 7 |
| | **Score B total** | **100** |

B2 and B11 are **behavioural** and are asserted at runtime by the harness; every other B line is graded statically from the patch.

## Score sheet

Copy into `runs/<run-name>/score-s<stage>.md` (one sheet per stage) and fill in. Two totals, never summed.

````markdown
# Score — <run-name> stage <stage> (v2)

| Field | Value |
|---|---|
| Run | `<run-name>` |
| Stage | <0 / 1 / 2> |
| Model | `<model>` |
| Date | <date> |
| Gates | tscheck ✅/❌ · lint ✅/❌ · build ✅/❌ (**precondition**) |
| **Score A — Ticket conformance** | **<n> / 100** |
| **Score B — Robustness & fidelity** | **<n> / 100** |
| Harness | <passed / partial / not run — why> |

<judging method note: judge model + invocation, whether the harness ran, maintainer spot-checks, re-judges>

## Score A lines

| # | Score | Notes (cite the harness assertion or patch evidence) |
|---|---|---|
| A1 | | |
| … | | through A21 |

## Score B lines

| # | Score | Notes |
|---|---|---|
| B1 | | |
| … | | through B11 |

## Reviewer notes

### Architecture
<approach summary — how the solution differs from the reference>

### Correctness risks
<numbered list of correctness risks / hackiness, with patch or harness evidence>

### Rubric gaps / notables
<+/~/− items: anything the rubric missed, good or bad>

**Bottom line**: <one-paragraph verdict, quoting both scores>
````

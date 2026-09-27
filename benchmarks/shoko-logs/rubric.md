# Rubric — shoko-logs

Score each line 0 / half / full against `reference.diff` and the run's patch.
Gates are binary. Total 100. The grader model (headless opencode, `<grader-model>`; see
README Protocol) runs the build gates and scores every line, then the maintainer
spot-checks.

Gates measure **build hygiene only** — no runtime behavior is verified by them.
Do not let green gates anchor the line scores: a patch can pass all three gates
with half the feature non-functional.

| # | Aspect | Pts |
|---|---|---|
| **Gates** | | **5** |
| 1 | `pnpm tscheck` clean | 2 |
| 2 | `pnpm lint` clean (dprint + oxlint + stylelint) | 1 |
| 3 | `pnpm build` succeeds | 2 |
| **Data layer** | | **19** |
| 4 | Live tail: SignalR subscription appends backlog (`GetBacklog`) and per-entry (`Log`); on reconnect the tail is reset so the fresh backlog replaces stale entries **without dropping the new ones**. Grade the outcome (post-reconnect list = fresh backlog, no lost entries); accept any race-free reset order | 6 |
| 5 | Server search: paginated `Range/Read` query (offset pages, `NextOffset` → next page, exhausted on null, `descending=false`/ascending) **and** correct read-endpoint query-param names (`level` singular, `message`, `offset`, `limit`, `descending`). Download params are graded separately (line 20) | 10 |
| 6 | Level filter derived into a stable, content-sensitive query key (Set never hashed directly; key order-independent — sorted — so toggle order is irrelevant; array-vs-Set source doesn't matter, only the derived key) | 3 |
| **Search integration** | | **15** |
| 7 | DSL handling: passthrough prefix check matching the server's mode/modifier grammar (mode char first, ≤1 `!` and ≤1 `#` in either order, then `:`); everything else wrapped as case-insensitive contains; empty search not wrapped/sent. Do not require `#` to modify `~`/`*` — the server ignores it there. *Discovery discriminator* | 10 |
| 8 | Empty `message`/`level` params omitted, never sent as empty strings | 5 |
| **Page composition** | | **18** |
| 9 | `filtersActive` (debounced search ≠ "" or any level chip) switches live view ↔ server search view | 7 |
| 10 | Level chips: six levels, toggleable, tooltip **and** active styling (active styling only = half) | 4 |
| 11 | Debounced (~250 ms) trimmed search input | 3 |
| 12 | Clear-filters action resets both filters; scroll-lock button disabled while filters active | 3 |
| 13 | Header reflects mode (live tail count / server-search hint) | 1 |
| **Live view** | | **8** |
| 14 | Scroll lock (behavioral): the view unlocks on a genuine user scroll-up (scrolled away from the bottom) and stays locked through programmatic `scrollToIndex` and virtualizer measurement corrections. Grade the observable outcome; the bottom-distance check is one valid mechanism, not the criterion | 4 |
| 15 | Virtualizer sized with live container dimensions (e.g. the `scrollRect` workaround) | 1 |
| 16 | Empty-tail spinner: shown while the live tail has no entries — including just after a reconnect reset — and gone once entries exist | 3 |
| **Search view** | | **15** |
| 17 | Subsequent pages are actually fetched as the user reaches the trailing row (effect on the trailing virtual row or an equivalent trigger); no render-phase side effect, no needless debounce. **Zero if no next-page fetch is ever invoked** — defining `useInfiniteQuery` with a correct `getNextPageParam` alone does not satisfy this | 6 |
| 18 | Results rendering: fetched pages are concatenated in order and rendered using the returned log fields, with no dropped or duplicated entries | 5 |
| 19 | Full-height "searching" state on first fetch only; phantom loader row for next page; "no results" state with Clear filters | 4 |
| **Download** | | **14** |
| 20 | Endpoint switching: no filters → `File/Current/Download`; any filter → `Range/Download`. **Full requires both** the endpoint switch **and** `level` (singular) + `message` sent with correct names; wrong/absent param name = half at most | 6 |
| 21 | Blob handling — full requires object URL + DOM-attached anchor + **deferred** revoke (async/`setTimeout`, not synchronous after `click()`); the filename may come from the server (`Content-Disposition`) **or** be generated with date+time. Immediate revoke or a detached anchor = half; both wrong = 0 | 3 |
| 22 | Loading state = visible busy indicator on the button (e.g. `loading` prop/spinner), not merely `disabled` (disabled-only = half); error toast on failure | 4 |
| 23 | `IconButton` gains a `loading` prop wired to the Button (the visible loading state itself is scored on line 22; this line only rewards the specific prop extension) | 1 |
| **Code quality** | | **6** |
| 24 | Dead code: reference's old `logs/` query file + `LogLineType` removed, no leftover commented search placeholder, **and no newly-added unused exports/imports** (unused exports are not caught by lint — check manually) | 3 |
| 25 | Typing quality: event/level/result types modeled to match the actual API/event shape; `Level` typed as the `LogLevelType` union (not bare `string`); no `any` leakage. Grade against the DTO — do not require any field be optional | 3 |
| | **Total** | **100** |

## Capability dimensions and rollup

The 25 lines above roll up into five capability dimensions, so models can be compared
by *task type* (discovery vs. implementation vs. wiring) instead of only by feature
area. Dimensions are **rollups of the same points** — not extra points. Score each line
once; a capability score is the sum of its mapped lines.

| Dimension | Definition | Lines | Pts |
|---|---|---|---|
| **Discovery & server-contract** | Find and correctly apply the ShokoServer search contract, including its filter DSL | 5, 7 | 20 |
| **Implementation** | Build the required UI behaviors, states, and component-level behavior | 10, 11, 13, 14, 15, 16, 19, 21, 22, 23 | 28 |
| **Integration & wiring** | Connect state, events, pagination, rendered data, and download requests end to end | 4, 6, 8, 9, 12, 17, 18, 20 | 41 |
| **Build hygiene** | Keep the project's type-check, lint, and build gates passing | 1–3 | 5 |
| **Code quality** | Keep the patch appropriately typed and free of obsolete or unused code | 24, 25 | 6 |
| | | | **100** |

Tie-breaks for lines that straddle two dimensions: line 7 (DSL handling) counts as
Discovery & server-contract because it measures applying the server grammar; lines 12,
17, 18, and 20 count as Integration & wiring because they grade cross-state coordination
and end-to-end data/request flow. Local mechanics (blob handling 21, scroll lock 14,
virtualizer sizing 15, loading UI 22) stay under Implementation.

> No separation signals: in the recorded cohort line 5 is saturated (every model full),
> so Discovery discriminates mainly through line 7, and Build hygiene separates no model
> (all pass the gates). See `scorecard.md`.

## Server contract (ground truth for grading API lines)

Do not re-open `LoggingController.cs` / `LogService.cs` — grade against this:

- Read endpoint `Range/Read`: `level` (singular — `levels` is ignored by the server),
  `message`, `logger`, `caller`, `exception`, `offset`, `limit` (≤1000), `descending`
  (defaults `true`; ascending requires `descending=false`). `message`, `logger`,
  `caller`, and `exception` accept the DSL.
- Download endpoints take the same filter params (no paging): `Range/Download` when
  filtered, `File/Current/Download` with no params when unfiltered.
- Pagination: response field `NextOffset`; non-null = next page offset, `null` = exhausted.
- DSL grammar: mode char first (`c` contains, `=` equals, `^` starts-with, `$`
  ends-with, `~` fuzzy, `*` regex), then ≤1 `!` (negate) and ≤1 `#` (case-insensitive)
  in either order, then `:`. Bare value = case-sensitive contains; `c#:` =
  case-insensitive contains. `#` is ignored for `~` fuzzy and `*` regex modes.

## Score sheet

Copy into `runs/<run-name>/score.md` and fill in. Markdown format.

````markdown
# Score — <run-name>

| Field | Value |
|---|---|
| Run | `<run-name>` |
| Model | `<model>` |
| Date | <date> |
| Gates | tscheck ✅/❌ · lint ✅/❌ · build ✅/❌ (**5/5 or partial**) |
| Rubric subtotal | **<n> / 95** |
| **Total** | **<n> / 100** |

<grading method note — grader model + invocation, maintainer spot-checks, re-grades>

## Capability subtotals

Percentage of each dimension's max (Discovery 20, Implementation 28, Integration &
wiring 41, Build hygiene 5, Code quality 6), summed from the mapped lines above (gates
1–3 under Build hygiene).

| Dimension | % |
|---|---:|
| Discovery & server-contract | <n>% |
| Implementation | <n>% |
| Integration & wiring | <n>% |
| Build hygiene | <n>% |
| Code quality | <n>% |
| **Total** | **<n>%** |

## Line scores

| # | Score | Notes |
|---|---|---|
| 4 | <0/0.5/1> | <one-line justification> |
| … | | through 25 |

## Reviewer notes

### Architecture
<approach summary — how the solution differs from the reference>

### Correctness risks
<numbered list of correctness risks / hackiness to double-check, with patch evidence>

### Rubric gaps / notables
<+/~/− items: anything the rubric missed, good or bad>

**Bottom line**: <one-paragraph verdict>
````

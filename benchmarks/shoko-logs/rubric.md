# Rubric — shoko-logs

Score each line 0 / half / full against `reference.diff` and the run's patch.
Gates are binary. Total 100.

Gates measure **build hygiene only** — no runtime behavior is verified by them.
Do not let green gates anchor the line scores: a patch can pass all three gates
with half the feature non-functional.

| # | Aspect | Pts |
|---|---|---|
| **Gates** | | **5** |
| 1 | `pnpm tscheck` clean | 2 |
| 2 | `pnpm lint` clean (dprint + oxlint + stylelint) | 1 |
| 3 | `pnpm build` succeeds | 2 |
| **Data layer** | | **18** |
| 4 | Live tail: SignalR subscription with backlog append + per-entry append; on reconnect, tail reset so fresh backlog replaces stale entries | 6 |
| 5 | Server search: paginated `Range/Read` query (offset pages, `NextOffset` → next page, exhausted on null, `descending=false`/ascending) **and** correct query-param names (`level` singular, `message`, `offset`, `limit`, `descending`) | 9 |
| 6 | Level filter derived into a stable, content-sensitive query key (Set never hashed directly; key order-independent — sorted — so toggle order is irrelevant; array-vs-Set source doesn't matter, only the derived key) | 3 |
| **Search integration** | | **15** |
| 7 | DSL handling: full-grammar passthrough regex (mode char first, ≤1 `!` and ≤1 `#` in either order, then `:`); everything else wrapped as case-insensitive contains; empty search not wrapped/sent. *Discovery discriminator — near-mechanical for full-spec runs* | 10 |
| 8 | Empty `message`/`level` params omitted, never sent as empty strings | 5 |
| **Page composition** | | **17** |
| 9 | `filtersActive` (debounced search ≠ "" or any level chip) switches live view ↔ server search view | 6 |
| 10 | Level chips: six levels, toggleable, tooltip **and** active styling (active styling only = half) | 4 |
| 11 | Debounced (~250 ms) trimmed search input | 3 |
| 12 | Clear-filters action resets both filters; scroll-lock button disabled while filters active | 3 |
| 13 | Header reflects mode (live tail count / server-search hint) | 1 |
| **Live view** | | **12** |
| 14 | Scroll lock (behavioral): lock reliably **unlocks only on a genuine user scroll-up** (bottom-distance check), and stays locked through programmatic `scrollToIndex` and virtualizer measurement corrections. Snapshot/throttle machinery is a smell, not the criterion — grade whether the lock unlocks at all and stays locked through programmatic scroll | 6 |
| 15 | Virtualizer scrollRect workaround present (container live dimensions patched on the virtualizer) | 3 |
| 16 | Empty-tail spinner gated correctly (initial state only) | 3 |
| **Search view** | | **9** |
| 17 | Subsequent pages are actually fetched as the user reaches the trailing row (effect on the trailing virtual row or an equivalent trigger); no render-phase side effect, no needless debounce. **Zero if no next-page fetch is ever invoked** — defining `useInfiniteQuery` with a correct `getNextPageParam` alone does not satisfy this | 5 |
| 18 | Full-height "searching" state on first fetch only; phantom loader row for next page; "no results" state with Clear filters | 4 |
| **Download** | | **18** |
| 19 | Endpoint switching: no filters → `File/Current/Download`; any filter → `Range/Download`. **Full requires both** the endpoint switch **and** `level` (singular) + `message` sent with correct names; wrong/absent param name = half at most | 6 |
| 20 | Blob handling — full requires all four: object URL + DOM-attached anchor + **deferred** revoke (async/`setTimeout`, not synchronous after `click()`) + local date**+time** filename. Immediate revoke or date-only UTC filename = half | 5 |
| 21 | Loading state = visible busy indicator on the button (e.g. `loading` prop/spinner), not merely `disabled` (disabled-only = half); error toast on failure | 4 |
| 22 | `IconButton` gains a `loading` prop wired to the Button | 3 |
| **Code quality** | | **6** |
| 23 | Dead code: reference's old `logs/` query file + `LogLineType` removed, no leftover commented search placeholder, **and no newly-added unused exports/imports** (unused exports are not caught by lint — check manually) | 3 |
| 24 | Typing quality: event/level/result types modeled; `Logger`/`Caller`/`ThreadID`/`ProcessID` modeled optional; `Level` typed as the `LogLevelType` union (not bare `string`); no `any` leakage | 3 |
| | **Total** | **100** |

## Server contract (ground truth for grading API lines)

Do not re-open `LoggingController.cs` / `LogService.cs` — grade against this:

- Query params: `level` (singular — `levels` is ignored by the server), `message`,
  `logger`, `caller`, `exception` (DSL only), `offset`, `limit` (≤1000),
  `descending` (defaults `true`; ascending requires `descending=false`).
- Pagination: response field `NextOffset`; non-null = next page offset, `null` = exhausted.
- Endpoints: `Range/Read`, `Range/Download`, `File/Current/Download`.
- DSL grammar: mode char first (`c` contains, `=` equals, `^` starts-with, `$`
  ends-with, `~` fuzzy, `*` regex), then ≤1 `!` (negate) and ≤1 `#` (case-insensitive)
  in either order, then `:`. Bare value = case-sensitive contains; `c#:` =
  case-insensitive contains.

## Score sheet

Copy into `runs/<run-name>/score.md` and fill in. Markdown format.

````markdown
# Score — <run-name>

| Field | Value |
|---|---|
| Run | `<run-name>` |
| Model | `<model>` |
| Variant | discovery \| api-summary \| full-spec |
| Date | <date> |
| Gates | tscheck ✅/❌ · lint ✅/❌ · build ✅/❌ (**5/5 or partial**) |
| Rubric subtotal | **<n> / 95** |
| **Total** | **<n> / 100** |

<grading method note — who graded, spot-checks, re-grades>

## Line scores

| # | Score | Notes |
|---|---|---|
| 4 | <0/0.5/1> | <one-line justification> |
| … | | through 24 |

## Reviewer notes

### Architecture
<approach summary — how the solution differs from the reference>

### Correctness risks
<numbered list of correctness risks / hackiness to double-check, with patch evidence>

### Rubric gaps / notables
<+/~/− items: anything the rubric missed, good or bad>

**Bottom line**: <one-paragraph verdict>
````

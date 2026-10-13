# shoko-logs v2 — runtime acceptance harness

A Playwright-driven acceptance suite for the **shoko-logs v2** coding benchmark. It replaces v1's static *"diff the patch against `reference.diff`"* grading with **runtime assertions**: it boots the candidate's Shoko-WebUI dev server, stubs the Shoko Server API and the SignalR logging hub, drives the real UI, and asserts on **(a) the app's outbound HTTP requests** and **(b) observable DOM/state** — never on component structure or source text.

It covers the Score A lines marked `[R]` in [`../rubric.md`](../rubric.md) — **A1–A13, A17, A18, A19, A20, A21** — plus the two **behavioural** Score B lines (**B2** scroll lock, **B11** search-input discipline). Score A's remaining static lines (A14, A15, A16) and the static Score B lines stay with the static judge.

> **Status: validated.** Every stub shape below was derived from the reference implementation (server-side log search + log download) and the suite runs green against it — see [Validation](#validation). The hooks that gate Score A are ticket-level and wording-tolerant — never dependent on arbitrary copy (see [Selector policy](#selector-policy--hooks-are-convention-based-never-copy-based)), so a conformant candidate with different markup or copy is not penalised.

---

## Why Playwright (tool decision)

**Chosen: Playwright** driving the real Vite dev server.

- The rubric is explicitly about **outbound requests + observable behavior** — exact query parameter names (`level` singular, `message`, `offset`, `limit`, `descending=false`, omitted-when-empty), cursor-driven pagination (`NextOffset`), and the DOM states around them. Playwright's `page.route()` is the only one of the two candidates that lets the harness both **stub** those responses *and* **record every request** at the network boundary in one place, while running the app unmodified.
- Pagination (A6) and the scroll-lock (A10) depend on a real browser layout and the `@tanstack/react-virtual` virtualizer firing scroll-driven effects — behavior a jsdom environment does not reproduce faithfully. Playwright uses a real Chromium.
- `page.routeWebSocket()` lets the harness stand in for the SignalR hub (A1) so the app can connect its real `@microsoft/signalr` client against a fake transport.
- Vitest + jsdom + MSW was considered: lighter, but it cannot exercise the virtualizer or scroll semantics (A6/A10) with confidence and would push request inspection into MSW handlers rather than the real network stack.

**One line:** Playwright, because the rubric asserts real network parameters and virtualizer/scroll behavior, which needs a real browser plus request interception that jsdom+MSW cannot match.

---

## Layout

```
harness/
├── README.md                  ← this file
├── package.json               ← dev deps + `test` script (pnpm-managed)
├── tsconfig.json
├── playwright.config.ts       ← boots/stops the dev server via webServer
├── run.sh                     ← one-command entry point (wires SHOKO_WEBUI_DIR)
├── .gitignore
├── reporters/
│   └── sanitized-report.ts    ← sanitized failure report (reviewer input)
├── scripts/
│   └── dev-server.mjs         ← launches the checkout's Vite dev server (headless)
├── fixtures/
│   └── mock-data.ts           ← canned log entries + `NextOffset` pages
├── helpers/
│   ├── app.ts                 ← auth seeding, navigation, view assertions
│   ├── mock-server.ts         ← API + SignalR stub and request recorder
│   ├── selectors.ts           ← convention-based, wording-tolerant locators
│   └── fixtures.ts            ← Playwright `test` extended with the mock server
└── specs/
    ├── live.a1.spec.ts                        ← A1
    ├── search-contract.a2-a5.spec.ts          ← A2, A3, A4, A5
    ├── pagination.a6.spec.ts                  ← A6, A7
    ├── states.a8-a10.spec.ts                  ← A8, A9, A10
    ├── download.a11-a13.spec.ts               ← A11, A12, A13
    ├── dsl.a17-a18.spec.ts                    ← A17, A18
    ├── reconnect.a19.spec.ts                  ← A19
    ├── cancellation-failure.a20-a21.spec.ts   ← A20, A21
    ├── score-b.b2.spec.ts                     ← B2 (behavioural)
    └── score-b.b11.spec.ts                    ← B11 (behavioural)
```

## How to run

The harness never hard-codes a checkout path. Point it at any Shoko-WebUI checkout with `SHOKO_WEBUI_DIR` (the same env var the benchmark's `./run.sh` uses):

```bash
# from benchmarks/shoko-logs-v2/harness/
SHOKO_WEBUI_DIR=/path/to/Shoko-WebUI ./run.sh

# a single rubric grouping:
SHOKO_WEBUI_DIR=/path/to/Shoko-WebUI ./run.sh specs/pagination.a6.spec.ts

# headed / interactive debugging:
SHOKO_WEBUI_DIR=/path/to/Shoko-WebUI ./run.sh --headed
```

`run.sh` installs the harness's own deps with `pnpm` on first use, ensures the Chromium browser is present, and exits non-zero if any assertion fails. The dev server is started and stopped automatically by Playwright's `webServer` (see `playwright.config.ts`); it is never left running.

Optional environment variables:

| Variable        | Default | Meaning                                             |
| --------------- | ------- | --------------------------------------------------- |
| `SHOKO_WEBUI_DIR` | —     | **Required.** Path to the candidate checkout.        |
| `HARNESS_PORT`  | `3100`  | Port for the Vite dev server + Playwright `baseURL`. |
| `CI`            | unset   | Set to disable `reuseExistingServer`.               |
| `HARNESS_REPORT` | `harness-report.md` (in the harness dir) | Path for the sanitized failure report. |

## Failure report — the reviewer's input

Alongside the usual Playwright output, the run writes a small markdown **failure report** (`reporters/sanitized-report.ts`, wired in `playwright.config.ts`). It is the only harness output handed to the reviewer during a repair round; the raw Playwright log is kept for humans and is **not** given to the reviewer.

It is written to `HARNESS_REPORT` when set, otherwise to `harness-report.md` in the process cwd (the harness dir). Its shape is stable and small:

```markdown
# Harness failure report

Result: 37/37 passed, 0 failed (96s)

## Failures

None — the suite is green.
```

When tests fail, `## Failures` lists one bullet per failed test — `**<spec> › <test>** — <symptom>` — where the symptom is reduced to its semantic lines (`Expected`/`Received`/`Error:`/`Timeout` and the first error line); stack frames, Playwright call-log blocks and any line carrying a selector (`getBy…`, `locator(…)`, `page.…`, `#id`) are dropped, so a raw selector can never reach the reviewer. Two Playwright prefixes name an API rather than a selector, so they are *replaced* rather than dropped — dropping would lose the symptom clause behind them: the interaction API (`locator.fill: `, `locator.click: `) and the assertion wrapper (`expect(locator).toBeVisible()`, `expect(page).toHaveURL(…)`) both become a neutral phrase (`the check`), leaving `Expected: visible; Timeout: 10000ms; Error: element(s) not found` intact.

## Validation

Validated end-to-end against the reference Shoko-WebUI implementation (the branch carrying server-side log search **and** log download):

```bash
cd benchmarks/shoko-logs-v2/harness
SHOKO_WEBUI_DIR=/path/to/Shoko-WebUI ./run.sh
```

Result: **37 passed** (Chromium, 1 worker, `retries: 0`), ~1.6 min. Every spec runs the real app against the stub — nothing is mocked at the component level, and no assertion depends on a class name or component internals.

A run's wall-clock is dominated by *failures*, not passes: Playwright can only conclude a failing test by exhausting the per-test `timeout` (30 s in `playwright.config.ts`), so a candidate that breaks N specs costs roughly `N x 30 s` on top of the green-case ~100 s.

## Selector policy — hooks are convention-based, never copy-based

Score A measures **ticket conformance**, not fidelity to the reference's markup. The ticket pins **no copy at all** — it states outcomes ("gives the user a way to clear the filters", "the view must say so", "an empty state that is visibly different from 'still loading'", "a failure surfaces as an error toast"). So no hook may depend on an arbitrary string. A hook may rely on structure or attributes that follow from the repo's own existing dependencies and components, but only as **one strategy in a union**, never as the only strategy — so a conformant candidate that chose different markup or copy still passes:

| Hook | Ticket basis | Resolution (in order) |
| ---- | ------------ | -------------------- |
| `searchInput` | "search input" — id/placeholder unpinned | accessible name ~ `/search/i` → `input[placeholder*=search]` → `input#search` → any enabled text input |
| `levelChip` | a chip for one of the six levels (the names are the server's own level values) | `button[data-tooltip-content*=«Level»]` → `getByRole('button', { name: /^«Level»/, or its common short form })` — the name match accepts the level word **or** its common abbreviation (`Info`/`Warn`), because these lines measure the chip's behaviour, never its spelling; a level with no chip at all (e.g. no Critical) still resolves to nothing |
| `clearFiltersInView` | "gives the user a way to clear the filters" — no copy pinned | accessible name ~ `/\b(clear\|reset)\b/i` → `button[aria-label*=clear]` → `button[aria-label*=reset]`. The tooltip strategy is deliberately **omitted**: the reference's toolbar holds an always-present icon-only clear button whose tooltip would match first, which would make A8's "empty state shows a Clear-filters action" vacuously true |
| `downloadButton` | "add a download button" | `button[data-tooltip-content*=download]` → accessible name ~ `/download/i` → `button[aria-label*=download]` |
| `scrollLockButton` | the scroll-to-bottom lock (ticket: it "belongs to the live tail only") | `button[data-tooltip-content*="scroll to bottom"]` → accessible name ~ `/scroll…bottom\|auto-scroll\|follow the tail/i` → `button[aria-label*=scroll]` → `button[title*=scroll]` |
| `searchingState` | "while the first fetch is in flight the view must say so" | a busy/status affordance inside the view (`[role=status]`, `[aria-busy=true]`, `[class*=spinner\|loading\|skeleton]`) → any visible text matching `/loading\|searching\|fetching\|retrieving\|looking/i` |
| `noResultsState` | "an empty state that is visibly different from 'still loading'" | any visible text matching `/no … (result\|match\|entr…\|found\|log)/i` → a `[role=status]` carrying such text |
| `rows` | the repo's existing long-list rendering (the checkout already depends on `@tanstack/react-virtual`) | `[data-index]` — the attribute that dependency sets on each mounted row |
| `errorToast` | "a failure surfaces as an error toast" | `.Toastify__toast--error` (the repo's existing toast library) → `[role=alert]` → `[class*=toast][class*=error]` |
| `errorAffordance` | "a failed read produces a visible error state, distinct from the empty-results state" | `errorToast` → failure wording inside the logs view ("failed to", "could not", "unable to", "something went wrong"). Deliberately not a bare `/error/i`: the "Error" level chip would satisfy that for every implementation |

Four deliberate consequences:

- **Reference-cosmetic copy never gates Score A.** The live-tail line count ("*n* lines in the live tail"), the page subtitle, the input `id`, the header copy and the scroll-lock's own tooltip wording are *reference* choices the ticket does not state, so the harness proves those outcomes behaviourally (e.g. the live tail is the view that renders the hub backlog; "no filter active" is never asserted via a count string) and the cosmetic matching stays with the static **Score B** review. The same rule governs the page-open signal: every spec waits on the layout's content wrapper (`.scroll-no-gutter`), never on the page title — a candidate that renames the title must fail only the lines that measure what it broke, not all 37.
- **Tolerance loosens the hook, never the assertion.** The semantics of each line stay at full strength: A3 still requires no read for blank input, B11 still requires exactly one read carrying only the final trimmed value, A4/A5 still require the exact parameter contract, A6 the cursor chain, A10 the not-usable lock (removed or disabled), A11–A13 the endpoint selection, the busy state and the error toast.
- **A union locator is asserted carefully.** `.or()` unions cannot be used with `toHaveCount()` (they report 0); union assertions use `.first().toBeVisible()` / `.toBeHidden()` or `expect.poll(() => locator.count())`.
- **"Absent" is not "disabled".** Playwright's `.not.toBeEnabled()` fails on a missing element with `element(s) not found`, so it cannot express "either removed or disabled" — a line that accepts both states must probe them explicitly (count 0 → absent, else `isEnabled()`), which is what A10 does in `states.a8-a10.spec.ts`. Conversely `toBeVisible()` + `toBeDisabled()` is the pair that *requires* the control to stay on screen, which is B2's extra test.

## How each runtime-asserted rubric line maps to an assertion

Every assertion targets outbound requests (`helpers/mock-server.ts` records url + query + body for each `api/v3/**` call) or observable DOM (`helpers/selectors.ts`). Request path names below are asserted **suffix-based** (`.endsWith('Logging/Range/Read')`) so the `/api/v3/` prefix and version do not matter.

The `Points` column mirrors `rubric.md`, which is the **sole source of point weights** — the `[R]` lines sum to 97 of Score A's 100 (the remaining 3 are `[S]`, judged statically).

| Line | Points | Spec | Assertion (outcome-level) |
| ---- | ------ | ---- | ------------------------- |
| **A1** | 5 | `live.a1.spec.ts` | With no filters, the app opens a SignalR connection to the logging hub; canned `GetBacklog` entries and a later `Log` push both appear in the DOM. The default live-tail view is proven **behaviourally** (the hub-delivered backlog renders — the server-search view renders HTTP read results instead), not by its line-count copy. |
| **A2** | 5 | `search-contract.a2-a5.spec.ts` | Non-empty search text **or** ≥1 active chip issues a `Range/Read` request (server-search view); clearing both returns to the live tail (proven behaviourally) and stops issuing `Range/Read`. |
| **A3** | 2 | `search-contract.a2-a5.spec.ts` | Whitespace-only input fires **no** `Range/Read` and the view stays on the live tail. The debounce/trim behaviour is **not** here — it is Score B's B11. |
| **A4** | 4 | `search-contract.a2-a5.spec.ts` | With ≥1 chip active, **every** `Range/Read` request carries a `level` param (the filter is server-side; the app never fetches unfiltered history and filters client-side). |
| **A5** | 6 | `search-contract.a2-a5.spec.ts` | `Range/Read` uses exactly `level` (singular), `message`, `offset`, `limit`, `descending=false`; a `levels` (plural) param is **absent**; and empty `level`/`message` are **omitted**, never sent as empty strings. |
| **A6** | 7 | `pagination.a6.spec.ts` | Scrolling the search list toward the end auto-fetches the next page (a page **is** fetched); the follow-up `Range/Read` `offset` equals the previous page's `NextOffset`; when the page returns `NextOffset: null`, no further fetch is issued. |
| **A7** | 5 | `pagination.a6.spec.ts` | Both fetched pages render together in order: the exact row count, each fetched message appearing exactly once (no dropped or duplicated row), ascending page-1-then-page-2 order, and each row carrying its timestamp, level and message. |
| **A8** | 4 | `states.a8-a10.spec.ts` | The first in-flight search shows an in-flight state — a wording-tolerant status hook (any busy/status affordance, or loading-ish copy), **plus** the behavioural check that no result rows are rendered while the response is held; a resolved-but-empty result set shows an empty state that is visibly distinct from loading, **and** a way to clear the filters. |
| **A9** | 3 | `states.a8-a10.spec.ts` | Clear-filters empties the search input, deactivates the level chips (no chip reports an active state) and resumes the live tail (a pushed entry renders with **no** extra `Range/Read`). |
| **A10** | 3 | `states.a8-a10.spec.ts` | With a level filter active the scroll-to-bottom lock is **not usable** — removed **or** disabled both satisfy the ticket (`"off while filters are active"` reads as absent) — and it is attached **and enabled** again in the live tail once the filters are cleared (the clear→usable half). |
| **A11** | 4 | `download.a11-a13.spec.ts` | With no filter, download hits `File/Current/Download`; with any filter active it hits `Range/Download`. |
| **A12** | 4 | `download.a11-a13.spec.ts` | The filtered download request carries `level` and `message` params (same singular/omitted-when-empty rules as A5). |
| **A13** | 3 | `download.a11-a13.spec.ts` | The download control shows a **visible** busy affordance while the request is in flight (a spinner/overlay, not merely `disabled`) which is gone once it settles, and a failed download surfaces an error toast. Two acceptable shapes: a marker derived from the **resolved download control** (`downloadButton(page)` plus a `:scope`-anchored CSS list: `aria-busy`, `data-loading`, a spinner class, an animated `svg`), or the control's **own appearance changing** while the request is in flight (`downloadControlSignature` samples what the control renders and how it marks itself working — inner HTML, inline `style`, a busy state attribute, a busy class token — before the click and compares during it; `disabled` is deliberately excluded, so a bare `disabled` cannot satisfy it) — an icon swap is a visible busy state too. Either way the idle appearance must return once the download settles, so a control that never changes, or that stays busy forever, still fails. |
| **A17** | 12 | `dsl.a17-a18.spec.ts` | A search expression that matches the server's filter-expression prefix grammar is recognised and sent **unchanged**: the `Range/Read` `message` param equals the typed expression verbatim (no `c#:` wrap), checked for a starts-with (`^:…`), a regex (`*:…`) and a mode+flag (`c#:…`) expression. The negative direction — an input that only *looks* like an expression — is A18's wrap rule, not this line. |
| **A18** | 13 | `dsl.a17-a18.spec.ts` | Only plain, non-DSL input is wrapped: a plain term's `message` is exactly `c#:<term>` (case-insensitive contains); a whitespace-only search is neither wrapped nor sent (no `Range/Read` recorded); and a colon-bearing literal (`http://x`, `a:b`) is sent **wrapped** as ordinary text, never passed through as an expression. |
| **A19** | 8 | `reconnect.a19.spec.ts` | Closing the logging socket forces a real reconnect; the replayed fresh backlog **replaces** the stale pre-disconnect entries (none stranded, none duplicated) and an entry pushed after the reconnect is still appended. A second test holds the replay and races two entries — one queued while the socket was **down** (so it must arrive in the replayed history) and one pushed **live** after the new handshake (so it must arrive as a live frame) — asserting each renders exactly once. |
| **A20** | 6 | `cancellation-failure.a20-a21.spec.ts` | A superseded search never renders its late result: a slow first read is left in flight, the filter changes and the new read renders, and when the stale read finally resolves its payload is **not** shown. |
| **A21** | 3 | `cancellation-failure.a20-a21.spec.ts` | A failed read surfaces a **visible** error affordance — the reference's toast or an inline failure banner — an outcome distinct from a successful-but-empty result set. |
| **B2** | 11 | `score-b.b2.spec.ts` | The tail follows a pushed entry and keeps it in the viewport; the follow survives a programmatic `scrollToIndex` jump; a genuine wheel-up releases it so a later push neither yanks the viewport down nor brings the entry into view; after a release a programmatic scroll back to the bottom does **not** silently re-engage it (re-engagement is the lock control's job); and while a filter is active the lock control stays **attached and disabled** (visible-but-unusable) — removing it from the DOM is the wrong answer. |
| **B11** | 7 | `score-b.b11.spec.ts` | Rapid keystrokes coalesce into a **single** read (not one request per keystroke); every recorded read carries exactly the settled final value (no intermediate keystroke, no superset); the value sent is trimmed. No millisecond interval is asserted — the repo's other search inputs use 200 ms and the reference uses 250 ms, so the check is behavioural. |

---

## Server contract stubbed by the harness

These are the shapes the mock server serves, confirmed against the reference app's own client code:

- `GET api/v3/Logging/Range/Read` (params `offset`, `limit`, `descending`, and — only when set — `level`, `message`) → `{ NextOffset: number | null, Entries: LogEntry[] }`, where `LogEntry = { TimeStamp, Level, Logger, Caller, ThreadID, ProcessID, Message, Exception? }`.
- `*/signalr/*/negotiate` → a WebSocket-only transport offer; the harness intercepts the resulting websocket, answers the SignalR JSON handshake, then sends a `GetBacklog` invocation on the logging hub; later pushes arrive as `Log` invocations. Both the logging and the aggregate hub connections are accepted (only the logging hub is counted/asserted). The `GetBacklog` replay runs on **every** handshake, so a reconnect (A19) receives the backlog again — `setBacklog()` swaps it for a fresh set first. The replay is **snapshotted at handshake time**, not read at release: a real hub reads its retained history when the connection is established, so an entry pushed *after* the handshake arrives only as a live `Log` frame (reading the live array at release would deliver it twice). `loggingHandshakes` (a `MockServer` field) counts logging-hub handshakes and is incremented as soon as the stub answers one — before any held replay — so a test can wait for a *new* connection with `expect.poll(() => server.loggingHandshakes)`.
- `GET api/v3/Logging/Range/Download` and `GET api/v3/Logging/File/Current/Download` → a text body (status/delay configurable per test).
- Auth/bootstrap: the harness seeds `localStorage.apiSession` (apikey + a truthy `version`) so `AuthenticatedRoute` does not bounce to login, and stubs `Init/Status` (`State: 'Started'`), `Settings` (a `WebUI_Settings` JSON string with `settingsRevision > 0`, or the app keeps its bootstrap spinner), `Init/Version` (nested `Server.Version`, a valid semver — a flat/invalid one crashes the update check), `User/Current` (must include `CommunitySites`), the two `WebUI/Latest*Version` update checks, `ManagedFolder`, and `Settings/SupportedLanguages`.

Any other `api/v3/**` request is answered with `{}` so an unexpected call cannot hang the app; it is still recorded in `server.requests`.

---

## Notes & limitations

- **Scope.** The `[R]` Score A lines (A1–A13, A17, A18, A19, A20, A21) plus the two behavioural Score B lines (B2, B11) are covered here. A14, A15, A16 and the static Score B lines stay with the static judge by design.
- **`descending=false` acceptance.** A5/A12 assert the app *sends* `descending=false`; the harness does not (and cannot) verify the server honors it.
- **Debounce timing (B11).** No millisecond interval is asserted; the check is behavioural — rapid keystrokes must coalesce into a single read carrying only the settled value, and the value must be trimmed. On an extremely slow machine the "single request" boundary can be tight.
- **Virtualizer layout (A6).** The search list is virtualized; the harness sets a tall viewport and scrolls the list programmatically, so a next-page fetch is triggered whether the implementation pages on the trailing row or on scroll.
- **The app's own dev-mode console output** (e.g. React StrictMode aborting a SignalR negotiation on first mount) is not asserted on; only the DOM and the recorded requests are.
- **SignalR keepalive is answered.** The mock replies to the client's `{"type":6}` ping and also sends its own on a 10 s timer, so the client's 30 s server-timeout never expires. Without it (the pre-fix behaviour) the client dropped the connection ~30 s into a test log, which killed the live tail and fired the app's reconnect path — enough to perturb a long spec and the tail it asserts on.
- **DSL grammar needs its trailing `:` (A17).** The server's filter grammar is `[c=^$~*][!]?[#]?:payload`, and the `:` is what marks an input as an expression at all: with **no** colon the whole string is a case-SENSITIVE literal contains, and the reference client's `hasDslPrefix` regex likewise requires the colon. The ticket's illustrative `^GET /api` has no colon and is therefore *not* a starts-with expression — the grammar-faithful form is `^:GET /api`, which is what A17 asserts (the illustrative wording is a rubric-level matter, not a harness assertion). The grammar is only engaged when the colon is preceded by a valid mode char and at most one `!` and one `#` in either order (`ShokoServer/Shoko.Server/Services/LogService.cs`, `TryParseLogFilterDsl`, `LogService.cs:824-908`: the char before the colon must be in `[c=^$~*]` and every char between it and the colon must be `!`/`#`, else `Invalid character … in modifiers`). A17/A18 therefore also assert the boundary: colon-bearing literals (`http://x`, `a:b`) and a malformed expression head (`cfoo:bar`) are **wrapped** as ordinary text (`c#:…`). The three cases are non-vacuous against *different* wrong detectors, which is why all three are needed: a detector that keys on colon presence alone (`value.includes(':')`) turns all three red, while the "first char in the mode set AND a colon exists, without validating the head" shape turns only `cfoo:bar` red — a literal like `http://x` starts with a non-mode char, so it is wrapped correctly by that detector and only the malformed head exposes it.
- **Reconnect budget (A19).** The reference's `withAutomaticReconnect` starts at 5 s, so the spec waits up to 20 s for the replayed backlog. `dropLoggingSockets()` closes the stub's open logging-hub socket(s); the app's own reconnect then re-handshakes and the stub replays the backlog set by `setBacklog()`. The race test waits on `loggingHandshakes` (not on a fixed delay) for the **new** handshake while the replay is still held, so it exercises the racing window rather than merely proving server-side retention.
- **B2 baselines are read from SETTLED geometry.** After a real wheel, the virtualizer re-measures the rows that came into view and corrects the container's total `scrollHeight` on a later frame, so a single read taken right after `wheelList()` catches the list mid-correction and over-estimates it. A baseline captured then is *stale* — once the list settles to a smaller true height a later single-row append can never exceed it, which makes the "did the list grow?" poll unsatisfiable rather than merely late (that was a real flake, ~1 run in 8). Both B2 tests that need a baseline therefore read it through `settledListScrollState()` (two consecutive agreeing reads, 5 s bound) instead of `listScrollState()`. Any future B2 assertion that compares against a captured geometry must do the same.
- **A geometry failure names its cause.** When the list container reports no height (`scrollHeight === 0`) the geometry helpers enrich the thrown failure with a first line that says so (`the live-tail list never rendered any rows - the scroll container has no height (a layout failure, not a scroll-lock behaviour)`), because a collapsed container and a broken follow both otherwise surface as an infinite bottom gap and the sanitized report cannot tell them apart. The wrapper only *enriches an already-thrown* failure, so it can never change which tests pass or fail.
- **Row detection follows the repo's convention.** `rows` keys off `[data-index]`, the attribute `@tanstack/react-virtual` sets on each mounted row. The ticket names no library; it asks the candidate to follow the project's existing conventions for rendering long lists, and that library is already a dependency of the checkout — so this is the discoverable convention, not a reference-specific markup assumption.
- **Fallback single points of failure.** Two resolvers could still miss on a conformant-but-unusual implementation. `searchInput`'s last resort (any enabled text input) misses only if the search field has neither an accessible name nor a "search" placeholder — which would also leave it undiscoverable to a user. The status hooks (`searchingState`, `noResultsState`) accept any busy/status affordance or loading-ish copy, so a miss means the implementation renders *no* visible in-flight or empty indication — which is the A8 behaviour itself, i.e. a genuine failure rather than a false negative. On the reference, `searchInput` resolves at the placeholder strategy and the status hooks match the reference's own copy.

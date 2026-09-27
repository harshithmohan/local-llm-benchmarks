# Consolidated score card — shoko-logs

One row per model + parameter set, with per-capability percentages (see `rubric.md` →
Capability dimensions and rollup). Each total is the mean of the 2 repeat totals
(gates /5 + rubric /95 = total /100). Rubric scores are produced by the grader model
(see README Protocol). **opencode-go models are single runs (no repeat-mean)**; local
models are 2-repeat means. Per-repeat rubric breakdown in `scorecards/<model>.md`; run
artifacts under `runs/<model>/` are deleted once recorded — the scorecards are the
persistent record.

> **⚠ Mixed rubric versions.** The rubric was revised after the first results — a new
> result-rendering line (#18, 5 pts), re-ranked weights (#5, #9, #14, #15, #17, #20,
> #22), clarified wording, and the capability rollup — and lines 18–24 were renumbered
> to 19–25. `qwen36-35b-iq4xs` has been **re-run and re-graded** under the revised rubric
> (2026-09-27); its capability columns are filled. The other rows are still **pre-review**
> (lines 1–24, older weights/wording); their totals are **not comparable** to the current
> rubric, and for them only **Build hygiene** is filled (**100%** — gates unchanged, all
> runs 5/5) while the other capability columns are **pending re-grade**. Capability
> columns are **percentages** of each dimension's max (Discovery 20, Implementation 28,
> Integration & wiring 41, Build hygiene 5, Code quality 6).

| Model + params | Total /100 (pre-review) | Discovery % | Implementation % | Integration & wiring % | Build hygiene % | Code quality % | Notes |
|---|---|---|---|---|---|---|---|
| mimo-v2.6-flash (opencode-go) | **79** | — | — | — | 100% | — | Coherent monolith (LogsPage + helpers/types): correct contract discovery, canonical-order key (6), scroll-triggered pagination (17), full search states incl. loader row (18), toast + spinner (21), no dead code (23), no deadlocks/render-phase effects. Gaps: DSL passthrough absent (7=0.5 — corrected 0→0.5 by spot-check for cross-run consistency), immediate revoke + no DOM attach (20=0.5), no tooltip/header/IconButton-loading, snapshot scroll-lock, needless 100ms pagination debounce. |
| deepseek-v4.1-flash (opencode-go, high reasoning) | **77** | — | — | — | 100% | — | Full data layer (5, 19), trailing-row pagination (17), sorted key via `normalizeLevels` (6), no dead code (23). DSL grammar **discovered** (helpers.ts comment) but passthrough never implemented — always-`c#:` wrap (7=0.5). Missing: reconnect reset, fragile base scroll-lock, immediate revoke, no tooltip/header/IconButton-loading. |
| qwen3.8-flash (opencode-go, xhigh reasoning) | **74.5** | — | — | — | 100% | — | Clean data layer + endpoint switch (5, 19), canonical-order key (6), search-view states incl. phantom row (18), `LogLineType` removed (23). Gaps: DSL passthrough absent (7=0.5) despite own `c#:` comment, render-phase `fetchNextPageDebounced` (17=0.5), detached anchor + no date+time filename (20=0.5), no error toast (21=0.5), reconnect reset missing, no tooltip/header/IconButton-loading. Notable: raw `fetch` download preserving server `Content-Disposition`. |
| qwen36-35b-iq4xs | **51.0** | 37.5% | 41.1% | 60.4% | 100% | 37.5% | 2-repeat mean, re-run + re-graded 2026-09-27 under the revised rubric (supersedes the pre-review 61.25). Request params correct both (r1 5=10/10; r2 5=5/10 — `res.data` unwrap bug), DSL absent both (7=0). One fatal wiring break each: r1's debounce ref never triggers the query; r2's active query mishandles the unwrapped response and never pages. Per-repeat: `scorecards/qwen36-35b-iq4xs.md` |
| qwen38-27b-w4a16 (local vLLM 150k ctx, medium reasoning) | **74.0** | — | — | — | 100% | — | 2-repeat mean. Both nailed the API contract (line 5 = 9/9, singular `level`, endpoint switch); r1 shipped malformed `c#` wrap (missing colon, search broken, 7=0), r2 fixed it (7=0.5, passthrough missing). Both miss: reconnect reset, tooltip/header/IconButton-loading, Firefox-broken blob download (immediate revoke; r2 also no DOM attach). |
| glm-5.3-flash (opencode-go, max reasoning) | **70** | — | — | — | 100% | — | Improvement over the high-reasoning run (+3.5): deferred revoke + date+time filename (20), real spinner + toast (21), sorted key (6), restored empty-tail spinner (16). Still: **no DSL handling at all** (7=0 — raw `message`), render-phase `fetchNextPageDebounced` (17=0.5), no DOM attach (20=0.5), no reconnect reset, no tooltip/header/IconButton-loading, snapshot scroll-lock. |
| glm-5.3-flash (opencode-go, high reasoning) | **66.5** | — | — | — | 100% | — | Replacement run (prior 70.5 discarded). Data layer solid (5, 9, 11, 17, 19 full; loader row 18; clean dead-code 23) but **no DSL handling at all** (7=0 — raw `message`) and **download broken** (20=0: no DOM attach + sync revoke + `anchor.download=''`). Live-tail spinner regressed (16=0), no reconnect reset (4), unsorted key (6=0.5), no IconButton loading (22=0). |
| katcoder-v2.5-dev | **65.5** | — | — | — | 100% | — | 2-repeat mean. Correct server-contract discovery both times (line 5 = 9/9, endpoint switch, scroll-triggered pagination) and cleanest dead-code record (23=1 in r2), but DSL 0 both times and composition broken both times — r1: chicken-and-egg level chips + deleted scrollRect workaround + stale scroll-listener element; r2: **circular filter gate** (search input `disabled` until filters active → search/level/download unreachable) + `createObjectURL(data.data)` blob misread + unsorted key. First benchmark lint flake hit r2 (oxlint false-positive on untouched files; passed re-run). |

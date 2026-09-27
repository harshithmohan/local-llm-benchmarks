# Consolidated score card — shoko-logs

One row per model + parameter set, with per-capability percentages (see `rubric.md` →
Capability dimensions and rollup). Each total is the mean of the 2 repeat totals
(gates /5 + rubric /95 = total /100); each row's notes give the run's wall-clock time
(min–max over repeats). Rubric scores are produced by the grader model
(see README Protocol). **opencode-go models are single runs (no repeat-mean)**; local
models are 2-repeat means. Per-repeat rubric breakdown in `scorecards/<model>.md`; run
artifacts under `runs/<model>/` are deleted once recorded — the scorecards are the
persistent record.

> **⚠ Mixed rubric versions.** The rubric was revised after the first results — a new
> result-rendering line (#18, 5 pts), re-ranked weights (#5, #9, #14, #15, #17, #20,
> #22), clarified wording, and the capability rollup — and lines 18–24 were renumbered
> to 19–25. `qwen36-35b-iq4xs` has been **re-run and re-graded** under the revised rubric
> (2026-09-27); its capability columns are filled. The `qwen38-27b-w4a16` low, medium, and
> xhigh reasoning rows have also been **re-graded** under the revised rubric (2026-09-27);
> their capability columns are filled, and the `swift-qwen38-27b` low, medium, and xhigh
> reasoning rows were graded under the revised rubric from the start. The other rows are
> still **pre-review** (lines 1–24, older
> weights/wording); their totals are **not comparable** to the current
> rubric, and for them only **Build hygiene** is filled (**100%** — gates unchanged, all
> runs 5/5) while the other capability columns are **pending re-grade**. Capability
> columns are **percentages** of each dimension's max (Discovery 20, Implementation 28,
> Integration & wiring 41, Build hygiene 5, Code quality 6).

| Model + params | Total /100 (pre-review) | Discovery % | Implementation % | Integration & wiring % | Build hygiene % | Code quality % | Notes |
|---|---|---|---|---|---|---|---|
| mimo-v2.6-flash (opencode-go) | **79** | — | — | — | 100% | — | Coherent monolith (LogsPage + helpers/types): correct contract discovery, canonical-order key (6), scroll-triggered pagination (17), full search states incl. loader row (18), toast + spinner (21), no dead code (23), no deadlocks/render-phase effects. Gaps: DSL passthrough absent (7=0.5 — corrected 0→0.5 by spot-check for cross-run consistency), immediate revoke + no DOM attach (20=0.5), no tooltip/header/IconButton-loading, snapshot scroll-lock, needless 100ms pagination debounce. |
| deepseek-v4.1-flash (opencode-go, high reasoning) | **77** | — | — | — | 100% | — | Full data layer (5, 19), trailing-row pagination (17), sorted key via `normalizeLevels` (6), no dead code (23). DSL grammar **discovered** (helpers.ts comment) but passthrough never implemented — always-`c#:` wrap (7=0.5). Missing: reconnect reset, fragile base scroll-lock, immediate revoke, no tooltip/header/IconButton-loading. |
| qwen3.8-flash (opencode-go, xhigh reasoning) | **74.5** | — | — | — | 100% | — | Clean data layer + endpoint switch (5, 19), canonical-order key (6), search-view states incl. phantom row (18), `LogLineType` removed (23). Gaps: DSL passthrough absent (7=0.5) despite own `c#:` comment, render-phase `fetchNextPageDebounced` (17=0.5), detached anchor + no date+time filename (20=0.5), no error toast (21=0.5), reconnect reset missing, no tooltip/header/IconButton-loading. Notable: raw `fetch` download preserving server `Content-Disposition`. |
| qwen36-35b-iq4xs | **51.0** | 37.5% | 41.1% | 60.4% | 100% | 37.5% | 2-repeat mean, re-run + re-graded 2026-09-27 under the revised rubric. Request params correct both (r1 5=10/10; r2 5=5/10 — `res.data` unwrap bug), DSL absent both (7=0). One fatal wiring break each: r1's debounce ref never triggers the query; r2's active query mishandles the unwrapped response and never pages. Per-repeat: `scorecards/qwen36-35b-iq4xs.md`. Run time 16.1–26.0 min. |
| qwen38-27b-w4a16 (local vLLM, fp8 KV, low reasoning) | **75.0** | 75% | 63.55% | 83.7% | 100% | 50% | 2-repeat mean, re-graded 2026-09-27 under the revised rubric. Both discovered the read contract (5=1) and clean dead-code record (24=0.5); r2 added a canonical-order key (6=1) and DOM-attached anchor (20=1). Both miss DSL passthrough (7=0.5), reconnect reset (4=0), header mode feedback (13=0), chip tooltips (10=0.5), and `IconButton` loading (23=0). r1 nudged, then delivered a browser-fragile download (detached anchor + sync revoke, 21=0). Run time 14.5–21.2 min. |
| qwen38-27b-w4a16 (local vLLM, fp8 KV, medium reasoning) | **69.25** | 62.5% | 70.75% | 72.35% | 100% | 37.5% | 2-repeat mean, re-graded 2026-09-27 under the revised rubric. r1: clean contract (5=1, 19=1) but unsorted key (6=0) and malformed `c#` wrap. r2 (nudged): fixed download handling (DOM attach + deferred revoke + date/time filename, 21=1) and added tooltips (10=1), but malformed `c#${message}` DSL (7=0) and legacy cleanup missed (24=0). Both miss reconnect reset (4=0), header feedback (13=0), phantom loader row, and `IconButton` loading (23=0). Run time 22.9–27.3 min. |
| qwen38-27b-w4a16 (local vLLM, fp8 KV, xhigh reasoning) | **70.75** | 62.5% | 59% | 84.5% | 100% | 37.5% | 2-repeat mean, re-graded 2026-09-27 under the revised rubric. r1: sorted key (6=1), correct download params (20=1), but pagination stops on short pages even with `NextOffset` (5=0.5) and no `scrollRect` (15=0). r2: full read contract (5=1) and scroll pagination (17=1) but unsorted key (6=0.5), thinner result rendering (18=0.5), and legacy cleanup missed (24=0). Both miss DSL passthrough (7=0.5), reconnect reset (4≤0.5), header feedback (13=0), chip tooltips (10=0.5), and `IconButton` loading (23=0). Run time 20.2–22.7 min. |
| swift-qwen38-27b (local vLLM, fp8 KV, low reasoning) | **64.5** | 50% | 56.25% | 76.84% | 100% | 37.5% | 2-repeat mean. r1 auto-compacted (harness intervention). r1: correct read/download endpoints but pagination stops on sub-100-entry pages even with `NextOffset` (5=0.5), malformed `c#${message}` DSL missing the colon (7=0), no `scrollRect` (15=0). r2: full read contract (5=1) but unsorted level key (6=0.5), render-phase `fetchNextPageDebounced` (17=0.5), stale live spinner (16=0), detached anchor + immediate revoke (21=0). Both miss DSL passthrough, reconnect reset (4=0), header feedback (13=0), chip tooltips, phantom loader row, and `IconButton` loading (23=0). Run time 11.1–13.5 min. |
| swift-qwen38-27b (local vLLM, fp8 KV, medium reasoning) | **74.0** | 62.5% | 60.85% | 89% | 100% | 50% | 2-repeat mean. Both discovered the read contract (5=1) and switch endpoints correctly (20=1); r2 removed `LogLineType` and adopted a level union (25=1). Both miss DSL passthrough (7=0 r1 / 0.5 r2), reconnect reset (4=0.5), header feedback (13=0), phantom loader row (19=0.5), and `IconButton` loading (23=0). Strongest swift variant by mean total. Run time 7.3–10.0 min. |
| swift-qwen38-27b (local vLLM, fp8 KV, xhigh reasoning) | **73.25** | 75% | 61.55% | 78.8% | 100% | 62.5% | 2-repeat mean. Both nailed the read contract (5=1) and download endpoint switch (20=1). r1 deduplicates flattened pages on timestamp/message (18=0.5); r2 lacks `scrollRect` (15=0) and uses a detached anchor + immediate revoke (21=0). Both miss DSL passthrough (7=0.5), reconnect reset (4=0), header feedback (13=0), chip tooltips, and `IconButton` loading (23=0). Run time 8.5–11.6 min. |
| glm-5.3-flash (opencode-go, max reasoning) | **70** | — | — | — | 100% | — | Improvement over the high-reasoning run (+3.5): deferred revoke + date+time filename (20), real spinner + toast (21), sorted key (6), restored empty-tail spinner (16). Still: **no DSL handling at all** (7=0 — raw `message`), render-phase `fetchNextPageDebounced` (17=0.5), no DOM attach (20=0.5), no reconnect reset, no tooltip/header/IconButton-loading, snapshot scroll-lock. |
| glm-5.3-flash (opencode-go, high reasoning) | **66.5** | — | — | — | 100% | — | Replacement run (prior 70.5 discarded). Data layer solid (5, 9, 11, 17, 19 full; loader row 18; clean dead-code 23) but **no DSL handling at all** (7=0 — raw `message`) and **download broken** (20=0: no DOM attach + sync revoke + `anchor.download=''`). Live-tail spinner regressed (16=0), no reconnect reset (4), unsorted key (6=0.5), no IconButton loading (22=0). |
| katcoder-v2.5-dev | **65.5** | — | — | — | 100% | — | 2-repeat mean. Correct server-contract discovery both times (line 5 = 9/9, endpoint switch, scroll-triggered pagination) and cleanest dead-code record (23=1 in r2), but DSL 0 both times and composition broken both times — r1: chicken-and-egg level chips + deleted scrollRect workaround + stale scroll-listener element; r2: **circular filter gate** (search input `disabled` until filters active → search/level/download unreachable) + `createObjectURL(data.data)` blob misread + unsorted key. First benchmark lint flake hit r2 (oxlint false-positive on untouched files; passed re-run). |

## Output-limit nudges

Models are served with `limit.output` **16384** (see README → Protocol → "Output limit
and nudges"). A reasoning model can spend the whole budget on a planning chain-of-thought
and stop at the cap with nothing implemented; such a run is resumed with a nudge to start
implementing. A nudge is a **harness intervention, not part of the task** — record every
nudged run here so nudged runs are only compared against other nudged runs.

| Model + params | Nudged repeats |
|---|---|
| qwen36-35b-iq4xs | 1 of 2 (repeat 1; repeat 2 clean) |
| qwen38-27b-w4a16 (local vLLM, fp8 KV, low reasoning) | 1 of 2 (repeat 1) |
| qwen38-27b-w4a16 (local vLLM, fp8 KV, medium reasoning) | 1 of 2 (repeat 2) |
| qwen38-27b-w4a16 (local vLLM, fp8 KV, xhigh reasoning) | 0 of 2 |

All other rows above predate the 16384 cap + nudge protocol (`—`).

## Auto-compactions

A run can hit the provider's size limit, at which point opencode compacts the session and
continues from a summarized context (see README → Protocol → "Auto-compaction"). This is
a **harness intervention, not part of the task** — record every compacted run here so
compacted runs are only compared against other compacted runs.

| Model + params | Compacted repeats |
|---|---|
| swift-qwen38-27b (local vLLM, fp8 KV, low reasoning) | 1 of 2 (repeat 1) |

All other rows above predate the auto-compaction protocol (`—`).

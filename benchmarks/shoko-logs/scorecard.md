# Consolidated score card — shoko-logs

One row per model + parameter set, with per-capability percentages (see `rubric.md` →
Capability dimensions and rollup). Each total is the mean of the 2 repeat totals
(gates /5 + rubric /95 = total /100); the **Time** column gives the run's wall-clock
time (the repeat mean for local runs; a single value for cloud runs). Rubric
scores are produced by the grader model
(see README Protocol). **opencode-go models are single runs (no repeat-mean)**; local
models are 2-repeat means. Per-repeat rubric breakdown in `scorecards/<model>.md`; run
artifacts under `runs/<model>/` are deleted once recorded — the scorecards are the
persistent record.

### Local (self-hosted) models

Self-hosted models — **2-repeat means** (see README → "Run naming and repeats").

| Model + params | Total /100 | Discovery % | Implementation % | Integration & wiring % | Build hygiene % | Code quality % | Notes | Time |
|---|---|---|---|---|---|---|---|---|
| qwen38-27b-w4a16 (local vLLM, fp8 KV, low reasoning) | **75.0** | 75% | 63.55% | 83.7% | 100% | 50% | 2-repeat mean. Both discovered the read contract (5=1) and clean dead-code record (24=0.5); r2 added a canonical-order key (6=1) and DOM-attached anchor (20=1). Both miss DSL passthrough (7=0.5), reconnect reset (4=0), header mode feedback (13=0), chip tooltips (10=0.5), and `IconButton` loading (23=0). r1 nudged, then delivered a browser-fragile download (detached anchor + sync revoke, 21=0). | 17.9 min |
| swift-qwen38-27b (local vLLM, fp8 KV, medium reasoning) | **74.0** | 62.5% | 60.85% | 89% | 100% | 50% | 2-repeat mean. Both discovered the read contract (5=1) and switch endpoints correctly (20=1); r2 removed `LogLineType` and adopted a level union (25=1). Both miss DSL passthrough (7=0 r1 / 0.5 r2), reconnect reset (4=0.5), header feedback (13=0), phantom loader row (19=0.5), and `IconButton` loading (23=0). Strongest swift variant by mean total. | 8.7 min |
| swift-qwen38-27b (local vLLM, fp8 KV, xhigh reasoning) | **73.25** | 75% | 61.55% | 78.8% | 100% | 62.5% | 2-repeat mean. Both nailed the read contract (5=1) and download endpoint switch (20=1). r1 deduplicates flattened pages on timestamp/message (18=0.5); r2 lacks `scrollRect` (15=0) and uses a detached anchor + immediate revoke (21=0). Both miss DSL passthrough (7=0.5), reconnect reset (4=0), header feedback (13=0), chip tooltips, and `IconButton` loading (23=0). | 10.1 min |
| qwen38-27b-w4a16 (local vLLM, fp8 KV, xhigh reasoning) | **70.75** | 62.5% | 59% | 84.5% | 100% | 37.5% | 2-repeat mean. r1: sorted key (6=1), correct download params (20=1), but pagination stops on short pages even with `NextOffset` (5=0.5) and no `scrollRect` (15=0). r2: full read contract (5=1) and scroll pagination (17=1) but unsorted key (6=0.5), thinner result rendering (18=0.5), and legacy cleanup missed (24=0). Both miss DSL passthrough (7=0.5), reconnect reset (4≤0.5), header feedback (13=0), chip tooltips (10=0.5), and `IconButton` loading (23=0). | 21.5 min |
| qwen38-27b-w4a16 (local vLLM, fp8 KV, medium reasoning) | **69.25** | 62.5% | 70.75% | 72.35% | 100% | 37.5% | 2-repeat mean. r1: clean contract (5=1, 19=1) but unsorted key (6=0) and malformed `c#` wrap. r2 (nudged): fixed download handling (DOM attach + deferred revoke + date/time filename, 21=1) and added tooltips (10=1), but malformed `c#${message}` DSL (7=0) and legacy cleanup missed (24=0). Both miss reconnect reset (4=0), header feedback (13=0), phantom loader row, and `IconButton` loading (23=0). | 25.1 min |
| katcoder-v2.5-dev | **66.25** | 62.5% | 56.45% | 68.85% | 100% | 37.5% | 2-repeat mean, 2026-09-28. Both discovered the read contract (5=10/10 both) and passed all gates; DSL missed (r1 0 / r2 0.5), no reconnect reset (4=0 both), no header hint (13=0 both), no chip tooltip, no `IconButton` loading. One wiring break each: r1 snapshot scroll-lock (14=0) + sync-revoke download (21=0.5); r2 `useRef`-captured `checkLoadMore` blocks paging (17=0) + filtered download hits the wrong endpoint (20=0.5). | 14.3 min |
| swift-qwen38-27b (local vLLM, fp8 KV, low reasoning) | **64.5** | 50% | 56.25% | 76.84% | 100% | 37.5% | 2-repeat mean. r1 auto-compacted (harness intervention). r1: correct read/download endpoints but pagination stops on sub-100-entry pages even with `NextOffset` (5=0.5), malformed `c#${message}` DSL missing the colon (7=0), no `scrollRect` (15=0). r2: full read contract (5=1) but unsorted level key (6=0.5), render-phase `fetchNextPageDebounced` (17=0.5), stale live spinner (16=0), detached anchor + immediate revoke (21=0). Both miss DSL passthrough, reconnect reset (4=0), header feedback (13=0), chip tooltips, phantom loader row, and `IconButton` loading (23=0). | 12.3 min |
| qwen36-35b-iq4xs | **51.0** | 37.5% | 41.1% | 60.4% | 100% | 37.5% | 2-repeat mean. Request params correct both (r1 5=10/10; r2 5=5/10 — `res.data` unwrap bug), DSL absent both (7=0). One fatal wiring break each: r1's debounce ref never triggers the query; r2's active query mishandles the unwrapped response and never pages. Per-repeat: `scorecards/qwen36-35b-iq4xs.md`. | 21.1 min |

### opencode-go (cloud) models

Cloud reference models — **single run** per model/level, no repeat-mean (see README → "Run naming and repeats").

| Model + params | Total /100 | Discovery % | Implementation % | Integration & wiring % | Build hygiene % | Code quality % | Notes | Time |
|---|---|---|---|---|---|---|---|---|
| qwen3.8-flash (opencode-go, xhigh reasoning) | **72.0** | 75% | 61% | 82% | 100% | 25% | Single run (cloud). Gates 5/5. Correct read contract incl. `NextOffset` cursor (5=1), trailing-viewport effect pagination with no render-phase/debounce (17=1), endpoint switch (20=1), flattened rendering (18=1), 250 ms debounce + trim (11=1). Gaps: no DSL passthrough — always-`c#:` wrap (7=0.5), no reconnect handling (4=0, corrected 0.5→0 by spot-check for cloud consistency), unsorted level key (6=0.5), detached anchor + sync revoke (21=0), no phantom loader row (19=0.5), no `IconButton` loading (23=0), legacy `logs/` query file + `LogLineType` kept (24=0). no nudge/compaction. | 10.4 min |
| deepseek-v4.1-flash (opencode-go, high reasoning) | **71.5** | 50% | 71% | 82% | 100% | 50% | Single run (cloud), 2026-09-28. Gates 5/5. Read contract correct but short-page exhaustion ignores `NextOffset` (5=0.5); full blob download (DOM attach + deferred revoke + date-time filename, 21=1); 600 px scroll-handler pagination (17=1); level chips + debounced search. Gaps: no DSL passthrough and case-sensitive `c:` wrap (7=0.5), no reconnect reset (4=0), unsorted level key (6=0.5), base scroll-lock (14=0.5, corrected 0→0.5 by spot-check), no phantom loader row (19=0.5), no `IconButton` loading (23=0), legacy query file kept (24=0.5). no nudge/compaction. | 4.7 min |
| mimo-v2.6-flash (opencode-go) | **67.5** | 50% | 73% | 74% | 100% | 25% | Single run (cloud), 2026-09-28. Gates 5/5. Read contract correct but short-page exhaustion ignores `NextOffset` (5=0.5); working infinite scroll + download mutation, six level chips, debounced search, loading/empty states. Gaps: DSL passthrough absent — always-`c#:` wrap (7=0.5, corrected 0→0.5 by spot-check), render-phase debounced pagination trigger (17=0.5), no reconnect reset (4=0), unsorted level key (6=0.5), sync-revoke download (21=0.5), no `IconButton` loading (23=0), legacy `LogLineType`/query file kept (24=0). Grader printed 59.5 (its own line scores sum to 62.5); maintainer corrected #7. no nudge/compaction. | 33.0 min |
| muse-spark-1.3-contributor (opencode-go, xhigh reasoning) | **66.0** | 50% | 66% | 72% | 100% | 50% | Single run (cloud), 2026-09-28. Gates 5/5. Correct read + download contract (endpoint switch, singular `level`/`message`, ascending reads), stable sorted key (6=1), 250 ms debounce, six level chips, live/search switch, flattened pages, empty-tail spinner (16=1). Gaps: no DSL passthrough — non-empty-guarded `c#:` wrap (7=0.5, corrected 0→0.5 by spot-check), short-page exhaustion ignores `NextOffset` (5=0.5), no reconnect reset (4=0), thin result rows — no logger/caller/exception (18=0.5), debounced trailing-row pagination without a phantom loader row (17=0.5, 19=0.5), sync-revoke download (21=0.5), no `IconButton` loading (23=0), legacy query file kept (24=0.5). no nudge/compaction. | 12.0 min |
| glm-5.3-flash (opencode-go, high reasoning) | **64.5** | 25% | 64% | 82% | 100% | 50% | Single run (cloud), 2026-09-28. Gates 5/5. Search/live mode switch, 250 ms debounce, six server-side level chips, filtered/unfiltered endpoint switch, download spinner + error toast, flattened result rendering, `IconButton` loading all wired. Gaps: hardcoded case-sensitive `c:` (DSL passthrough absent, 7=0), `getNextPageParam` uses entry count ignoring `NextOffset` (5=0.5), no reconnect reset (4=0), unsorted level key (6=0.5), detached anchor + sync revoke (21=0), no chip tooltips (10=0.5), no phantom loader row (19=0.5), bare header (13=0). no nudge/compaction. | 10.2 min |

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

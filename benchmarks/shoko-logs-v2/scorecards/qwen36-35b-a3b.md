# qwen36-35b-a3b — scores (v2)

Model: `qwen36-35b-a3b`, served on the rigs as `qwen36-35b-ud-iq4xs` (UD-IQ4_XS quant) at 262144 context with a 32768 output cap. One trajectory (Stage 0 + up to two reviewer-driven rounds). One card per model — it covers every quant of this model; quants are rows, not separate cards.

Reviewer: `opencode-go/muse-spark-1.3-contributor#xhigh` · Judge: `opencode-go/muse-spark-1.3-contributor#xhigh` — pinned for the whole card; a trajectory is only comparable to another run with the same reviewer.

| Quant | Param set | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|---|
| UD-IQ4_XS | default sampling | default | not converged | 67.5 / 30.5 | 26.3 | ✅ tscheck · ✅ lint · ✅ build | Stage 2's first turn ended with zero edits and was resumed — a zero-work stop, not an output-cap nudge (this trajectory hit no cap); the host's billion-context plugin made 8 `compress` calls (context 13.5k at the start → peak 120.4k early in Stage 0 → 36.1k at the end) |

> Stage 2's first turn ended after 85 s with **zero edits** — it planned the fix and stopped on its own (`finishReason: stop`), never reaching the output cap, so the extra run is recorded as a **zero-work stop**, not a nudge. The host's billion-context plugin made `compress` calls in every stage (3 in Stage 0, 3 in Stage 1, 2 in Stage 2) — its routine context-management tool, not a protocol event. A17/A18 were rebalanced from 17/8 to 12/13 immediately after this run was graded (the easy direction of the DSL discrimination was worth the largest line in the suite); the stage scores above are the **same per-line verdicts recut at the new weights** (Stage 1 A 60.5 → 55.5, Stage 2 A 72.5 → 67.5), not a re-judge.

## UD-IQ4_XS — default sampling

Parameter set: default sampling, 262144 context, 32768 output cap.

### Stage 0 — initial run
- Model time: 12.4 min (no nudge, no zero-work stop)
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 10/37
- Score A: 15.5 /100   Score B: 25 /100
- Flags: nudges: none; zero-work stop: no; context size: 262144 served; session context 13.5k → 71.1k at the stage's end (3 billion-context `compress` calls)
- Findings: typed search never reached the server — `hasFilters` derived from a ref that is written in the debounce callback, so nothing re-rendered and no `Range/Read` was issued for text input (chips worked, being state). The level chips carried correct values but labels `Info`/`Warn`/`Crit`; the roster was missing a sixth chip only in an earlier probe reading. Pagination was unreachable without a working text path, so the pagination and level-parameter lines were red for a reason unrelated to their own subject. Score B 25 came from a stable-ish query key, the empty-tail spinner, the outside-list loading row and active-only chips.

### Review round 1 → Stage 1
- Review prompt (verbatim, round 1): five severity-ordered findings, symptoms only. (1) Typing text never leaves the live tail — no server-backed history search runs for typed text; rapid keystrokes should coalesce into one search for the settled value, whitespace ignored, blank stays live. (2) Filter expressions are not honoured, and ordinary text is not an ordinary case-insensitive substring; a colon-bearing literal or a malformed head is still plain text. (3) Scrolling toward the end never pulls further pages — join pages oldest→newest and stop when the server says there is no more. (4) A slow older response can render over newer results, and a failed search looks the same as no matches — the first fetch must read as loading, and a failure must be visibly distinct. (5) Reconnect strands stale entries above the fresh backlog and can lose entries arriving around the recovery window.
- Model time: 6.2 min      Gates: ✅✅✅      Harness: 21/37      Score A: 55.5 /100   Score B: 19.5 /100
- Flags: nudges: none; zero-work stop: no; session context 35.2k at the stage's end (3 billion-context `compress` calls)
- Findings: the text path was rebuilt around a debounced state hook, so the whole text-search and DSL cluster started issuing reads; A17's three verbatim expressions now pass. But the wrap rule was rewritten to prefix plain input with `#` instead of `c#:`, and `withAutomaticReconnect([])` left the connection unable to recover. Score B fell to 19.5 — the stage rewrote files and lost the query-key ordering guarantee while leaving the scroll workaround, header mode, button extension, unused exports and input-discipline values unaddressed.

### Review round 2 → Stage 2
- Review prompt (verbatim, round 2): five severity-ordered findings. (1) Active filters are not described to the server the way it expects — ordinary text must be a case-insensitive contains, expressions honoured as typed, blank = no search, whitespace ignored, only the settled text sent, each chip combination distinct and order-independent. (2) Filtered search never moves past the first page — use the server's continuation marker, join oldest→newest with no drops or duplicates, stop at the end. (3) The live view does not recover cleanly from a dropped connection. (4) Downloading never leaves a usable file, and the button never looks busy. (5) The scroll-to-bottom control is backwards and the follow does not release.
- Model time: 7.7 min (incl. the resumed run)      Gates: ✅✅✅      Harness: 23/37      Score A: 67.5 /100   Score B: 30.5 /100
- Flags: nudges: none; **zero-work stop: yes** — the first turn ended with zero edits after planning, without reaching the cap; session context 36.1k at the end of the trajectory (2 billion-context `compress` calls)
- Findings: the query key became content-sensitive and order-independent (B1 full), the lock became disabled-while-filtering (A10 passes), and the reconnect tests went green. The stage instead inverted the DSL boundary — the detector became `value.includes(':')`, so colon-bearing literals and malformed heads pass through unwrapped while plain text is sent as `#server`/`#err` rather than `c#:server`/`c#:err`. Pagination still ignores the server's continuation marker, there is still no toolbar Clear-filters control, the download busy affordance is an icon swap the harness cannot see, and the follow still leaves a 34px gap.

**Outcome:** not converged — still 14 harness failures after two review rounds (23/37); the two scores never meet, and the final round fixed two lines while inverting two others.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) |
|---|---|---|---|---|---|
| UD-IQ4_XS | default | not converged | 67.5 | 30.5 | 26.3 |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) |
|---|---|---|---|---|---|---|
| UD-IQ4_XS | 0 | 15.5 | 25 | 10/37 | ✅ | 12.4 |
| UD-IQ4_XS | 1 | 55.5 | 19.5 | 21/37 | ✅ | 6.2 |
| UD-IQ4_XS | 2 | 67.5 | 30.5 | 23/37 | ✅ | 7.7 |

Cold, the model produced a page that drew the whole search UI and hit the request contracts but never issued a read for typed text — the single largest defect, and one that made the pagination and level-parameter lines red for reasons unrelated to their own subject. Review round 1 rebuilt the text path and took Score A from 15.5 to 55.5 (harness 10/37 → 21/37), at the cost of Score B (25 → 19.5) and a new wrap-rule error. Review round 2 fixed the query key and the lock, taking Score A to 67.5 and Score B to 30.5, but inverted the DSL boundary while doing so: the detector became colon-presence, so the boundary cases and the plain-wrap rule both went the wrong way. What never converged: pagination (the server's continuation marker is ignored, so a second page never loads), the Clear-filters control (absent outside the empty state), the download's busy affordance and its save path, the scroll-follow geometry, and the DSL wrap rule. Total model time 26.3 min across three stages; harness, reviewer and judge time are not counted — the figure measures the model producing code, not the apparatus measuring it. The session used 654,632 input and 104,129 output tokens with 11,877,690 cache reads, made 8 billion-context `compress` calls, and peaked at 120.4k tokens of context.

# katcoder-v2.5-dev — scores

Model: `katcoder-v2.5-dev`, served on Rig 2 as `katcoder-apex-i-compact` (APEX-I-Compact quant) at 262144 context with a 32768 output cap. One trajectory (Stage 0 + up to two reviewer-driven rounds). One card per model — it covers every quant of this model; quants are rows, not separate cards.

Reviewer: `opencode-go/muse-spark-1.3-contributor#xhigh` · Judge: `opencode-go/muse-spark-1.3-contributor#xhigh` — pinned for the whole card; a trajectory is only comparable to another run with the same reviewer.

| Quant | Param set | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|---|
| APEX-I-Compact | moe-cache fork, kv-q8, MTP on | default | not converged | 38 / 37.5 | 21.8 | ✅ tscheck · ✅ lint · ✅ build | The host's billion-context plugin made 5 `compress` calls (context 13.5k at the start → peak 127.1k at the Stage-0/1 boundary → 41.0k at the end) |

> The trajectory never went green: 13/37 harness tests at Stage 0, 15/37 at Stages 1 and 2. Two defects survive every round — the plain-text wrap is written without the separator colon (`c#<text>` instead of `c#:<text>`), and the filtered-read effect keys off the **un-debounced** search text while the query value comes from the debounced one, so the first keystroke fires a read with **no** `message` parameter before the debounce settles. That second read is what the harness samples, which keeps the whole text-search/DSL cluster (A5, A17, A18, B11) red and destabilises pagination (A6/A7).

## APEX-I-Compact — default sampling

Parameter set: moe-cache fork (`--spec-type draft-mtp --spec-draft-n-max 2`), kv-q8, 262144 context, 32768 output cap, served sampling (temp 1.0 / top-k 20 / presence-penalty 1.5), reasoning level `default` (the served chat template carries no `reasoning_effort`, so no effort variant is declared).

### Stage 0 — initial run
- Model time: 10.5 min
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 13/37
- Score A: 31 /100   Score B: 37.5 /100
- Flags: context size: 262144 served; session context 13.5k → 122.1k at the stage's end (2 billion-context `compress` calls)
- Findings: the broad shape is there — live tail, a filtered history view, paginated loading, downloads with a busy state, expression pass-through, reconnect replacement — but the detectors and affordances miss the contract. Score A passes on the live tail, blank-input, download busy, virtualization, DSL pass-through and failure surfacing; it fails filters/chips, the `Range/Read` parameter contract, pagination, the searching/empty/error/lock states, the DSL wrap direction, reconnect and cancellation. Score B 37.5 comes from the virtualizer `scrollRect`, the spinners, the phantom-footer, chip styling, half of typing discipline and export hygiene; the stable query key, the scroll lock, the header, the IconButton extension and input discipline are red.

### Review round 1 → Stage 1
- Review prompt (verbatim, round 1): five severity-ordered findings, symptoms only. (1) Opening the page shows no level choices — they appear only after text is typed, so a level alone never leaves the live tail and never starts a server-backed search; all level choices must be visible from a clean page and any one of them must switch to a filtered history search, with downloads honouring the same filters. (2) Ordinary text is not matched as a case-insensitive substring, and ordinary text that merely contains a colon (web addresses, `a:b` fragments, malformed expression heads) is passed through as if it were an expression; only genuine expressions pass through, blank input is not a search. (3) Scrolling the search view never pulls the next page — the continuation marker must be used, pages joined oldest→newest with no drops or duplicates, stopping when the server reports no more. (4) The searching, empty, failure and lock states are missing or unusable while filtered — a visible searching state on the first fetch, a distinct empty state with a labelled clear action, a distinct error state, and a scroll lock that stays visible but unusable while filters are active. (5) Rapid input, stale responses and reconnects lose or overwrite entries — keystrokes must coalesce to one settled trimmed request, a stale response must never render over newer results, and reconnect must replace the stale tail with the fresh backlog without dropping an entry that arrived around the window.
- Model time: 4.2 min      Gates: ✅✅✅      Harness: 15/37      Score A: 37.5 /100   Score B: 37.5 /100
- Flags: session context 74.7k at the stage's end (1 billion-context `compress` call as the round opened)
- Findings: the chips became always-visible and a level alone now starts a server-backed search, so A2/A3/A4 went green; the searching/empty/error states and the disabled-while-filtering lock landed (A9/A10 green) and the download button gained its busy affordance (A11/A12). A1, A13, A21 held at full and A15/A16 at partial. But the plain-text wrap was written without the separator colon and the detector's boundary direction stayed wrong, so A17/A18 and the contract's text half (A5) stayed red; pagination (A6/A7), reconnect (A19) and cancellation (A20) were untouched, and A14's download revokes the object URL in the same tick as the click. Score B is unchanged at 37.5 — B3 11, B4 6, B5/B6/B9 4.5, B10 7, everything else zero.

### Review round 2 → Stage 2
- Review prompt (verbatim, round 2): five severity-ordered findings, symptoms only. (1) Ordinary text is still not a case-insensitive substring and typed expressions are not honoured as written. (2) Scrolling toward the end never pulls the next page. (3) After a dropped connection stale entries remain above the fresh backlog and an entry arriving around the window can be lost. (4) An older response can render over newer results, and rapid keystrokes issue several reads including empty and intermediate values instead of one settled read. (5) The first filtered fetch shows no searching indication, and an empty result looks the same as still loading with no discoverable way to clear the filters.
- Model time: 7.1 min      Gates: ✅✅✅      Harness: 15/37      Score A: 38 /100   Score B: 37.5 /100
- Flags: session context 41.0k at the end of the trajectory (2 billion-context `compress` calls)
- Findings: the DSL detector was rewritten as a mode-character set with a modifier loop, and the reconnect handler now replaces the tail with the fresh backlog instead of appending to it. Neither fixed the observable behaviour: the wrap still emits `c#<text>` without the colon, and the filtered-read effect depends on the un-debounced search text, so the first keystroke fires a read carrying no `message` at all before the 300 ms debounce settles. The harness samples that empty request, which is why every DSL assertion reports `message` as `undefined`, A5's text-only half fails on `indexOf` of an undefined value, and B11 sees one extra read whose settled value is `''`. A6/A7 stay red (the extra read resets the page), A20's stale-read guard and all three B2 scroll-lock assertions remain broken. The only movement is A16 (0.5 → 1) — the four states are now fully scored.

**Outcome:** not converged — 15/37 after two review rounds, one test above Stage 0's 13/37. Both repair rounds re-aimed the same two defects without landing them: the wrap rule kept losing its colon, and the read effect kept keying off the raw text. Score B never moved off 37.5.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) |
|---|---|---|---|---|---|
| APEX-I-Compact | default | not converged | 38 | 37.5 | 21.8 |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) |
|---|---|---|---|---|---|---|
| APEX-I-Compact | 0 | 31 | 37.5 | 13/37 | ✅ | 10.5 |
| APEX-I-Compact | 1 | 37.5 | 37.5 | 15/37 | ✅ | 4.2 |
| APEX-I-Compact | 2 | 38 | 37.5 | 15/37 | ✅ | 7.1 |

Cold, the model produced the whole search surface — live tail, filtered view, chips, pagination scaffolding, downloads, reconnect handling — and hit the request shape but not the request contents. Review round 1 turned the chips into a working filter entry point and added the four states, taking Score A from 31 to 37.5 (harness 13/37 → 15/37). Review round 2 rewrote the DSL detector and the reconnect path and moved Score A to 38, without changing a single failing harness test beyond A16. What never converged: the plain-text wrap (the separator colon is still missing), the debounced text path (the read effect fires on the raw text, so the first request carries no `message`), pagination past the first page, the stale-read guard, the reconnect race, and the scroll lock. Total model time 21.8 min across three stages; harness, reviewer and judge time are not counted — the figure measures the model producing code, not the apparatus measuring it. The session used 388,895 input and 89,292 output tokens with 7,044,221 cache reads, made 5 billion-context `compress` calls, and peaked at 127.1k tokens of context.

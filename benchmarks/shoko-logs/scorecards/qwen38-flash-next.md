# qwen38-flash-next — scores

Model: `qwen38-flash-next-iq3xxs-strata` (Qwen3.8-Flash-Next, 512-expert GSQ-RCO `IQ3_XXS`, ~75.8 GB two-shard build with a separate MTP head), self-hosted by Strata at context 200000 and run at reasoning level `xhigh`. One trajectory per quant/level (Stage 0 + up to two reviewer-driven rounds). One card per model — it covers every quant of `qwen38-flash-next`; quants are rows, not separate cards.

Reviewer: `opencode-go/muse-spark-1.3-contributor#xhigh` · Judge: `opencode-go/muse-spark-1.3-contributor#xhigh` — pinned for the whole card; a trajectory is only comparable to another run with the same reviewer.

| Quant | Param set | Level | Outcome | Final A/B | Total model time (min) | Gates | Notes |
|---|---|---|---|---|---|---|---|
| IQ3_XXS | Strata int8 KV, ctx 200000, `--expert-cache auto`, `--prefill auto` (lend 95%), MTP `--spec 4` | xhigh | not converged | 96 / 100 | 94.2 | ✅ tscheck · ✅ lint · ✅ build | Harness 26/37 → 35/37 → 36/37 |

> **Harness revision, 2026-10-14 (maintainer correction):** the suite's page-open gate matched the page title text exactly, so a candidate that renamed the ticket's page title failed all 37 specs at page open — on copy `prompt.md` never states. The gate now anchors on the layout's scrolling root instead, and every figure on this card was measured on the revised harness. An earlier same-day trajectory of this model, graded on the pre-revision harness, is superseded and is not recorded here.

> Level `xhigh` is the model's declared top reasoning-effort variant, selected with `#xhigh`; the effort reaches the served engine on the wire as `reasoning_effort: xhigh`. Context was injected at 200000 (the served ceiling) with a 32768 output cap.

## IQ3_XXS — xhigh reasoning

Parameter set: Strata, context 200000, int8 KV, `--expert-cache auto`, `--prefill auto` at the 95% lend setting, MTP `--spec 4`, reasoning level `xhigh`. Self-hosted on Rig 1's RTX 3060 (~35 t/s decode), so the stage timings are dominated by engine throughput rather than by the harness's fixtures.

### Stage 0 — initial run
- Model time: 46.1 min (the served entry's cold load falls inside this window)
- Gates: ✅ tscheck · ✅ lint · ✅ build
- Harness: 26/37
- Score A: 78 /100   Score B: 58.5 /100
- Flags: context: served and injected 200000, output cap 32768
- Findings: cold, the model built the whole ticket surface in one pass — live tail, server-backed filtered search with paginated infinite scroll, filter-aware downloads, DSL pass-through and plain-term wrapping, reconnect recovery, and cancellation with failure surfacing. Score A 78: full on the tail, the filter switch and its `Range/Read` parameter contract, pagination and page order, the empty/searching/failure states, the download endpoints and busy state, the DSL pass-through lines and the static virtualizer/dead-code lines. It lost A18 outright — any colon in the input was treated as DSL syntax, so ordinary text that merely contained a colon (a URL, `a:b`, a malformed head such as `cfoo:bar`) was sent through verbatim instead of being wrapped as a case-insensitive substring search — half of A19 (the reconnect path had no reset: stale tail entries stayed put and a window entry was lost), and the A14 static line (the download tore its object URL down synchronously, before the click could complete). Score B 58.5: full for query-key stability, live virtualizer dimensions, the phantom loading-more row and export hygiene; halves for the scroll-follow release (throttled direction check, so both behavioural release tests failed) and for the post-reconnect spinner, the chip tooltips and the level typing; zero for the header mode/count, the `IconButton` loading extension and the input discipline (untrimmed, colon-less `c#err` sent).

### Review round 1 → Stage 1
- Review prompt (verbatim, round 1):
  > Follow-up review — logs search, download and live tail
  >
  > 1. Ordinary search words are not honoured as ordinary text. A plain word is sent in a malformed shape instead of as a case-insensitive substring search, while everyday text that happens to contain punctuation is passed through as if it were a structured expression, including web addresses, simple word-colon-word snippets and near-miss shapes that are not valid expressions. We expect only true structured expressions to pass through as written and everything else to behave as ordinary case-insensitive substring search, with empty input meaning no search.
  > 2. Reconnect recovery leaves the tail inconsistent. After a drop and reconnect stale entries from before the drop can remain stranded above the fresh backlog, and a message arriving right in the reset window can go missing so the count after recovery is short. We expect the fresh backlog to replace what came before, with nothing stranded above it and nothing arriving around the reconnect lost, and the rest of the view staying consistent through the change.
  > 3. Follow behaviour does not match scrolling. A genuine scroll up while following does not reliably release the follow, a programmatic scroll can re-engage a follow the user just released, and the follow control disappears entirely while filters are active. We expect a real user scroll up to release the follow and stay released, and the follow control to stay visible but unusable while a filtered search is shown, returning to normal once filters clear.
  > 4. Search requests do not reflect the settled trimmed value. Intermediate keystrokes can be sent and surrounding whitespace is not trimmed before sending, so the server sees something other than the final text the user settled on. We expect only the settled final value to be sent, trimmed of surrounding whitespace, with whitespace-only input treated the same as no search.
  > 5. Downloads can be unreliable in some browsers. The temporary download link is torn down synchronously right after the click, which can cancel the download before it starts. We expect starting a download to consistently deliver the file, with a working indicator while it is in flight and a visible error message if it fails.
- Model time: 20.9 min      Gates: ✅✅✅      Harness: 35/37      Score A: 92 /100   Score B: 64 /100
- Flags: context: served 200000, output cap 32768
- Findings: the round fixed all five findings — plain text is now wrapped as `c#:<trimmed>` behind a valid-head expression check (and colon-bearing literals wrap again), the reconnect path gained an `onreconnecting` clear plus a raw-timestamp backlog merge, the scroll release became a 48 px distance check with the lock button always mounted and disabled while filtering, the search key and params take the trimmed settled value, and the download link teardown was deferred. The harness went 26/37 → 35/37: the DSL wrap lines (A18) all pass now, but both A19 reconnect tests still fail — the fresh backlog never renders, and the window entry is dropped. Score A 92 loses only A19's 8 points; Score B 64 gains the behavioural B2 and B11 lines, and halves B4/B6/B9 while keeping B7, B8 and B10 at zero (bare `Logs` header, no `IconButton` extension, one newly-exported unused helper).

### Review round 2 → Stage 2
- Review prompt (verbatim, round 2):
  > Hi — the search, pagination, download and empty and error handling are all in good shape and the build still passes, so this round is just about finishing the live tail recovery and a few fidelity gaps.
  >
  > 1. The live tail never recovers after the connection drops. Right now dropping the logging connection leaves the old entries on screen and the fresh backlog never appears, so stale entries stay stranded above where the new ones should be and anything that arrives around the reconnect can go missing or show twice. What we want is for the connection to retry on its own after a short delay, clear the stale tail when the reconnect starts, then replace it with the fresh backlog that is replayed on every connect. Entries that were queued while the connection was down should come back as part of that replay, entries that arrive live while the replay is still in flight should be kept rather than dropped by the reset, neither should be duplicated, and new live entries should keep appending normally afterwards.
  > 2. There is no loading transition around that reconnect. Right now the view keeps showing the old tail right up until the new backlog lands, so there is no moment where it is visibly waiting. What we want is for the tail to clear to empty as soon as the reconnect begins and show the same kind of waiting indicator you already show on first load, until the fresh backlog arrives. That waiting view should be distinct from the no-results message and from the failure message with its retry action.
  > 3. The page header looks the same in both modes. Right now it is just a static title whether you are watching the live tail or paging through a server search. What we want is for the header to tell the two apart: in live mode it should show how many entries are currently held in the tail with thousands separators, and in search mode it should say that the list is a server-side search over the full history rather than the live tail.
  > 4. The small interactive affordances are missing. Right now the level filter buttons only change colour when active, with no hover text explaining what they do, and only the large download button knows how to show it is busy. What we want is for every level button to announce on hover whether it will hide or show that level, and for the small icon button variant to support the same busy visual that the large button already has, so any busy state looks consistent whichever button style is used.
  > 5. A couple of modelling and hygiene gaps. Right now the log entry shape requires details that older servers can omit, so those rows would be treated as malformed, the level field is plain text with no shared set of allowed values and no representation for the unfiltered state, and there is one exported search helper that nothing imports. What we want is for the optional details to actually be optional, for the level to be modelled as the known set plus the unfiltered case, and for any helper that is only used internally to stay private so no unused exports are left behind.
- Model time: 27.2 min      Gates: ✅✅✅      Harness: 36/37      Score A: 96 /100   Score B: 100 /100
- Flags: context: served 200000, output cap 32768
- Findings: the round rebuilt reconnect recovery — a self-retrying connection with no custom ladder, a state flag that clears the tail and shows a waiting view the moment the reconnect begins (distinct from both the no-results and failure views), and a backlog merge that keeps entries racing the replay. The first reconnect test now passes (fresh backlog replaces the stale tail, then live appends continue), but the second still fails: the merge compares raw timestamps with a strict "after the backlog cutoff" test, so an entry that arrives with the same timestamp as the replay cutoff is dropped. Score A 96 takes the A19 half the rubric allows (stale tail replaced, window entry lost) and holds every other line, and Score B 100 closes header mode text, chip tooltips, the shared busy visual on the small icon button, the optional entry fields and the level union, and keeps the behavioural B2/B11 lines. The equal-timestamp merge is the only thing between this trajectory and convergence.

**Outcome:** not converged — after two review rounds the harness stands at 36/37, the remaining failure being the reconnect-window entry dropped by the merge's strict same-timestamp comparison. Score A 78 → 92 → 96 and Score B 58.5 → 64 → 100; the trajectory never reached a fully green suite, so it is recorded as run, with no repeat.

## Summary

| Quant | Level | Outcome | Final A /100 | Final B /100 | Total model time (min) |
|---|---|---|---|---|---|
| IQ3_XXS | xhigh | not converged | 96 | 100 | 94.2 |

| Quant | Stage | Score A /100 | Score B /100 | Harness | Gates | Model time (min) |
|---|---|---|---|---|---|---|
| IQ3_XXS | 0 | 78 | 58.5 | 26/37 | ✅ | 46.1 |
| IQ3_XXS | 1 | 92 | 64 | 35/37 | ✅ | 20.9 |
| IQ3_XXS | 2 | 96 | 100 | 36/37 | ✅ | 27.2 |

Cold, the model again built the entire ticket surface in one pass and landed the highest first-stage ticket conformance this cohort has recorded (A 78), with its two real defects both in the reconnect path and its plain-term DSL wrapping. The review rounds lifted conformance to A 96 and fidelity all the way to B 100 — headers, tooltips, the small icon button's busy state, the level union and the optional entry fields all landed — but the final round's reconnect merge compares raw timestamps strictly, so a live entry stamped at exactly the backlog cutoff is discarded, and the second reconnect assertion keeps the suite at 36/37. The trajectory ends one line short of convergence rather than short of understanding: the A/B pair (96 vs 100) says the implementation now reads like the reference everywhere except that one equality comparison. Total model time 94.2 min across three stages (Stage 0 carries the served entry's cold load); harness, reviewer and judge time are not counted — the figure measures the model producing code, not the apparatus measuring it.

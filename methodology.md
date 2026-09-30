# Methodology (shared across rigs)

Applies to both rigs ([rig1-3060.md](rig1-3060.md), [rig2-3090.md](rig2-3090.md)).
Unless a page says otherwise, all results in this folder were measured on Rig 1.

## Inference engines

Four engines are used across the rigs. Each has its own flag vocabulary, so engine labels
are per-row and results are not interchangeable across engines. Per-engine flags, features,
and quirks live in [engine-notes/](engine-notes/):

- [moe-cache fork](engine-notes/moe-cache-fork.md) - dynamic CUDA expert cache, no profile/trace.
- [upstream (stock)](engine-notes/upstream-stock.md) - reference build; no fork features.
- [ik-llama.cpp](engine-notes/ik-llama.md) - different flag syntax; no fork features.
- [vLLM](engine-notes/vllm.md) - container stack for the Rig 2 Qwen3.8-27B quants.

## Measurement methods

- Prefill/decode bench (the only method in current use): llama-server, served through
  llama-swap, hit with a **raw `/v1/completions`** request (no chat template) using one of
  two prompts - the ~10k opencode session-context prompt (the default timing prompt) or the
  ~60K long-context refactor prompt - with `n_predict` 512. The bullets in
  this section are the **canonical request protocol**; the prompt texts live in
  [test-prompts.md](test-prompts.md). `llama-bench` is not used.
- **`cache_prompt: false` on every request.** Without it, a resend on the same slot is
  served from the KV-prefix cache and reports a fake near-zero prefill (only the few
  uncached tokens get evaluated). With it, every pass does a full prefill.
- **`ignore_eos: true` on every request.** Forces the full `n_predict` decode window, so
  every pass measures the same number of decode steps and no pass ends early (some engines
  emit a spurious first-token EOS on the long prompts - see issues.md §6/§8).
- Timings come from the response `timings` object: `prompt_per_second` (prefill),
  `predicted_per_second` (decode), plus `cache_n` and the MTP draft `draft_n` /
  `draft_n_accepted`. The server log's `slot print_timing` lines (`prompt eval time` /
  `eval time`) carry the same numbers when a log read is needed instead.
- Run each prompt (see [test-prompts.md](test-prompts.md)) per config and report its
  prefill/decode. MEASURE ON THE SECOND PASS - the first pass warms the mmap page cache;
  discard it. Single run; single-run noise is about +-2-4%. (Timing runs before
  2026-09-29 used two short C#/React prompts and averaged them; those numbers are
  annotated as the retired protocol on the model pages.)
- Sampling policy: requests never override server-side sampling. Payloads carry only the
  prompt and request shape (`n_predict` / `max_tokens`); all sampling parameters
  (temperature, top_p, top_k, min_p, presence/repetition penalties) are whatever the
  server is configured with - the served config is the single source of truth for a run.
- Every cache/ctx config gets a large-prompt stability check before its decode number is
  recorded (catches the slot-sizing OOM trap).
- ALWAYS capture BOTH prefill and decode in every server test.

## Memory measurement

Every `VRAM used` figure in this folder is the model's **per-process** GPU allocation,
never the whole-GPU total. Read it from the compute-apps query, taking the serving
process's row:

    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

- vLLM: the process is `VLLM::EngineCore`.
- llama.cpp (stock or any fork): the process is `llama-server` - match on whatever name
  the query reports (it may be a full path ending in `llama-server`).

## Test prompts

The timing prompts are the ~10k opencode session-context prompt (the default; the owner's
real workload is opencode) and, for long-context runs, the ~60K long-context refactor
prompt: texts and provenance in [test-prompts.md](test-prompts.md). Both are measured with
the request protocol in [Measurement methods](#measurement-methods). The 10k prompt is
non-repetitive by construction (repeated text crashes the qwen4exp arch - see issues.md);
the ~60K prompt is deliberately near-repetitive because it is realistic text, and is used
for large-prompt stability checks and long-context speed at large ctx - a crash on it is a
recorded finding (issues.md), not a prompt defect. The earlier ~116K variant
(retired 2026-09-27) is archived per model page.

## VRAM headroom rule

The expert pack must leave headroom for compute buffers that grow with context. Rule used
here: keep ~900+ MB free after pack + KV + compute reservation. Slot counts that load fine
but leave less headroom OOM on the first large prompt.

## Known measurement caveats

- The expert cache (any model) can only be exercised with a real context, so all cache
  numbers come from llama-server, never `llama-bench` (which has no cache plumbing and no
  `-c` flag).
- Server single-run decode carries about +-2-4% noise; treat sub-5% deltas with caution.
- Cold-load measurements are the trustworthy ones: mid-session warm measurements produced
  several prefill flukes (page-cache-warm sessions) that re-verified 20-30% lower cold.
- Absolute numbers are not directly comparable across sessions written at different times;
  treat comparisons within one page as valid, across pages as approximate.

## Coding benchmark (shoko-logs)

The agentic coding benchmark under [benchmarks/shoko-logs/](benchmarks/shoko-logs/)
has its own, independent methodology — task, build-gate + rubric scoring, and grading
protocol. It is documented in [benchmarks/shoko-logs/README.md](benchmarks/shoko-logs/README.md)
and is separate from the inference-timing methodology above.

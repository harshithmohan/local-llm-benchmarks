# Methodology (shared across rigs)

Applies to both rigs ([rig1-3060.md](rig1-3060.md), [rig2-3090.md](rig2-3090.md)).
Unless a page says otherwise, all results in this folder were measured on Rig 1.
Tuning procedure (which knobs to sweep, in what order): [tuning.md](tuning.md).

## Inference engines

Five engines produce the measured results in this folder. Each has its own flag vocabulary,
so engine labels are per-row and results are not interchangeable across engines. Per-engine
flags, features, and quirks live in [engine-notes/](engine-notes/):

- [moe-cache fork](engine-notes/moe-cache-fork.md) - dynamic CUDA expert cache (+ opt-in
  generic hybrid CPU/GPU executor), no profile/trace needed for the cache itself.
- [upstream (stock)](engine-notes/upstream-stock.md) - reference build; no fork features.
- [ik-llama.cpp](engine-notes/ik-llama.md) - different flag syntax; no fork features.
- [vLLM](engine-notes/vllm.md) - container stack for the Rig 2 Qwen3.8-27B quants.
- [Strata](engine-notes/strata.md) - pack engine for Flash-Next on Rig 1; its own API server
  and its own flag vocabulary.

Strata serves no raw `/v1/completions` route and ignores `cache_prompt` and `ignore_eos`, so
it cannot take the request protocol below as written. Its rows are measured through
`/v1/chat/completions` - a chat template is always applied - with `--prompt-cache 0` in the
engine args, and a pass counts only when `cache_n` is 0 and `predicted_n` reaches the
requested window.

## Measurement methods

- Prefill/decode bench (the only method in current use): llama-server, served through
  llama-swap, hit with a **raw `/v1/completions`** request (no chat template) using one of
  three prompts - the ~10k opencode session-context prompt (the default timing prompt), the
  ~60K long-context refactor prompt, or the ~120K long-context refactor prompt - with
  `n_predict` 512. The bullets in
  this section are the **canonical request protocol**; the prompt texts live in
  [test-prompts.md](test-prompts.md). `llama-bench` is not used.
- **`cache_prompt: false` on every request.** Without it, a resend on the same slot is
  served from the KV-prefix cache and reports a fake near-zero prefill (only the few
  uncached tokens get evaluated). With it, every pass does a full prefill.
- **`ignore_eos: true` on every request.** Forces the full `n_predict` decode window, so
  every pass measures the same number of decode steps and no pass ends early (some engines
  emit a spurious first-token EOS on the long prompts - see issues.md §3/§5).
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
prompt at ordinary windows and the ~120K long-context refactor prompt at the large ones:
texts and provenance in [test-prompts.md](test-prompts.md). All are measured with
the request protocol in [Measurement methods](#measurement-methods). The 10k prompt is
non-repetitive by construction (repeated text crashes the qwen4exp arch - see issues.md);
the two long-context prompts are deliberately near-repetitive because it is realistic text,
and are used for large-prompt stability checks and long-context speed at large ctx - a crash
on one is a recorded finding (issues.md), not a prompt defect. A config is checked at the
size of the window it serves: the ~60K prompt is the ordinary large-prompt check, and a
window above 140k is additionally checked on the ~120K prompt, which is the one that
exercises the prompt-side buffers of that window.

## VRAM headroom

There is no fixed free-VRAM number that holds across models and configs. How much headroom
a config can leave (and still serve the largest prompt) depends on the model, quant, cache
size, context, and ubatch, so it is settled empirically per model and per config - never by
a threshold. Every cache/ctx config is taken through the large-prompt stability check
([Measurement methods](#measurement-methods)) before its numbers are recorded, and is
accepted or rejected on whether it actually serves the large prompt without OOM. The check
exists because a config that loads fine can still OOM on the first large prompt (compute
buffers grow with context).

## Known measurement caveats

- The expert cache (any model) can only be exercised with a real context, so all cache
  numbers come from llama-server, never `llama-bench` (which has no cache plumbing and no
  `-c` flag).
- Server single-run decode carries about +-2-4% noise; treat sub-5% deltas with caution.
- An expert cache fills lazily, so a load-time VRAM reading understates steady state, sometimes
  by many GiB (Gemma4-26B reads ~3 GiB at load and ~11.5 GiB during decode). Sample VRAM during
  decode - never at `listening on http` - when checking headroom or a cache ceiling.
- Cold-load measurements are the trustworthy ones: mid-session warm measurements produced
  several prefill flukes (page-cache-warm sessions) that re-verified 20-30% lower cold.
- Absolute numbers are not directly comparable across sessions written at different times;
  treat comparisons within one page as valid, across pages as approximate.

## Coding benchmark (shoko-logs)

The agentic coding benchmark under [benchmarks/shoko-logs/](benchmarks/shoko-logs/)
has its own, independent methodology — task, build-gate + rubric scoring, and grading
protocol. It is documented in [benchmarks/shoko-logs/README.md](benchmarks/shoko-logs/README.md)
and is separate from the inference-timing methodology above.

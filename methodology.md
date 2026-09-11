# Methodology (shared across rigs)

Applies to both rigs ([rig1-3060.md](rig1-3060.md), [rig2-3090.md](rig2-3090.md)).
Unless a page says otherwise, all results in this folder were measured on Rig 1.

## Codacus fork features used (env vars / flags, all off by default)

All fork-specific features below come from the [Codacus fork](https://github.com/thecodacus/llama.cpp)
of llama.cpp (branch `perf`).

- `GGML_CUDA_REGISTER_HOST=1` - pin CPU expert weights, faster DMA upload (prefill)
- `GGML_SCHED_PREFETCH_EXPERTS=1` - overlap expert uploads with compute on a second stream (prefill, also helps decode on the 177B model)
- `LLAMA_ARG_MOE_CACHE_PROFILE=<csv>` + `LLAMA_ARG_MOE_CACHE_SLOTS=<n>` - VRAM-resident hot-expert cache (decode); also usable as CLI flags `--moe-cache-profile` / `--moe-cache-slots`

The upstream README's mention of legacy `GGML_MOE_CACHE_*` env vars for llama-bench is
wrong for this build. The working env names for llama-server AND llama-cli are
`LLAMA_ARG_MOE_CACHE_*` (they go through the common arg parser).

## Measurement methods

- Prefill/decode bench: `llama-bench -ngl 99 -fa 1 -p 2048 -n 512 -b 2048 -ub 2048 -r 3`
  (varied per run: `-ncmoe`, env vars, `-c`/`-ctk`/`-ctv`). Batch size caps prefill - the
  default ubatch 512 under-reports prefill badly, always set `-b 2048 -ub 2048`.
- Expert cache and large-ctx decode: llama-server + `curl /completion` with each coding
  prompt + 512 generated tokens, timing read from the server log
  (`slot print_timing ... prompt eval time` / `eval time`). Run BOTH coding prompts
  (C# and React/TypeScript, see [test-prompts.md](test-prompts.md)) per config and
  report the AVERAGE of the two speeds; record per-prompt numbers in the notes when
  they diverge noticeably. MEASURE ON THE SECOND PASS of each prompt - the first pass
  warms the mmap page cache and its prefill reads cold-NVMe; discard it.
  Single run each; server timings read slightly higher than llama-bench's 3-rep tg.
- Server payloads use the models' recommended sampling: temperature 1.0, top_p 0.95,
  top_k 20, min_p 0.0; presence_penalty 1.5 on the 35B models, 0.0 on Flash-Next
  (repetition_penalty 1.0).
- Every cache/ctx config gets a large-prompt stability check before its decode number is
  recorded (catches the slot-sizing OOM trap).
- ALWAYS capture BOTH prefill and decode in every server test.

## Test prompts

The actual prompt texts used for timing runs, including coding prompts for C# and
React/TypeScript (the owner's main languages): see [test-prompts.md](test-prompts.md).
All server prompts are non-repetitive by construction (repeated text crashes the
qwen4exp arch - see issues.md).

Exception: the ~116K messy-code refactor prompt (test-prompts.md) is deliberately
near-repetitive because it is realistic text; it is used for large-prompt stability
checks and output-quality comparison at large ctx. A crash on it is a recorded finding
(issues.md), not a prompt defect. Timed re-sends need a fresh slot or a nonce (KV
prefix cache would otherwise fake a near-zero prefill).

## Trace methodology (routing profiles)

Profiles made with `llama-moe-trace -ngl 99 -ncmoe N -fa 1 -c 4096 -n 512`, using the
code and chat prompts from [test-prompts.md](test-prompts.md), merged into one CSV per
model (`<model>-code.csv` + `<model>-chat.csv` -> `<model>-merged.csv`).

Routing profiles are config-independent (routing is a model property), so a profile traced
at one ncmoe works for any ncmoe config.

## VRAM headroom rule

The expert pack must leave headroom for compute buffers that grow with context. Rule used
here: keep ~900+ MB free after pack + KV + compute reservation. Slot counts that load fine
but leave less headroom OOM on the first large prompt.

## Known measurement caveats

- llama-bench cannot test the expert cache (any model): it has no cache plumbing and no
  `-c` flag. All cache numbers come from llama-server + curl.
- Server single-run decode reads slightly higher than llama-bench tg512 (3 reps); single-run
  noise is about +-2-4%.
- Cold-load measurements are the trustworthy ones: mid-session warm measurements produced
  several prefill flukes (page-cache-warm sessions) that re-verified 20-30% lower cold.
- Absolute numbers are not directly comparable across sessions written at different times;
  treat comparisons within one page as valid, across pages as approximate.

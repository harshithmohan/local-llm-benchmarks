# Issues found

Issues discovered during benchmarking, covering the Codacus fork, upstream llama-server,
and the test harness.
Applies to this build (b10818-27c54b4bb, branch `perf`) unless noted otherwise.

## 1. IQ4_XS quant incompatible with expert cache

`Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf` stores fused `ffn_gate_up_exps.weight` (plus separate
gate/up/down patterns in the header). The cache requires separate gate/up/down expert tensors,
so `init_moe_expert_cache` exits at the "no CPU-resident MoE layers" check.

Check GGUF tensor names: separate `blk.N.ffn_gate_exps/ffn_up_exps/ffn_down_exps` = OK;
fused `ffn_gate_up_exps` = cache will not build. The UD-Q6/Q4_K_M quants have the
3 separate tensors and work.

Gotcha: cache diagnostics are logged with `LLAMA_LOG_INFO` (llama-model.cpp ~line 1910),
which is invisible in llama-cli's chat UI and llama-server's default logs. Run with `-v`
(or `-lv 2`) to see `init_moe_expert_cache:` lines. The failure paths:

- profile path empty or slots <= 0 -> silent return (no log)
- "no CPU-resident MoE layers" -> INFO (invisible without -v)
- "pack allocation failed" -> WARN (visible)
- success line -> INFO (invisible without -v)

## 2. llama-bench cannot test the expert cache (any model)

`tools/llama-bench/llama-bench.cpp` has no moe-cache support and ignores both
`GGML_MOE_CACHE_*` and `LLAMA_ARG_MOE_CACHE_*` env vars. This is a tool limitation, not a
model one - it applies to every model, including the cache-compatible quants. It also has
no `-c` flag (context is derived from -p/-n). Use llama-server + `curl /completion` timing
(or llama-cli) to measure the cache.

Model-level cache compatibility is a separate question: IQ4_XS is incompatible (fused
gate_up), UD-Q6_K / UD-Q4_K_M / the Flash-Next quants are compatible but can be unprofitable
at 12 GB VRAM (see model pages).

## 3. Slot sizing OOM trap

80 slots loaded fine but OOMed on the first ~770-token prompt (VRAM 11879/11911 MiB).
The pack must leave headroom for compute buffers that grow with ctx. Rule used here:
keep ~900+ MB free after the pack + KV + compute reservation. 72 slots was stable.

## 4. pkill footgun in containers

`pkill -f llama-server` matches your own `sh -c` wrapper (killed the launcher instead of the
server). Use `pkill -x llama-server`.

## 5. llama-bench default batch under-reports prefill

Default llama-bench batch (ub 512) severely under-reports prefill: `-b 2048 -ub 2048`
required to match the Codacus fork's README methodology.

## 6. Display quirks (harmless)

- llama-bench may show `(guessed) all F32` or a wrong quant label in the model column -
  display quirk only, quants load and run correctly.
- The Qwen3.8-Flash-Next GGUF metadata says size_label `512x56B`, but the model is
  176.94B params (512 experts, ~3B active).

## 7. Qwen3.8-Flash-Next specific

- Repeated/repetitive prompt text can crash llama-server with
  "CUDA error: the requested functionality is not supported" (PLE n-gram graph path).
  Varied prompts, llama-cli interactive, and llama-bench are fine.
- The ~116K messy-code refactor prompt (test-prompts.md) does NOT crash (the PLE
  n-gram path above did not fire) but makes the server stop immediately with EOS on
  raw /completion: stop_type eos, 1 predicted token, empty output. It still does this
  after a nonce removes the trailing closed fence from the prompt end, so the
  documented 35B-era fence trigger is NOT the cause. Workaround: `ignore_eos: true`
  in the payload - then the full n_predict decodes with real output and normal MTP
  acceptance (0.854 on the messy prompt). Timing-only runs are unaffected in
  interpretation: prefill/decode t/s and acceptance are valid under ignore_eos.
- Shard 1 header lists 0 tensors (unusual for llama.cpp split GGUFs) but loads correctly;
  llama.cpp reads the tensor list from the shards.
- The compute buffer scales with `-ub` on this arch (indexer): at c 204800, ub 2048 would
  need ~6 GB compute; ub 512 needs ~2.1 GB. This is what caps context, not KV.
- With `GGML_SCHED_PREFETCH_EXPERTS=1`, the prefetch stream costs VRAM and caps ncmoe
  ~2 layers below the no-prefetch max (measured on the Q4_K_M quant).
- First-request prompt eval is slow with MTP active (~14 t/s for 81 tokens); it recovers
  afterwards, but prefill-heavy workloads may prefer no-MTP + env vars.

## 8. config.yaml review note

A reviewed llama-swap config.yaml had 35B and KAT-Coder models running with MTP spec
decode but without the prefill env vars - adding `GGML_CUDA_REGISTER_HOST=1`
(+ `GGML_SCHED_PREFETCH_EXPERTS=1` where VRAM allows) is free prefill speed for them.

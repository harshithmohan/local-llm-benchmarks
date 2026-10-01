# Issues found

Issues discovered during benchmarking, covering upstream llama-server, ik-llama.cpp,
the moe-cache fork, and the test harness. Each item is tagged with the engine(s) it
affects: **stock** (upstream llama.cpp), **ik-llama.cpp**, or **moe-cache fork**. Never
assume a new engine shares an issue - check the tags.

## 1. llama-bench default batch under-reported prefill (retired)

Applies: **tool-level** (any engine).

Default llama-bench batch (ub 512) severely under-reported prefill: `-b 2048 -ub 2048`
was required. llama-bench is retired; server-side prefill is now measured directly
(see methodology.md).

## 2. Display quirks (harmless)

Applies: **model-side** (any engine).

- The Qwen3.8-Flash-Next GGUF metadata says size_label `512x56B`, but the model is
  176.94B params (512 experts, ~3B active).

## 3. Qwen3.8-Flash-Next specific

Applies: **stock** unless marked - these are model/arch issues, not fork features.

- Repeated/repetitive prompt text can crash llama-server with
  "CUDA error: the requested functionality is not supported" (PLE n-gram graph path).
  Varied prompts and llama-cli interactive are fine.
- The long-context refactor prompt (test-prompts.md; measured on the retired ~116K
  variant) does NOT crash (the PLE
  n-gram path above did not fire) but makes the server stop immediately with EOS on
  raw /completion: stop_type eos, 1 predicted token, empty output. It still does this
  after a nonce removes the trailing closed fence from the prompt end, so the
  documented 35B-era fence trigger is NOT the cause. Workaround: `ignore_eos: true`
  in the payload - then the full n_predict decodes with real output and normal MTP
  acceptance (0.854 on the long-context prompt). Timing-only runs are unaffected in
  interpretation: prefill/decode t/s and acceptance are valid under ignore_eos.
- Shard 1 header lists 0 tensors (unusual for llama.cpp split GGUFs) but loads correctly;
  llama.cpp reads the tensor list from the shards.
- The compute buffer scales with `-ub` on this arch (indexer): at c 204800, ub 2048 would
  need ~6 GB compute; ub 512 needs ~2.1 GB. This is what caps context, not KV.
- First-request prompt eval is slow with MTP active (~14 t/s for 81 tokens); it recovers
  afterwards, but prefill-heavy workloads may prefer no-MTP.

## 4. ik-llama.cpp specific

Applies: **ik-llama.cpp** (build 3bb386e).

- A log line `draft size 2 exceeds max 1, truncating` appears with MTP on the 35B and
  is benign - MTP still runs with normal acceptance (0.81-0.84 at 256k).
- MTP + deep GPU expert packs fails at init (256k): the draft context needs a ~489 MiB
  CUDA buffer that does not fit alongside the pack (ncmoe 18/24 + MTP both fail; the
  256k MTP ceiling is ncmoe 28). At extended ctx the picture differs from stock: ik MTP
  fits at 512K on the lean split (ncmoe 34) but OOMs at the best split (ncmoe 28 - the
  draft context eats the KV headroom) and at 736K even all-CPU (ncmoe 41: per-step
  recurrent speculative checkpoint init, 782 MiB main KV alloc fails); stock fits MTP
  at 512K but loses (draft context evicts the GPU expert layers, 36.3 vs 37.1).
- Extended-context ceiling failure mode: past the usable limit (~852K), the next
  config (917504) LOADS fine but crashes on the first request with a runtime CUDA OOM
  in the decode cublas path - unlike stock, where an over-ceiling config OOMs cleanly
  at init/context creation. Loads-fine is not proof of serviceability near the ik
  ceiling.

## 5. Immediate-EOS on the 10k opencode prompt (35B, moe-cache fork)

Applies: **moe-cache fork (GenerelSchwerz)** - measured on the dynamic expert-cache fork;
not seen on stock.

`Qwen3.6-35B-A3B-IQ4_XS-4.19bpw` on the current ~10k opencode session-context timing
prompt ([test-prompts.md](test-prompts.md)) occasionally stops immediately with EOS:
`stop_type eos`, 1 predicted token, empty output. It is rare and cache-independent - ~2 of
~20 measured passes at 256k, seen once at cache 48 and once at cache 64. A plain retry
decodes normally (full `n_predict`, normal MTP acceptance), so it is a transient, not a
config fault. Distinct from the Flash-Next EOS behaviour (§3): different model and prompt,
and not the PLE/long-context path. Timing interpretation is unaffected - drop the anomalous
pass and re-run, or set `ignore_eos: true` as for the long-context prompt.

## 6. Fork CUDA-graph capture rejects the pruned (256-expert) Flash-Next Coder

Applies: **moe-cache fork (GenerelSchwerz)** - measured on the dynamic expert-cache fork
build b11608; not seen on stock.

`Qwen3.8-Flash-Next GSQ-RCO Coder IQ1_M` has 256 experts per layer (the base has 512). On
the moe-cache fork with the expert cache enabled, the server loads and its health check
passes, but the first decode fails and the process exits:

    ggml_cuda_graph_evaluate_and_capture: op not supported ffn_moe_gate-N (MUL_MAT_ID)
    graph_compute: ggml_backend_sched_graph_compute_async failed with error -1
    llama_decode: failed to decode, ret = -3

The 512-expert quants (UD-IQ3_XXS, GSQ-RCO Q2_0) are unaffected. The 256-expert layout
makes the fork's cached-expert path emit a fused `ffn_moe_gate` (`MUL_MAT_ID`) node that
CUDA graph capture does not support. `GGML_CUDA_DISABLE_GRAPHS=1` does not help; running
the fork with `GGML_CUDA_DISABLE_FUSION=1` avoids the fused node and the model serves
normally (all Coder IQ1_M numbers in the Flash-Next archive use it).

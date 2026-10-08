# moe-cache fork

[GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp), branch `moe-cache`.
Both rigs serve b11814-28d73c87c: built on Rig 1 (2026-10-08), and copied verbatim to Rig 2
the same day (no rebuild; the previous b11608-2b8088c2a dir is kept beside it as a backup).
The fork revision documented here is b11814-28d73c87c (`28d73c87c`), which adds the
generic-hybrid and profile flags below. Published fork numbers were measured on b11608 unless
the row says otherwise (Rig 1's Qwen3.6-35B 256k and KAT-Coder rows are b11814).

Two opt-in, CUDA-only features: a *dynamic* CUDA LRU/frequency-aware expert cache (no routing
profile, no trace step) and a *generic hybrid* CPU/GPU MoE executor that shares that cache as
its single residency owner. Their flags are fork-specific and do not exist in the upstream or
ik-llama.cpp builds.

## Flags

- `--moe-expert-cache-size N` - expert slabs kept on GPU per expert tensor, per owning
  device (0 = off, default). Enabling it routes all MoE expert tensors through the cache
  and **overrides** `--cpu-moe` / `--n-cpu-moe` placement; cold experts stay in host pinned
  memory. `--moe-expert-cache-mib MiB[,MiB,...]` is the byte-budget alternative (one value
  broadcasts across devices; mutually exclusive with a nonzero size).
- `--moe-expert-cache-layers N[,N-M,...]` - restrict caching to listed layers; this flips
  precedence so CPU/tensor overrides win and the cache claims only leftovers.
- `--moe-expert-cache-host-pinned-mb N` - model-wide pinned host budget in MiB (source weights
  + staging). Default `0` tries full pinning, then auto-registers complete groups after a
  pageable fallback.
- `--spec-draft-moe-expert-cache-size/-layers/-mib` - an independent cache for the draft
  model (0 disables it).
- `--spec-draft-ubatch-size` / `--ubatch-size-draft` / `-ubd N` (env
  `LLAMA_ARG_SPEC_DRAFT_UBATCH`) - sizes the *draft* context's own ubatch, independent of
  the target's `-ub`; default 0 inherits the target `-ub`. Fork-specific.
- Env aliases `LLAMA_ARG_MOE_EXPERT_CACHE_*`; `GGML_CUDA_MOE_FREQUENCY=0` forces pure LRU.

Generic hybrid execution (opt-in, off by default; needs the expert cache):

- `--moe-hybrid on|off` (env `LLAMA_ARG_MOE_HYBRID`) - select the generic source executor:
  resident experts run on CUDA and cache misses split between CUDA transfers and a persistent
  CPU pool, sharing the grouped cache as the single residency owner. Model layout, operators and
  backend capabilities decide eligibility (no architecture whitelist); unsupported layouts fall
  back to ordinary execution, or fail closed where a graph requires grouped execution. `off`
  overrides an inherited activation.
- `--moe-gpu-miss-fraction F` (env `LLAMA_ARG_MOE_GPU_MISS_FRACTION`) - fraction of distinct
  cache misses transferred to the GPU, at 1/256 resolution; default `0.17`, range `[0,1]`; the
  rest use CPU. Resident hits already run on CUDA.
- `--moe-source-graph-capacity` / `--no-moe-source-graph-capacity` (env
  `LLAMA_ARG_MOE_SOURCE_GRAPH_CAPACITY`) - reserve reusable hybrid source graph shapes to reduce
  rebuilds; may change outputs; no effect on normal full-GPU execution.
- On the 12 GB Rig 1 card, hybrid needs `--phase-aware-workspace` even to decode, and is then
  VRAM-bound at cache 64 (OOM on the first request) - roughly half the decode of cache-only
  execution. Not competitive with the grouped cache alone on this card.

Expert profiles (off by default; reuse the grouped-cache owner, no second cache):

- `--moe-expert-profile FILE` (env `LLAMA_ARG_MOE_EXPERT_PROFILE`) - load model-bound expert
  statistics (GGUF) or a geometry-compatible ranked STRP profile.
- `--moe-profile-adapt off|occurrence|occurrence-sync` (env `LLAMA_ARG_MOE_PROFILE_ADAPT`,
  requires `--moe-expert-profile`) - online residency adaptation; default `off`.
- `--spec-draft-moe-expert-profile` / `--spec-draft-moe-profile-adapt` - independent
  draft-context equivalents (env `LLAMA_ARG_SPEC_DRAFT_MOE_EXPERT_PROFILE` / `..._ADAPT`).
- Collect a weighted corpus profile in-tree: `test-llama-archs --collect-moe-profile model.gguf
  --profile-corpus corpus.json --profile-output calibration.gguf` (auto-enables hybrid; bounded
  and greedy-to-EOG). The profile is metadata-only GGUF; version 2 adds source-indexed F64
  `moe.profile.ranking_scores`. `--moe-expert-cache-size 0` / cache-off still restores baseline
  placement.
- Serving constraint (measured): the collector calibrates the default graph only - it omits
  prefill, draft and MTP-acceptance sources - so a profile cannot be served with MTP (the load is
  rejected with `profile omits a returned expert source`, from the per-source non-empty-count
  check). `--moe-profile-adapt` additionally requires generic source execution, i.e.
  `--moe-hybrid on`. With MTP off and no adaptation a profile loads but changed nothing
  measurable on Qwen3.6-35B (Rig 1).

Fork-specific companions (all default off, absent from stock and ik-llama.cpp):

- `--moe-early-router` - predicts the next layer's routed experts and prepacks eligible
  adjacent pageable groups (fixed one-layer lookahead).
- `--ple-prefetch` - advises lazy CPU row pages before CPU `GET_ROWS` (the lazy
  per-layer-embedding tables). A no-op without a lazy tensor.
- `--decode-overlap` - queues eligible CUDA decode work while the CPU handles the previous
  result; for integrated MTP it also overlaps the first next-draft pass. Needs
  `--backend-sampling` (an upstream flag).
- `--decode-boundary-overlap` - also prepares the next decode boundary and updates CUDA
  graphs while prior GPU work runs; use with `--decode-overlap`. For eligible single-CUDA MTP
  contexts it also stages token/embedding/hidden-state inputs in the two event-protected host
  buffers, dropping a draft/target synchronize (opt-in; engine unchanged).
- `--phase-aware-workspace` - releases eligible prompt-only workspace before decode. On the
  12 GB Rig 1 card this freed ~1.9 GiB on Qwen3.6-35B, raising the expert-cache ceiling 64 → 80
  slabs (~+9-10% decode at 10K, ~+4% at 60K, for ~−3% prefill); 88/96 slabs then load but OOM on
  the first request. On KAT-Coder-V2.5-Dev it frees ~800 MiB and carries cache 80 → 88 slabs
  (~+5% decode at 10K and 60K, no prefill cost), with 100/104 slabs OOMing at load; on Gemma4-26B
  it frees nothing at steady state, where the cache tops out at 72 slabs anyway. A sizing change:
  the cache serves the same way, just with more slabs resident. On the 24 GB RTX 3090 (Rig 2),
  where the model already fits at 256k, the expert cache is a straight loss (128/168 slabs cost
  ~25%/15% decode vs cache 0) and this flag is the only lever: ~1.3 GiB freed at cache 0 for no
  decode cost, and on the 512k YaRN shape it carries cache 168 -> 200 (~+3% prefill / ~+4%
  decode at the same peak; 224 OOMs at load).
- `--live-context-workspace` - sizes supported attention workspace from the live KV extent
  instead of the full allocation.
- `--experimental-logs` - prints detailed cache, host-source, grouped-execution, and transfer
  counters (used by the validation step below).
- Env aliases `LLAMA_ARG_MOE_EARLY_ROUTER`, `LLAMA_ARG_PLE_PREFETCH`,
  `LLAMA_ARG_DECODE_OVERLAP`, `LLAMA_ARG_DECODE_BOUNDARY_OVERLAP`.

Speculative companions (fork-specific, absent from stock/ik-llama.cpp):

- `--mtp-draft-vocab FILE` (env `LLAMA_ARG_MTP_DRAFT_VOCAB`; requires `--spec-type draft-mtp`) -
  restrict a supported MTP final projection to a model-bound GGUF sidecar vocabulary; default
  empty = unrestricted.
- `--spec-lookup-chain N` (env `LLAMA_ARG_SPEC_LOOKUP_CHAIN`; 0 = off, range 0..1024) and
  `--spec-lookup-chain-min N` (env `LLAMA_ARG_SPEC_LOOKUP_CHAIN_MIN`; default 3, min 3) - bounded
  history matching that replaces or extends an MTP proposal from matching recent token history.
  Layered on the generic speculative path, not the Strata suffix drafter.

Standard llama.cpp flags (`-b`/`-ub`, `-fa`, `-lm/--load-mode`, `-kvo/--kv-offload`,
`-lzm/--lazy-mode`, `-cram/--cache-ram`, `-bs/--backend-sampling`, `--spec-type draft-mtp`,
`--spec-draft-n-max`) behave as in [upstream](upstream-stock.md). Env
`GGML_CUDA_DISABLE_FUSION=1` (ggml-cuda) disables CUDA op fusion; it is needed to run
models whose fused `ffn_moe_gate` (`MUL_MAT_ID`) node is not CUDA-graph-capturable on this
fork (the pruned 256-expert Flash-Next Coder). `GGML_CUDA_DISABLE_GRAPHS=1` does not help.
See [issues.md](../issues.md) §6.

## Validation

The cache can only be exercised with a real context, so all cache numbers come from
llama-server (`/v1/completions`), never `llama-bench`. Validate a dynamic-cache run with one
`--experimental-logs` pass and check: `moe-grouped-decode` `calls > 0`, and
`fallback` / `rollback` / `prepare_error` / `finish_error` / `upload_errors` all `0`.

A hybrid run additionally logs `provider=source-core` with complete copy/GPU/CPU/publication
counts and zero failures - a flag alone does not prove the executor ran. The fork's own hybrid
qualification is a single RTX 5070 Ti on Linux; native Windows hybrid and physical multi-GPU
generic serving are unqualified.

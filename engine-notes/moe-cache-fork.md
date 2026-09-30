# moe-cache fork

[GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp), branch `moe-cache`.
Rig 1 build b11608-2b8088c2a.

A *dynamic* CUDA LRU/frequency-aware expert cache: no routing profile, no trace step.
Opt-in and CUDA-only. Its expert-cache flags are fork-specific and do not exist in the
upstream or ik-llama.cpp builds.

## Flags

- `--moe-expert-cache-size N` - expert slabs kept on GPU per expert tensor, per owning
  device (0 = off, default). Enabling it routes all MoE expert tensors through the cache
  and **overrides** `--cpu-moe` / `--n-cpu-moe` placement; cold experts stay in host pinned
  memory. `--moe-expert-cache-mib MiB[,MiB,...]` is the byte-budget alternative (one value
  broadcasts across devices; mutually exclusive with a nonzero size).
- `--moe-expert-cache-layers N[,N-M,...]` - restrict caching to listed layers; this flips
  precedence so CPU/tensor overrides win and the cache claims only leftovers.
- `--moe-expert-cache-host-pinned-mb N` - model-wide pinned host budget in MiB.
- `--spec-draft-moe-expert-cache-size/-layers/-mib` - an independent cache for the draft
  model (0 disables it).
- `--spec-draft-ubatch-size` / `--ubatch-size-draft` / `-ubd N` (env
  `LLAMA_ARG_SPEC_DRAFT_UBATCH`) - sizes the *draft* context's own ubatch, independent of
  the target's `-ub`; default 0 inherits the target `-ub`. Fork-specific.
- Env aliases `LLAMA_ARG_MOE_EXPERT_CACHE_*`; `GGML_CUDA_MOE_FREQUENCY=0` forces pure LRU.

Fork-specific companions (all default off, absent from stock and ik-llama.cpp):

- `--moe-early-router` - predicts the next layer's routed experts and prepacks eligible
  adjacent pageable groups (fixed one-layer lookahead).
- `--ple-prefetch` - advises lazy CPU row pages before CPU `GET_ROWS` (the lazy
  per-layer-embedding tables). A no-op without a lazy tensor.
- `--decode-overlap` - queues eligible CUDA decode work while the CPU handles the previous
  result; for integrated MTP it also overlaps the first next-draft pass. Needs
  `--backend-sampling` (an upstream flag).
- `--decode-boundary-overlap` - also prepares the next decode boundary and updates CUDA
  graphs while prior GPU work runs; use with `--decode-overlap`.
- `--phase-aware-workspace` - releases eligible prompt-only workspace before decode.
- `--live-context-workspace` - sizes supported attention workspace from the live KV extent
  instead of the full allocation.
- `--experimental-logs` - prints detailed cache, host-source, grouped-execution, and transfer
  counters (used by the validation step below).
- Env aliases `LLAMA_ARG_MOE_EARLY_ROUTER`, `LLAMA_ARG_PLE_PREFETCH`,
  `LLAMA_ARG_DECODE_OVERLAP`, `LLAMA_ARG_DECODE_BOUNDARY_OVERLAP`.

Standard llama.cpp flags (`-b`/`-ub`, `-fa`, `-lm/--load-mode`, `-kvo/--kv-offload`,
`-lzm/--lazy-mode`, `-cram/--cache-ram`, `-bs/--backend-sampling`, `--spec-type draft-mtp`,
`--spec-draft-n-max`) behave as in [upstream](upstream-stock.md).

## Validation

The cache can only be exercised with a real context, so all cache numbers come from
llama-server (`/v1/completions`), never `llama-bench`. Validate a dynamic-cache run with one
`--experimental-logs` pass and check: `moe-grouped-decode` `calls > 0`, and
`fallback` / `rollback` / `prepare_error` / `finish_error` / `upload_errors` all `0`.

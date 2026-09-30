# Upstream (stock) llama.cpp

[ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp).
Rig 1: v0.5.0-dev d834d44 (since the 2026-09-26 container rebuild; older stock rows were
measured on v0.4.0-dev 30b6a75). Rig 2: v0.5.0-dev build 11146 (7fe450e193).

The reference build. No expert cache.

## Flags / defaults

- `-b/--batch-size N` - logical maximum batch size (default 2048).
- `-ub/--ubatch-size N` - physical maximum batch size (default 512; env `LLAMA_ARG_UBATCH`).
  `-ub` is the compute unit and the prefill lever; `-b` above `-ub` only changes
  chunking/logical buffers, since the compute arena is sized by `min(n_ctx, n_ubatch)`.
- `-fa/--flash-attn [on|off|auto]` - Flash Attention (default `auto`).
- `-lm/--load-mode MODE` - model loading mode (default `auto`).
- `-ncmoe/--n-cpu-moe N` - keep the MoE weights of the first N layers in CPU memory
  (default 0 = all experts on GPU).
- `-cram/--cache-ram N` - maximum prompt-cache size in MiB (default 8192).
- MTP / speculative decode: `--spec-type draft-mtp` with `--spec-draft-n-max N`
  (default 3) / `--spec-draft-n-min N` (default 0), and `-md/--model-draft <file>` for a
  separate draft model. Also available: `draft-simple`, `draft-eagle3`, `draft-dflash`,
  `draft-dspark`, and the `ngram-*` types. The old `--draft` / `--draft-max` flags are
  removed.
- `--reasoning-preserve` - keep reasoning spans in context.

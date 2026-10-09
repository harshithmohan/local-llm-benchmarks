# Strata

[Niko1221/Strata](https://github.com/Niko1221/Strata), engine 0.1.40.2 on Rig 1.

A llama.cpp-derived engine that runs
[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) (~125B parameters,
24,576 routed experts, ~10 of them used per token) on one 12 GB consumer card, by splitting
the work across the whole PC instead of fitting the model in VRAM:

- **GPU:** attention and DeltaNet mixers, the gated-residual weights, routers, shared
  experts, the output head, the MTP draft layer, the KV cache, and an **expert cache** that
  fills the rest of VRAM with the most-used experts and adapts to the conversation as it
  runs.
- **Host RAM:** every expert, pinned. The CPU computes the experts the GPU does not hold,
  in place and in parallel with the GPU.
- **SSD:** a 28.8 GB n-gram table, read a few rows per token through the OS cache.

The same engine builds for CUDA and HIP.

**Measured on Rig 1** (engine 0.1.40.2): the GSQ-RCO `Q2_0` release of
[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), on its own pack. The
timing rows, the ctx/chunk ladders and the `STRATA_*` A/Bs are on the model card and its
archive ([Qwen3.8-Flash-Next](../models/rig1-3060/qwen38-flash-next.md)).

## Why it is not a `llama-server` build

- **The HTTP API is a separate process.** The `strata` binary is a stdio backend
  (`--serve`); a Python server (`serve/server.py`) spawns it and owns the OpenAI
  (`/v1/chat/completions`) and Anthropic (`/v1/messages`) routes, the conversation cache
  and the agent features (tools, MCP, reasoning). Run settings live in a JSON config - an
  `exe` plus its `args`, `cwd`, tokenizer, model name and log path - rather than on the
  server's command line, so the same settings can drive the CLI, the app and the server.
  The two are not combined: the server's own command line takes only server-level flags
  (`--config`, `--port`, `--host`, `--lazy`, `--idle-unload`, ...) and an engine flag passed
  there is a startup error, while the config is read as plain JSON with no includes or
  substitutions - so a change to an engine flag is always a change to the config file, and a
  second configuration (a longer window, say) is a second file.
- **The model is a pack, not one GGUF.** `--pack DIR` holds a per-layer index, the dense
  weights and a tokenizer; `native_experts.txt` says where each expert's rows live, and an
  optional `experts.bin` maps them for low-RAM machines. The original GGUF shards stay on
  disk and are named separately (`--native`, `--ple-gguf`).
- **Its own flag vocabulary** - the mapping to the llama.cpp names is below. Only
  `--rope-scaling` and its companions, plus the sampling flags, keep the llama.cpp names.

## Flags

Flags used on this benchmark:

- `--pack DIR` - the pack directory (per-layer index, dense weights, tokenizer, expert map).
- `--native SHARD1` - the first model GGUF shard; turns on every "native" (precomputed,
  GGUF-mapped) path at once: stream-token, head, dense + PLE projections, MoE combine, GDN,
  router, QSA, indexer, RoPE and the CPU `q8_0` contract. The individual `--native-*` flags
  stay for A/B runs, and `--no-capture` runs the layers directly instead of replaying graphs.
- `--ple-gguf PATH` - the shard holding the per-layer embedding table (the PLE layer). Which
  shard that is depends on the pack's layer split and is not always the second: a release can
  keep all layers in shard 1 and put the table alone in shard 2, or break earlier and carry the
  table in shard 1. Left unset it defaults to the shard that holds
  `per_layer_token_embd.weight`, found by name - as are the model's shards themselves, by their
  `<name>-0000N-of-0000M.gguf` names beside `--native` (a missing shard is an error).
  `--ple-io direct|mmap|ram` picks how the n-gram table is read: unbuffered SSD reads by
  default, `ram` locks the whole table.
- `--expert-profile P` - pre-loads the VRAM expert tier from a saved `profile.bin` instead
  of admitting on first use; `--expert-profile-save P` writes back what the adaptive policy
  learned.
- `--expert-cache N|auto` - expert blobs kept resident in VRAM (`0` = off). `auto` sizes the
  tier from the VRAM left after the weights, session buffers and KV. Multi-GPU variants:
  `--expert-cache-device1..3 N`, `--peer-device N`, and `--expert-cache-per-layer` (per-layer
  slots instead of one shared counter).
- `--mtp DIR` - the MTP runtime directory (the draft layer's weights and `draft_vocab.bin`).
- `--spec T` - the speculative verify window. `T >= 2` is structural on this pack: a native
  (IQ) pack refuses to start at `--spec 1` (it needs `--native SHARD1`, `--spec T` with
  `T >= 2`, and `--prefill CHUNK`), and `--mtp` is ignored when `T < 2`.
- `--spec-min-p F` - the draft acceptance floor (default 0.0). At `0.0` the verify window is
  always the full `--spec`; above it the window is truncated to the run of leading drafts whose
  probability clears `F`. Sweep it with `--spec` ([tuning.md](../tuning.md#strata-only));
  measured rows are in the [Flash-Next archive](../models/rig1-3060/archive/qwen38-flash-next.md).
- `--prefill CHUNK` - batched prompt processing in chunks; `auto[:N]` picks the largest chunk
  whose buffers the expert cache can lend (needs `--native`). The prompt path borrows the top
  of the expert cache for its per-chunk buffers and refills those slots after each chunk, so a
  bigger chunk borrows more: `auto` takes the largest chunk whose buffers leave `>= 128`
  cache slots free and take at most `90%` of them - `85%` when under 90% of the expert bytes are
  pinned host RAM. That scan is a bisection on the 256-token grid, not a fixed list: the list
  (`8192`, `6144`, `4096`, `3072`, ...) is the pre-0.1.39b behaviour, still reachable with
  `STRATA_RING_BYTES=0`, and since 0.1.39b the default also holds the prompt ring full, so the
  value it lands on is pack-specific and can sit between the list's sizes. `32768` and `16384`
  need `auto:N` (a bare `auto` stops at `8192`), and an explicit `--prefill N` is the
  operator's number, which only has to fit - the percentage is an `auto`-only rule, so an
  explicit chunk never consults it and can be larger than `auto` would pick on the same cache.
  An oversized pin is clamped rather than rejected: it is halved until it fits, so an explicit
  chunk lands on the pin or one of its halves. The percentage is a share of the *resident*
  cache, not of free VRAM, so `--expert-cache N` moves the step; the cache shrinks as
  `--max-context` grows, so the chunk steps down with it, and each step down costs prefill.
  `STRATA_PREFILL_LEND_PCT=N` overrides the percentage and lets a larger chunk fit a wider
  window; wherever the chosen chunk does not change it does nothing. Rows and the A/Bs are in
  the [Flash-Next archive](../models/rig1-3060/archive/qwen38-flash-next.md).
- `--kv fp16|int8|q4_0|k8v4` - KV storage. `int8` is int8 codes with an fp16 scale per 64
  values (half of fp16); `q4_0` is a Hadamard-rotated 4-bit K/V; `k8v4` is INT8 K with a
  rotated `q4_0` V. `--kv-resident N` streams all but N cells of each attention layer from
  pinned RAM and gives the freed VRAM to the expert cache.
- `--max-context N` - KV/state capacity (default 4096). The pack's trained window is what it
  should stay within unless `--rope-scaling` is used. Size it to what you serve: at a fixed
  chunk and expert cache, raising the window alone still costs prefill even though the same
  prompt is read, so headroom you do not use is not free.
- `--prompt-cache N` - how many conversation checkpoints the server keeps between requests
  (default 6, ~118 MB of RAM each; `0` = read every prompt from the start). This is what makes
  a resent prompt cheap - the second pass reports a nonzero `cache_n` - and it is an engine
  flag, not a request field. `--prompt-cache-every N` also checkpoints every N fresh prompt
  tokens (default 16384, `0` = off) and `--prompt-cache-tail` adds one more near the prompt's
  end. Checkpoints land only on prompt-chunk boundaries, so the spacing that matters is
  `ceil(N / chunk) x chunk` - the default 16384 is several chunks apart - and a growing session
  pays that gap on every turn. Pinning N to the chunk minimises the per-turn re-read, and the
  grid cannot be finer than one chunk, so the chunk size is the optimum. The measured ladder is
  in the [Flash-Next archive](../models/rig1-3060/archive/qwen38-flash-next.md).
- `--conversation-cache-mib N` / `--conversation-cache-slots N` /
  `--conversation-cache-min-free-mib N` - parked conversations between requests: the RAM
  budget (default 0 = off), the number kept (default 4) and a RAM floor (default 2560).

### Against the llama.cpp engines

| Concept | llama.cpp | Strata |
| --- | --- | --- |
| context | `-c` / `--ctx-size` | `--max-context` |
| KV type | `--cache-type-k/-v` (`q8_0`, `q4_0`) | `--kv fp16\|int8\|q4_0\|k8v4` |
| prompt batch | `-b` / `-ub` | `--prefill auto[:N]` (needs `--native`) |
| expert cache | `--moe-expert-cache-size` ([moe-cache fork](moe-cache-fork.md)) | `--expert-cache N\|auto` (+ `--expert-profile`) |
| spec decode (MTP) | `--spec-type draft-mtp --spec-draft-n-max` | `--mtp DIR --spec T --spec-min-p F` |
| context extension | `--rope-scaling yarn --rope-scale F --yarn-orig-ctx N` | same names |
| sampling | `--temp` / `--top-k` / `--min-p` / `--seed` | `--temperature` / `--top-k` / `--top-p` / `--seed` |

## Validation

The engine prints one line per request - `request prompt P cached C output O prompt_read R ms
total S ms prefill X tok/s decode Y tok/s` - and the server returns the same numbers in the
response's `timings` object **under llama.cpp's field names**: `prompt_n`, `prompt_ms`,
`prompt_per_second`, `predicted_n`, `predicted_ms`, `predicted_per_second`, `cache_n`, plus
`draft_n` / `draft_n_accepted` when MTP reported them. `cache_n` is the part of the prompt
answered from Strata's own conversation cache and `prompt_n` is the rest, so a pass that
reports a nonzero `cache_n` is not a full prefill - and that cache engages on its own: send
the same prompt twice and the second pass comes back with a nonzero `cache_n`, with no cache
parameter set on the request.

The request protocol in [methodology.md](../methodology.md) does **not** carry over as
written: Strata serves no raw `/v1/completions` route - only `/v1/chat/completions`,
`/v1/messages` and `/v1/responses`, so a chat template is always applied - and it ignores
both `cache_prompt` and `ignore_eos`. **Run every prefill measurement with `--prompt-cache
0`** - that reads each prompt from the start rather than resuming a checkpoint - and treat a
pass as a full prefill only when `cache_n` is 0. Only a `predicted_n` that reaches the
requested window is a complete decode run. There is no `llama-bench` equivalent, and
`llama-bench` is not used anywhere here.

Served without an API key, the server also refuses a request whose `Host` is not a name it
answers to (403, DNS-rebinding protection): an IP address, `localhost` and the names it
already answers to pass, and any other name must be listed in the config's `allowed_hosts` -
which includes the name a proxy or gateway forwards, since it passes the `Host` header on.

A load is valid when the startup log names a nonzero VRAM expert tier (the engine warns when
the weights leave no VRAM for the cache) and the CPU/GPU split actually happens;
`--dump-routing PATH` writes the routed expert ids and weights per layer and position when
the split needs checking, and `--expert-cache-cpu-order` makes the GPU's reduction follow
the CPU's order for an A/B.

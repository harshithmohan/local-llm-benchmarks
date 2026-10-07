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

**Measured on Rig 1** (engine 0.1.40.2) - GSQ-RCO Q2_0, `--kv int8`, MTP on, at the two served
windows: the 200000 window measures **1058 t/s prefill / 44.2 t/s decode** on the ~10k prompt,
**1045 / 42.4** at ~60K and **1008 / 41.8** at ~120k; the 250000 window (a 4096-token chunk
against the 200000 window's 6144) measures **975 / 39.2**, **970 / 39.9** and **936 / 38.2**.
Against the 0.1.38 rows the ~10k prefill is unchanged and the longer prompts gain (+2.4% at ~60K,
+8.4% at ~120k), so the long-prompt prefill penalty is now ~4-5% where it was ~9-12%; decode is
higher in every cell. The timing rows are on the
[Qwen3.8-Flash-Next (Rig 1) card](../models/rig1-3060/qwen38-flash-next.md).

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
- `--ple-gguf PATH` - the shard holding the per-layer embedding table (the PLE layer).
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
  bigger chunk borrows more: `auto` takes the largest size on the engine's list
  (`8192`, then `6144`, `4096`, `3072`, `2048`, `1024`, `512`, `256`) whose buffers leave `>= 128`
  cache slots free and take at most `90%` of them - `85%` when under 90% of the expert bytes are
  pinned host RAM. `32768` and `16384` need `auto:N` (a bare `auto` stops at `8192`), and an
  explicit `--prefill N` is the operator's number, which only has to fit - the percentage is an
  `auto`-only rule, so an explicit chunk never consults it, which is how the served 200000
  config keeps 6144 (2670 cache slots, a 2427-slot loan - `auto` would step down to 4096
  there, since 0.90 x 2670 = 2403 < 2427). The cache shrinks as
  `--max-context` grows, so the chunk steps down with it: on Rig 1 (GSQ-RCO Q2_0, `--kv int8`)
  8192 holds to ~134k ctx, 6144 to ~198k, 4096 to ~261k, and 3072 only above that - and each
  step down costs prefill (11% at ~98k). That percentage is a share of the *resident* cache, not
  of free VRAM, so `--expert-cache N` moves the step: forcing 3248 slots at 122880 drops the
  chunk to 6144 with 866 MiB still free. `STRATA_PREFILL_LEND_PCT=N` overrides the percentage:
  at `95` a 6144-token chunk keeps fitting to ~210k ctx instead of ~198k (8192 to ~150k instead
  of ~134k), 4096 becomes the floor for the rest of the 262144 window, and the freed chunk is
  worth +6.4% prompt read at 204800; wherever the chosen chunk does not change, it does nothing
  (the earlier shipped 81920 included). Rows and the A/B are in the
  [Flash-Next archive](../models/rig1-3060/archive/qwen38-flash-next.md).
- `--kv fp16|int8|q4_0|k8v4` - KV storage. `int8` is int8 codes with an fp16 scale per 64
  values (half of fp16); `q4_0` is a Hadamard-rotated 4-bit K/V; `k8v4` is INT8 K with a
  rotated `q4_0` V. `--kv-resident N` streams all but N cells of each attention layer from
  pinned RAM and gives the freed VRAM to the expert cache.
- `--max-context N` - KV/state capacity (default 4096). The pack's trained window is what it
  should stay within unless `--rope-scaling` is used. Size it to what you serve: at a fixed
  chunk and expert cache, raising the window alone costs prefill (122880 -> 149000 reads the
  same 119344-token prompt 8.1% slower), so headroom you do not use is not free. Rig 1 serves
  two tiers on the app side: 200000 with an explicit `6144` chunk (default) and 250000 with
  `4096` (max ctx), each pinned as above.
- `--prompt-cache N` - how many conversation checkpoints the server keeps between requests
  (default 6, ~118 MB of RAM each; `0` = read every prompt from the start). This is what makes
  a resent prompt cheap - the second pass reports a nonzero `cache_n` - and it is an engine
  flag, not a request field. `--prompt-cache-every N` also checkpoints every N fresh prompt
  tokens (default 16384, `0` = off) and `--prompt-cache-tail` adds one more near the prompt's
  end. Checkpoints land only on prompt-chunk boundaries, so the spacing that matters is
  `ceil(N / chunk) x chunk`: the default 16384 is three 6144-chunks apart, and a growing
  session pays that gap on every turn - pinning N to the chunk cut a 23-turn ladder from 555 s
  to 416 s on the 6144 chunk (565 s to 413 s on the 4096 one) by taking the per-turn re-read
  from ~2.5x to ~1.4x the tokens added. The grid cannot be finer than
  one chunk, so the chunk size is the optimum.
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

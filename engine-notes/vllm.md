# vLLM

[syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) container stack, Rig 2. Used for the Qwen3.8-27B W4A16-AutoRound quant and the Swift-1.5-INT4 fine-tune quant; the notes below hold for vLLM 0.31.0 (current pin: [rig2-3090.md](../rig2-3090.md)).

## Flags

- Engine labels are per-row: llama.cpp and vLLM results are not interchangeable.
- Knobs come in two tiers: launcher env vars, read by the image's scripts, and engine flags passed through `EXTRA_ARGS`.

### Launcher knobs

- `CTX` picks a context preset (`fast`, `long`, `huge`) - shorthand that sets `MAX_LEN` and the KV mode together. Pick the largest preset whose KV pool still fits.
- `MAX_LEN` sets the served context length. The model's native RoPE limit is 262144; beyond it the engine needs `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` and returns NaNs otherwise. `CTX` alone does not pin the pool - `--kv-cache-memory` does.
- `MAX_SEQS` sets concurrent sequence slots. Chained spec-decode buffers come out of the same budget as the KV pool, so at a low GPU memory fraction too high a `MAX_SEQS` leaves the pool too small to boot; lower it to fit.
- `DRAFT_TOKENS` sets the chained MTP draft count - acceptance plateaus around 4, and each extra draft costs KV.
- `SPEC` selects the speculator (`mtp`, `dflash2`); `DFLASH_MAX_LEN` caps the DFlash2 request length (the launcher reads it rather than `MAX_LEN` on that path).
- `GPU_UTIL` sets vLLM's GPU memory fraction (batch default 0.94, single-user 0.93). Raising it squeezes the KV pool; 0.95 has OOM'd on a short-prompt step.
- `EXTRA_ARGS` appends raw vLLM flags to the launch line, last-wins - the escape hatch for anything with no knob of its own (`--kv-cache-memory` to pin the KV pool by bytes beyond the `GPU_UTIL` reserve, `--no-enable-prefix-caching` to force a cold pass, `--kv-cache-dtype` for a KVarN tile).
- `PREFIX_CACHE=1` adds `--enable-prefix-caching` (with `--mamba-cache-mode align`); the knob can only turn caching on, never off.
- `MODEL` and `PREPARE` point a run at an alternative checkpoint directory instead of the shipped one, `PREPARE=0` reusing an already-prepared one.
- `KV_MEM` sizes the draft KV for the DFlash2 branch; it is not read on the MTP branch.

### Engine flags

- `KVARN_FP16_DEQUANT=1` runs the three fused KVarN decode kernels' dequant in fp16 (the dots still accumulate in fp32). Halving the working tiles halves their register pressure, which is what lifts the long-context split-K decode, at no cost to prefill or VRAM. It is part of vLLM's torch.compile cache key, so the first boot after enabling it recompiles; the compile cache persists, so that is paid once per cache volume rather than on every boot. With it on, the split-K stage1 and verify autotune narrows to tile shapes that spill few registers - a heavily spilling shape is 2.5-24x slower at long context, so the win is worth confirming per config rather than assumed.
- `EMBED_UVA=1` keeps the quantized token embedding in pinned host RAM behind a CUDA UVA view and gives the freed VRAM to the KV pool (~15% more pool tokens for ~2.1 GiB of host RAM and ~20 s of boot). A pool-size knob, not a speed one; skipped for tied embeddings and unmeasured at TP>1.
- `INT8_ACT=int8` is the W4A8 path - int4 weights with int8 activations through the Marlin prefill, worth roughly 25-30% more prefill in the prefill-bound regime. `PREFILL_ATTN=int8` is its optional prefill-attention companion and adds nothing measurable here; `INT8_LAYERS` defaults to the full layer set, `mlp` is the smaller middle point, and `mlp|linear_attn` crashes on an inductor codegen bug.
- `TOOL_STRICT` (default `parameter`) is the `--tool-strict-level` the launchers pass, so every tool call is held to its argument schema and a forced call to a parameterless tool sends `{}`; `auto` holds a call to the schema only when the tool sends `strict: true`, which lets such a call invent arguments - relevant to any tool-calling or agent row.
- `KV_OFFLOAD_GB=N` sets a CPU KV tier behind the GPU prefix cache; size it above what it holds, because a tier that fills while a request is still running drops chunks the next look-up needs. Not a speed win on its own.
- Draft sampling: `DRAFT_SAMPLE` (default `probabilistic`), `VLLM_DRAFT_TEMP_SCALE` and `VLLM_DRAFT_TOPK_TOPP` - the defaults beat every tested alternative.

### Tested, not used

- `VLLM_PREFIX_CACHE_RETENTION_INTERVAL` is a no-op on this image (the upstream retention fix is already in), and `VLLM_MARLIN_TUNE` gives no win at a 250 W cap.
- `KVARN_DECODE_CONFIG`, `KVARN_FUSED_*` and `KVARN_FA_*` are Intel-XPU kernel-routing knobs with no CUDA path.
- `--max-num-batched-tokens` is left at the launcher's 2048: 4096 is neutral and 8192 boots but OOMs on a large prefill. `--hf-overrides max_position_embeddings` is not the lever for a longer context here - the ceiling is VRAM, not RoPE - and `--bits 4` / `--keep-fc` belong to drafter-quant preparation, not a boot line.
- For `--kv-cache-dtype`, KVarN's `kvarn_k4v2_g128` is the balanced default; the `k4v4_g128` / `k4v2_g64` / `k4v4_g64` tiles only trade KV capacity for accuracy.

## Measurement specifics

- Timings come from vLLM's **Prometheus metrics**, not the llama-server `timings` object; `llama-bench` is not used. Prefill = `prompt_tokens_total` / `request_prefill_time_seconds`; decode = `generation_tokens_total` / `request_decode_time_seconds`; acceptance = `spec_decode_num_accepted_tokens_total` / `spec_decode_num_draft_tokens_total`; VRAM is the per-process allocation, read from the compute-apps query - the process is `VLLM::EngineCore`.
- A row is two passes per boot on the shared timing prompt ([test-prompts.md](../test-prompts.md)), the second recorded. The served profiles run vLLM's default automatic prefix caching: the image's `PREFIX_CACHE` env only ever *adds* `--enable-prefix-caching`, so it cannot turn caching off, and a repeated identical send is served from cache (~99% `cached` on a measured re-send). The recorded pass therefore has to be made cold explicitly - run the bench container with `--no-enable-prefix-caching` appended to `EXTRA_ARGS` (it expands last on the launch line, so it wins) and assert `prompt_tokens_cached_total` 0. The ~120K rows on the two Rig 2 model pages were taken that way; the retired single-pass rows were cold by construction (fresh boot, first send).
- Decode includes the accepted MTP drafts, so it tracks draft acceptance, and that is a stochastic draw at the protocol's sampling settings: the same prompt re-sent in the same boot has read ±10 points of acceptance and, with it, ±15% of decode, while prefill stayed within ~1%. Compare decode only across runs that send the same prompts in the same order, and reach for the acceptance figure when a decode difference needs explaining.

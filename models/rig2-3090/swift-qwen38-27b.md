# Swift-1.5-Qwen3.8-27B (Rig 2) - recommended configs

Updated: 2026-11-05 · [full experiment log](archive/swift-qwen38-27b.md) · [methodology](../../methodology.md)

`Swift-1.5-INT4`, the Swift-1.5 fine-tune of Qwen3.8-27B (`qwen35` dense hybrid SSM + attention - only every 4th layer carries full attention, `full_attention_interval=4` - native ctx 262144, embedded MTP head). Dense, not a MoE, so no expert split applies. Served on the same [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) vLLM container (vLLM 0.32.0) as the base model. The served build is `Swift-1.5-INT4-fast`: the port's int8 heads requantized to the same int4-GPTQ `lm_head` and draft head the base build runs, which brings the profile inside the rig's VRAM budget (the step the port skipped - experiment 6 of the port study). Model card: [ukisai/Swift-1.5-Qwen3.8-27b-INT4](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b-INT4). The base `W4A16-AutoRound-fast` quant is a separate model: [qwen38-27b.md](qwen38-27b.md).

Fine-tune port study (checkpoint preparation, not engine tuning): [../../experiments/qwen38-27b-swift-1.5-int4.md](../../experiments/qwen38-27b-swift-1.5-int4.md). Rig and setup: [../../rig2-3090.md](../../rig2-3090.md).

## Recommended configs

Two contexts: int8 KV at 167936 read by the pth-flash-attn kernel (4 chained MTP drafts, `PTH_FA=1`) for the fastest decode - the deployed profile since 2026-11-05, measured on this checkpoint below - and KVarN 4/2-bit KV at the native 262144 (3 chained drafts) for long requests. The 176128 fp8 row below is the previous 0.31.0-image profile. Speeds on that profile are measured on this checkpoint, not borrowed from the base quant ([qwen38-27b.md](qwen38-27b.md)).

| Config | ctx | engine | drafter | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Swift-1.5-INT4-fast | 167936 | vLLM | on | 2494 | **118.8** | 20674 MiB | `PTH_FA=1` int8 KV; 4 drafts, `MAX_SEQS=4`; pool pinned 6.8 GB (173,207 tokens); `EMBED_UVA=1`; accept 52.9% - measured on this checkpoint 2026-11-05 |
| Swift-1.5-INT4-fast | 176128 | vLLM | on | 2433 | **107.7** | 22028 MiB | fp8 KV; 4 drafts, `MAX_SEQS=4`; pool pinned 6.8 GB; `EMBED_UVA=1`; accept 54.2% |
| Swift-1.5-INT4-fast | 262144 | vLLM | on | 2374 | **97.6** | 21856 MiB | KVarN k4v2 KV, 3 drafts; pool pinned 5.3 GB; `KVARN_FP16_DEQUANT=1`; `EMBED_UVA=1`; accept 58.9% |

All rows are served with `INT8_ACT=int8`.

### PTH_FA profile on this checkpoint (2026-11-05, 0.32.0 image)

Same protocol as the base model's A/B: image `7592fbbb4e17`, 370 W, one cold boot at `MAX_LEN=167936`, two passes per prompt with the second recorded, prefix caching off (`--no-enable-prefix-caching`, `cached_tokens` 0 on every row). Load 261 s, VRAM 20674 MiB.

| prompt | prefill t/s | decode t/s | accept |
| --- | --- | --- | --- |
| 10k | 2494 | **118.8** | 52.9% |
| ~60K | 1821 | **119.2** | 65.7% |
| ~120K | 1328 | **91.9** | 59.8% |

Against the base quant on the same profile and pinned pool (`2604` / `120.4`, `1912` / `132.0`, `1424` / `106.6`; that boot ran at 176128, before the window was cut - the pool is pinned by bytes, so the KV allocation is the same): prefill −4.2% / −4.8% / −6.8% and decode −1.3% / −9.7% / −13.8%. The gap widens with context and tracks the checkpoint's own drafter: at long context its acceptance (65.7% at ~60K, 59.8% at ~120K) sits below the base model's (68.1%, 66.9%), and long-context decode follows acceptance; at 10k the two are within run noise. The borrowed numbers this row carried before overstated it; they are replaced.

## Configs

### Swift-1.5-INT4-fast at 176128 - vLLM, fp8 KV, 4 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: MODEL=Swift-1.5-INT4-fast  CTX=long  MAX_LEN=176128  GPU_UTIL=0.88
    #      DRAFT_TOKENS=4  MAX_SEQS=4
    #      EXTRA_ARGS=--kv-cache-memory=6800000000
    #      INT8_ACT=int8  EMBED_UVA=1
    # sampling (model default, from generation_config.json): temperature 1.0, top_p 0.95, top_k 20

### Swift-1.5-INT4-fast at 262144 - vLLM, KVarN 4/2-bit KV, 3 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: MODEL=Swift-1.5-INT4-fast  CTX=huge  MAX_LEN=262144  GPU_UTIL=0.88
    #      EXTRA_ARGS=--kv-cache-memory=5300000000
    #      INT8_ACT=int8  KVARN_FP16_DEQUANT=1  EMBED_UVA=1
    # sampling (model default, from generation_config.json): temperature 1.0, top_p 0.95, top_k 20

## Notes

- Both profiles pin the KV pool by bytes (`EXTRA_ARGS=--kv-cache-memory=...`): `KV_MEM` is not read on the MTP branch, and auto-sizing floats with free desktop memory.
- Both profiles run `EMBED_UVA=1`: the quantized embedding sits in pinned host RAM behind a CUDA UVA view, which frees ~1.1 GiB of card memory at no decode cost. That free memory is what pays for the larger pools - the fp8 pool needs ~6.7 GB to boot at 176128.
- `CTX=long` (fp8) needs `MAX_SEQS=4`: at the default 8 the 4-draft spec buffers push the pool below 176128 and the engine refuses to boot.
- The KVarN profile serves the model's native 262144; vLLM refuses 290000 unless `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` (risks NaN beyond native RoPE).
- vLLM's automatic prefix caching is ON by default in these profiles - the image's `PREFIX_CACHE` env only *adds* `--enable-prefix-caching` (with `--mamba-cache-mode align`), it cannot turn caching off; use `--no-enable-prefix-caching` in `EXTRA_ARGS` for that, as the timing rows do so their recorded pass is cold.
- `PREFIX_CACHE=1` with `MTP + CTX=huge` corrupts `prompt_logprobs` only (ordinary generation is unaffected).
- The KVarN profile runs `KVARN_FP16_DEQUANT=1`: KVarN's fused decode kernels dequantize in fp16 while the dots still accumulate in fp32, which halves their register pressure and is what lifts the long-context split-K decode - ~34% more decode at ~60K and ~53% at ~120K here, with prefill, VRAM and acceptance unchanged. It is part of vLLM's compile cache key, so the first boot after enabling it recompiles once (~3.5 min).
- Both profiles serve the int4-GPTQ head pair the base build runs (`lm_head` and the draft head, from a calibration pass over the fine-tune's own hidden states; the MTP module stays int8), so the fp8 profile now reads 22028 MiB peak at the standard 10k row, well inside the 22 GB budget. The port's first build kept every head at int8; on it the fp8 profile peaked at 22988 MiB (~460 MiB over the budget) and the KVarN profile at 22656 MiB (~128 MiB over). The requant also reads ~5% more decode at both ends and prefill flat, since less head weight is read per step.
- The checkpoint needs one config edit before it serves: its `quantization_config.ignore` blanket-blacklists the MTP head, which the prepare pipeline requantizes - see the port study above.
- Sampling is the checkpoint's own (`generation_config.json`: temperature 1.0, top_p 0.95, top_k 20) with no override in the served config; every other sampler setting is the vLLM default (min_p 0.0, repetition_penalty 1.0, presence/frequency penalty 0.0).

## Long-context refactor benchmark

The real-task long-context refactor prompts ([test-prompts.md](../../test-prompts.md)) - 79 repeats for the ~60K prompt, 157 for the ~120K one - same protocol as the recommended configs.

| Config | ctx | engine | drafter | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Swift-1.5-INT4-fast | 167936 | vLLM | on | ~60K | 1821 | **119.2** | 20674 MiB | `PTH_FA=1` int8 KV; accept 65.7% |
| Swift-1.5-INT4-fast | 167936 | vLLM | on | ~120K | 1328 | **91.9** | 20674 MiB | `PTH_FA=1` int8 KV; accept 59.8% |
| Swift-1.5-INT4-fast | 176128 | vLLM | on | ~60K | 1756 | **99.9** | 22030 MiB | fp8 KV; accept 58.5% |
| Swift-1.5-INT4-fast | 176128 | vLLM | on | ~120K | 1293 | **95.9** | 22030 MiB | fp8 KV; accept 68.9% |
| Swift-1.5-INT4-fast | 262144 | vLLM | on | ~60K | 1821 | **67.8** | 21856 MiB | KVarN k4v2 KV; accept 56.0% |
| Swift-1.5-INT4-fast | 262144 | vLLM | on | ~120K | 1429 | **53.9** | 21856 MiB | KVarN k4v2 KV; accept 58.9% |

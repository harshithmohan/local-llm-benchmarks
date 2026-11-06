# Qwen3.8-27B (Rig 2) - recommended configs

Updated: 2026-11-05 · [full experiment log](archive/qwen38-27b.md) · [methodology](../../methodology.md)

`W4A16-AutoRound-fast` (`qwen35` dense hybrid SSM + attention - only every 4th layer carries full attention, `full_attention_interval=4` - native ctx 262144, embedded MTP head). Dense, not a MoE, so no expert split applies. Runs on the [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) vLLM container (vLLM 0.32.0). Model card: [dbirks/Qwen3.8-27B-W4A16-AutoRound](https://huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound); the dense llama.cpp [unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) quant and the DFlash2 profile are archived. The Swift-1.5 fine-tune of this model is a separate model: [swift-qwen38-27b.md](swift-qwen38-27b.md).

Low-level knob transferability study: [../../experiments/qwen38-27b-da3dsoul-arc-transfer.md](../../experiments/qwen38-27b-da3dsoul-arc-transfer.md). Rig and setup: [../../rig2-3090.md](../../rig2-3090.md).

## Recommended configs

Three contexts: int8 KV at 167936 read by the pth-flash-attn kernel (4 chained MTP drafts) for the fastest decode - the deployed profile since 2026-11-05 - fp8 KV at 176128 (the same profile on the previous 0.31.0 image), and KVarN 4/2-bit KV at the native 262144 (3 chained drafts) for long requests.

| Config | ctx | engine | drafter | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | 167936 | vLLM | on | 2604 | **120.4** | 20580 MiB | `PTH_FA=1` int8 KV on the pth-flash-attn kernel; 4 drafts, `MAX_SEQS=4`; pool pinned 6.8 GB (173,207 tokens); `EMBED_UVA=1`; accept 47.7% - speed rows measured at 176128, 370 W, cold, 2026-11-05 |
| W4A16-AutoRound-fast | 176128 | vLLM | on | 2465 | **120.6** | 21870 MiB | fp8 KV; 4 drafts, `MAX_SEQS=4`; pool pinned 6.8 GB; `EMBED_UVA=1`; accept 61.9% |
| W4A16-AutoRound-fast | 262144 | vLLM | on | 2403 | **101.8** | 21756 MiB | KVarN k4v2 KV, 3 drafts; pool pinned 5.3 GB; `KVARN_FP16_DEQUANT=1`; `EMBED_UVA=1`; accept 60.3% |

All rows are served with `INT8_ACT=int8`.

## Configs

### W4A16-AutoRound-fast at 176128 - vLLM, fp8 KV, 4 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: CTX=long  MAX_LEN=176128  GPU_UTIL=0.88
    #      DRAFT_TOKENS=4  MAX_SEQS=4
    #      EXTRA_ARGS=--kv-cache-memory=6800000000
    #      INT8_ACT=int8  EMBED_UVA=1
    # sampling (model default, from generation_config.json): temperature 1.0, top_p 0.95, top_k 20

### W4A16-AutoRound-fast at 262144 - vLLM, KVarN 4/2-bit KV, 3 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: CTX=huge  MAX_LEN=262144  GPU_UTIL=0.88
    #      EXTRA_ARGS=--kv-cache-memory=5300000000
    #      INT8_ACT=int8  KVARN_FP16_DEQUANT=1  EMBED_UVA=1
    # sampling (model default, from generation_config.json): temperature 1.0, top_p 0.95, top_k 20

### PTH_FA A/B - int8 KV on the pth-flash-attn kernel (2026-11-05, 0.32.0 image)

Same rig, same image (`7592fbbb4e17`, vLLM 0.32.0), 370 W, `DRAFT_TOKENS=4`, `VISION=1`, `INT8_ACT=int8`, one cold boot per arm at `MAX_LEN=176128` (the A/B predates the window cut), two passes per prompt and the second recorded. Prefix caching was off in both arms (`--no-enable-prefix-caching`, `cached_tokens` 0 on every row) so the passes are cold.

| Arm | prompt | prefill t/s | decode t/s | accept | VRAM |
| --- | --- | --- | --- | --- | --- |
| fp8 on FlashInfer | 10k | 2536 | 116.5 | 61.9% | 21394 MiB |
| fp8 on FlashInfer | ~60K | 1843 | 119.7 | 71.4% | 21394 MiB |
| fp8 on FlashInfer | ~120K | 1316 | 93.7 | 61.3% | 21394 MiB |
| `PTH_FA=1` | 10k | 2604 | **120.4** | 47.7% | 20574 MiB |
| `PTH_FA=1` | ~60K | 1912 | **132.0** | 68.1% | 20574 MiB |
| `PTH_FA=1` | ~120K | 1424 | **106.6** | 66.9% | 20574 MiB |

Decode +3.3% at 10k, +10.3% at ~60K and +13.8% at ~120K; prefill +2.7% / +3.7% / +8.2%; VRAM 820 MiB lower and load 306 s -> 256 s. Acceptance differs only within the sampling noise of one boot per arm (the two arms ran different draft sequences), so it is not evidence of a drafter change. The direction and size match upstream's own 3090 A/B at k=3 without vision (+12.2% at ~66k, +14.0% at ~100k), which is why the k=4 + vision arm was kept.

Deployment note: the profile is deployed at **167936**, not 176128. With `PTH_FA=1` the int8/`CUSTOM` path plus prefix-cache mamba alignment (`--mamba-cache-mode align`) leaves 6.31 GiB for KV against the 6.38 GiB that 176128 needs, and the engine refuses to boot; at 167936 the pool is 173,207 tokens (1.03x concurrency for a full-window request). Prefix caching on that backend was re-checked after the bump: 58,240 of 59,751 tokens cached on a re-send at ~60K and 118,144 of 119,293 at ~120K.

## Notes

- Both profiles pin the KV pool by bytes (`EXTRA_ARGS=--kv-cache-memory=...`): `KV_MEM` is not read on the MTP branch, and auto-sizing floats with free desktop memory.
- Both profiles run `EMBED_UVA=1`: the quantized embedding sits in pinned host RAM behind a CUDA UVA view, which frees ~1.1 GiB of card memory at no decode cost. That free memory is what pays for the larger pools - the fp8 pool needs ~6.7 GB to boot at 176128.
- `PTH_FA=1` is refused unless `SPEC=mtp`/`dflash2` with `CTX=long`, and with a KV tier or any of `--attention-backend`/`--kv-cache-dtype`/`--speculative-config` in `EXTRA_ARGS`. It never auto-enables for these profiles: the 8.6 default also requires `DRAFT_TOKENS` unset or 3 and `VISION` off, both of which the served env files contradict, so it is set explicitly.
- `CTX=long` (fp8) needs `MAX_SEQS=4`: at the default 8 the 4-draft spec buffers push the pool below 176128 and the engine refuses to boot.
- The KVarN profile serves the model's native 262144; vLLM refuses 290000 unless `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` (risks NaN beyond native RoPE).
- vLLM's automatic prefix caching is ON by default in these profiles - the image's `PREFIX_CACHE` env only *adds* `--enable-prefix-caching` (with `--mamba-cache-mode align`), it cannot turn caching off; use `--no-enable-prefix-caching` in `EXTRA_ARGS` for that, as the timing rows do so their recorded pass is cold.
- `PREFIX_CACHE=1` with `MTP + CTX=huge` corrupts `prompt_logprobs` only (ordinary generation is unaffected).
- The KVarN profile runs `KVARN_FP16_DEQUANT=1`: KVarN's fused decode kernels dequantize in fp16 while the dots still accumulate in fp32, which halves their register pressure and is what lifts the long-context split-K decode - ~26% more decode at ~60K and ~38% at ~120K here, with prefill, VRAM and acceptance unchanged. It is part of vLLM's compile cache key, so the first boot after enabling it recompiles once (~3.5 min).
- Sampling is the checkpoint's own (`generation_config.json`: temperature 1.0, top_p 0.95, top_k 20) with no override in the served config; every other sampler setting is the vLLM default (min_p 0.0, repetition_penalty 1.0, presence/frequency penalty 0.0).

## Long-context refactor benchmark

The real-task long-context refactor prompts ([test-prompts.md](../../test-prompts.md)) - 79 repeats for the ~60K prompt, 157 for the ~120K one - same protocol as the recommended configs.

| Config | ctx | engine | drafter | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | 176128 | vLLM | on | ~60K | 1828 | **86.7** | 21870 MiB | fp8 KV; accept 46.6% |
| W4A16-AutoRound-fast | 176128 | vLLM | on | ~120K | 1311 | **91.3** | 21870 MiB | fp8 KV; accept 63.1% |
| W4A16-AutoRound-fast | 262144 | vLLM | on | ~60K | 1877 | **64.0** | 21756 MiB | KVarN k4v2 KV; accept 47.1% |
| W4A16-AutoRound-fast | 262144 | vLLM | on | ~120K | 1438 | **49.2** | 21758 MiB | KVarN k4v2 KV; accept 49.8% |

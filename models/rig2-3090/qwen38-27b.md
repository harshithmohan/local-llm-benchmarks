# Qwen3.8-27B (Rig 2) - recommended configs

Updated: 2026-10-12 · [full experiment log](archive/qwen38-27b.md) · [methodology](../../methodology.md)

`W4A16-AutoRound-fast` (`qwen35` dense hybrid SSM + attention - only every 4th layer
carries full attention, `full_attention_interval=4` - native ctx 262144, embedded MTP head).
Dense, not a MoE, so no expert split applies. Runs on the
[syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) vLLM container (vLLM 0.31.0).
Model card: [dbirks/Qwen3.8-27B-W4A16-AutoRound](https://huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound);
the dense llama.cpp [unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF)
quant and the DFlash2 profile are archived. The Swift-1.5 fine-tune of this model is a
separate model: [swift-qwen38-27b.md](swift-qwen38-27b.md).

Low-level knob transferability study:
[../../experiments/qwen38-27b-da3dsoul-arc-transfer.md](../../experiments/qwen38-27b-da3dsoul-arc-transfer.md).
Rig and setup: [../../rig2-3090.md](../../rig2-3090.md).

## Recommended configs

Two contexts: fp8 KV at 176128 (4 chained MTP drafts) for the fastest decode, and
KVarN 4/2-bit KV at the native 262144 (3 chained drafts) for long requests.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
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

### W4A16-AutoRound-fast at 262144 - vLLM, KVarN 4/2-bit KV, 3 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: CTX=huge  MAX_LEN=262144  GPU_UTIL=0.88
    #      EXTRA_ARGS=--kv-cache-memory=5300000000
    #      INT8_ACT=int8  KVARN_FP16_DEQUANT=1  EMBED_UVA=1

## Notes

- Both profiles pin the KV pool by bytes (`EXTRA_ARGS=--kv-cache-memory=...`): `KV_MEM` is
  not read on the MTP branch, and auto-sizing floats with free desktop memory.
- Both profiles run `EMBED_UVA=1`: the quantized embedding sits in pinned host RAM behind a
  CUDA UVA view, which frees ~1.1 GiB of card memory at no decode cost. That free memory is
  what pays for the larger pools - the fp8 pool needs ~6.7 GB to boot at 176128.
- `CTX=long` (fp8) needs `MAX_SEQS=4`: at the default 8 the 4-draft spec buffers push the
  pool below 176128 and the engine refuses to boot.
- The KVarN profile serves the model's native 262144; vLLM refuses 290000 unless
  `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` (risks NaN beyond native RoPE).
- vLLM's automatic prefix caching is ON by default in these profiles - the image's
  `PREFIX_CACHE` env only *adds* `--enable-prefix-caching` (with `--mamba-cache-mode align`),
  it cannot turn caching off; use `--no-enable-prefix-caching` in `EXTRA_ARGS` for that, as
  the timing rows do so their recorded pass is cold.
- `PREFIX_CACHE=1` with `MTP + CTX=huge` corrupts `prompt_logprobs` only (ordinary generation
  is unaffected).
- The KVarN profile runs `KVARN_FP16_DEQUANT=1`: KVarN's fused decode kernels dequantize in
  fp16 while the dots still accumulate in fp32, which halves their register pressure and is
  what lifts the long-context split-K decode - ~26% more decode at ~60K and ~38% at ~120K
  here, with prefill, VRAM and acceptance unchanged. It is part of vLLM's compile cache key,
  so the first boot after enabling it recompiles once (~3.5 min).

## Long-context refactor benchmark

The real-task long-context refactor prompts ([test-prompts.md](../../test-prompts.md)) - 79
repeats for the ~60K prompt, 157 for the ~120K one - same protocol as the recommended configs.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | 176128 | vLLM | on | ~60K | 1610 | **86.7** | 21870 MiB | fp8 KV; accept 46.6% |
| W4A16-AutoRound-fast | 176128 | vLLM | on | ~120K | 1130 | **91.3** | 21870 MiB | fp8 KV; accept 63.1% |
| W4A16-AutoRound-fast | 262144 | vLLM | on | ~60K | 1686 | **64.0** | 21756 MiB | KVarN k4v2 KV; accept 47.1% |
| W4A16-AutoRound-fast | 262144 | vLLM | on | ~120K | 1235 | **49.2** | 21758 MiB | KVarN k4v2 KV; accept 49.8% |

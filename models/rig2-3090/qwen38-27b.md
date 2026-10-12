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

Two contexts: fp8 KV at 150000 (4 chained MTP drafts) for the fastest decode, and
KVarN 4/2-bit KV at 250000 (3 chained drafts) for long requests.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | 150000 | vLLM | on | 2472 | **108.9** | 22188 MiB | fp8 KV; 4 drafts, `MAX_SEQS=4`; pool pinned 5.8 GB |
| W4A16-AutoRound-fast | 250000 | vLLM | on | 2383 | **92.9** | 22056 MiB | KVarN k4v2 KV, 3 drafts; pool pinned 4.2 GB; `KVARN_FP16_DEQUANT=1` |

All rows are served with `INT8_ACT=int8`.

## Configs

### W4A16-AutoRound-fast at 150000 - vLLM, fp8 KV, 4 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: CTX=long  MAX_LEN=150000  GPU_UTIL=0.88
    #      DRAFT_TOKENS=4  MAX_SEQS=4
    #      EXTRA_ARGS=--kv-cache-memory=5800000000
    #      INT8_ACT=int8

### W4A16-AutoRound-fast at 250000 - vLLM, KVarN 4/2-bit KV, 3 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: CTX=huge  MAX_LEN=250000  GPU_UTIL=0.88
    #      EXTRA_ARGS=--kv-cache-memory=4200000000
    #      INT8_ACT=int8  KVARN_FP16_DEQUANT=1

## Notes

- Both profiles pin the KV pool by bytes (`EXTRA_ARGS=--kv-cache-memory=...`): `KV_MEM` is
  not read on the MTP branch, and auto-sizing floats with free desktop memory.
- `CTX=long` (fp8) needs `MAX_SEQS=4`: at the default 8 the 4-draft spec buffers push the
  pool below 150000 and the engine refuses to boot.
- 250000 is just under the native 262144; vLLM refuses 290000 unless
  `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` (risks NaN beyond native RoPE).
- vLLM's automatic prefix caching is ON by default in these profiles - the image's
  `PREFIX_CACHE` env only *adds* `--enable-prefix-caching` (with `--mamba-cache-mode align`),
  it cannot turn caching off; use `--no-enable-prefix-caching` in `EXTRA_ARGS` for that, as
  the timing rows do so their recorded pass is cold.
- `PREFIX_CACHE=1` with `MTP + CTX=huge` corrupts `prompt_logprobs` only (ordinary generation
  is unaffected).
- The 250000 profile runs `KVARN_FP16_DEQUANT=1`: KVarN's fused decode kernels dequantize in
  fp16 while the dots still accumulate in fp32, which halves their register pressure and is
  what lifts the long-context split-K decode - ~26% more decode at ~60K and ~38% at ~120K
  here, with prefill, VRAM and acceptance unchanged. It is part of vLLM's compile cache key,
  so the first boot after enabling it recompiles once (~3.5 min).

## Long-context refactor benchmark

The real-task long-context refactor prompts ([test-prompts.md](../../test-prompts.md)) - 79
repeats for the ~60K prompt, 157 for the ~120K one - same protocol as the recommended configs.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W4A16-AutoRound-fast | 150000 | vLLM | on | ~60K | 1609 | **105.6** | 22188 MiB | fp8 KV |
| W4A16-AutoRound-fast | 150000 | vLLM | on | ~120K | 1129 | **91.6** | 22190 MiB | fp8 KV |
| W4A16-AutoRound-fast | 250000 | vLLM | on | ~60K | 1680 | **69.0** | 22056 MiB | KVarN k4v2 KV |
| W4A16-AutoRound-fast | 250000 | vLLM | on | ~120K | 1171 | **51.3** | 22056 MiB | KVarN k4v2 KV |

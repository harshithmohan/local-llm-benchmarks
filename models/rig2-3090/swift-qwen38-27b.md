# Swift-1.5-Qwen3.8-27B (Rig 2) - recommended configs

Updated: 2026-10-12 · [full experiment log](archive/swift-qwen38-27b.md) · [methodology](../../methodology.md)

`Swift-1.5-INT4`, the Swift-1.5 fine-tune of Qwen3.8-27B (`qwen35` dense hybrid SSM +
attention - only every 4th layer carries full attention, `full_attention_interval=4` -
native ctx 262144, embedded MTP head). Dense, not a MoE, so no expert split applies. Served
on the same [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) vLLM container (vLLM
0.31.0) as the base model. The served build is `Swift-1.5-INT4-fast`: the port's int8 heads
requantized to the same int4-GPTQ `lm_head` and draft head the base build runs, which brings
the profile inside the rig's VRAM budget (the step the port skipped - experiment 6 of the port
study). Model card:
[ukisai/Swift-1.5-Qwen3.8-27b-INT4](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b-INT4).
The base `W4A16-AutoRound-fast` quant is a separate model: [qwen38-27b.md](qwen38-27b.md).

Fine-tune port study (checkpoint preparation, not engine tuning):
[../../experiments/qwen38-27b-swift-1.5-int4.md](../../experiments/qwen38-27b-swift-1.5-int4.md).
Rig and setup: [../../rig2-3090.md](../../rig2-3090.md).

## Recommended configs

Two contexts: fp8 KV at 150000 (4 chained MTP drafts) for the fastest decode, and
KVarN 4/2-bit KV at 250000 (3 chained drafts) for long requests.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Swift-1.5-INT4-fast | 150000 | vLLM | on | 2460 | **121.0** | 22188 MiB | fp8 KV; 4 drafts, `MAX_SEQS=4`; pool pinned 5.8 GB |
| Swift-1.5-INT4-fast | 250000 | vLLM | on | 2377 | **102.7** | 21918 MiB | KVarN k4v2 KV, 3 drafts; pool pinned 4.2 GB; `KVARN_FP16_DEQUANT=1` |

All rows are served with `INT8_ACT=int8`.

## Configs

### Swift-1.5-INT4-fast at 150000 - vLLM, fp8 KV, 4 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: MODEL=Swift-1.5-INT4-fast  CTX=long  MAX_LEN=150000  GPU_UTIL=0.88
    #      DRAFT_TOKENS=4  MAX_SEQS=4
    #      EXTRA_ARGS=--kv-cache-memory=5800000000
    #      INT8_ACT=int8

### Swift-1.5-INT4-fast at 250000 - vLLM, KVarN 4/2-bit KV, 3 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: MODEL=Swift-1.5-INT4-fast  CTX=huge  MAX_LEN=250000  GPU_UTIL=0.88
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
  what lifts the long-context split-K decode - ~34% more decode at ~60K and ~53% at ~120K
  here, with prefill, VRAM and acceptance unchanged. It is part of vLLM's compile cache key,
  so the first boot after enabling it recompiles once (~3.5 min).
- Both profiles serve the int4-GPTQ head pair the base build runs (`lm_head` and the draft
  head, from a calibration pass over the fine-tune's own hidden states; the MTP module stays
  int8), so the 150000 profile now reads 22188 MiB peak at the standard 10k row - the base
  quant's footprint, ~340 MiB under the 22 GB budget. The port's first build kept every head
  at int8; on it the fp8 profile peaked at 22988 MiB (~460 MiB over the budget) and the KVarN
  profile at 22656 MiB (~128 MiB over). The requant also reads ~5% more decode at both ends
  and prefill flat, since less head weight is read per step.
- The checkpoint needs one config edit before it serves: its `quantization_config.ignore`
  blanket-blacklists the MTP head, which the prepare pipeline requantizes - see the port
  study above.

## Long-context refactor benchmark

The real-task long-context refactor prompts ([test-prompts.md](../../test-prompts.md)) - 79
repeats for the ~60K prompt, 157 for the ~120K one - same protocol as the recommended configs.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Swift-1.5-INT4-fast | 150000 | vLLM | on | ~60K | 1604 | **108.5** | 22190 MiB | fp8 KV |
| Swift-1.5-INT4-fast | 150000 | vLLM | on | ~120K | 1126 | **95.5** | 22190 MiB | fp8 KV |
| Swift-1.5-INT4-fast | 250000 | vLLM | on | ~60K | 1674 | **71.4** | 21918 MiB | KVarN k4v2 KV |
| Swift-1.5-INT4-fast | 250000 | vLLM | on | ~120K | 1229 | **52.9** | 21918 MiB | KVarN k4v2 KV |

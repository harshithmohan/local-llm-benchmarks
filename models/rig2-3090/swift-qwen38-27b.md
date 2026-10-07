# Swift-1.5-Qwen3.8-27B (Rig 2) - recommended configs

Updated: 2026-09-30 · [full experiment log](archive/swift-qwen38-27b.md) · [methodology](../../methodology.md)

`Swift-1.5-INT4`, the Swift-1.5 fine-tune of Qwen3.8-27B (`qwen35` dense hybrid SSM +
attention - only every 4th layer carries full attention, `full_attention_interval=4` -
native ctx 262144, embedded MTP head). Dense, not a MoE, so no expert split applies. Served
on the same [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) vLLM container (vLLM
0.29.0) as the base model. Model card:
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
| Swift-1.5-INT4 | 150000 | vLLM | on | 2417 | **116.9** | 22510 MiB | fp8 KV; 4 drafts, `MAX_SEQS=4`; pool pinned 5.8 GB |
| Swift-1.5-INT4 | 250000 | vLLM | on | 2394 | **94.3** | 22052 MiB | KVarN k4v2 KV, 3 drafts; pool pinned 4.2 GB |

All rows are served with `INT8_ACT=int8`.

## Configs

### Swift-1.5-INT4 at 150000 - vLLM, fp8 KV, 4 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: MODEL=Swift-1.5-INT4  CTX=long  MAX_LEN=150000  GPU_UTIL=0.88
    #      DRAFT_TOKENS=4  MAX_SEQS=4
    #      EXTRA_ARGS=--kv-cache-memory=5800000000
    #      INT8_ACT=int8

### Swift-1.5-INT4 at 250000 - vLLM, KVarN 4/2-bit KV, 3 MTP drafts

    docker run --gpus all --ipc host \
      --env-file <env> \
      -v <models>:/app/models \
      ghcr.io/syv-ai/hyperqwen:latest single

    # env: MODEL=Swift-1.5-INT4  CTX=huge  MAX_LEN=250000  GPU_UTIL=0.88
    #      EXTRA_ARGS=--kv-cache-memory=4200000000
    #      INT8_ACT=int8

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
- Swift-1.5-INT4 runs ~520 MiB heavier than the base quant at 150000 (22510 vs 21992 MiB) -
  ~18 MiB under the 22528 cap.
- The checkpoint needs one config edit before it serves: its `quantization_config.ignore`
  blanket-blacklists the MTP head, which the prepare pipeline requantizes - see the port
  study above.

## Long-context refactor benchmark

The real-task long-context refactor prompts ([test-prompts.md](../../test-prompts.md)) - 79
repeats for the ~60K prompt, 157 for the ~120K one - same protocol as the recommended configs.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Swift-1.5-INT4 | 150000 | vLLM | on | ~60K | 1610 | **99.1** | 22510 MiB | fp8 KV |
| Swift-1.5-INT4 | 150000 | vLLM | on | ~120K | 1110 | **91.1** | 22828 MiB | fp8 KV |
| Swift-1.5-INT4 | 250000 | vLLM | on | ~60K | 1694 | **51.2** | 22052 MiB | KVarN k4v2 KV |
| Swift-1.5-INT4 | 250000 | vLLM | on | ~120K | 1192 | **38.7** | 22554 MiB | KVarN k4v2 KV |

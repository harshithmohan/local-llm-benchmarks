# Qwen3.8-27B (Rig 1) - recommended configs

Updated: 2026-09-30 · [full experiment log](archive/qwen38-27b.md) · [methodology](../../methodology.md)

`IQ2_XS` of the **Swift-1.5 fine-tune** (`qwen35`, native ctx 262144, embedded MTP head).
Dense hybrid SSM + attention - only every 4th layer carries full attention
(`full_attention_interval=4`) - and not a MoE, so no expert split applies. Model card:
[ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF) (`IQ2_XS`).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IQ2_XS | 81920 | stock | on | 467 | **35.6** | 11474 MiB | q4_0 KV; default `-b/-ub` |

## Configs

### IQ2_XS (Swift-1.5 fine-tune) at 81920 - stock, q4_0 KV + MTP

    llama-server --port PORT \
      -m <models>/Swift-1.5-Qwen3.8-27B-GSQ-RCO-IQ2_XS.gguf \
      --ctx-size 81920 -ngl all -fit off \
      --cache-type-k q4_0 --cache-type-v q4_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0

`-b/-ub` and sampling are the server defaults.

## Notes

- **q4_0 KV.** The native 262144 window does not fit the 12 GB cap; q4_0 KV is what reaches 80k.
- **`-ub` is capped by the 12 GB cap.** Raising it does not raise prefill, and `-ub ≥ 2048`
  fails to allocate compute buffers (OOM) at 80k with q4_0 KV.

## Long-context refactor benchmark (~60K prompt)

The real-task ~60K refactor prompt ([test-prompts.md](../../test-prompts.md)), same protocol
as the recommended configs.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IQ2_XS | 81920 | stock | on | 383 | **24.4** | 11472 MiB | q4_0 KV |

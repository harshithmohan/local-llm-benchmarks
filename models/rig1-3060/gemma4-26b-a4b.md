# Gemma4-26B-A4B (Rig 1) - recommended configs

Updated: 2026-10-01 · [full experiment log](archive/gemma4-26b-a4b.md) · [methodology](../../methodology.md)

`Q4_K_M` (`gemma4` arch, native ctx 262144, MTP draft head). Model card:
[HauhauCS/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-MTP](https://huggingface.co/HauhauCS/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-MTP) (`Q4_K_M`).

**This model is not useful for coding on Rig 1; the recommended config below is tuned for
chatting, not coding.**

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q4_K_M | 32768 | moe-cache fork | on | 937 | **68** | 11468 MiB | chatting (not coding), cache 72, `-b/-ub 1024` |

## Configs

### Q4_K_M 32k (chat) - moe-cache fork, cache 72 + MTP

    llama-server --port PORT \
      -m <models>/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-Q4_K_M.gguf \
      --spec-draft-model <models>/mtp-gemma-4-26B-A4B-it.gguf \
      --ctx-size 32768 -ngl all -fit off \
      --moe-expert-cache-size 72 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 1024 -ub 1024 \
      --temp 0.6 --top-p 0.9 --top-k 64 --repeat-penalty 1.1

## Long-context refactor benchmark

Not applicable to the 32k chat config (the model is not used for coding here); the
non-chat 256k measurement lives in the [archive](archive/gemma4-26b-a4b.md).

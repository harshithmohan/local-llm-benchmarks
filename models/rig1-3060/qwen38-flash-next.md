# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-09-29 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`UD-IQ3_XXS` (`qwen4exp`, native ctx 262144, separate shared MTP head). 177B total =
125B compute + 51B n-gram embedding table + 4B MTP; 48 layers =
12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 512 experts
(10 routed + 1 shared). Model cards:
[unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF) (`UD-*` quants).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ3_XXS | 81920 | moe-cache fork | off | 362 | **21.4** | 11496 MiB | cache 48, `-b/-ub 1024` |

## Configs

### UD-IQ3_XXS 80k - moe-cache fork, cache 48 + `-b/-ub 1024`

    llama-server --port PORT \
      -m <models>/Qwen3.8-Flash-Next-UD-IQ3_XXS-00001-of-00003.gguf \
      --ctx-size 81920 -ngl all -fit off \
      --moe-expert-cache-size 48 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --lazy-mode on --no-mmproj-offload --threads 12 --parallel 1 \
      --backend-sampling --decode-overlap --decode-boundary-overlap \
      --cache-ram 0 \
      -b 1024 -ub 1024 \
      --temp 1.0 --top-k 20 --min-p 0.0

## Notes

- **MTP is off.** The shared MTP head does not fit alongside the expert cache at 12 GB.
- **`--load-mode none` and `--lazy-mode on` are required.**

## Long-context refactor benchmark (~60K prompt)

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) ~60K-token Python
file of 79 near-identical legacy templates. Same protocol as the recommended configs
([methodology.md](../../methodology.md) §Measurement methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ3_XXS | 81920 | moe-cache fork | off | 341 | **13.1** | 11492 MiB | cache 48, `-b/-ub 1024` |

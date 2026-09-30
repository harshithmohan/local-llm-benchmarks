# Gemma4-26B-A4B (Rig 1) - recommended configs

Updated: 2026-09-30 · [full experiment log](archive/gemma4-26b-a4b.md) · [methodology](../../methodology.md)

`Q4_K_M` (`gemma4` arch, native ctx 262144, MTP draft head). Model card:
[HauhauCS/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-MTP](https://huggingface.co/HauhauCS/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-MTP) (`Q4_K_M`).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q4_K_M | 262144 | moe-cache fork | on | 1623 | **52** | 10409 MiB | cache 44, `-b/-ub 4096` |

## Configs

### Q4_K_M 256k - moe-cache fork, cache 44 + MTP

    llama-server --port PORT \
      -m <models>/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-Q4_K_M.gguf \
      --spec-draft-model <models>/mtp-gemma-4-26B-A4B-it.gguf \
      --ctx-size 262144 -ngl all -fit off \
      --moe-expert-cache-size 44 \
      --moe-early-router --phase-aware-workspace --live-context-workspace \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 4096 -ub 4096 \
      --temp 0.6 --top-p 0.9 --top-k 64 --repeat-penalty 1.1

## Notes

- Native context is 262144, so no `--rope-scaling` is needed.
- While the expert cache is enabled it overrides `--n-cpu-moe` placement, so the command
  sets no `--n-cpu-moe` (a cache-off control is `--moe-expert-cache-size 0` plus manual
  placement).
- `--moe-early-router --phase-aware-workspace --live-context-workspace` must stay together
  at this config: any subset fails to fit at cache 44 / `-b/-ub 4096` (see the archive).
- The MTP draft head ships as a separate `mtp-` GGUF and shares the target KV cache; the
  q8_0 draft KV keeps acceptance at ~0.6-0.7.

## Long-context refactor benchmark (~60K prompt)

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) ~60K-token Python
file of 79 near-identical legacy templates. Same protocol as the recommended configs
([methodology.md](../../methodology.md) §Measurement methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q4_K_M | 262144 | moe-cache fork | on | 1278 | **35.5** | 10857 MiB | cache 44 |

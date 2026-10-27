# Cyber-Tiel-Coder-35B-A3B (Rig 1) - recommended configs

Updated: 2026-10-27 · [full experiment log](archive/cybertiel-35b-a3b.md) · [methodology](../../methodology.md)

`UD-IQ4_XS` (`qwen35moe` arch, native ctx 262144, embedded MTP head, 16.9 GiB + 883 MiB BF16 mmproj). Model card: [peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF-MTP](https://huggingface.co/peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF-MTP).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ4_XS | 262144 | moe-cache fork | on | 2201 | **64.2** | 11626 MiB | cache 76 + `--phase-aware-workspace`, `-b/-ub 6144` |

## Configs

### UD-IQ4_XS 256k - moe-cache fork, cache 76 + phase-aware workspace + MTP

    llama-server --port PORT \
      -m <models>/Cyber-Tiel-Coder-35B-A3B-MTP-UD-IQ4_XS.gguf \
      --mmproj <models>/mmproj-Cyber-Tiel-Coder-35B-A3B-BF16.gguf \
      --image-min-tokens 1024 \
      --ctx-size 262144 -ngl all -fit off \
      --moe-expert-cache-size 76 --phase-aware-workspace \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 6144 -ub 6144 \
      --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --presence-penalty 0.0 --repeat-penalty 1.0

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)): a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement methods): q8_0 KV, cold load per prompt.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ4_XS | 262144 | moe-cache fork | on | ~60K | 1768 | **52.5** | 11624 MiB | 59751-token prompt, cache 76 + phase-aware |
| UD-IQ4_XS | 262144 | moe-cache fork | on | ~120K | 1364 | **42.8** | 11624 MiB | 119293-token prompt, cache 76 + phase-aware |

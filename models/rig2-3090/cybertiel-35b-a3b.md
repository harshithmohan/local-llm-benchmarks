# Cyber-Tiel-Coder-35B-A3B (Rig 2) - recommended configs

Updated: 2026-10-27 · [full experiment log](archive/cybertiel-35b-a3b.md) · [methodology](../../methodology.md)

`UD-Q4_K_XL` (`qwen35moe` arch, native ctx 262144, embedded MTP head, 21.19 GiB + 883 MiB BF16 mmproj). Model card: [peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF-MTP](https://huggingface.co/peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF-MTP).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-Q4_K_XL | 262144 | moe-cache fork | on | 3766 | **148.9** | 21260 MiB | cache 192 + `--phase-aware-workspace`, `-b/-ub 4096` |

## Configs

### UD-Q4_K_XL 256k - moe-cache fork, cache 192 + phase-aware workspace + MTP

    llama-server --port PORT \
      -m <models>/Cyber-Tiel-Coder-35B-A3B-MTP-UD-Q4_K_XL.gguf \
      --mmproj <models>/mmproj-Cyber-Tiel-Coder-35B-A3B-BF16.gguf \
      --image-min-tokens 1024 \
      --ctx-size 262144 -ngl 999 \
      --moe-expert-cache-size 192 --phase-aware-workspace \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 8 --parallel 1 \
      --reasoning-preserve \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 4096 -ub 4096 \
      --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --presence-penalty 0.0 --repeat-penalty 1.0

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)): a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement methods): q8_0 KV, cold load per prompt.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UD-Q4_K_XL | 262144 | moe-cache fork | on | ~60K | 3600 | **121.6** | 21254 MiB | 59751-token prompt, cache 192 + phase-aware |
| UD-Q4_K_XL | 262144 | moe-cache fork | on | ~120K | 2964 | **96.3** | 21254 MiB | 119293-token prompt, cache 192 + phase-aware |

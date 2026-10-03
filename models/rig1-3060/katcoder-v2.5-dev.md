# KAT-Coder-V2.5-Dev (Rig 1) - recommended configs

Updated: 2026-10-03 · [full experiment log](archive/katcoder-v2.5-dev.md) · [methodology](../../methodology.md)

`APEX-I-Compact` (`qwen35moe`, 41 blocks, 256 experts / 8 active, native ctx 262144,
embedded MTP head). Model card:
[gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF](https://huggingface.co/gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | 262144 | moe-cache fork | on | 1673 | **66** | 11774 MiB | cache 80, `-b/-ub 4096`, draft ubatch 3072 |

## Configs

### APEX-I-Compact 256k - moe-cache fork, cache 80 + MTP

    llama-server --port PORT \
      -m <models>/KAT-Coder-V2.5-Dev-MTP-APEX-I-Compact.gguf \
      --ctx-size 262144 -ngl all -fit off \
      --moe-expert-cache-size 80 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --spec-draft-ubatch-size 3072 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 4096 -ub 4096 \
      --temp 1.0 --top-k 20 --presence-penalty 1.5

## Notes

None - no model-specific caveats recorded for this quant. Shared fork behaviour (expert
cache overriding `--n-cpu-moe`, flag vocabulary) is in
[engine-notes/moe-cache-fork.md](../../engine-notes/moe-cache-fork.md).

## Long-context refactor benchmark (~60K prompt)

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) ~60K-token Python
file of 79 near-identical legacy templates. Same protocol as the recommended configs
([methodology.md](../../methodology.md) §Measurement methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | 262144 | moe-cache fork | on | 1434 | **51.6** | 11774 MiB | cache 80, `-b/-ub 4096`, draft ubatch 3072 |

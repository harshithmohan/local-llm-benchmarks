# KAT-Coder-V2.5-Dev (Rig 1) - recommended configs

Updated: 2026-10-08 · [full experiment log](archive/katcoder-v2.5-dev.md) · [methodology](../../methodology.md)

`APEX-I-Compact` (`qwen35moe`, 41 blocks, 256 experts / 8 active, native ctx 262144,
embedded MTP head). Model card:
[gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF](https://huggingface.co/gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | 262144 | moe-cache fork | on | 1534 | **71** | 10895 MiB | cache 88 + `--phase-aware-workspace`, `-b/-ub 3072` |

## Configs

### APEX-I-Compact 256k - moe-cache fork, cache 88 + phase-aware + MTP

    llama-server --port PORT \
      -m <models>/KAT-Coder-V2.5-Dev-MTP-APEX-I-Compact.gguf \
      --ctx-size 262144 -ngl all -fit off \
      --moe-expert-cache-size 88 --phase-aware-workspace \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 3072 -ub 3072 \
      --temp 1.0 --top-k 20 --presence-penalty 1.5

## Notes

- `--phase-aware-workspace` frees ~800 MiB on this model, which carries the expert cache from
  80 to 88 slabs (~+5% decode at both ~10K and ~60K, no prefill cost); 100/104 slabs load but
  OOM on the first request.
- This config runs `-b/-ub 3072`. `-b/-ub 4096` measured ~+6% prefill (~1624 t/s) at the same
  VRAM, but it is not adopted here: it changes the draft-context budget and has not been through
  the large-prompt stability check (see the `--spec-draft-ubatch-size` note in the fork pages).

Shared fork behaviour (expert cache overriding `--n-cpu-moe`, flag vocabulary) is in
[engine-notes/moe-cache-fork.md](../../engine-notes/moe-cache-fork.md).

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of
near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same
protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement
methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | 262144 | moe-cache fork | on | ~60K | 1343 | **54.1** | 10875 MiB | cache 88 + `--phase-aware-workspace`, `-b/-ub 3072` |
| APEX-I-Compact | 262144 | moe-cache fork | on | ~120K | 1107 | **45.7** | 10875 MiB | 119293-token prompt, cache 88 + `--phase-aware-workspace`, `-b/-ub 3072` |

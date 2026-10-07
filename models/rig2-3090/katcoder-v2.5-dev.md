# KAT-Coder-V2.5-Dev (Rig 2) - recommended configs

Updated: 2026-09-30 · [full experiment log](archive/katcoder-v2.5-dev.md) · [methodology](../../methodology.md)

`APEX-I-Compact` (`qwen35moe`, 41 blocks, 256 experts / 8 active, native ctx 262144,
embedded MTP head). Model card:
[gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF](https://huggingface.co/gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | 262144 | moe-cache fork | on | 4591 | **163** | 22204 MiB | cache 200 (max fit), `-b/-ub 12288` (~320 MiB headroom) |

## Configs

### APEX-I-Compact 256k - moe-cache fork, cache 200 + MTP, `-b/-ub 12288`

    llama-server --port PORT \
      -m <models>/KAT-Coder-V2.5-Dev-MTP-APEX-I-Compact.gguf \
      --ctx-size 262144 -ngl 999 --fit off \
      --moe-expert-cache-size 200 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 8 --parallel 1 \
      --reasoning-preserve \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 12288 -ub 12288 \
      --temp 1.0 --top-k 20 --presence-penalty 1.5

## Notes

- The expert cache is enabled (`--moe-expert-cache-size 200`); it overrides `--n-cpu-moe`
  placement.
- `-b/-ub 12288` is the prefill-maximizing ubatch; 16384 fails to load.
- Shared fork behaviour (flag vocabulary, `--experimental-logs` validation) is in
  [engine-notes/moe-cache-fork.md](../../engine-notes/moe-cache-fork.md).

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of
near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same
protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement
methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | 262144 | moe-cache fork | on | ~60K | 3701 | **126** | 22204 MiB | cache 200, `-b/-ub 12288` |
| APEX-I-Compact | 262144 | moe-cache fork | on | ~120K | 2812 | **85.6** | 22204 MiB | 119293-token prompt, cache 200, `-b/-ub 12288` |

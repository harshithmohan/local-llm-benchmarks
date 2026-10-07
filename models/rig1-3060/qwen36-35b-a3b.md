# Qwen3.6-35B-A3B (Rig 1) - recommended configs

Updated: 2026-09-29 · [full experiment log](archive/qwen36-35b-a3b.md) · [methodology](../../methodology.md)

`IQ4_XS-4.19bpw` (`qwen35moe` arch, native ctx 262144, embedded MTP head). Model card:
[byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | 262144 | moe-cache fork | on | 1909 | **76** | 11545 MiB | cache 64, `-b/-ub 6144` |
| IQ4_XS | 524288 (YaRN 2x) | moe-cache fork | off | 2063 | **52** | 11749 MiB | cache 48, `-b/-ub 6144` |

## Configs

### IQ4_XS 256k - moe-cache fork, cache 64 + MTP

    llama-server --port PORT \
      -m <models>/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      --ctx-size 262144 -ngl all -fit off \
      --moe-expert-cache-size 64 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 6144 -ub 6144 \
      --temp 0.6 --top-k 20 --min-p 0.0

### IQ4_XS 512K - moe-cache fork, cache 48, MTP off

    llama-server --port PORT \
      -m <models>/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      --ctx-size 524288 -ngl all -fit off \
      --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 \
      --moe-expert-cache-size 48 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      -b 6144 -ub 6144 \
      --temp 0.6 --top-k 20 --min-p 0.0

YaRN 2x - `--rope-scale` must equal ctx/262144 exactly (the command above uses 2).

## Notes

- Rare fork quirk: this prompt occasionally returns EOS as the first token (`predicted_n` 1,
  empty output) - a retry decodes normally; see [issues.md](../../issues.md) §8.

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of
near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same
protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement
methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | 262144 | moe-cache fork | on | ~60K | 1552 | **59.2** | 11551 MiB | cache 64 |
| IQ4_XS | 262144 | moe-cache fork | on | ~120K | 1230 | **45.3** | 11508 MiB | 119293-token prompt, cache 64 |
| IQ4_XS | 524288 | moe-cache fork | off | ~60K | 1693 | **40.8** | 11747 MiB | cache 48 |
| IQ4_XS | 524288 | moe-cache fork | off | ~120K | 1342 | **30.3** | 11708 MiB | 119293-token prompt, cache 48 |


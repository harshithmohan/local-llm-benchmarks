# Qwen3.6-35B-A3B (Rig 1) - recommended configs

Updated: 2026-10-08 · [full experiment log](archive/qwen36-35b-a3b.md) · [methodology](../../methodology.md)

`IQ4_XS-4.19bpw` (`qwen35moe` arch, native ctx 262144, embedded MTP head). Model card:
[byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | 262144 | moe-cache fork | on | 1761 | **83** | 10275 MiB | cache 80 + `--phase-aware-workspace`, `-b/-ub 6144` |
| IQ4_XS | 524288 (YaRN 2x) | moe-cache fork | off | 2063 | **52** | 11749 MiB | cache 48, `-b/-ub 6144` |

## Configs

### IQ4_XS 256k - moe-cache fork, cache 80 + phase-aware workspace + MTP

    llama-server --port PORT \
      -m <models>/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      --ctx-size 262144 -ngl all -fit off \
      --moe-expert-cache-size 80 --phase-aware-workspace \
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

- Tuning result (b11814): `--phase-aware-workspace` releases prompt-only workspace after the
  prompt phase (~1.9 GiB on the 12 GB card), lifting the expert-cache ceiling from 64 to 80
  slabs. At 10K that is decode **76 → 83** (median, 8 samples) for ~3% prefill; 88/96 slabs
  load but OOM on the first request (**80 is the ceiling**). The 256K rows were re-measured on
  b11814; the 512K rows are unchanged (b11608).
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
| IQ4_XS | 262144 | moe-cache fork | on | ~60K | 1429 | **62.5** | 10275 MiB | cache 80 + phase-aware |
| IQ4_XS | 262144 | moe-cache fork | on | ~120K | 1157 | **48.8** | 10275 MiB | 119293-token prompt, cache 80 + phase-aware |
| IQ4_XS | 524288 | moe-cache fork | off | ~60K | 1693 | **40.8** | 11747 MiB | cache 48 |
| IQ4_XS | 524288 | moe-cache fork | off | ~120K | 1342 | **30.3** | 11708 MiB | 119293-token prompt, cache 48 |

Near-full-window check: a ~250K-token prefill completes on both the cache-64 and the cache-80
configs with no OOM (prefill falls to ~830 t/s at the tail); it exceeds the usual timing window,
so it is a stability check, not a recorded decode row.

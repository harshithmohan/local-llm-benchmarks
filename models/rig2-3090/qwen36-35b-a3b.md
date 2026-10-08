# Qwen3.6-35B-A3B (Rig 2) - recommended configs

Updated: 2026-10-08 · [full experiment log](archive/qwen36-35b-a3b.md) · [methodology](../../methodology.md)

`UD-IQ4_XS` (`qwen35moe` arch, native ctx 262144, embedded MTP head). Model cards:
[unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(`UD-*` quants); [byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF) (`IQ4_XS-4.19bpw`).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ4_XS | 262144 | moe-cache fork | on | 4983 | **223** | 22946 MiB | cache 0 + `--phase-aware-workspace`, `-b/-ub 4096` |
| UD-IQ4_XS | 524288 | moe-cache fork | on | 3984 | **170** | 22714 MiB | YaRN 2x; cache 200 + `--phase-aware-workspace`, `-b/-ub 8192` |

The native 262144 window runs on GPU, q8_0 KV, no expert cache (with `--phase-aware-workspace`
to release prompt-only workspace before decode). The 524288 entry runs YaRN 2x; the window no
longer fits on GPU, so the expert cache keeps 200 slots/layer resident.

## Configs

### UD-IQ4_XS 256k - moe-cache fork, MTP on, `--phase-aware-workspace`, `-b/-ub 4096`

    llama-server --port PORT \
      -m <models>/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
      --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 8 --parallel 1 \
      --reasoning-preserve \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 4096 -ub 4096 \
      --phase-aware-workspace \
      --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0

### UD-IQ4_XS 512k (YaRN 2x) - moe-cache fork, MTP on, cache 200 + `--phase-aware-workspace`, `-b/-ub 8192`

    llama-server --port PORT \
      -m <models>/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
      --ctx-size 524288 -ngl 999 \
      --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 \
      --moe-expert-cache-size 200 \
      --phase-aware-workspace \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 8 --parallel 1 \
      --reasoning-preserve \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 8192 -ub 8192 \
      --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0

## Notes

- All experts run on GPU at 262144 (the default placement); set no expert-cache flag there -
  the cache has no CPU expert layers to build, and on this card it only costs decode when the
  model already fits (128/168 slabs: ~-25%/-15% vs cache 0).
- `--phase-aware-workspace` is the one free lever here: ~1.3 GiB freed at cache 0 on the 256k
  entry with no decode cost, and at 524288 it carries the cache 168 -> 200 (~+3% prefill /
  ~+4% decode at the same peak); cache 224 OOMs at load.
- At 524288 all experts no longer fit on GPU: `--moe-expert-cache-size 200` is required
  (the all-on-GPU config fails to load).
- `-b/-ub 4096` stays the 256k prefill ceiling: 6144/8192 do load with
  `--phase-aware-workspace` but add no prefill and push peak past the 22 GB budget (8192
  without the flag aborts).
- Rare moe-cache fork quirk: a 10k-prompt pass can occasionally return EOS as the first
  token (empty output); a retry decodes normally - see [issues.md](../../issues.md) §5.

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of
near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same
protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement
methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ4_XS | 262144 | moe-cache fork | on | ~60K | 3945 | **154.6** | 21980 MiB | cache 0 + `--phase-aware-workspace`, `-b/-ub 4096` |
| UD-IQ4_XS | 262144 | moe-cache fork | on | ~120K | 3083 | **113.2** | 21980 MiB | 119293-token prompt; cache 0 + `--phase-aware-workspace`, `-b/-ub 4096` |
| UD-IQ4_XS | 524288 | moe-cache fork | on | ~60K | 3591 | **129.7** | 22714 MiB | YaRN 2x; cache 200 + `--phase-aware-workspace`, `-b/-ub 8192` |
| UD-IQ4_XS | 524288 | moe-cache fork | on | ~120K | 2901 | **102.2** | 22714 MiB | 119293-token prompt; YaRN 2x, cache 200 + `--phase-aware-workspace`, `-b/-ub 8192` |

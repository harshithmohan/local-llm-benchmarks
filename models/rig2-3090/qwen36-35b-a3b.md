# Qwen3.6-35B-A3B (Rig 2) - recommended configs

Updated: 2026-09-30 · [full experiment log](archive/qwen36-35b-a3b.md) · [methodology](../../methodology.md)

`UD-IQ4_XS` (`qwen35moe` arch, native ctx 262144, embedded MTP head). Model cards:
[unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(`UD-*` quants); [byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF) (`IQ4_XS-4.19bpw`).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ4_XS | 262144 | moe-cache fork | on | 4686 | **214** | 22182 MiB | `-b/-ub 4096` (max prefill that fits; ~350 MiB headroom) |
| UD-IQ4_XS | 524288 | moe-cache fork | on | 3925 | **154** | 22230 MiB | YaRN 2x; cache 168, `-b/-ub 8192` |

The native 262144 window runs on GPU, q8_0 KV, no expert cache. The 524288 entry runs
YaRN 2x; the window no longer fits on GPU, so the expert cache keeps 168 slots/layer resident.

## Configs

### UD-IQ4_XS 256k - moe-cache fork, MTP on, `-b/-ub 4096`

    llama-server --port PORT \
      -m <models>/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
      --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 8 --parallel 1 \
      --reasoning-preserve \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 4096 -ub 4096 \
      --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0

### UD-IQ4_XS 512k (YaRN 2x) - moe-cache fork, MTP on, cache 168, `-b/-ub 8192`

    llama-server --port PORT \
      -m <models>/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
      --ctx-size 524288 -ngl 999 \
      --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 \
      --moe-expert-cache-size 168 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 8 --parallel 1 \
      --reasoning-preserve \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 8192 -ub 8192 \
      --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0

## Notes

- All experts run on GPU (the default placement); set no expert-cache flag, since the
  cache has no CPU expert layers to build here.
- At 524288 all experts no longer fit on GPU: `--moe-expert-cache-size 168` is required
  (the all-on-GPU config fails to load).
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
| UD-IQ4_XS | 262144 | moe-cache fork | on | ~60K | 3891 | **154.0** | 22182 MiB | `-b/-ub 4096` |
| UD-IQ4_XS | 262144 | moe-cache fork | on | ~120K | 2934 | **107.2** | 22340 MiB | 119293-token prompt, `-b/-ub 4096` |
| UD-IQ4_XS | 524288 | moe-cache fork | on | ~60K | 3587 | **131.2** | 22230 MiB | YaRN 2x; cache 168, `-b/-ub 8192` |
| UD-IQ4_XS | 524288 | moe-cache fork | on | ~120K | 2779 | **93.8** | 22608 MiB | 119293-token prompt; YaRN 2x, cache 168, `-b/-ub 8192` |

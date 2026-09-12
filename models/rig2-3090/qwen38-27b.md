# Qwen3.8-27B (Rig 2) - best configs

Dense 27B from the Qwen3.8 family (arch `qwen35`): hybrid SSM + attention, only every
4th layer full attention (`full_attention_interval=4`), embedded MTP head. Not a MoE,
so the Codacus fork has nothing to add - every row is stock. Native context 262144, but
155648 is the largest that loads under the 22 GB cap with q8_0 KV.

Rig details and setup: [../../rig2-3090.md](../../rig2-3090.md). Methodology:
[../../methodology.md](../../methodology.md). Full experiment log:
[qwen38-27b-archive.md](qwen38-27b-archive.md).
Model card: [unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF).

Same protocol as the rest of Rig 2: coding prompts C#+React averaged, second-pass
prefill, recommended sampling (temp 1.0, top_p 0.95, top_k 20, min_p 0.0,
presence_penalty 1.5), cold load, q8_0 KV, `--threads 8 --threads-batch 16`,
22 GB VRAM cap (desktop reserve).

## Measured results at c 155648 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV, stock)

| Quant | MTP | ncmoe | ctx | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| UD-Q4_K_S | on | n/a (dense) | 155648 | 1019.7 | **61.6** | 22127 MiB |

- Prefill 1019.7 and decode 61.6 vs the 35B-A3B winner (2375.8 / 165.1): this is a dense
  model, so every token runs all ~27B active params - the 35B MoE only wakes ~3B.
- MTP acceptance ~0.703 (mean len ~2.4) at n-max 2. `--spec-draft-n-max 2` is the decode
  peak (1-4 swept; see the archive).
- `ncmoe` is n/a: dense, no expert tensors to place on CPU. `--threads-batch` 8/16/32 is
  flat (long-prompt prefill within 0.5%), so the default 16 is kept.
- `-b`/`-ub` above 512 does not fit at this context (ub 2048 adds ~1.2 GiB of compute
  buffer with no headroom); `--threads` 6/8/12 is flat too. The winner stays on defaults.

## Best config per quant

### UD-Q4_K_S - winner (only quant tested)

    llama-server -m <models>/Qwen3.8-27B-UD-Q4_K_S.gguf \
      -ngl 999 --ctx-size 155648 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --reasoning-preserve --no-mmproj-offload \
      --threads 8 --threads-batch 16 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0

-> 61.6 t/s decode @ 155648 (prefill 1019.7, acceptance 0.703), 22127 MiB.

Tested on stock only, deliberately: the model is dense, so the fork's expert cache and
MoE prefill/prefetch patches have no expert tensors to act on.

## Alternatives (archived)

None - only one quant has been tested so far.

## Messy-code refactor benchmark

A deliberately messy ~116K-token refactor prompt, single run, winner config:

| Quant | MTP | ctx | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| UD-Q4_K_S | on | 155648 | 809.8 | 28.9 | 0.411 | 22440 MiB |

- Long context is expensive on this dense model: vs the short-prompt headline (1019.7 /
  61.6) prefill drops 21% and decode 53%, and MTP acceptance falls 0.703 -> 0.411
  (mean accepted run 1.82).
- The decode hit is larger than the 35B-A3B's on the same task (-37%): every token here
  runs ~27B dense params against a 116K context, while the MoE only wakes ~3B.
- Ran to the full 512 tokens (`finish_reason length`), no crash or early EOS.
- Total 22440 MiB at load (~88 MiB under the 22528 line); this run was in a desktop
  session using ~400 MiB, so the 155648 ceiling had almost no spare room.

## Key arch notes

- Hybrid SSM + attention: only ~16 of 65 layers own a growing KV cache
  (`full_attention_interval=4`), so context is much cheaper than a same-size dense
  transformer; the SSM state is constant-size.
- 4 KV heads x 256 key/value length; q8_0 KV costs ~0.045 MiB/token, which is why 155648
  (not the native 262144) is the ceiling under the 22 GB cap.
- Embedded MTP (`nextn_predict_layers=1`): no separate draft model needed. n-max 2 is
  the decode peak; VRAM rises ~150 MiB per extra draft token.
- KV type and load flags are settled: f16 KV runs at the same speed but halves the usable
  context (ceiling ~98304 vs 155648), and `--load-mode none` is a no-op steady-state, so
  q8_0 and the default load path stay.

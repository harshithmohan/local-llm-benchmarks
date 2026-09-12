# KAT-Coder-V2.5-Dev (Rig 1) - best configs

Coding-specialised model on the `qwen35moe` arch (same family as Qwen3.6-35B-A3B): 41
blocks, 256 experts / 8 active, native ctx 262144, embedded MTP head. Model card:
[gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF](https://huggingface.co/gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF).
Full experiment log: [katcoder-v2.5-dev-archive.md](katcoder-v2.5-dev-archive.md).
Methodology in [methodology](../../methodology.md); model-specific issues in
[issues](../../issues.md).

Quants tested: `APEX-I-Compact` (16.24 GiB, single file, Q4_K_M / file_type 15) - the only
quant on this rig.

## Measured results at c 262144 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV, stock)

| Quant | MTP | ncmoe | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | on | 28 | 338.5 | **47.7** | 11729 MiB |

All rows use the current protocol: coding prompts (C# ~192 tokens, React ~155 tokens)
averaged, second-pass measurement with slot prompt caching disabled (`cache_prompt:false`) so
the measure pass re-prefills instead of reusing the KV prefix (see the archive's method
note), recommended sampling (temp 1.0, top_p 0.95, top_k 20, min_p 0.0, presence_penalty
1.5), MTP n-max 2, cold load, stock binary. Prefill on these short prompts is batch-bound;
the same model prefills at 517 t/s on the ~116K messy prompt (below), which is the
saturated rate - compare prefill across pages only within the same prompt size.

Reading:

- ncmoe 28 is the lowest that fits at 262144 with MTP on (24/26/27 abort in the
  compute-buffer allocation, even at `-b 512 -ub 512`) and also the fastest measured (ncmoe
  32 loses ~14% decode for ~1.3 GB less VRAM).
- MTP is worth its ~2 GB draft context: with MTP off the config drops to ncmoe 24, but
  decode is still 45.2 vs 47.7, and short-prompt prefill rises to 391.9 (the draft compute
  is gone).
- The Codacus-fork expert cache was not probed: at ncmoe 28 only ~560 MiB is free, which is
  not enough for a pack (an all-CPU ncmoe + cache path is left for a future pass).

## Best config per quant

### APEX-I-Compact - winner (only quant on this rig)

Stock binary + MTP, full 256k:

    llama-server -m <models>/KAT-Coder-V2.5-Dev-MTP-APEX-I-Compact.gguf \
      --n-cpu-moe 28 --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --reasoning-preserve

-> 47.7 t/s decode @ 262144 (prefill 338.5 short-prompt / 517 on the ~116K messy prompt,
acceptance 0.71), 11729 MiB. Stock is the config as tested; the fork has no measured
advantage here (the cache is the fork's differentiator and it does not fit at ncmoe 28).

## Alternatives (archived)

Leaner or slower splits, all at c 262144 (full ladder and numbers in the archive):

- MTP off, ncmoe 24 - 45.2 t/s decode / 391.9 short-prompt prefill, 10963 MiB: the leanest
  config if VRAM must be shared, at ~5% decode cost.
- MTP off, ncmoe 28 - 42.5 decode, 9647 MiB.
- MTP on, ncmoe 32 - 40.9 decode, 10411 MiB (more CPU experts, less VRAM).

## Messy-code refactor benchmark (real-task ~116K prompt, single-pass)

One-time real-task speed test of the messy-code refactor prompt (see
[test-prompts.md](../../test-prompts.md), 116,257 prompt tokens), winner config, q8_0 KV,
cold load, single-run protocol (ONE timed `/v1/chat/completions` pass, no warm-up,
`max_tokens` 512, `ignore_eos: true`):

| Quant | MTP | ignore_eos | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- |
| APEX-I-Compact | on | yes | 517.13 | 36.08 |

- Decode 36.08 vs the 47.7 headline (-24%): attention cost over ~116K cached KV tokens,
  normal MTP acceptance (0.814, mean len 2.63). Prefill 517.13 is the saturated rate - the
  ~192-token headline prompts are too small to amortize the per-request overhead, so the
  two prefill columns measure different regimes, not a regression.
- No crash and no EOS quirk: the near-repetitive prompt is safe on `qwen35moe` (the PLE
  n-gram path is `qwen4exp`-only), and `/v1/chat/completions` decoded the full 512 tokens.
  VRAM 11729 MiB at load.

## Key arch notes

- Same `qwen35moe` family as Qwen3.6-35B-A3B (41 blocks, 256 experts / 8 active, embedded
  MTP); the general notes in [methodology.md](../../methodology.md) apply, there are no
  model-specific issues recorded for this quant.
- The embedded MTP draft context costs ~2 GB at 262144 - this is what forces ncmoe 28 (the
  minimum split that fits); without MTP the model fits down to ncmoe 24.
- `--n-cpu-moe 28` is a hard floor at full ctx: 27 and below abort during context creation.

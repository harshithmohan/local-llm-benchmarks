# KAT-Coder-V2.5-Dev (Rig 1) - best configs

Coding-specialised model on the `qwen35moe` arch (same family as Qwen3.6-35B-A3B): 41
blocks, 256 experts / 8 active, native ctx 262144, embedded MTP head. Model card:
[gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF](https://huggingface.co/gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF).
Full experiment log: [katcoder-v2.5-dev-archive.md](katcoder-v2.5-dev-archive.md).
Methodology in [methodology](../../methodology.md); model-specific issues in
[issues](../../issues.md).

Quants tested: `APEX-I-Compact` (16.24 GiB, single file, Q4_K_M / file_type 15) - the only
quant on this rig.

## Measured results at c 262144 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV)

| Quant | Engine | MTP | ncmoe | cache | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | moe-cache fork | on | 28 | 80 | ~344 | **~76** | 11029 MiB |
| APEX-I-Compact | stock | on | 28 | - | 338.5 | 47.7 | 11729 MiB |

All rows use the current protocol: coding prompts (C# ~192 tokens, React ~155 tokens)
averaged, second-pass measurement with slot prompt caching disabled (`cache_prompt:false`) so
the measure pass re-prefills instead of reusing the KV prefix (see the archive's method
note), recommended sampling (temp 1.0, top_p 0.95, top_k 20, min_p 0.0, presence_penalty
1.5), MTP n-max 2, cold load; engine per row. Prefill on these short prompts is batch-bound;
the same model prefills at ~609 (fork) / ~573 (stock) t/s on the ~60K messy prompt (below),
which is the saturated rate - compare prefill across pages only within the same prompt size.

Reading:

- ncmoe 28 is the lowest that fits at 262144 with MTP on (24/26/27 abort in the
  compute-buffer allocation, even at `-b 512 -ub 512`) and also the fastest measured (ncmoe
  32 loses ~14% decode for ~1.3 GB less VRAM).
- MTP is worth its ~2 GB draft context: with MTP off the config drops to ncmoe 24, but
  decode is still 45.2 vs 47.7, and short-prompt prefill rises to 391.9 (the draft compute
  is gone).
- The moe-cache (GenerelSchwerz) fork is the fastest config here: its dynamic CUDA expert
  cache overrides the ncmoe placement, so only the cached slabs sit on the GPU. Cache 80 at
  full ctx -> ~76 t/s decode (+59% over the stock 47.7) at 11029 MiB; cache 96 matches that
  decode but leaves only ~430 MiB free, so 80 is the safe max.
- Its own cache-0 control is already 51.8 t/s (+8.6% over stock) - the fork tracks a newer
  upstream build, so part of the gain is engine, not cache.
- The Codacus CSV-profile cache was not probed: it needs a VRAM-resident profile pack, and at
  ncmoe 28 only ~560 MiB is free. The moe-cache fork needs no pack, which is why it fits.

## Best config per quant

### APEX-I-Compact - winner (only quant on this rig)

moe-cache fork + MTP, full 256k (fastest):

    llama-server -m <models>/KAT-Coder-V2.5-Dev-MTP-APEX-I-Compact.gguf \
      --ctx-size 262144 --n-cpu-moe 28 --moe-expert-cache-size 80 \
      -fit off --load-mode none -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --reasoning-preserve \
      --temp 1.0 --top-p 0.95 --top-k 20 --presence-penalty 1.5

-> ~76 t/s decode @ 262144 (prefill ~344 short-prompt, acceptance ~0.75), 11029 MiB: the
dynamic expert cache keeps only the cached expert slabs on the GPU, so it is both faster and
leaner than the stock split. Cache 96 hits the same decode but leaves only ~430 MiB free.

Stock binary + MTP, full 256k (fallback where the fork engine is unavailable):

    llama-server -m <models>/KAT-Coder-V2.5-Dev-MTP-APEX-I-Compact.gguf \
      --n-cpu-moe 28 --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --reasoning-preserve \
      --temp 1.0 --top-p 0.95 --top-k 20 --presence-penalty 1.5

-> 47.7 t/s decode @ 262144 (prefill 338.5 short-prompt / 572.8 on the ~60K messy prompt,
acceptance 0.71), 11729 MiB. Engine-vs-engine, the fork's cache-0 control alone is 51.8.

## Alternatives (archived)

Leaner or slower splits, all at c 262144 (full ladder and numbers in the archive):

- MTP off, ncmoe 24 - 45.2 t/s decode / 391.9 short-prompt prefill, 10963 MiB: the leanest
  config if VRAM must be shared, at ~5% decode cost.
- MTP off, ncmoe 28 - 42.5 decode, 9647 MiB.
- MTP on, ncmoe 32 - 40.9 decode, 10411 MiB (more CPU experts, less VRAM).

## Messy-code refactor benchmark (real-task ~60K prompt, single-pass)

Single timed pass, cold load, prompt-only payload (`ignore_eos`), 512 gen, q8_0 KV; both
rows measured 2026-09-28. The retired ~116K-prompt run is in
[katcoder-v2.5-dev-archive.md](katcoder-v2.5-dev-archive.md).

| Quant | Engine | MTP | ncmoe | cache | prompt tokens | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | moe-cache fork | on | 28 | 80 | 59760 | 608.7 | **49.06** | 11077 MiB |
| APEX-I-Compact | stock | on | 28 | - | 59760 | 572.8 | 38.33 | 11781 MiB |

-> the fork holds a ~+6% prefill lead and ~+28% decode at ~60K; acceptance 275/470 (0.59)
fork vs 288/446 (0.65) stock. Full cold prefill (`cached_tokens` 0).

## Key arch notes

- Same `qwen35moe` family as Qwen3.6-35B-A3B (41 blocks, 256 experts / 8 active, embedded
  MTP); the general notes in [methodology.md](../../methodology.md) apply, there are no
  model-specific issues recorded for this quant.
- The embedded MTP draft context costs ~2 GB at 262144 - this is what forces ncmoe 28 (the
  minimum split that fits); without MTP the model fits down to ncmoe 24.
- `--n-cpu-moe 28` is a hard floor at full ctx: 27 and below abort during context creation.

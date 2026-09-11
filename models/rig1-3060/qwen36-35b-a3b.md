# Qwen3.6-35B-A3B (Rig 1) - best configs

Clean summary. Full experiment log: [qwen36-35b-a3b-archive.md](qwen36-35b-a3b-archive.md).
Context covered: 262144 only (204800 and 131072 runs are in the archive - dropped because
this model's speed barely changes with context: 204800 was within 6-9% of 262144, and the
only thing 200k buys is 1-2 extra cache slots at the cost of 57k tokens of window).

## Measured results at c 262144 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV)

| Quant | binary | MTP | ncmoe | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | stock | on | 28 | n/a | 525.7 | **49.4** |
| UD-Q4_K_M | stock | on | 99 | n/a | 370.3 | 32.5 |
| UD-Q4_K_M | Codacus fork | on | 99 | 40 | 268.6 | 38.8 |

All rows use the current protocol: coding prompts (C# + React, ~308 tokens each) averaged,
second-pass measurement (first pass warms mmap page cache, discarded), recommended
sampling (temp 1.0, top_p 0.95, top_k 20, min_p 0.0; presence_penalty 1.5), cold load.
No ub standardization between rows - each uses its best feasible ubatch (MTP rows need
ub 512 at 256k). Prefill is prompt-size-bound: compare rows to
each other, not to llama-bench pp numbers or archived rows.

- Q4_K_M's only argument might be quantization quality (bpw 4.4-4.8 vs 4.19) - never
  tested, treat as an unverified alternative.

Reading:

- With MTP on, the UD-Q4_K_M fork row (38.8) narrows the decode gap to IQ4 stock+MTP
  (49.4) via the expert cache; its prefill stays cache-bound (268.6 vs 525.7).
- Codacus fork vs stock is a wash in same-flag pairings; the fork's real differentiator
  is the expert cache, which IQ4 cannot use.
- Best config: see the blocks below.

## Best config per quant

### IQ4_XS - fastest at large ctx (winner)

Stock binary + MTP, at full 256k:

    llama-server --port PORT \
      -m /models/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      --n-cpu-moe 28 --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --reasoning-preserve

-> 49.4 t/s decode @ 262144 (prefill 525.7, acceptance 0.67-0.70). The Codacus fork has
nothing to add for this quant: no cache possible (fused gate_up), and the prefill patches
do nothing at 256k prefill - stock is the config.

### UD-Q4_K_M - alternative to IQ4_XS at large ctx (might be better quality - untested); cache works

Codacus fork + expert cache + MTP, at full 256k (at ub 512 the draft context and a 40-slot
pack coexist; the old ub 2048 protocol could only fit 20 slots, which made MTP pointless):

    GGML_CUDA_REGISTER_HOST=1 GGML_SCHED_PREFETCH_EXPERTS=1 \
    llama-server -m /models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf \
      --n-cpu-moe 99 --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --reasoning-preserve -b 512 -ub 512 \
      --moe-cache-profile /models/moe-cache-profiles/qwen36-udq4km-merged.csv \
      --moe-cache-slots 40 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0

-> 38.8 t/s decode @ 262144 (prefill 268.6, acceptance 0.59-0.72). Trade: prefill is
cache-bound (~45% below stock+MTP) in exchange for possibly higher quality (never
tested). Stock + MTP without the cache is 32.5 - the cache is worth +19% decode here.

UD-Q6_K was dropped from this page: it is the weakest 35B quant at large ctx in every
measured config (see the archive for its full history).

# Qwen3.6-35B-A3B (Rig 2) - best configs

Rig details and setup:
[../../rig2-3090.md](../../rig2-3090.md). Methodology: [../../methodology.md](../../methodology.md).
Full experiment log: [qwen36-35b-a3b-archive.md](qwen36-35b-a3b-archive.md).
Model cards: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(`UD-*` quants); [byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF) (`IQ4_XS-4.19bpw`).

Same protocol as Rig 1: coding prompts C#+React averaged, second-pass prefill,
recommended sampling (temp 1.0, top_p 0.95, top_k 20, min_p 0.0, presence_penalty 1.5),
cold load, q8_0 KV, `--threads 8` (Ryzen 7 5700X), 22 GB VRAM cap (desktop reserve).
Context covered: 262144 for the headline config; a YaRN extension probe reaches 1M (512K
and 768K also tested) - see the extended-context results below.

## Measured results at c 262144 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV)

| MTP | ncmoe | cache slots | ctx | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| on | 0 | n/a | 262144 | 2375.8 | **165.1** | 22065 MiB |

Why it wins on this rig:

- Fastest quant that holds FULL 262144 ctx within the 22 GB cap (the 4.19bpw IQ4 is
  faster only at 230400 - see the archive for that trade).
- Cache-compatible (separate gate/up/down tensors), so the Codacus fork's cache stays
  available if a future config ever shifts layers to CPU. Nothing to cache at ncmoe 0.
- Decode 3-4x Rig 1's best 35B numbers (49.4) - the 3090 fits the expert tensors on GPU
  (ncmoe 0 here; the whole MoE-offload story inverts on this rig).

## Measured results at extended context (YaRN, q8_0 KV, MTP off)

Same protocol as above; every row extends past the native 262144 with
`--rope-scaling yarn --rope-scale <ctx/262144> --yarn-orig-ctx 262144` (2.0 at 512K, 3.0
at 768K, 4.0 at 1M). UD-IQ4_XS only. MTP is off: at extended ctx its draft context costs
~2.3 GiB, which funds 6-7 fewer GPU expert layers and loses more than it gains at every
point (MTP-on rows in the archive).

| Quant | binary | MTP | ncmoe | ctx | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ4_XS | stock | off | 6 | 524288 | 1656.7 | **89.9** | 21915 MiB |
| UD-IQ4_XS | stock | off | 15 | 786432 | 1181.9 | 65.2 | 22205 MiB |
| UD-IQ4_XS | stock | off | 25 | 1048576 | 871.8 | 49.4 | 22141 MiB |

- 1M fits on this rig: the 22 GB budget absorbs the 10.6 GiB q8_0 KV cache by pushing
  experts to CPU (ncmoe 25), something Rig 1's 12 GB cannot do.
- MTP costs decode at extended context here too (Rig 1 repeats): dropping it buys 6-7 GPU
  expert layers, and every point gains (512K 89.9 vs 83.9 decode, 1656.7 vs 1249.1
  prefill). Acceptance is higher with MTP but does not convert.
- Decode and prefill each fall ~25-28% per context step (89.9 -> 65.2 -> 49.4) while VRAM
  stays flat (21.9-22.2 GB) - each step offloads more experts to make room for KV.
- Long-range retrieval quality under YaRN was **not validated** - see
  [methodology.md](../../methodology.md).

## Best config per quant

### UD-IQ4_XS - winner (full ctx within the 22 GB cap)

    llama-server -m <models>/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
      --n-cpu-moe 0 --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 8 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --reasoning-preserve -b 512 -ub 512

-> 165.1 t/s decode @ 262144 (prefill 2375.8, acceptance 0.70), 22065 MiB.

Tested on stock only, deliberately: at ncmoe 0 the Codacus fork has nothing to add -
no CPU layers means no cache to build and no weights to pin/prefetch, and a higher-ncmoe
fork config with a cache pack measured slower on both rigs (Q4_K_M: 119.3 < 165.1 here).
Same-flags fork vs stock is a wash in every pairing measured on either rig.

### UD-IQ4_XS - extended context via YaRN (512K / 768K / 1M)

    llama-server -m <models>/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
      --n-cpu-moe <ncmoe> --ctx-size <ctx> -ngl 999 \
      --rope-scaling yarn --rope-scale <ctx/262144> --yarn-orig-ctx 262144 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 8 --parallel 1 \
      --reasoning-preserve -b 512 -ub 512

| ctx | rope-scale | ncmoe |
| --- | --- | --- |
| 524288 | 2.0 | 6 |
| 786432 | 3.0 | 15 |
| 1048576 | 4.0 | 25 |

-> Speeds in the extended-context table above (89.9 t/s decode at 512K, 49.4 at 1M). MTP
stays off. `rope-scale` must equal ctx/262144 exactly - `--ctx-size` is clamped to
`n_ctx_train * rope-scale`.

## Alternatives (archived)

- IQ4_XS-4.19bpw: 178.1 t/s @ 230400 / 147.7 @ 262144 - faster at reduced ctx, cannot
  use the cache ever.
- UD-Q4_K_M: 119.3 t/s (Codacus fork cache+MTP) - possibly better quality (untested).
See the archive.

## Messy-code refactor benchmark (real-task ~116K prompt)

One-time real-task speed test of the messy-code refactor prompt (see
[test-prompts.md](../../test-prompts.md), generated by `scripts/generate-messy-prompt.py`,
seed 42, 116,235 prompt tokens), winner config, q8_0 KV, cold load, single-run protocol
(ONE timed pass, no warm-up; /v1/chat/completions, max_tokens 512, `ignore_eos: true`):

| Quant | binary | MTP | ncmoe | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- | --- |
| UD-IQ4_XS | stock | on | 0 | n/a | 1958.04 | 104.27 |

- Prefill 1958.04 vs the 2375.8 headline (-18%): the same prompt barely moves Rig 1's
  prefill (522.16 vs 525.7), so the extra long-context attention cost is only visible with
  the model fully on GPU (ncmoe 0) rather than behind Rig 1's CPU-expert bottleneck.
- Decode 104.27 vs the 165.1 headline (-37%), MTP acceptance 0.781 (mean len 2.56) vs 0.70
  on the short prompts: the drop is per-step attention cost over ~116K cached KV tokens,
  not an MTP failure - acceptance is actually higher on this prompt.
- No crash or EOS quirk on this arch - see [issues.md](../../issues.md). VRAM 22065 MiB at
  load, same as the short-prompt winner (KV is preallocated for 262144).

## Key arch notes

Ncmoe 0 (all experts on GPU) is optimal up to 262144. Past that the q8_0 KV cache forces
expert offload, and the Rig 1 MoE-offload trade-offs apply: each context step trades GPU
expert layers for KV at ~flat VRAM (21.9-22.2 GB across 512K-1M), and MTP must be dropped
because its draft context evicts experts. General notes in [methodology.md](../../methodology.md).

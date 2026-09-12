# Qwen3.6-35B-A3B (Rig 2) - best configs

Rig details and setup:
[../../rig2-3090.md](../../rig2-3090.md). Methodology: [../../methodology.md](../../methodology.md).
Full experiment log: [qwen36-35b-a3b-archive.md](qwen36-35b-a3b-archive.md).

Same protocol as Rig 1: coding prompts C#+React averaged, second-pass prefill,
recommended sampling (temp 1.0, top_p 0.95, top_k 20, min_p 0.0, presence_penalty 1.5),
cold load, q8_0 KV, `--threads 8` (Ryzen 7 5700X), 22 GB VRAM cap (desktop reserve).

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

## Alternatives (archived)

- IQ4_XS-4.19bpw: 178.1 t/s @ 230400 / 147.7 @ 262144 - faster at reduced ctx, cannot
  use the cache ever.
- UD-Q4_K_M: 119.3 t/s (Codacus fork cache+MTP) - possibly better quality (untested).
See the archive.

## Messy-code refactor benchmark (real-task ~116K prompt)

Not run on this rig.

## Key arch notes

None specific to this rig - at ncmoe 0 the MoE-offload trade-offs documented on Rig 1
do not apply; general notes in [methodology.md](../../methodology.md).

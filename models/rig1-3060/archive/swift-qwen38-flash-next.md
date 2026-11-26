# Swift-1.5-Qwen3.8-Flash-Next (Rig 1) - experiment archive

Superseded rows and experiment tables for the [Swift-1.5-Qwen3.8-Flash-Next model card](../swift-qwen38-flash-next.md). The card carries only the current numbers; everything below was measured on this rig and is kept for the mechanism records.

Methodology: [methodology.md](../../../methodology.md). Base model: [qwen38-flash-next.md](../qwen38-flash-next.md) and its [archive](qwen38-flash-next.md).

## Speedy 0.3.1 + MTP (2026-11-07)

Measured on the same Swift pack and the base model's MTP head, using a `--prompt-cache 0` bench variant of the Speedy config; cold load per prompt, two passes, second recorded. Every recorded pass reported `cache_n` 0, `predicted_n` 512 and finished on `length`.

| Config | ctx | engine | drafter | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Speedy 0.3.1 | MTP | ~10K | 1248.2 | **73.3** | 11325 MiB | 10514-token prompt, draft 321/483; pass 1 1219.0 / 78.7 |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Speedy 0.3.1 | MTP | ~60K | 1291.1 | **73.6** | 11325 MiB | 59762-token prompt, draft 328/432; pass 1 1291.7 / 66.9 |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Speedy 0.3.1 | MTP | ~120K | 1253.6 | **73.7** | 11325 MiB | 119304-token prompt, draft 334/443; pass 1 1254.6 / 68.7 |

Against Strata 0.2.10 + MTP: prefill +14.1 / +13.8 / +12.9%, decode +15.3 / +37.3 / +39.8%. Against Speedy on the base Qwen3.8 checkpoint at the same prompt sizes: prefill +0.6 / +0.2 / +0.1%, decode -12.4 / +9.5 / +8.7%. The Swift decode gain grows with depth; recorded draft acceptance was 66.5-75.9%.

## Pack and drafter notes

- `--ple-gguf` names **shard 1** here. The engine resolves that flag by finding `per_layer_token_embd.weight` among the shards beside `--native`: this checkpoint puts the per-layer embedding table in shard 1 and breaks its blocks at layer 12 (shard 1 = layers 0-12, 317 tensors; shard 2 = layers 12-47, 907), where the base model keeps all layers in shard 1 and puts the table alone in shard 2. Pointing the flag at shard 2, as the base model's config does, does not load.
- **MTP only.** Neither shard carries MTP tensors; the base model's head drafts this checkpoint. `terminal/serve/drafting.py` restricts DFlash2 to `SUPPORTED_FAMILIES = ("qwen","gyro","unsloth")`, so asking for it here leaves the entry with no speculative decoding at all rather than falling back.
- **Pack**: `iq_pack.py --gguf <shard1> --out <pack>`, no `--base` (the base-model reuse is refused for this split). It reports 1079 tensors, 302 served natively, 0 in `extra.bin`, arena 1.43 GiB, 96 tensors converted to the engine's form (96 exact, max |err| 0), and a tokenizer of 248320 vocab / 247587 merges (`pre` qwen35, eos 248046, pad 248044, bos 248044).
- **Cache and chunk**: `--expert-cache auto` settles at 1639 slots / 2.70 GiB (MTP layer 1035 MiB), `--prefill auto` at a 4864-token chunk with 1481 slots borrowed, 679 MiB free with everything loaded.
- **Vision** is the Swift projector, `mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf` (907 MB, `clip`, 334 tensors), on the CPU on 8 threads with a 4096-token cap and 1024-token floor per picture. 8 is the container's physical core count; leaving `threads` unset derives `min(16, hardware_concurrency()/2)` from the host's 20 threads, which oversubscribes. A 64x64 PNG reached the model as 1091 prompt tokens (1024 floor + text) and was answered correctly.
- Measurement rows use `--prompt-cache 0` (protocol). The Strata served config pins `--prompt-cache-every 5632`; the Speedy config leaves prompt caching at its defaults.

## Strata 0.2.7 / 0.1.52 (rows retired 2026-11-06)

Re-benched 2026-10-29. The 0.2.10 upgrade needed no repack: the expert-layout version only moved to v5 for Hadamard-folded packs, so this v3 pack loads unchanged, and the base model's MTP head and expert profile are byte-identical across the two engines.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on (base head) | 1076.7 | **55.9** | 11559 MiB | `--kv int8`, CPU vision encoder |

### Long-context refactor benchmark (0.2.7)

Real-task timing test: a fixed refactor instruction wraps a generated file of near-identical legacy Python templates ([test-prompts.md](../../../test-prompts.md)). Same protocol as above.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on (base head) | ~60K | 1048.1 | **55.8** | 11559 MiB | 59802 prompt tokens, `cache_n` 0, `predicted_n` 512, draft 188-207/327-337 |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on (base head) | ~120K | 1009.9 | **54.6** | 11559 MiB | 119344 prompt tokens, `cache_n` 0, `predicted_n` 512, draft 205-219/387-409 |

Every pass finished on `length` with `cache_n` 0 after one cold load; two measured passes per prompt, medians above. The ~10k prompt does **not** end on a tool call for this checkpoint, unlike its IQ2_XS build on engine 0.1.40.2.

### Load shape on 0.1.52

`expert cache auto` reports 1352 slots from free VRAM (+73 MiB for the 40,525-token draft head), then the profile ranks up to 1784 slots (2.93 GiB, PROFILE policy, no eviction), and `--prefill auto` reports `prompt chunk auto: 5632 tokens, a 227-slot ring`. The engine warns `only 460 MiB of VRAM free at the start of this request (below 512 MiB)` and suggests `--vram-reserve-mib 768`; the flag is deliberately not set - the base model's config at the same window runs in the same 322-462 MiB band and warns identically, so this is the served shape, not a config defect. Adding it would cost cache slots.

## Strata 0.2.19 / engine 0.1.65 (2026-11-22)

Retired the 0.2.13 rows. Same protocol as the card: `--prompt-cache 0`, `cache_n` 0, `predicted_n` 512, cold load per prompt, second pass recorded. The 0.2.13 card's `--prefill auto` resolved to 4864 on the Swift entry; 0.2.19's `auto` undersizes the cache to 1536 slots and a 2304-token chunk, so the served config pins `--prefill 4864`.

### 10K (retired)

| engine | chunk | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- |
| Strata 0.2.13 | auto (4864) | 1094.0 | **63.6** | 11393 MiB | 10554-token prompt |
| Strata 0.2.19 | 4864 | 1272.8 | **59.1** | 11101 MiB | 10554-token prompt, draft 214/378; pass 1 1280.5 / 59.4 |

### 0.2.13 long-context baseline (retired)

| Config | ctx | engine | drafter | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.13 | MTP | ~60K | 1134.3 | **53.6** | 11393 MiB | 59802-token prompt, draft 183/352 |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.13 | MTP | ~120K | 1110.2 | **52.7** | 11393 MiB | 119344-token prompt, draft 185/320 |

### 0.2.19: auto vs pinned

| chunk | expert cache | prompt chunk | ~60K | ~120K | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `auto` | 1536 slots / 2.53 GiB | 2304 / 8-slot ring | 916.1 / **51.7** | 887.7 / **51.1** | 11097 MiB | MTP layer 1035 MiB; draft 224/383, 227/380 |
| `4864` | 2990 slots / 4.89 GiB | 4864 | 1252.9 / **59.7** | 1196.6 / **57.5** | 11101 MiB | MTP layer 837 MiB; draft 225/346, 231/389; 830 MiB free |

The 0.2.19 auto chunk undersizes the expert cache and costs ~20% prefill at both depths; the explicit pin restores the 0.2.13 chunk and removes the regression. Decode tracks draft acceptance, not prefill.

## Speedy 0.5.5 + MTP (2026-11-26)

Same Swift pack and base-model MTP head; `--prompt-cache 0` bench config, cold load per prompt, two passes, second recorded, `cache_n` 0 and `predicted_n` 512.

| prompt | prompt tokens | prefill t/s | decode t/s | draft accepted |
| --- | --- | --- | --- | --- |
| 10k | 10514 | 1247.8 | **80.1** | 339/433 |
| 60k | 59762 | 1289.2 | **74.1** | 328/437 |
| 120k | 119304 | 1249.8 | **66.9** | 312/427 |

Loads 35-41 s; VRAM 11215 MiB. The 10K pass 1 stopped at 53 tokens; pass 2 was valid.

Against 0.4.7 on the same prompts (10K 1241.3 / 86.7, 60K 1289.9 / 67.6, 120K 1250.8 / 65.3): prefill unchanged, 60K decode +9.6%, 120K +2.5%. The 10K decode sits inside this model's session band and is treated as noisy. llama-swap cold load on the Swift entry was 38.7 s and returned `SWIFT-READY`; the startup log showed `session is up` and only the harmless CPU `strata-vision` CUDA-init line.

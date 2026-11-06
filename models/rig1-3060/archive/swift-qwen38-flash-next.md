# Swift-1.5-Qwen3.8-Flash-Next (Rig 1) - experiment archive

Superseded rows and experiment tables for the [Swift-1.5-Qwen3.8-Flash-Next model card](../swift-qwen38-flash-next.md). The card carries only the current numbers; everything below was measured on this rig and is kept for the mechanism records.

Methodology: [methodology.md](../../../methodology.md). Base model: [qwen38-flash-next.md](../qwen38-flash-next.md) and its [archive](qwen38-flash-next.md).

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

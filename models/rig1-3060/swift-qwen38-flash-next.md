# Swift-1.5-Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-24 · [methodology](../../methodology.md) · base model: [qwen38-flash-next.md](qwen38-flash-next.md)

`GSQ-RCO` quant `IQ3_XXS` (75.9 GB, 2 shards: 39.8 GB + 36.2 GB) - the Swift-1.5 fine-tune of Qwen3.8-Flash-Next (`qwen4exp`, native ctx 262144, 512 experts). Same architecture and size as the base model, and it ships **no MTP head**: the base model's MTP head drafts it and is used as-is. Model card: [ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF). Served by [Strata](https://github.com/Niko1221/Strata) as a pack engine, from a pack built for this checkpoint alone.

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata | on (base head) | 1055.3 | **42.3** | 11482 MiB | `--kv int8`, `--expert-cache auto` (1739 slots / 2.86 GiB), `--prefill auto` (chunk 5376) + `STRATA_PREFILL_LEND_PCT=95` in the server env; the five 0.1.45 CUDA decode switches are on and the vision encoder is enabled on the CPU |

## Configs

Rows above were measured on engine **0.1.45**. The Swift pack itself is engine-version-agnostic (layout v3/v4 still loads on 0.2.7, no repack needed) but the entries have not been re-benched on 0.2.7. On the base model 0.2.7 gave +26% decode at the ~10k prompt and −5.4% prefill ([qwen38-flash-next.md](qwen38-flash-next.md)).


### GSQ-RCO IQ3_XXS + MTP - Strata pack engine, 204800

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/swift-iq3_xxs",
               "--native", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--expert-profile", "<engine>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5", "--mtp", "<mtp>/rt",
               "--max-context", "204800", "--kv", "int8", "--vision", "--prompt-cache-every", "5632"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/swift-iq3_xxs/tokenizer",
      "model_name": "swift-qwen38-flash-next-iq3xxs",
      "vision": {"exe": "<engine>/strata-vision",
                 "mmproj": "<models>/mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
                 "gpu": false, "max_tokens": 4096, "min_tokens": 1024, "threads": 10},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

`--ple-gguf` names **shard 1** here. The engine resolves that flag by finding `per_layer_token_embd.weight` among the shards beside `--native`: this checkpoint puts the per-layer embedding table in shard 1 and breaks its blocks at layer 12 (shard 1 = layers 0-12, 317 tensors; shard 2 = layers 12-47, 907), where the base model keeps all layers in shard 1 and puts the table alone in shard 2. Pointing the flag at shard 2, as the base model's config does, does not load.

## Notes

- **Pack**: `iq_pack.py --gguf <shard1> --out <pack>`, no `--base` (the base-model reuse is refused for this split). It reports 1079 tensors, 302 served natively, 0 in `extra.bin`, arena 1.43 GiB, 96 tensors converted to the engine's form (96 exact, max |err| 0), and a tokenizer of 248320 vocab / 247587 merges (`pre` qwen35, eos 248046, pad 248044, bos 248044).
- **MTP**: neither shard carries MTP tensors. The base model's head drafts this checkpoint correctly - draft 206-242 accepted of 342-421 per 512-token pass. Decode rows move with that acceptance session to session, so compare them within one session.
- **Cache and chunk land where they do on the base model at this window**: `expert cache auto` reports 1318 slots from free VRAM, then the profile ranks up to 1739 slots (2.86 GiB, PROFILE policy, no eviction), and `--prefill auto` reports `prompt chunk auto: 5376 tokens, a 227-slot ring` borrowing 1597 cache slots (2.62 GiB) for the prompt path.
- **Headroom**: the engine warns `only 460 MiB of VRAM free at the start of this request (below 512 MiB)` and suggests `--vram-reserve-mib 768`. The flag is deliberately not set - the base model's config at the same window runs in the same 322-462 MiB band and warns identically, so this is the served shape, not a config defect. Adding it would cost cache slots.
- **Vision** is the Swift projector, `mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf` (907 MB, `clip`, 334 tensors), run on the CPU with a 4096-token cap and 1024-token floor per picture. A 64x64 PNG reached the model as 1091 prompt tokens (1024 floor + text) and was answered correctly; an image prompt reads at ~518 t/s prefill.
- Measurement rows use `--prompt-cache 0` (protocol); the served config pins `--prompt-cache-every 5632` instead.

## Long-context refactor benchmark

Real-task timing test: a fixed refactor instruction wraps a generated file of near-identical legacy Python templates ([test-prompts.md](../../test-prompts.md)). Same protocol as above.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata | on (base head) | ~10k | 1055.3 | **42.3** | 11482 MiB | 10554 prompt tokens, `cache_n` 0, `predicted_n` 512, draft 210/421 |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata | on (base head) | ~60K | 1008.2 | **41.7** | 11482 MiB | 59802 prompt tokens, `cache_n` 0, `predicted_n` 512, draft 214/376 |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata | on (base head) | ~120K | 982.7 | **41.9** | 11482 MiB | 119344 prompt tokens, `cache_n` 0, `predicted_n` 512, draft 215/356 |

Every pass finished on `length` with `cache_n` 0 after one cold load; decode expert-cache hit rate was 62-69% across the six passes. The ~10k prompt does **not** end on a tool call for this checkpoint, unlike its IQ2_XS build on engine 0.1.40.2.

Against the base model's `GSQ-RCO IQ3_XXS` at the same window and engine ([qwen38-flash-next.md](qwen38-flash-next.md)):

| prompt | Swift IQ3_XXS | Base IQ3_XXS | prefill delta |
| --- | --- | --- | --- |
| ~10k | 1055.3 / 42.3 | 1054.2 / 43.4 | +0.1% |
| ~60K | 1008.2 / 41.7 | 1027.3 / 43.0 | -1.9% |
| ~120K | 982.7 / 41.9 | 987.8 / 37.8 | -0.5% |

Prefill is within ~2% of the base model on the identical engine and window. The decode columns come from different sessions, so read the delta as MTP-acceptance spread, not a model difference.

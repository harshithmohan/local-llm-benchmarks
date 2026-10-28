# Swift-1.5-Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-29 · [methodology](../../methodology.md) · base model: [qwen38-flash-next.md](qwen38-flash-next.md)

`GSQ-RCO` quant `IQ3_XXS` (75.9 GB, 2 shards: 39.8 GB + 36.2 GB) - the Swift-1.5 fine-tune of Qwen3.8-Flash-Next (`qwen4exp`, native ctx 262144, 512 experts). Same architecture and size as the base model, and it ships **no MTP head**: the base model's MTP head drafts it and is used as-is. Model card: [ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF). Served by [Strata](https://github.com/Niko1221/Strata) as a pack engine, from a pack built for this checkpoint alone.

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on (base head) | 1076.7 | **55.9** | 11559 MiB | `--kv int8`, CPU vision encoder |

## Configs

Rows above are engine **0.2.7** (build `0.1.52`), re-benched 2026-10-29. The upgrade needed no repack: the expert-layout version only moved to v5 for Hadamard-folded packs, so this v3 pack loads unchanged, and the base model's MTP head and expert profile are byte-identical across the two engines.


### GSQ-RCO IQ3_XXS + MTP - Strata pack engine, 204800

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/swift-iq3_xxs",
               "--native", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--expert-profile", "<engine>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5", "--mtp", "<mtp>/rt",
               "--mtp-draft-vocab", "<engine>/data/draft_vocab_en.bin",
               "--max-context", "204800", "--kv", "int8", "--vision", "--prompt-cache-every", "5632"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/swift-iq3_xxs/tokenizer",
      "model_name": "swift-qwen38-flash-next-iq3xxs",
      "vision": {"exe": "<engine>/strata-vision",
                 "mmproj": "<models>/mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
                 "gpu": false, "max_tokens": 4096, "min_tokens": 1024, "threads": 8},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

`--ple-gguf` names **shard 1** here. The engine resolves that flag by finding `per_layer_token_embd.weight` among the shards beside `--native`: this checkpoint puts the per-layer embedding table in shard 1 and breaks its blocks at layer 12 (shard 1 = layers 0-12, 317 tensors; shard 2 = layers 12-47, 907), where the base model keeps all layers in shard 1 and puts the table alone in shard 2. Pointing the flag at shard 2, as the base model's config does, does not load.

## Notes

- **Pack**: `iq_pack.py --gguf <shard1> --out <pack>`, no `--base` (the base-model reuse is refused for this split). It reports 1079 tensors, 302 served natively, 0 in `extra.bin`, arena 1.43 GiB, 96 tensors converted to the engine's form (96 exact, max |err| 0), and a tokenizer of 248320 vocab / 247587 merges (`pre` qwen35, eos 248046, pad 248044, bos 248044).
- **MTP**: neither shard carries MTP tensors. The base model's head drafts this checkpoint correctly - draft 177-219 accepted of 317-409 per 512-token pass. Decode rows move with that acceptance session to session, so compare them within one session.
- **Cache and chunk land where they do on the base model at this window**: `expert cache auto` reports 1352 slots from free VRAM (+73 MiB for the 40,525-token draft head), then the profile ranks up to 1784 slots (2.93 GiB, PROFILE policy, no eviction), and `--prefill auto` reports `prompt chunk auto: 5632 tokens, a 227-slot ring`.
- **Headroom**: the engine warns `only 460 MiB of VRAM free at the start of this request (below 512 MiB)` and suggests `--vram-reserve-mib 768`. The flag is deliberately not set - the base model's config at the same window runs in the same 322-462 MiB band and warns identically, so this is the served shape, not a config defect. Adding it would cost cache slots.
- **Vision** is the Swift projector, `mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf` (907 MB, `clip`, 334 tensors), run on the CPU on 8 threads with a 4096-token cap and 1024-token floor per picture. 8 is the container's physical core count; leaving `threads` unset derives `min(16, hardware_concurrency()/2)` from the host's 20 threads, which oversubscribes. A 64x64 PNG reached the model as 1091 prompt tokens (1024 floor + text) and was answered correctly; an image prompt reads at ~518 t/s prefill.
- Measurement rows use `--prompt-cache 0` (protocol); the served config pins `--prompt-cache-every 5632` instead.

## Long-context refactor benchmark

Real-task timing test: a fixed refactor instruction wraps a generated file of near-identical legacy Python templates ([test-prompts.md](../../test-prompts.md)). Same protocol as above.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on (base head) | ~60K | 1048.1 | **55.8** | 11559 MiB | 59802 prompt tokens, `cache_n` 0, `predicted_n` 512, draft 188-207/327-337 |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on (base head) | ~120K | 1009.9 | **54.6** | 11559 MiB | 119344 prompt tokens, `cache_n` 0, `predicted_n` 512, draft 205-219/387-409 |

Every pass finished on `length` with `cache_n` 0 after one cold load; two measured passes per prompt, medians above. The ~10k prompt does **not** end on a tool call for this checkpoint, unlike its IQ2_XS build on engine 0.1.40.2.

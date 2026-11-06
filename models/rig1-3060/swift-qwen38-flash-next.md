# Swift-1.5-Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-11-06 · [full experiment log](archive/swift-qwen38-flash-next.md) · [methodology](../../methodology.md) · base model: [qwen38-flash-next.md](qwen38-flash-next.md)

`GSQ-RCO` quant `IQ3_XXS` (75.9 GB, 2 shards: 39.8 GB + 36.2 GB) - the Swift-1.5 fine-tune of Qwen3.8-Flash-Next (`qwen4exp`, native ctx 262144, 512 experts). Same architecture and size as the base model, and it ships **no MTP head**: the base model's MTP head drafts it and is used as-is. Model card: [ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF). Served by [Strata](https://github.com/Niko1221/Strata) as a pack engine, from a pack built for this checkpoint alone.

## Recommended configs

| Config | ctx | engine | drafter | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | MTP | 1094.0 | **63.6** | 11393 MiB | `--kv int8`, CPU vision encoder, 1639 slots / 2.70 GiB cache |

## Configs

### GSQ-RCO IQ3_XXS + MTP - Strata pack engine, 204800

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/swift-iq3_xxs",
               "--native", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--expert-profile", "<engine>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5",
               "--mtp", "<mtp>/rt", "--mtp-draft-vocab", "<engine>/data/draft_vocab_en.bin",
               "--max-context", "204800", "--kv", "int8", "--vision", "--prompt-cache-every", "5632"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/swift-iq3_xxs/tokenizer",
      "model_name": "swift-qwen38-flash-next-iq3xxs",
      "drafting": "mtp",
      "vision": {"exe": "<engine>/strata-vision",
                 "mmproj": "<models>/mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
                 "gpu": false, "max_tokens": 4096, "min_tokens": 1024, "threads": 8},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

Entry env: `STRATA_PREFILL_LEND_PCT=95`, `STRATA_KEEP_EMPTY_TURNS=1`, `STRATA_EXPDEC=1`, `STRATA_QSA_SPLIT_ATTN=1`, `STRATA_ROUTE_PRIOR=1.5`, `STRATA_PF_SMALL=0`.

## Notes

- `--ple-gguf` names **shard 1** here. The engine resolves that flag by finding `per_layer_token_embd.weight` among the shards beside `--native`: this checkpoint puts the per-layer embedding table in shard 1 and breaks its blocks at layer 12 (shard 1 = layers 0-12, 317 tensors; shard 2 = layers 12-47, 907), where the base model keeps all layers in shard 1 and puts the table alone in shard 2. Pointing the flag at shard 2, as the base model's config does, does not load.
- **MTP only.** Neither shard carries MTP tensors; the base model's head drafts this checkpoint. `terminal/serve/drafting.py` restricts DFlash2 to `SUPPORTED_FAMILIES = ("qwen","gyro","unsloth")`, so asking for it here leaves the entry with no speculative decoding at all rather than falling back.
- **Pack**: `iq_pack.py --gguf <shard1> --out <pack>`, no `--base` (the base-model reuse is refused for this split). It reports 1079 tensors, 302 served natively, 0 in `extra.bin`, arena 1.43 GiB, 96 tensors converted to the engine's form (96 exact, max |err| 0), and a tokenizer of 248320 vocab / 247587 merges (`pre` qwen35, eos 248046, pad 248044, bos 248044).
- **Cache and chunk**: `--expert-cache auto` settles at 1639 slots / 2.70 GiB (MTP layer 1035 MiB), `--prefill auto` at a 4864-token chunk with 1481 slots borrowed, 679 MiB free with everything loaded.
- **Vision** is the Swift projector, `mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf` (907 MB, `clip`, 334 tensors), on the CPU on 8 threads with a 4096-token cap and 1024-token floor per picture. 8 is the container's physical core count; leaving `threads` unset derives `min(16, hardware_concurrency()/2)` from the host's 20 threads, which oversubscribes. A 64x64 PNG reached the model as 1091 prompt tokens (1024 floor + text) and was answered correctly.
- Measurement rows use `--prompt-cache 0` (protocol); the served config pins `--prompt-cache-every 5632` instead.

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)): a fixed refactor instruction wraps a deterministically generated Python file of near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement methods), against a derived config carrying `--prompt-cache 0`: `/v1/chat/completions` passes, no request overrides, cold load per prompt, two passes with the second recorded.

| Config | ctx | engine | drafter | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | MTP | ~60K | 1134.3 | **53.6** | 11393 MiB | 59802-token prompt, draft 183/352 |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | MTP | ~120K | 1110.2 | **52.7** | 11393 MiB | 119344-token prompt, draft 185/320 |

Every recorded pass reported `cache_n` 0 and `predicted_n` 512 and finished on `length`. Decode moves with the base head's acceptance run to run, not depth.

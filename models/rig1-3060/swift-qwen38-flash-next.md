# Swift-1.5-Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-11-07 · [full experiment log](archive/swift-qwen38-flash-next.md) · [methodology](../../methodology.md) · base model: [qwen38-flash-next.md](qwen38-flash-next.md)

`GSQ-RCO` quant `IQ3_XXS` (75.9 GB, 2 shards: 39.8 GB + 36.2 GB) - the Swift-1.5 fine-tune of Qwen3.8-Flash-Next (`qwen4exp`, native ctx 262144, 512 experts). Same architecture and size as the base model, and it ships **no MTP head**: the base model's MTP head drafts it and is used as-is. Model card: [ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF). Served as a pack engine by [Strata](https://github.com/Niko1221/Strata) 0.2.10 and its tuned fork [Speedy](https://github.com/DevDock-AI/Speedy) 0.3.1, from a pack built for this checkpoint alone.

## Recommended configs

| Config | ctx | engine | drafter | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | MTP | 1094.0 | **63.6** | 11393 MiB | `--kv int8`, CPU vision encoder, 1639 slots / 2.70 GiB cache |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Speedy 0.3.1 | MTP | 1248.2 | **73.3** | 11325 MiB | `--kv int8`, CPU vision encoder, 3274 slots / 5.35 GiB cache (bench shape) |

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

Entry env: `STRATA_KEEP_EMPTY_TURNS=1`. Config JSON `env`: `STRATA_PREFILL_LEND_PCT=95`, `STRATA_EXPDEC=1`, `STRATA_QSA_SPLIT_ATTN=1`, `STRATA_ROUTE_PRIOR=1.5`, `STRATA_PF_SMALL=0`.

### GSQ-RCO IQ3_XXS + MTP - Speedy 0.3.1, 204800

    {
      "exe": "<speedy>/build/strata",
      "args": ["--pack", "<pack>/swift-iq3_xxs",
               "--native", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--expert-profile", "<speedy>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5",
               "--mtp", "<mtp>/rt",
               "--max-context", "204800", "--kv", "int8",
               "--kv-resident", "20480", "--vram-reserve-mib", "700",
               "--conversation-cache-mib", "8192", "--adapt-async", "1",
               "--adapt-swaps", "80", "--pool-affinity", "measure", "--vision"],
      "cwd": "<speedy>",
      "tokenizer": "<pack>/swift-iq3_xxs/tokenizer",
      "model_name": "swift-qwen38-flash-next-iq3xxs",
      "drafting": "mtp",
      "answer_room": false,
      "fit_max_tokens": true,
      "repeat_stop_tokens": 0,
      "reasoning_effort": "none",
      "reasoning_budget_tokens": 0,
      "reasoning_close_retry": false,
      "vision": {"exe": "<speedy>/strata-vision",
                 "mmproj": "<models>/mmproj-Swift-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
                 "gpu": false, "max_tokens": 4096, "min_tokens": 1024, "threads": 8},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

Entry env: `STRATA_KEEP_EMPTY_TURNS=1`. Config JSON `env`: `STRATA_ROUTE_TAIL_SKIP=0`, `STRATA_PREFILL_CPU_SHARE=auto`, `STRATA_PIN_BY_NEED=1`, `STRATA_EXPDEC=1`, `STRATA_EXCHANGE_ROTATE=1`, `STRATA_ATTN_DAILY=1`, `STRATA_VERIFY_DEFER_CPU=1`, `STRATA_VERIFY_DEFER_CPU_BELOW=0.1`, `STRATA_PROMPT_ATTN_IMMA=1`, `STRATA_KV_PREFETCH=1`, `STRATA_PF_GROUP_SCRATCH=1`, `STRATA_PF_HC_REGION=1`, `STRATA_HC_Q8=1`.

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)): a fixed refactor instruction wraps a deterministically generated Python file of near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement methods), against a derived config carrying `--prompt-cache 0`: `/v1/chat/completions` passes, no request overrides, cold load per prompt, two passes with the second recorded.

| Config | ctx | engine | drafter | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | MTP | ~60K | 1134.3 | **53.6** | 11393 MiB | 59802-token prompt, draft 183/352 |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Speedy 0.3.1 | MTP | ~60K | 1291.1 | **73.6** | 11325 MiB | 59762-token prompt, draft 328/432 |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | MTP | ~120K | 1110.2 | **52.7** | 11393 MiB | 119344-token prompt, draft 185/320 |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Speedy 0.3.1 | MTP | ~120K | 1253.6 | **73.7** | 11325 MiB | 119304-token prompt, draft 334/443 |

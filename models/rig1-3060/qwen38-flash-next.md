# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-11-27 · [methodology](../../methodology.md)

Two pack-engine builds are recommended: Strata 0.2.19 with DFlash2 and Speedy 0.5.5 with MTP. A 4-bit UD-IQ4_XS variant is measured as a slower alternative.

`GSQ-RCO` quant `IQ3_XXS` (the served quant: a 75.8 GB 2-shard build of these weights) (`qwen4exp`, native ctx 262144, 512 experts, a separate MTP head from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B n-gram embedding table + 4B MTP; 48 layers = 12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared expert per token. Model card: [ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants); MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF).

## Recommended configs

| Config | ctx | engine | drafter | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata | DFlash2 | 1334 | **59.7** | 10978 MiB | `--kv int8`, CPU vision encoder, 3147 slots / 5.14 GiB cache |
| GSQ-RCO IQ3_XXS | 262144 | Speedy | MTP | 1245 | **60.7** | 11252 MiB | `--kv int8`, CPU vision encoder |
| UD-IQ4_XS | 262144 | Speedy | MTP | 1022 | **50.8** | 11352 MiB | `--kv int8`, CPU vision encoder |

## Configs

### GSQ-RCO IQ3_XXS + DFlash2 - Strata pack engine, 204800

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/iq3_xxs",
               "--native", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf",
               "--expert-profile", "<engine>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "6144", "--spec", "4", "--spec-min-p", "0.5",
               "--draft", "dflash2", "--draft-model", "<dflash2>/qwen38-dflash2-q4s.pack",
               "--draft-fallback", "none", "--mtp-draft-vocab", "<engine>/data/draft_vocab_en.bin",
               "--max-context", "204800", "--kv", "int8", "--vision", "--prompt-cache-every", "5632"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/iq3_xxs/tokenizer",
      "model_name": "qwen3.8-flash-next-iq3xxs",
      "drafting": "dflash2",
      "user_args": ["--spec", "4", "--draft-conf", "0.5"],
      "vision": {"exe": "<engine>/strata-vision",
                 "mmproj": "<models>/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
                 "gpu": false, "max_tokens": 4096, "min_tokens": 1024, "threads": 8},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

Entry env: `STRATA_KEEP_EMPTY_TURNS=1`. Config JSON `env`: `STRATA_PREFILL_LEND_PCT=95`, `STRATA_EXPDEC=1`, `STRATA_QSA_SPLIT_ATTN=1`, `STRATA_ROUTE_PRIOR=1.5`, `STRATA_PF_SMALL=0`.

### GSQ-RCO IQ3_XXS - Speedy pack engine, 262144

    {
      "exe": "<speedy>/build/strata",
      "args": ["--pack", "<pack>/iq3_xxs",
               "--native", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf",
               "--expert-profile", "<speedy>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5",
               "--mtp", "<mtp>/rt",
               "--max-context", "262144", "--kv", "int8",
               "--kv-resident", "20480", "--vram-reserve-mib", "700",
               "--conversation-cache-mib", "8192", "--adapt-async", "1",
               "--adapt-swaps", "80", "--pool-affinity", "measure", "--vision"],
      "cwd": "<speedy>",
      "tokenizer": "<pack>/iq3_xxs/tokenizer",
      "model_name": "qwen3.8-flash-next-iq3xxs",
      "drafting": "mtp",
      "answer_room": false,
      "fit_max_tokens": true,
      "repeat_stop_tokens": 0,
      "reasoning_effort": "high",
      "reasoning_effort_floor": "off",
      "reasoning_budget_tokens": 0,
      "reasoning_close_retry": false,
      "vision": {"exe": "<speedy>/strata-vision",
                 "mmproj": "<models>/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
                 "gpu": false, "max_tokens": 4096, "min_tokens": 1024, "threads": 8},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

Entry env: `STRATA_KEEP_EMPTY_TURNS=1`. Config JSON `env`: `STRATA_ROUTE_TAIL_SKIP=0`, `STRATA_PREFILL_CPU_SHARE=auto`, `STRATA_PIN_BY_NEED=1`, `STRATA_EXPDEC=1`, `STRATA_EXCHANGE_ROTATE=1`, `STRATA_ATTN_DAILY=1`, `STRATA_VERIFY_DEFER_CPU=1`, `STRATA_VERIFY_DEFER_CPU_BELOW=0.1`, `STRATA_PROMPT_ATTN_IMMA=1`, `STRATA_KV_PREFETCH=1`, `STRATA_PF_GROUP_SCRATCH=1`, `STRATA_PF_HC_REGION=1`, `STRATA_HC_Q8=1`.

### UD-IQ4_XS - Speedy pack engine, 262144

    {
      "exe": "<speedy>/build/strata",
      "args": ["--pack", "<pack>/unsloth-ud-iq4_xs",
               "--native", "<models>/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00004.gguf",
               "--expert-profile", "<speedy>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5",
               "--mtp", "<mtp>/rt",
               "--max-context", "262144", "--kv", "int8",
               "--kv-resident", "20480", "--vram-reserve-mib", "700",
               "--conversation-cache-mib", "8192", "--adapt-async", "1",
               "--adapt-swaps", "80", "--pool-affinity", "measure",
               "--resident-budget-gib", "80", "--vision"],
      "cwd": "<speedy>",
      "tokenizer": "<pack>/unsloth-ud-iq4_xs/tokenizer",
      "model_name": "qwen3.8-flash-next-ud-iq4_xs",
      "drafting": "mtp",
      "answer_room": false,
      "fit_max_tokens": true,
      "repeat_stop_tokens": 0,
      "reasoning_effort": "high",
      "reasoning_effort_floor": "off",
      "reasoning_budget_tokens": 0,
      "reasoning_close_retry": false,
      "vision": {"exe": "<speedy>/strata-vision",
                 "mmproj": "<models>/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00004.gguf",
                 "gpu": false, "max_tokens": 4096, "min_tokens": 1024, "threads": 8},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

Entry env: `STRATA_KEEP_EMPTY_TURNS=1`. Config JSON `env`: `STRATA_ROUTE_TAIL_SKIP=0`, `STRATA_PREFILL_CPU_SHARE=0`, `STRATA_PIN_BY_NEED=1`, `STRATA_EXPDEC=1`, `STRATA_EXCHANGE_ROTATE=1`, `STRATA_ATTN_DAILY=1`, `STRATA_VERIFY_DEFER_CPU=1`, `STRATA_VERIFY_DEFER_CPU_BELOW=0.1`, `STRATA_PROMPT_ATTN_IMMA=1`, `STRATA_KV_PREFETCH=1`, `STRATA_PF_GROUP_SCRATCH=1`, `STRATA_PF_HC_REGION=1`, `STRATA_HC_Q8=1`, `STRATA_SELECT_TWO_PASS=1`, `STRATA_PREFILL_ROUTED_STREAM=1`.

The UD-IQ4_XS shards are the 4-shard `main` build; build the pack from shard 1 with `tools/iq_pack.py --compat-bf16` (needs llama.cpp's `gguf-py`). The 4-shard pack is 1.4 GB.

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)): a fixed refactor instruction wraps a deterministically generated Python file of near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same request shape and two-pass rule as the recommended configs ([methodology.md](../../methodology.md) §Measurement methods), against a derived config carrying `--prompt-cache 0`: `/v1/chat/completions` passes; the rows below add `temperature: 0` only; cold load per prompt, two passes with the second recorded.

| Config | ctx | engine | drafter | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata | DFlash2 | ~60K | 1276 | **74.1** | 10978 MiB | 59802-token prompt, draft 355/298 |
| GSQ-RCO IQ3_XXS | 262144 | Speedy | MTP | ~60K | 1281 | **59.4** | 11252 MiB | 59762-token prompt, draft 346/231 |
| UD-IQ4_XS | 262144 | Speedy | MTP | ~60K | 1125 | **47.0** | 11352 MiB | 59762-token prompt, draft 310/221 |
| GSQ-RCO IQ3_XXS | 204800 | Strata | DFlash2 | ~120K | 1218 | **62.1** | 10978 MiB | 119344-token prompt, draft 318/244 |
| GSQ-RCO IQ3_XXS | 262144 | Speedy | MTP | ~120K | 1247 | **55.6** | 11252 MiB | 119304-token prompt, draft 354/219 |
| UD-IQ4_XS | 262144 | Speedy | MTP | ~120K | 1119 | **49.0** | 11352 MiB | 119304-token prompt, draft 357/262 |

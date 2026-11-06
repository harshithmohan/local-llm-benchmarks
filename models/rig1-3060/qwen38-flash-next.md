# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-11-06 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO` quant `IQ3_XXS` (the served quant: a 75.8 GB 2-shard build of these weights) (`qwen4exp`, native ctx 262144, 512 experts, a separate MTP head from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B n-gram embedding table + 4B MTP; 48 layers = 12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared expert per token. Model card: [ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants); MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | DFlash2 | 1210.1 | **59.1** | 11261 MiB | `--kv int8`, CPU vision encoder, 1910 slots / 3.14 GiB cache |

## Configs

### GSQ-RCO IQ3_XXS + DFlash2 - Strata pack engine, 204800

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/iq3_xxs",
               "--native", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf",
               "--expert-profile", "<engine>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5",
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

Entry env: `STRATA_PREFILL_LEND_PCT=95`, `STRATA_KEEP_EMPTY_TURNS=1`, `STRATA_EXPDEC=1`, `STRATA_QSA_SPLIT_ATTN=1`, `STRATA_ROUTE_PRIOR=1.5`, `STRATA_PF_SMALL=0`.

## Notes

- **DFlash2 is asked for, not defaulted into.** `--draft dflash2 --draft-model <dflash2>/qwen38-dflash2-q4s.pack --draft-fallback none` with no `--mtp DIR`; `--mtp-draft-vocab` is still required. The engine warns at load that MTP was faster in most of its own 12 GB measurements - on this rig DFlash2 is the prefill win and decode is a wash.
- **`STRATA_PF_SMALL=0` is required.** The auto prompt chunk lands on 6144 at this window, under the engine's fixed 8192-token small-cache test, which would otherwise switch on the unfused small-expert path.
- **Vision** runs on the CPU (`"gpu": false`, 8 threads - the container's physical core count) with a 4096-token cap and a 1024-token floor per picture.

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)): a fixed refactor instruction wraps a deterministically generated Python file of near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement methods), against a derived config carrying `--prompt-cache 0`: `/v1/chat/completions` passes, no request overrides, cold load per prompt, two passes with the second recorded.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | DFlash2 | ~60K | 1200.4 | **59.4** | 11261 MiB | 59802-token prompt, draft 227/349 |
| GSQ-RCO IQ3_XXS | 204800 | Strata 0.2.10 | DFlash2 | ~120K | 1155.1 | **52.5** | 11261 MiB | 119344-token prompt, draft 180/305 |

Every recorded pass reported `cache_n` 0 and `predicted_n` 512 and finished on `length`; 773 MiB free with everything loaded. Decode tracks DFlash2 acceptance run to run, not depth.

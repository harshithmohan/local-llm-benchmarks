# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-28 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO` quant `IQ3_XXS` (the served quant: a 75.8 GB 2-shard build of these weights) (`qwen4exp`, native ctx 262144, 512 experts, a separate MTP head from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B n-gram embedding table + 4B MTP; 48 layers = 12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared expert per token. Model card: [ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants); MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata | on | 999.4 | **54.5** | 11470 MiB | engine 0.2.7 (build 0.1.52): `--kv int8`, `--expert-cache auto`, `--prefill auto` + `STRATA_PREFILL_LEND_PCT=95`; the sm_86 switch table and the ≤13 GiB route prior are the engine's defaults, only `STRATA_EXPDEC`, `STRATA_QSA_SPLIT_ATTN`, `STRATA_PREFILL_LEND_PCT` and `STRATA_KEEP_EMPTY_TURNS` are set; vision encoder on the CPU |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata | on | 1056.6 | 43.4 | 11571 MiB | previous engine **0.1.45** — same-session A/B arm, kept for comparison |

## Configs

### GSQ-RCO IQ3_XXS + MTP - Strata pack engine

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/iq3_xxs",
               "--native", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf",
               "--expert-profile", "<pack>/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5", "--mtp", "<mtp>/rt",
               "--max-context", "204800", "--kv", "int8", "--vision", "--prompt-cache-every", "5632"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/iq3_xxs/tokenizer",
      "model_name": "qwen3.8-flash-next-iq3xxs",
      "vision": {"exe": "<engine>/strata-vision",
                 "mmproj": "<models>/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
                 "gpu": false, "max_tokens": 1024, "threads": 10},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

## Long-context refactor benchmark

Real-task timing test: a fixed refactor instruction wraps a generated file of near-identical legacy Python templates ([test-prompts.md](../../test-prompts.md)). Same protocol as above ([methodology.md](../../methodology.md) §Measurement methods).

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on | ~10k opencode | 999.4 | **54.5** | 11470 MiB |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on | ~60K | 1034.1 | **50.2** | 11470 MiB |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on | ~120K | 995.4 | **52.5** | 11470 MiB |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.1.45 | on | ~10k opencode | 1056.6 | 43.4 | 11571 MiB |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.1.45 | on | ~60K | 1010.5 | 46.4 | 11571 MiB |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.1.45 | on | ~120K | 983.0 | 44.6 | 11571 MiB |

The two engines were benched back to back on 2026-10-28, both arms on a derived config carrying `--prompt-cache 0` ([engine notes §Validation](../../engine-notes/strata.md)), second pass only, `cache_n` 0 and `predicted_n` 512 on every row. Decode is +25.6% / +8.2% / +17.7%; prefill is **-5.4% on the ~10k prompt** (confirmed by three interleaved re-runs: 0.1.45 1053.1/1054.0/1056.6 vs 0.2.7 998.7/999.1/999.4) and within noise at ~60K/~120K. MTP draft acceptance is *lower* on 0.2.7 (63.9%→50.2% at ~60K, 68.5%→56.7% at ~120K), so the decode gain comes from the kernel table and the route prior, not from drafting. Answers differ between the arms: the 0.2.7 route prior (1.5, applied on ≤13 GiB cards) re-ranks experts.

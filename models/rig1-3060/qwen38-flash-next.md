# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-11-03 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO` quant `IQ3_XXS` (the served quant: a 75.8 GB 2-shard build of these weights) (`qwen4exp`, native ctx 262144, 512 experts, a separate MTP head from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B n-gram embedding table + 4B MTP; 48 layers = 12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared expert per token. Model card: [ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants); MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on | 1077.4 | **54.4** | 11559 MiB | `--kv int8`, CPU vision encoder |

## Configs

### GSQ-RCO IQ3_XXS + MTP - Strata pack engine

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/iq3_xxs",
               "--native", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf",
               "--expert-profile", "<engine>/data/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5", "--mtp", "<mtp>/rt",
               "--mtp-draft-vocab", "<engine>/data/draft_vocab_en.bin",
               "--max-context", "204800", "--kv", "int8", "--vision", "--prompt-cache-every", "5632"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/iq3_xxs/tokenizer",
      "model_name": "qwen3.8-flash-next-iq3xxs",
      "vision": {"exe": "<engine>/strata-vision",
                 "mmproj": "<models>/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
                 "model": "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
                 "gpu": false, "max_tokens": 4096, "min_tokens": 1024, "threads": 8},
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

## Long-context refactor benchmark

Real-task timing test: a fixed refactor instruction wraps a generated file of near-identical legacy Python templates ([test-prompts.md](../../test-prompts.md)). Same protocol as above ([methodology.md](../../methodology.md) §Measurement methods).

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on | ~60K | 1052.4 | **52.5** | 11559 MiB |
| GSQ-RCO IQ3_XXS + MTP | 204800 | Strata 0.2.7 | on | ~120K | 1011.1 | **55.4** | 11559 MiB |

Measured 2026-10-29 on a derived config carrying `--prompt-cache 0` ([engine notes §Validation](../../engine-notes/strata.md)), two measured passes per row (median) with `cache_n` 0 and `predicted_n` 512 throughout. Prefill falls 3.9% from ~60K to ~120K; decode moves with MTP acceptance rather than depth.

## Strata 0.2.10 / engine 0.1.56 (2026-11-03)

App 0.2.10, engine build 0.1.56, replacing the 0.2.7 / 0.1.52 rows above. Served shape otherwise unchanged - ctx 204800, `--kv int8`, `--spec 4 --spec-min-p 0.5`, MTP (`--mtp` pinned, so 0.2.10's new DFlash2 drafter does not engage), the vision block on with the CPU encoder, and `STRATA_PREFILL_LEND_PCT=95` - plus two entry env switches added today that are part of the recorded shape: `STRATA_ROUTE_PRIOR=1.5` and `STRATA_PF_SMALL=0`. Protocol unchanged ([methodology.md](../../methodology.md) §Inference engines, [engine notes §Validation](../../engine-notes/strata.md#validation)): Strata serves no `/v1/completions`, so each row is a `/v1/chat/completions` pass on the standard prompts (10k = `scripts/opencode-10k-prompt.txt`, 10554 prompt tokens; 60k = `generate-long-context-prompt.py --repeats 79`, 59802 tokens; 120k = the same with `--repeats 157`, 119344 tokens) against a derived config carrying `--prompt-cache 0`, no request overrides (served sampling), two passes per prompt with the second recorded - every recorded pass reported `cache_n` 0 and `predicted_n` 512. Timings are the response `timings` object (`prompt_per_second`, `predicted_per_second`, `draft_n` / `draft_n_accepted`).

| prompt | prompt tokens | prefill t/s | decode t/s | MTP draft accepted |
| --- | --- | --- | --- | --- |
| 10k | 10554 | 986.9 | 54.3 | 180 / 354 |
| 60k | 59802 | 1021.7 | 51.8 | 160 / 303 |
| 120k | 119344 | 994.7 | 52.4 | 190 / 341 |

Against the 0.2.7 rows above (10k 1077.4 / 54.4, 60k 1052.4 / 52.5, 120k 1011.1 / 55.4): prefill -8.4% / -2.9% / -1.6%, decode -0.2% / -1.3% / -5.4%. Sub-5% decode deltas are inside this model's run-to-run noise, and decode moves with MTP acceptance rather than depth.

### Arm table (10k prompt unless stated)

Each arm is a separate cold load in the same session, on the same derived `--prompt-cache 0` config:

| arm | prefill t/s | decode t/s |
| --- | --- | --- |
| as-deployed 0.1.56 defaults (no extra switches) | 869.0 | 44.4 |
| + `STRATA_ROUTE_PRIOR=1.5` | 864.7 | 53.5 |
| + `STRATA_ROUTE_PRIOR=1.5` + `STRATA_PF_SMALL=0` | 984.7 | 56.5 |
| same, with `--max-context 180000` instead of 204800 | 1082.7 | 57.5 |
| 60k with `STRATA_ROUTE_PRIOR=1.5` only | 918.3 | 55.3 |
| 120k with `STRATA_ROUTE_PRIOR=1.5` only | 899.8 | 53.9 |

The as-deployed 0.1.56 figures for the last two arms are 922.0 / 43.3 at 60k and 900.7 / 41.9 at 120k.

**Decode - the route prior.** 0.2.8 turned off the route prior that 0.2.7 applied by default to discrete CUDA cards at ≤13 GiB. `STRATA_ROUTE_PRIOR=1.5` restores it and recovers the whole decode loss: 44.4 -> 53.5 at 10k, 43.3 -> 55.3 at 60k, 41.9 -> 53.9 at 120k. Prefill is unaffected by the prior (869.0 vs 864.7). Caveat recorded with the rows: the prior is upstream's own loop suspect - 0.2.8 dropped it because reports tied it to repeated text in long sessions - and these passes are single-turn 512-token runs, so they cannot see that; `STRATA_ROUTE_PRIOR=0` isolates it if a long session ever repeats itself.

**Prefill - the cache reservation and the small-expert path.** Engine 0.1.56 reserves `700 MiB reserved (+75 MiB for the draft head, +256 MiB for what is allocated after the cache)` where 0.1.52 reserved only `+73 MiB for the draft head`, so the auto cache lands 1626 slots / 2.68 GiB instead of 1784 / 2.93 GiB, the prompt path borrows 1481 instead of 1654 slots, and the auto chunk drops 5632 -> 4864 tokens. Below 8192 tokens the engine switches to the new small expert cache prompt path (unfused experts, layer-major walk from two chunks) and prints `strata serve: small expert cache: ...`; `STRATA_PF_SMALL=0` suppresses it and is worth 864.7 -> 984.7 prefill at 10k.

**The ctx-180000 arm, and why the chunk hypothesis was wrong.** At `--max-context 180000` the load reports `4.05 GiB free ... -> 1400 slots` -> 1848 slots / 3.04 GiB, borrow 1712, chunk 5632, and that arm meets or beats the 0.2.7 rows (1082.7 prefill / 57.5 decode at 10k vs 1077.4 / 54.4). It was read at the time as "1848 slots restores the 5632 chunk", and that reading did not survive the DFlash2 test: at ctx 204800 the auto chunk is **6144** and at 1895 slots it stays 6144 (see the drafter section below). The small-cache trigger in 0.1.56 is a fixed `under 8192` test on whatever chunk the window produces, so `STRATA_PF_SMALL=0` is needed at every shape we measured; the ctx-180000 arm only helps through the larger cache, not through clearing the warning.

### Drafter: DFlash2 against MTP (2026-11-03)

0.2.10 makes DFlash2 the default drafter for Qwen3.8 on sm_86. Ours engages only on the base entry, and only because the config asks for it: `--draft dflash2 --draft-model /etc/strata/dflash2/qwen3.8-flash-next-dflash2.q4_0-selq4.pack --draft-fallback none` (no `--mtp DIR`; `--mtp-draft-vocab` is still required). Same protocol config and env as the rows above; only the drafter differs.

| arm | 10k | 60k | 120k |
| --- | --- | --- | --- |
| MTP (1035 MiB layer, 1626 slots) | 986.9 / 54.3 | 1021.7 / 51.8 | 994.7 / 52.4 |
| DFlash2, Q4_0 matrices + Q4_0 selector (478 MiB, 1895 slots), run 1 / run 2 | 1081.8 / 55.0 · 1079.3 / 53.9 | 1075.5 / 53.9 · 1072.3 / 52.0 | 1032.7 / 53.4 · 1031.4 / 56.3 |
| DFlash2, Q8_0 matrices + Q4_0 selector (705 MiB, 1761 slots) | 1085.2 / 56.6 | 1041.9 / 50.4 | 1010.2 / 49.9 |
| DFlash2 Q4_0, `STRATA_PF_SMALL=0` removed | 1084.2 / 58.1 | 967.5 / 49.4 | 934.5 / 57.9 |

**Prefill is the finding; decode is not.** Prefill repeats to ±5 t/s across every DFlash2 load, and the Q4_0-matrices pack is +9% at 10k, +5% at 60k, +4% at 120k over MTP - the mechanism is the VRAM: DFlash2 is 478 MiB where the MTP layer is 1035 MiB, so `--expert-cache auto` takes 1895 slots / 3.12 GiB instead of 1626 / 2.68 GiB and the prompt path borrows 1767 slots rather than 1481. Decode moves 1-3 t/s between runs of the *same* arm (120k: 53.4 vs 56.3 on Q4_0, 49.9 vs 56.8 on Q8_0), which is the same size as any drafter-to-drafter difference, so no decode claim is made in either direction. Draft proposals rise (DFlash2 offers 330-435 per 512 tokens against MTP's 303-354) without a matching rise in acceptance.

The engine states its own view at load: `--draft dflash2: on a 12 GB NVIDIA card the MTP drafter was faster in most measurements (code prompts at a window of 6 gained 3%); continuing as asked`. Upstream's one-card acceptance table has no sm_86 row (sm_120 +6.23% short / +1.38% at 2K sampled, Arc -2.6%).

**Two packing facts that decide whether drafting runs at all.** `tools/dflash2_pack.py --q4_0-selector` quantizes the *matrices* as well as the selector (the flag sets `q4` in the CLI), so Q8_0 matrices need a two-step: pack plain, then `--convert-selector`. And the serve layer only treats the drafter as downloaded when `dflash2/qwen3.8-flash-next-dflash2.q4_0.pack` (522,458,112 B, `PACK_SHA256`) exists - a pack under any other name is ignored and drafting silently switches off.

**The swift entry stays on MTP.** `terminal/serve/drafting.py` restricts DFlash2 to `SUPPORTED_FAMILIES = ("qwen","gyro","unsloth")` - not Swift fine-tunes - and strips hand-set flags, so asking for it there leaves the entry with no speculative decoding at all rather than falling back.

**`STRATA_PF_SMALL=0` is still required on both entries.** With DFlash2 at 1895 slots the auto chunk is 6144, still under the engine's 8192 test: removing the switch cost -9.8% prefill at 60k (1079.5 -> 967.5) and -9.4% at 120k, decode flat.

**Unchanged on 0.1.56.** The sm_86 nine-switch default table, the CPU vision encoder (`strata-vision: model files loaded in 1.0 s`; an image request reports prompt_n 1091 against the 1024-token floor), and 679-775 MiB of free VRAM with everything loaded depending on the drafter.

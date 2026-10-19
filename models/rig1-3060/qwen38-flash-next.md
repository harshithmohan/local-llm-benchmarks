# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-19 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO` quants `Q2_0` (2.40 bpw) and `IQ3_XXS` (the larger 75.8 GB 2-shard quant of the same weights) (`qwen4exp`, native ctx 262144, 512 experts, a separate MTP head from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B n-gram embedding table + 4B MTP; 48 layers = 12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared expert per token. Model card: [ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants); MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF). The **Swift 1.5** fine-tune of this base is a separate checkpoint with its own pack, layer/shard boundary and expert mix - retired 2026-10-09: [archive/swift-qwen38-flash-next.md](archive/swift-qwen38-flash-next.md).

**`Q2_0` retired 2026-10-13** - dropped from the serving configuration (the checkpoint, pack and config JSON stay on disk); its record is in the [full experiment log](archive/qwen38-flash-next.md). `IQ3_XXS` is the served quant.

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | 1054.4 | **48.9** | 11557 MiB | `--kv int8`, `--expert-cache auto`, `--prefill auto` + `STRATA_PREFILL_LEND_PCT=95` in the server env -> 5632 chunk (1784-slot cache); the five 0.1.45 CUDA decode switches are on |

## Configs

### GSQ-RCO IQ3_XXS + MTP - Strata pack engine

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/iq3_xxs",
               "--native", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf",
               "--expert-profile", "<pack>/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5", "--mtp", "<mtp>/rt",
               "--max-context", "200000", "--kv", "int8", "--prompt-cache-every", "5632"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/iq3_xxs/tokenizer",
      "model_name": "qwen3.8-flash-next-iq3xxs",
      "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20,
                   "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    }

Launched with `STRATA_PREFILL_LEND_PCT=95` in the server's environment (the entry's `env:` list) so the auto scan takes the 5632 chunk. The `--prefill auto` scan takes the 5632-token chunk at 200000 - a 227-slot ring borrowing 1655 of the 1784 cache slots - but only at the 95% lend cap: the default 90% cap allows at most 1608 slots and rules the 5632 chunk out. An explicit `--prefill` pin can never reach 5632: a pin that does not fit is clamped by a halving walk from the requested value (measured: `--prefill 6144` -> 3072, `--prefill 5632` -> 2816), and the pin's walk keeps the default 384-slot prefill ring - the byte-budget ring sizing is an `auto`-only feature, so the same chunk fits more easily under auto than under a pin (5632 fits under auto's 227-slot ring, not under a pin's 384-slot one). `auto` bisects the fine 256-token grid and sizes its own ring, which is how it finds 5632; a pin can therefore never beat `auto`. [Full experiment log, including the clamped-3072 shape](archive/qwen38-flash-next.md).

A different engine on the same weights, not a `llama-server` flag set: `strata` is a stdio backend, and the HTTP API plus every run setting (the `exe` and its `args`, `cwd`, tokenizer, model name, log path) live in a JSON config read by the engine's own Python server - see [engine-notes/strata.md](../../engine-notes/strata.md). The engine takes its flags from that config's `args` and from nowhere else: the server is started with `--config <file>`, and an engine flag on that command line is a startup error, so a second window would be a second config that differs in `--max-context`, `--prefill`, `--prompt-cache-every`, `model_name` and `log`. Prefill measurements add `--prompt-cache 0`, which is a measurement setting and not part of a served config.

Sampling rides in the same JSON: the engine's serve path ignores sampling flags on the command line, so the `sampling` object is the only lever, and the engine's own serve-path default is greedy (`temperature 0.0`) - `temperature 1.0` here is the one deliberate change. A request field still overrides it.

## Notes

- **MTP is on.** The Strata config takes its draft runtime from the pack (`--mtp <mtp>/rt --spec 4 --spec-min-p 0.5`), and every measured pass reported `draft_n` and `draft_n_accepted`.
- Prefill/decode come from the second pass after a cold load; the first pass is a page-in pass and is excluded.
- Rows re-measured 2026-10-15 on **Strata engine 0.1.44.1**; the 0.1.41 figures are in the [full experiment log](archive/qwen38-flash-next.md). Decode gained +6% (120K) to +19% (10k) with 0.1.42+'s route-tail-skip default; prefill is unchanged within 0.5% at every prompt size.
- **Rows re-measured 2026-10-19 on Strata 0.1.45**, which is the served engine, with its five CUDA decode switches on (`STRATA_ATTN_DAILY`, `STRATA_EXPDEC`, `STRATA_SIDE_MIXER`, `STRATA_B6_MMVQ_ROWS`, `STRATA_QSA_SPLIT_ATTN`). Same-session A/B on the 10k prompt: 42.7 t/s with them against 40.8 without (+4.5%). Decode is session-sensitive on this model: three cold sessions of the identical 10k shape on this build read **48.9, 43.6 and 47.2** t/s (same 1784-slot cache and 11557 MiB, no throttling: 1995-2032 MHz, 63-71 °C), and the 17-pass A/B arms sat at 40.8-42.7. Treat an absolute row as one session's number and compare rows only within a session. The 0.1.44.1 figures and the switch A/B are in the [full experiment log](archive/qwen38-flash-next.md#engine-0145-and-the-cuda-decode-switches-2026-10-19).
- **The Strata rows use a different request protocol** than the llama.cpp rows in the experiment log: the pack engine's `/v1/chat/completions` with a chat template and `--prompt-cache 0`, which is why the prompts tokenize to 10554 (10k) / 59802 (60K) / 119344 (120k) tokens. Both passes reported `cache_n` 0 and a full 512-token decode window, with no sampling overrides (the served `temperature 1.0` applies); the 60K and 120K rows double as the large-prompt stability check.
- The retired moe-cache fork config and its tuning record are in the [full experiment log](archive/qwen38-flash-next.md).
- **IQ3_XXS:** a two-shard quant - 47.0 GB weights (shard 1) + the same 28.8 GB n-gram table (shard 2), 75.8 GB total; its pack is built from shard 1 and uses the shared 512-expert expert profile.
- **IQ3_XXS now decodes at or above the retired Q2_0 at every prompt size**: 48.9 vs 44.2 at 10k, 49.7 vs 42.4 at 60K, 43.7 vs 41.8 at 120K, on a smaller expert cache (1784 vs 2670 slots) and a lower hit rate (63-66% vs ~77-78%). The Q2_0 figures are 0.1.41 numbers (that quant was retired 2026-10-13 and not re-measured), so the comparison crosses engine versions - on the 0.1.44.1 rows the same quant was still 5-9% behind. Prefill is near-parity with Q2_0 at the 5632 chunk (1054.4 vs 1058.5 at 10k).

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)): a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same measurement protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement methods) - cold load, with each row using its engine's KV setting from the config sections above.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | ~60K | 1022.2 | **49.7** | 11557 MiB | 59802-token prompt, `--prompt-cache 0`, 5632 chunk (`--prefill auto`, PCT 95); passes 48.0 / 49.7 |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | ~120K | 984.3 | **43.7** | 11557 MiB | 119344-token prompt, `--prompt-cache 0`, 5632 chunk (`--prefill auto`, PCT 95); passes 44.2 / 43.7 |

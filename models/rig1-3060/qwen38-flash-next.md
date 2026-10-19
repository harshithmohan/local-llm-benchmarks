# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-19 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO` quants `Q2_0` (2.40 bpw) and `IQ3_XXS` (the larger 75.8 GB 2-shard quant of the same weights) (`qwen4exp`, native ctx 262144, 512 experts, a separate MTP head from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B n-gram embedding table + 4B MTP; 48 layers = 12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared expert per token. Model card: [ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants); MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF). The **Swift 1.5** fine-tune of this base is a separate checkpoint with its own pack, layer/shard boundary and expert mix - retired 2026-10-09: [archive/swift-qwen38-flash-next.md](archive/swift-qwen38-flash-next.md).

**`Q2_0` retired 2026-10-13** - dropped from the serving configuration (the checkpoint, pack and config JSON stay on disk); its record is in the [full experiment log](archive/qwen38-flash-next.md). `IQ3_XXS` is the served quant.

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | 1054.2 | **43.4** | 11571 MiB | `--kv int8`, `--expert-cache auto`, `--prefill auto` + `STRATA_PREFILL_LEND_PCT=95` in the server env -> 5632 chunk (1781-slot cache); the five 0.1.45 CUDA decode switches are on and the vision encoder is enabled (CPU, see the vision note) |

## Configs

### GSQ-RCO IQ3_XXS + MTP - Strata pack engine

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/iq3_xxs",
               "--native", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf",
               "--expert-profile", "<pack>/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5", "--mtp", "<mtp>/rt",
               "--max-context", "200000", "--kv", "int8", "--vision", "--prompt-cache-every", "5632"],
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

Launched with `STRATA_PREFILL_LEND_PCT=95` in the server's environment (the entry's `env:` list) so the auto scan takes the 5632 chunk. The `--prefill auto` scan takes the 5632-token chunk at 200000 - a 227-slot ring borrowing 1655 of the 1784 cache slots - but only at the 95% lend cap: the default 90% cap allows at most 1608 slots and rules the 5632 chunk out. An explicit `--prefill` pin can never reach 5632: a pin that does not fit is clamped by a halving walk from the requested value (measured: `--prefill 6144` -> 3072, `--prefill 5632` -> 2816), and the pin's walk keeps the default 384-slot prefill ring - the byte-budget ring sizing is an `auto`-only feature, so the same chunk fits more easily under auto than under a pin (5632 fits under auto's 227-slot ring, not under a pin's 384-slot one). `auto` bisects the fine 256-token grid and sizes its own ring, which is how it finds 5632; a pin can therefore never beat `auto`. [Full experiment log, including the clamped-3072 shape](archive/qwen38-flash-next.md).

A different engine on the same weights, not a `llama-server` flag set: `strata` is a stdio backend, and the HTTP API plus every run setting (the `exe` and its `args`, `cwd`, tokenizer, model name, log path) live in a JSON config read by the engine's own Python server - see [engine-notes/strata.md](../../engine-notes/strata.md). The engine takes its flags from that config's `args` and from nowhere else: the server is started with `--config <file>`, and an engine flag on that command line is a startup error, so a second window would be a second config that differs in `--max-context`, `--prefill`, `--prompt-cache-every`, `model_name` and `log`. Prefill measurements add `--prompt-cache 0`, which is a measurement setting and not part of a served config.

Images ride in the same JSON: `--vision` plus a `vision` object naming the `strata-vision` encoder, an mmproj and the native shard. `"gpu": false` puts the encoder on the CPU, which is what this 12 GB card needs - the GPU encoder holds ~1.4 GB of VRAM, and the engine only adds its `--vram-reserve-mib 700` (the VRAM it would set aside for the encoder) when `"gpu"` is true. Image parts are then preprocessed into prompt tokens like any other content.

Sampling rides in the same JSON: the engine's serve path ignores sampling flags on the command line, so the `sampling` object is the only lever, and the engine's own serve-path default is greedy (`temperature 0.0`) - `temperature 1.0` here is the one deliberate change. A request field still overrides it.

## Notes

- **MTP is on.** The draft runtime comes from the pack (`--mtp <mtp>/rt --spec 4 --spec-min-p 0.5`); every pass reports `draft_n` / `draft_n_accepted`.
- Prefill/decode come from the second pass after a cold load; the first is a page-in pass and is excluded.
- **Engine 0.1.45** (served since 2026-10-19) with the five CUDA decode switches on (+4.5% decode in a same-session 10k A/B) and the vision encoder enabled. Decode also moves with MTP draft acceptance from session to session - 28 passes of the 10k prompt span **40.8-46.9 t/s, mean 43.2** - so compare rows only within a session. The 0.1.44.1 rows and the switch A/B are in the [full experiment log](archive/qwen38-flash-next.md).
- **Protocol:** `/v1/chat/completions` with the chat template and `--prompt-cache 0` (a measurement setting, not the served shape), which tokenizes the prompts to 10554 / 59802 / 119344. Every recorded pass reported `cache_n` 0 and a full 512-token window.
- **Vision** (added 2026-10-19): `--vision` plus a `vision` block, with the encoder on the **CPU** (BF16 mmproj, ~1.35 GB of RAM while the engine is loaded). It costs nothing measurable on the text path; a picture is charged to the prompt at ~300 tokens for 640x480 and ~970 for 1280x960. Encoder tests are in the [full experiment log](archive/qwen38-flash-next.md#vision-encoder-2026-10-19).
- **IQ3_XXS:** a two-shard quant - 47.0 GB of weights plus the 28.8 GB n-gram table (75.8 GB total). Against the retired `Q2_0` it is within ~2% at 10k and 60K and ~10% behind at 120K (smaller expert cache), so the two read as close rather than ranked.

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)): a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same measurement protocol as the recommended configs ([methodology.md](../../methodology.md) §Measurement methods) - cold load, with each row using its engine's KV setting from the config sections above.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | ~60K | 1027.3 | **43.0** | 11571 MiB | 59802-token prompt, `--prompt-cache 0`, 5632 chunk (`--prefill auto`, PCT 95); passes 40.8 / 43.0 |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | ~120K | 987.8 | **37.8** | 11571 MiB | 119344-token prompt, `--prompt-cache 0`, 5632 chunk (`--prefill auto`, PCT 95); passes 39.9 / 37.8 |

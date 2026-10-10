# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-10 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO` quants `Q2_0` (2.40 bpw) and `IQ3_XXS` (the larger 75.8 GB 2-shard quant of the
same weights) (`qwen4exp`, native ctx 262144, 512 experts, a separate MTP head from the
ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B
n-gram embedding table + 4B MTP; 48 layers =
12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared
expert per token. Model card:
[ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants);
MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF). The
**Swift 1.5** fine-tune of this base is a separate checkpoint with its own pack, layer/shard
boundary and expert mix - retired 2026-10-09:
[archive/swift-qwen38-flash-next.md](archive/swift-qwen38-flash-next.md).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO Q2_0 + MTP | 200000 | Strata | on | 1058 | **44** | 11498 MiB | `--kv int8`, `--expert-cache auto`, `--prefill 6144`, standalone pack engine |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | 1017.6 | **35.1** | 11498 MiB | `--kv int8`, `--expert-cache auto`, `--prefill auto` + `STRATA_PREFILL_LEND_PCT=95` in the server env -> 5632 chunk (1791-slot cache) |

## Configs

### GSQ-RCO Q2_0 + MTP - Strata pack engine

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/q2_0",
               "--native", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf",
               "--expert-profile", "<pack>/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "6144", "--spec", "4", "--spec-min-p", "0.5", "--mtp", "<mtp>/rt",
               "--max-context", "200000", "--kv", "int8", "--prompt-cache-every", "6144"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/q2_0/tokenizer",
      "model_name": "qwen3.8-flash-next-q2_0"
    }

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
      "model_name": "qwen3.8-flash-next-iq3xxs"
    }

Launched with `STRATA_PREFILL_LEND_PCT=95` in the server's environment (the entry's `env:`
list) so the auto scan takes the 5632 chunk. The `--prefill auto` scan takes the 5632-token
chunk at 200000 - a 227-slot ring borrowing 1654 of the 1791 cache slots - but only at the
95% lend cap: the default 90% cap allows at most 1612 slots and rules the 5632 chunk out. An
explicit `--prefill` pin can never reach 5632: a pin that does not fit is clamped by a halving
walk from the requested value (measured: `--prefill 6144` -> 3072, `--prefill 5632` -> 2816),
and the pin's walk keeps the default 384-slot prefill ring - the byte-budget ring sizing is an
`auto`-only feature, so the same chunk fits more easily under auto than under a pin (5632 fits
under auto's 227-slot ring, not under a pin's 384-slot one). `auto` bisects the fine
256-token grid and sizes its own ring, which is how it finds 5632; a pin can therefore never
beat `auto`. [Full experiment log, including the clamped-3072 shape](archive/qwen38-flash-next.md).

A different engine on the same weights, not a `llama-server` flag set: `strata` is a stdio
backend, and the HTTP API plus every run setting (the `exe` and its `args`, `cwd`,
tokenizer, model name, log path) live in a JSON config read by the engine's own Python
server - see [engine-notes/strata.md](../../engine-notes/strata.md). The engine takes its
flags from that config's `args` and from nowhere else: the server is started with
`--config <file>`, and an engine flag on that command line is a startup error, so a second
window would be a second config that differs in `--max-context`, `--prefill`,
`--prompt-cache-every`, `model_name` and `log`. Prefill measurements add `--prompt-cache 0`,
which is a measurement setting and not part of a served config.

## Notes

- GSQ-RCO Q2_0 is a two-shard quant: shard 1 of 2 is the transformer and shard 2 is the
  28.8 GB n-gram table. The Strata config passes them as `--native` (shard 1) and `--ple-gguf`
  (shard 2).
- **MTP is on.** The Strata config takes its draft runtime from the pack
  (`--mtp <mtp>/rt --spec 4 --spec-min-p 0.5`), and every measured pass reported `draft_n`
  and `draft_n_accepted`.
- **The Q2_0 config pins `--prefill 6144` because `--prefill auto` would step the chunk down
  with a wider window** (8192 -> 6144 -> 4096 as the expert-cache loan shrinks); at 200000 the
  6144 pin fits the 2670-slot cache. The chunk ladder and the loan caps are in the
  [full experiment log](archive/qwen38-flash-next.md).
- Prefill/decode come from the second pass after a cold load; the first pass is a page-in
  pass and is excluded.
- **The Strata rows use a different request protocol** than the llama.cpp rows in the
  experiment log: the pack engine's `/v1/chat/completions` with a chat template and
  `--prompt-cache 0`, which is why the prompts tokenize to 10507 (10k) / 59802 (60K) / 119344
  (120k) tokens. Both passes reported `cache_n` 0 and a full 512-token decode window; the 60K
  and 120K rows double as the large-prompt stability check.
- The retired moe-cache fork config and its tuning record are in the
  [full experiment log](archive/qwen38-flash-next.md).
- **IQ3_XXS:** a two-shard quant - 47.0 GB weights (shard 1) + the same 28.8 GB n-gram table
  (shard 2), 75.8 GB total; its pack is built from shard 1 and uses the shared 512-expert
  expert profile.
- **IQ3_XXS decode is below Q2_0 at every prompt size**: 35.1 vs 44.2 at 10k (-21%),
  35.6 vs 42.4 at 60K (-16%), 36.0 vs 41.8 at 120K (-14%): the expert cache is smaller
  (1791 vs 2670 slots) and its decode hit rate is lower (61-73% vs ~77-78%). Prefill is
  near-parity with Q2_0 at the 5632 chunk - within 6% at every prompt size
  (1017.6 vs 1058.5 at 10k).

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of
near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same
measurement protocol as the recommended configs ([methodology.md](../../methodology.md)
§Measurement methods) - cold load, with each row using its engine's KV setting from the config
sections above.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO Q2_0 + MTP | 200000 | Strata | on | ~60K | 1045 | **42** | 11498 MiB | 59802-token prompt, `--kv int8`, `--prompt-cache 0` |
| GSQ-RCO Q2_0 + MTP | 200000 | Strata | on | ~120K | 1008 | **42** | 11498 MiB | 119344-token prompt, `--kv int8`, `--prompt-cache 0` |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | ~60K | 988.7 | **35.6** | 11498 MiB | 59802-token prompt, `--prompt-cache 0`, 5632 chunk (`--prefill auto`, PCT 95); decode is the mean of a 4-pass check (34.1-36.5) after a 41.1 pass proved unreproducible |
| GSQ-RCO IQ3_XXS + MTP | 200000 | Strata | on | ~120K | 954.9 | **36.0** | 11498 MiB | 119344-token prompt, `--prompt-cache 0`, 5632 chunk (`--prefill auto`, PCT 95) |

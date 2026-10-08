# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-08 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO Q2_0` (`qwen4exp`, 2.40 bpw, native ctx 262144, 512 experts, a separate MTP head
from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B
n-gram embedding table + 4B MTP; 48 layers =
12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared
expert per token. Model card:
[ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants);
MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF). The
**Swift 1.5** fine-tune of this base is a separate checkpoint with its own pack, layer/shard
boundary and expert mix: [swift-qwen38-flash-next.md](swift-qwen38-flash-next.md).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO Q2_0 + MTP | 200000 | Strata | on | 1058 | **44** | 11498 MiB | `--kv int8`, `--expert-cache auto`, `--prefill 6144`, standalone pack engine |

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
- **The window sets the prompt chunk when the chunk is left to `auto`, so the served config
  pins it instead.** With `--prefill auto` the chunk is what the expert cache can lend, and
  `--max-context` is what shrinks that cache, so a wider window steps the chunk down
  (8192 -> 6144 -> 4096) and costs prefill. An explicit `--prefill` is the operator's number
  and only has to fit, so the served window keeps its chunk: 200000 lands a 2670-slot cache
  and borrows 2427 for the 6144 chunk, with ~475 MiB free. The window itself still costs: at a
  pinned cache and chunk, 122880 -> 149000 was 8.1% on the same prompt, and free VRAM does not
  buy the chunk back, the cache share does. Measured on the served config on engine 0.1.40.2:
  1058 / 44.2 (10k), 1045 / 42.4 (60K), 1008 / 41.8 (120k). The ladder and the loan caps are in
  the [full experiment log](archive/qwen38-flash-next.md).
- Prefill/decode come from the second pass after a cold load; the first pass is a page-in
  pass and is excluded.
- **The Strata rows are a different engine on a different request protocol.** They come from
  the standalone pack engine through its own `/v1/chat/completions` route - a chat template is
  always applied - with `--prompt-cache 0` in the engine args, which is why the prompt
  tokenizes to 10507 (10k) / 59802 (60K) rather than the llama.cpp counts. Not directly
  comparable with the moe-cache fork rows in the experiment log; both Strata passes reported
  `cache_n` 0 and a full 512-token decode window, and the 60K and 120K passes serve as the
  large-prompt stability check.
- The retired moe-cache fork config and its tuning record are in the
  [full experiment log](archive/qwen38-flash-next.md).

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

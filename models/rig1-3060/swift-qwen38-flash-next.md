# Swift-1.5-Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-08 · [full experiment log](archive/swift-qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO IQ2_XS` (`qwen4exp`, 3.08 bpw overall / 2.35 bpw over the routed experts, native ctx
262144, 512 experts, a separate MTP head from the ggml-org repo - the GSQ-RCO release ships
none - and the same one the base model's config uses). The **Swift-1.5 fine-tune** of
Qwen3.8-Flash-Next: same architecture as the base model's Q2_0, a different layer/shard
boundary and a different expert mix - see Notes. Base model:
[qwen38-flash-next.md](qwen38-flash-next.md). Model card:
[ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ2_XS + MTP | 200000 | Strata | on | 1004 | **47** | 11360 MiB | default: `--kv int8`, `--expert-cache auto` (2590 slots), `--prefill 6144`, standalone pack engine; the 10k pass ends at 305 tokens on tool calls - see Notes |

## Configs

### GSQ-RCO IQ2_XS + MTP - Strata pack engine at 200000

    {
      "exe": "<engine>/strata",
      "args": ["--pack", "<pack>/swift-iq2_xs",
               "--native", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf",
               "--ple-gguf", "<models>/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf",
               "--expert-profile", "<pack>/expert-profile.bin", "--expert-cache", "auto",
               "--prefill", "6144", "--spec", "4", "--spec-min-p", "0.5", "--mtp", "<mtp>/rt",
               "--max-context", "200000", "--kv", "int8", "--prompt-cache-every", "6144"],
      "cwd": "<engine>",
      "tokenizer": "<pack>/swift-iq2_xs/tokenizer",
      "model_name": "swift-1.5-iq2_xs"
    }

A different engine on the same weights, not a `llama-server` flag set: `strata` is a stdio
backend, and the HTTP API plus every run setting (the `exe` and its `args`, `cwd`,
tokenizer, model name, log path) live in a JSON config read by the engine's own Python
server - see [engine-notes/strata.md](../../engine-notes/strata.md). The engine takes its
flags from that config's `args` and from nowhere else: the server is started with
`--config <file>`, and an engine flag on that command line is a startup error. Prefill
measurements add `--prompt-cache 0`, which is a measurement setting and not part of a served
config.

The pack is built from shard 1 alone - `iq_pack.py --gguf <shard1> --out <pack>` - because the
base-model `--base` reuse is refused for this split (it needs every tensor in shard 1, and
shard 2 carries layers 13-47). The per-layer embedding table stays out of the pack
(`per_layer_token_embd.weight` is never packed) and is read from the GGUF shard given to
`--ple-gguf`.

## Notes

- **`--ple-gguf` is shard 1 here, and the shard split is not the base model's.** The base Q2_0
  keeps all 48 layers in shard 1 and puts the 28.8 GB per-layer embedding table alone in
  shard 2; Swift 1.5 puts the table in shard 1 and breaks at layer 13 (shard 1 holds layers
  0-13, shard 2 layers 13-47, with layer 13's attention tensors in shard 1 and its MoE tensors
  in shard 2). Copying the base config's `--native`/`--ple-gguf` pair points the table at a
  shard that has none. The layer-13 split is attention-vs-MoE, not expert rows split across
  shards, so it does not break the pack tool; the shards' own `split.no` values are in the
  right order and are not swapped.
- **MTP is on.** The draft runtime is the base model's (`--mtp <mtp>/rt --spec 4
  --spec-min-p 0.5`), and every measured pass reported `draft_n` and `draft_n_accepted`.
- **The served chunk is pinned, not `auto`.** With `--prefill auto` this pack lands a
  5632-token chunk (a 2590-slot expert cache, 2260 slots borrowed = 87%), because `auto` only
  takes a chunk whose buffers stay within 90% of the resident cache. An explicit `--prefill`
  skips that rule and only has to fit, and 6144 (2454 slots borrowed = 95%) measured **~1.5%
  faster prefill** at 10k, 60K and 120K with decode unchanged, so the served config pins
  6144 with `--prompt-cache-every 6144`. 8192 does not fit for this pack - it clamps to 4096 -
  and the halving rule never tests 6144, so a pinned chunk is the only way to land on it. 476
  MiB of VRAM stays free with everything loaded.
- **The ~10k opencode prompt ends early on this fine-tune.** Swift 1.5 leaves its reasoning
  and emits an opencode-style tool call (`finish_reason: tool_calls`, `content` null, a few
  `grep`/`read`/`glob` calls) after 305-348 tokens, imitating the tool-call format the 10k
  prompt itself documents; the base model on the same payload stays in `reasoning_content` and
  reaches the full 512-token window. So the 10k row's decode is measured over ~305 tokens, not
  512, and the row would otherwise read as a window that was cut short. `tool_choice: "none"`
  and an empty `tools` array do not suppress the calls. The generated ~60K and ~120K prompts
  do not trigger it - those rows reach the full window.
- Prefill/decode come from the second pass after a cold load; the first pass is a page-in
  pass and is excluded. Every recorded pass reported `cache_n` 0, `predicted_n` as listed, and
  `0 checkpoints`.
- **The Strata rows are a different engine on a different request protocol.** They come from
  the standalone pack engine through its own `/v1/chat/completions` route - a chat template is
  always applied - with `--prompt-cache 0` in the engine args, which is why the prompt
  tokenizes to 10507 (10k) / 59802 (60K) / 119344 (120K). Read the last two as the
  large-prompt stability check.

## Long-context refactor benchmark

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) Python file of
near-identical legacy templates - 79 repeats for the ~60K prompt, 157 for the ~120K one. Same
measurement protocol as the recommended configs ([methodology.md](../../methodology.md)
§Measurement methods) - cold load, with each row using its engine's KV setting from the config
sections above.

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO IQ2_XS + MTP | 200000 | Strata | on | ~60K | 994 | **41** | 11360 MiB | 59802-token prompt, `--kv int8`, `--prompt-cache 0` |
| GSQ-RCO IQ2_XS + MTP | 200000 | Strata | on | ~120K | 956 | **43** | 11360 MiB | 119344-token prompt, `--kv int8`, `--prompt-cache 0` |

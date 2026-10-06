# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-06 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO Q2_0` (`qwen4exp`, 2.40 bpw, native ctx 262144, 512 experts, a separate MTP head
from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B
n-gram embedding table + 4B MTP; 48 layers =
12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared
expert per token. Model card:
[ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants);
MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO Q2_0 + MTP | 81920 | Strata | on | 1061 | **44** | 11514 MiB | `--kv int8`, `--expert-cache auto`, standalone pack engine |

## Configs

### GSQ-RCO Q2_0 80k + MTP - Strata pack engine

    strata --serve --pack <pack>/q2_0 \
      --native <models>/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
      --ple-gguf <models>/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf \
      --expert-profile <pack>/expert-profile.bin --expert-cache auto \
      --prefill auto --mtp <mtp>/rt --spec 4 --spec-min-p 0.5 \
      --max-context 81920 --kv int8

A different engine on the same weights, not a `llama-server` flag set: `strata` is a stdio
backend, and the HTTP API plus every run setting (the `exe` and its `args`, `cwd`,
tokenizer, model name, log path) live in a JSON config read by the engine's own Python
server - see [engine-notes/strata.md](../../engine-notes/strata.md). Prefill measurements
add `--prompt-cache 0`, which is a measurement setting and not part of a served config.

## Notes

- GSQ-RCO Q2_0 is a two-shard quant: shard 1 of 2 is the transformer and shard 2 is the
  28.8 GB n-gram table. The Strata config passes them as `--native` (shard 1) and `--ple-gguf`
  (shard 2).
- **MTP is on.** The Strata config takes its draft runtime from the pack
  (`--mtp <mtp>/rt --spec 4 --spec-min-p 0.5`), and every measured pass reported `draft_n`
  and `draft_n_accepted`.
- Prefill/decode come from the second pass after a cold load; the first pass is a page-in
  pass and is excluded.
- **The Strata rows are a different engine on a different request protocol.** They come from
  the standalone pack engine through its own `/v1/chat/completions` route - a chat template is
  always applied - with `--prompt-cache 0` in the engine args, which is why the prompt
  tokenizes to 10507 (10k) / 59802 (60K) rather than the llama.cpp counts. Not directly
  comparable with the moe-cache fork rows in the experiment log; both Strata passes reported
  `cache_n` 0 and a full 512-token decode window, and the 60K pass served as the
  large-prompt stability check.
- The retired moe-cache fork config and its tuning record are in the
  [full experiment log](archive/qwen38-flash-next.md).

## Long-context refactor benchmark (~60K prompt)

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) ~60K-token Python
file of 79 near-identical legacy templates. Same measurement protocol as the recommended
configs ([methodology.md](../../methodology.md) §Measurement methods) - cold load, with each
row using its engine's KV setting from the config sections above.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO Q2_0 + MTP | 81920 | Strata | on | 1093 | 43 | 11474 MiB | 59802-token prompt, `--kv int8`, `--prompt-cache 0` |

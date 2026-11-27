# Speedy

Measured, tuned fork of [Strata](strata.md) by [DevDock-AI/Speedy](https://github.com/DevDock-AI/Speedy), MIT. Installed: Speedy **0.5.5**, engine build **0.1.53**, tag commit `1f172963`; prebuilt sm_86 CUDA release. The release archive contains the engine binary only; the OpenAI/Anthropic API layer comes from the source tree's `serve/` and `strata_control/` Python packages and runs on the Strata terminal's bundled CPython. Same pack format, tokenizer and API surface as Strata; it uses a pack per quant, the base model's MTP head and the `strata-vision` reader.

## What changes against Strata

- **Production defaults.** The engine applies 12 built-in production defaults at startup; `STRATA_UPSTREAM_DEFAULTS=1` turns them off. Do not set that switch on a served entry.
- **MTP.** The 1x preset recommends MTP on this 12 GB card (`--mtp <mtp>/rt`); DFlash2 is compiled in but is not the recommended drafter here.
- **Runtime flags.** `--kv-resident`, `--conversation-cache-mib`, `--adapt-async`, `--adapt-swaps` and `--pool-affinity` are Speedy-specific; the preset's `env` block carries the rest. Put `STRATA_KEEP_EMPTY_TURNS=1` in the llama-swap entry `env:`, not the config JSON; `serve/frontend.py` reads it from the server process before the engine is spawned.
- **Vision.** The engine accepts `--vision`, but the release does not ship the separate `strata-vision` reader. Place a CLI/protocol-compatible reader at the engine-folder root (not `build/`) and add the `vision` block.
- **API.** Same as Strata: no raw `/v1/completions`; benchmark through `/v1/chat/completions` with the chat template applied.

## Installed behavior

- **Reasoning effort.** The served configs default to `reasoning_effort:"high"` (the Qwen template's **xhigh** level) with `reasoning_budget_tokens:0` (no cap). The serve layer has a server-side effort floor, default `low`: a config-level `reasoning_effort:"none"` is raised to `low` for tool-bearing requests. All three configs pin `"reasoning_effort_floor": "off"`; an explicit client `none`/`enable_thinking:false` is respected. `serve/test_effort_floor.py` covers the client-off case.
- **Tool-name constraining** is on by default and lets the model write the name, masking only when no declared name can follow; the startup INFO line reports `tool_name_constraint=%d` (`tnc_format = o.batch>0 ? 0 : 2`). The loop breaker and the "says X does Y" intent guard are on by default.
- **Suffix n-gram 8** (`STRATA_SUFFIX_NGRAM8`) is on by default: a second 2^19-slot table, +16 MiB host RAM. `STRATA_SUFFIX_NGRAM8=0` disables it.
- **Tuned MTP drafter** is optional. The serve layer can use a coding-tuned `dense.bin` in `mtp/rt-tuned`; the served config keeps `--mtp /etc/strata/mtp/rt` and falls back to the stock drafter. `STRATA_MTP_DRAFTER=stock` pins the stock head.

## Serving checks

- Cold-load and `/v1/chat/completions` work on all three entries; `--prompt-cache 0` benchmark runs use `cache_n` 0, `predicted_n` 512 and record the second pass.
- The 200K UD run reaches 200636 prompt tokens at 1096.5 t/s prefill / 45.8 t/s decode.
- Serve suite: 1757 tests, one failure + one error, both known non-product (`test_git_update_and_rollback` needs `git`; `IncrementalPrompts.test_turns` at `serve/test_server.py:2071`). llama-swap E2E passes on all three entries, including tool calls and a vision request on the base entry.

## Measurement

Rows are on the [Qwen3.8-Flash-Next](../models/rig1-3060/qwen38-flash-next.md) and [Swift-1.5-Qwen3.8-Flash-Next](../models/rig1-3060/swift-qwen38-flash-next.md) model pages, measured under the Strata protocol with a derived `--prompt-cache 0` config: two passes, second recorded, `cache_n` 0 and `predicted_n` 512. New speed rows add `temperature: 0` only; reasoning effort and the rest of sampling stay at the served/config value. The rows currently on the model pages predate the 2026-11-27 temp-0 protocol and used the bench config's `reasoning_effort:"none"`; the served default is `high`/xhigh.

Configs: [Qwen3.8-Flash-Next + Speedy](../models/rig1-3060/qwen38-flash-next.md) and [Swift-1.5-Qwen3.8-Flash-Next + Speedy](../models/rig1-3060/swift-qwen38-flash-next.md).

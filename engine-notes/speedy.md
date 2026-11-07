# Speedy

Measured, tuned fork of [Strata](strata.md) by [DevDock-AI/Speedy](https://github.com/DevDock-AI/Speedy), MIT. Base is upstream Strata **v0.2.7.1**; the deployed engine is Speedy **0.3.1** (engine build **0.1.53**), a prebuilt sm_86 CUDA release. The release archive contains the engine binary only; the OpenAI/Anthropic API layer comes from the source tree's `serve/` and `strata_control/` Python packages and runs on the Strata terminal's bundled CPython. Same pack format, tokenizer and API surface as Strata; it reuses the Strata IQ3_XXS pack, the base model's MTP pack and the `strata-vision` reader.

## What changes against Strata

- **Production defaults.** The engine applies 12 built-in production defaults at startup; `STRATA_UPSTREAM_DEFAULTS=1` turns them off. Do not set that switch on a served entry.
- **MTP.** The 1x preset recommends MTP on this 12 GB card (`--mtp <mtp>/rt`); DFlash2 is compiled in but is not the recommended drafter here.
- **Runtime flags.** `--kv-resident`, `--conversation-cache-mib`, `--adapt-async`, `--adapt-swaps` and `--pool-affinity` are Speedy-specific; the preset's `env` block carries the rest. Put `STRATA_KEEP_EMPTY_TURNS=1` in the llama-swap entry `env:`, not the config JSON; `serve/frontend.py` reads it from the server process before the engine is spawned.
- **Vision.** The engine accepts `--vision`, but the release does not ship the separate `strata-vision` reader. Place a CLI/protocol-compatible reader at the engine-folder root (not `build/`) and add the `vision` block.
- **API.** Same as Strata: no raw `/v1/completions`; benchmark through `/v1/chat/completions` with the chat template applied.

## Measurement

Rows are on the [Qwen3.8-Flash-Next](../models/rig1-3060/qwen38-flash-next.md) and [Swift-1.5-Qwen3.8-Flash-Next](../models/rig1-3060/swift-qwen38-flash-next.md) model pages, measured under the Strata protocol with a derived `--prompt-cache 0` config: two passes, second recorded, `cache_n` 0 and `predicted_n` 512. No request overrides; served sampling is the config's.

Configs: [Qwen3.8-Flash-Next + Speedy](../models/rig1-3060/qwen38-flash-next.md) and [Swift-1.5-Qwen3.8-Flash-Next + Speedy](../models/rig1-3060/swift-qwen38-flash-next.md).

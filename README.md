# local-llm-benchmarks

Benchmark reports for running local LLMs on two consumer GPUs, using three builds of [llama.cpp](https://github.com/ggml-org/llama.cpp): upstream llama.cpp, [ik-llama.cpp](https://github.com/ikawrakow/ik_llama.cpp), and the [moe-cache fork](https://github.com/GenerelSchwerz/llama.cpp) (branch `moe-cache`). One Rig 2 model also has a [vLLM](https://github.com/syv-ai/HyperQwen) container stack, and Rig 1 runs Qwen3.8-Flash-Next on a fifth engine, the [Strata](https://github.com/Niko1221/Strata) pack engine.

## Rigs

- **Rig 1:** RTX 3060 12GB + i7-12700, 128 GB RAM - hardware and build info in [rig1-3060.md](rig1-3060.md)
- **Rig 2:** RTX 3090 24GB + Ryzen 7 5700X, 32 GB RAM; GA102 FP/BF16 issue rate unlocked at boot with [gpu-unlock](https://github.com/Zagitta/gpu-unlock) - hardware and build info in [rig2-3090.md](rig2-3090.md)

Rig 1 was first benchmarked 2026-09-10; the engines used on each rig are listed below. Measurement methodology: [methodology.md](methodology.md); per-engine flags: [engine-notes/](engine-notes/). Known issues and gotchas: [issues.md](issues.md).

## Inference engines

- **vLLM** ([syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen)) - a vLLM container stack running MTP with two KV modes, fp8 and KVarN 4/2-bit, both with pinned pools (Rig 2). Flags: [engine-notes/vllm.md](engine-notes/vllm.md).
- **llama.cpp** ([ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)) - upstream stock builds (Rig 1, Rig 2). Flags/defaults: [engine-notes/upstream-stock.md](engine-notes/upstream-stock.md).
- **ik-llama.cpp** ([ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp), Rig 1) - Ilya Kawrakow's performance fork of llama.cpp. Flag syntax: [engine-notes/ik-llama.md](engine-notes/ik-llama.md).
- **llama.cpp (moe-cache fork)** ([GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp), branch `moe-cache`, both rigs) - a llama.cpp fork adding a dynamic CUDA expert cache (`--moe-expert-cache-size`; no profile/trace step needed) and an opt-in generic hybrid CPU/GPU executor (`--moe-hybrid`) with model-bound expert profiles; while the cache is enabled it overrides `-ncmoe` placement. Flags and the `--experimental-logs` validation recipe: [engine-notes/moe-cache-fork.md](engine-notes/moe-cache-fork.md).
- **Strata** ([Niko1221/Strata](https://github.com/Niko1221/Strata), Rig 1) - a llama.cpp-derived engine that runs Qwen3.8-Flash-Next from a *pack* (expert rows indexed on the SSD, all experts pinned in host RAM, an adaptive VRAM expert cache) behind its own OpenAI/Anthropic API server. Not a `llama-server` build: its rows are measured through Strata's own `/v1/chat/completions` route with a chat template always applied, so they are not directly comparable with the llama.cpp rows above. Flags, the KV modes and the llama.cpp flag mapping: [engine-notes/strata.md](engine-notes/strata.md).

Current per-rig engine pins (build ids with dates) live on the rig pages: [rig1-3060.md](rig1-3060.md), [rig2-3090.md](rig2-3090.md).

The llama.cpp builds support MTP speculative decode; Strata has its own MTP. Timings are read from the `llama-server` response `timings` (or its request log) for llama.cpp, from the same `timings` fields for Strata, and vLLM's Prometheus metrics for vLLM. `llama-bench` is not used.

## Contents

- [methodology.md](methodology.md) - measurement methods, memory measurement, VRAM headroom (per-model), caveats
- [tuning.md](tuning.md) - tuning procedure: common vs engine/fork-specific knobs, sweep order, rules of thumb
- [engine-notes/](engine-notes/) - per-engine notes (flags, features, quirks), one file per engine
- [test-prompts.md](test-prompts.md) - the actual prompt texts used for timing runs (a ~10k opencode session-context timing prompt; ~60K and ~120K long-context refactor prompts)
- [rig1-3060.md](rig1-3060.md) - Rig 1 hardware and build info
- [rig2-3090.md](rig2-3090.md) - Rig 2 hardware and build info
- [issues.md](issues.md) - engine and tool-level issues found during testing
- [models/_template.md](models/_template.md) - template for the model cards (recommended configs, per-config commands, notes, long-context table)
- [models/rig1-3060/](models/rig1-3060/) - Rig 1 model pages (recommended configs per model)
- [models/rig2-3090/](models/rig2-3090/) - Rig 2 model pages (recommended configs per model)
- [experiments/](experiments/) - transferability studies of low-level inference knobs (engine/arch-specific tuning evaluated against the recommended stacks)
- [benchmarks/shoko-logs/](benchmarks/shoko-logs/) - agentic coding benchmark (reproduce the Shoko-WebUI logs-page rewrite — server-side search + infinite-scroll pagination, DSL pass-through, reconnect recovery, cancellation/failure handling — and log download, against a backend API the model must discover itself in a sibling ShokoServer checkout)
- [benchmarks/crucible/](benchmarks/crucible/) - capability benchmark (Crucible LLM: long-context retrieval, reasoning, structured output)

Each model page carries its full experiment log in the matching `archive/<model>.md` alongside it.

## Rig 1 results

Headline tables list only usable configs (full context, no rejected/OOM setups); all tested quants, including archived ones, are on the model pages ([Contents](#contents) above). YaRN-extended rows raise context past the native window; each row names its engine.

| Model | Quant | Engine | Full-ctx support | Prefill t/s | Decode t/s |
| --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | moe-cache fork | 262144 | 2047 | **83.5** |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | moe-cache fork | 524288 (YaRN 2x) | 2318 | **59.6** |
| Qwen3.8-Flash-Next | GSQ-RCO IQ3_XXS + MTP | Strata | 204800 | 1054.2 | **43.4** |
| Swift-1.5-Qwen3.8-Flash-Next | GSQ-RCO IQ3_XXS + MTP | Strata | 204800 | 1055.3 | **42.3** |
| KAT-Coder-V2.5-Dev | APEX-I-Compact | moe-cache fork | 262144 | 1770 | **72.2** |
| Gemma4-26B-A4B | Q4_K_M | moe-cache fork | 32768 | 1252 | **83.5** |
| Cyber-Tiel-Coder-35B-A3B | UD-IQ4_XS | moe-cache fork | 262144 | 2201 | **64.2** |

All rows here are measured on the 10k opencode session prompt ([test-prompts.md](test-prompts.md)) on the current engine pins (rig pages). The Gemma4 row is a chat-tuned config - not useful for coding on Rig 1.

## Rig 2 results

Headline tables list only usable configs (full context, no rejected/OOM setups); all tested quants, including archived ones, are on the model pages ([Contents](#contents) above). YaRN-extended rows raise context past the native window. llama.cpp rows use q8_0 KV under the 22 GB cap; vLLM rows pin their KV pool by bytes to stay under the cap. vLLM rows also run MTP spec decode, so decode moves with the run's draft acceptance ([engine-notes/vllm.md](engine-notes/vllm.md)) - sub-15% decode differences between two vLLM rows are not significant; each row names its engine.

| Model | Quant | Engine | ctx | Prefill t/s | Decode t/s |
| --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | UD-IQ4_XS | moe-cache fork | 262144 | 5258 | **189** |
| Qwen3.6-35B-A3B | UD-IQ4_XS | moe-cache fork | 524288 (YaRN 2x) | 4553 | **152.6** |
| KAT-Coder-V2.5-Dev | APEX-I-Compact | moe-cache fork | 262144 | 5254 | **155.6** |
| Qwen3.8-27B | W4A16-AutoRound-fast | vLLM | 176128 | 2465 | **120.6** |
| Qwen3.8-27B | W4A16-AutoRound-fast | vLLM | 262144 | 2403 | **101.8** |
| Swift-1.5-Qwen3.8-27B | Swift-1.5-INT4-fast | vLLM | 176128 | 2433 | **107.7** |
| Swift-1.5-Qwen3.8-27B | Swift-1.5-INT4-fast | vLLM | 262144 | 2374 | **97.6** |

All rows here are measured on the 10k opencode session prompt ([test-prompts.md](test-prompts.md)) on the current engine pins (rig pages).

## Coding benchmark (shoko-logs)

A separate, agentic benchmark under [benchmarks/shoko-logs/](benchmarks/shoko-logs/): from a clean Shoko-WebUI base commit, a model must reproduce the upstream logs-page rewrite (server-side search + infinite-scroll pagination, DSL pass-through, reconnect recovery, cancellation/failure handling) and log download against a backend API it must discover itself in a sibling ShokoServer checkout. It carries two **independent 0–100 scores per stage, never summed**: **Score A** is ticket conformance (only what `prompt.md` explicitly requests, runtime-checked by a Playwright harness for `[R]` lines) and **Score B** is robustness/reference fidelity (the behaviours the ticket deliberately leaves unstated, scored against the reference implementation). The build gates (`pnpm tscheck` / `pnpm lint` / `pnpm build`) are a precondition, not points — a red build carries no Score-A number. Method: one trajectory per model per parameter set — a clean-base implementation run plus up to two reviewer-driven repair rounds in the same session — reported as `converged: stage 0|1|2` or `not converged`, with no repeats and no median.

- Protocol, rubric, and prompts: [benchmarks/shoko-logs/README.md](benchmarks/shoko-logs/README.md)
- Results: [benchmarks/shoko-logs/scorecard.md](benchmarks/shoko-logs/scorecard.md)

## Crucible (capability)

A separate, suite-level benchmark under [benchmarks/crucible/](benchmarks/crucible/): [Crucible LLM](https://github.com/MadGoatHaz/crucible-llm) points at any OpenAI-compatible `/v1` endpoint and runs a set of capability engines — needle-in-a-haystack retrieval, deterministic reasoning, and structured output. Its numbers are **not comparable** to the timing rows above: it always applies a chat template and sends its own sampling params, so it has its own, independent methodology (see the suite README for the full deviation list).

- Protocol and engines: [benchmarks/crucible/README.md](benchmarks/crucible/README.md)
- Results: [benchmarks/crucible/scorecard.md](benchmarks/crucible/scorecard.md)

## References

External repositories referenced on these pages.

- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) - upstream (`stock`)
- [GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp) - moe-cache fork (dynamic CUDA expert cache), branch `moe-cache`
- [ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) - ik-llama.cpp performance fork
- [Niko1221/Strata](https://github.com/Niko1221/Strata) - pack-based Qwen3.8-Flash-Next engine with its own API server (Rig 1)
- [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) - vLLM container stack (Rig 2 Qwen3.8-27B W4A16 and Swift-1.5-INT4)
- [da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments](https://github.com/da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments) - source of the long-context refactor prompt and of the tuning experiments tested in [experiments/](experiments/)
- [Zagitta/gpu-unlock](https://github.com/Zagitta/gpu-unlock) - GA102/GA103/GA104/GA106 FP/BF16 issue-rate unlock, used on Rig 2

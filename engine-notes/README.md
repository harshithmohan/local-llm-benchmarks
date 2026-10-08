# Engine notes

Per-engine reference for the inference engines used in this benchmark. Engine labels are
kept explicit on every page - never "both" - because flag vocabularies differ and results
are not interchangeable across engines.

The request protocol common to the llama.cpp engines (endpoint, request flags, two-pass,
sampling) is defined in [methodology.md](../methodology.md) §Measurement methods; the
prompt texts are in [test-prompts.md](../test-prompts.md). Per-rig build ids are in
[rig1-3060.md](../rig1-3060.md) / [rig2-3090.md](../rig2-3090.md).

| Engine | Upstream | Rig(s) | In one line |
| --- | --- | --- | --- |
| [moe-cache fork](moe-cache-fork.md) | [GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp) (`moe-cache`) | 1, 2 | dynamic CUDA expert cache + opt-in generic hybrid CPU/GPU executor |
| [upstream (stock)](upstream-stock.md) | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | 1, 2 | reference build; no fork features |
| [ik-llama.cpp](ik-llama.md) | [ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) | 1 | Ilya Kawrakow's fork; different flag syntax |
| [vLLM](vllm.md) | [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) | 2 | container stack for the Qwen3.8-27B quants |
| [Strata](strata.md) | [Niko1221/Strata](https://github.com/Niko1221/Strata) | 1 | pack-based Flash-Next engine behind its own Python API server |

Flags, features, and quirks for each engine live in its own file above. `llama-bench` is
not used anywhere - see [methodology.md](../methodology.md) for why.

# local-llm-benchmarks

Benchmark reports for running local LLMs on two consumer GPUs, using three builds
of [llama.cpp](https://github.com/ggml-org/llama.cpp): upstream llama.cpp,
[ik-llama.cpp](https://github.com/ikawrakow/ik_llama.cpp), and the
[moe-cache fork](https://github.com/GenerelSchwerz/llama.cpp) (branch `moe-cache`).
One Rig 2 model also has a
[vLLM](https://github.com/syv-ai/HyperQwen) container stack.

## Rigs

- **Rig 1:** RTX 3060 12GB + i7-12700, 128 GB RAM - hardware and build info in
  [rig1-3060.md](rig1-3060.md)
- **Rig 2:** RTX 3090 24GB + Ryzen 7 5700X, 32 GB RAM - hardware and build info in
  [rig2-3090.md](rig2-3090.md)

Rig 1 was first benchmarked 2026-09-10; the engines used on each rig are listed below.
Measurement methodology: [methodology.md](methodology.md); per-engine flags: [engine-notes/](engine-notes/).
Known issues and gotchas: [issues.md](issues.md).

## Inference engines

- **vLLM** ([syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen), vLLM 0.29.0) - a vLLM
  container stack running MTP with two KV modes, fp8 and KVarN 4/2-bit, both with pinned
  pools.
- **llama.cpp** ([ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)) -
  Rig 1: v0.5.0-dev d834d44 since the 2026-09-26 container rebuild (older stock rows on
  v0.4.0-dev 30b6a75); Rig 2: v0.5.0-dev build 11146 (7fe450e193).
- **ik-llama.cpp** ([ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp),
  build 1aaf710 (v1; older rows 3bb386e), Rig 1) - Ilya Kawrakow's performance fork of
  llama.cpp. Flag syntax: [engine-notes/ik-llama.md](engine-notes/ik-llama.md).
- **llama.cpp (moe-cache fork)** ([GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp),
  branch `moe-cache`, build b11608-2b8088c2a) - a llama.cpp fork adding a dynamic CUDA expert
  cache (`--moe-expert-cache-size`), with no profile/trace step; while enabled it overrides
  `-ncmoe` placement. Flags and the `--experimental-logs` validation recipe:
  [engine-notes/moe-cache-fork.md](engine-notes/moe-cache-fork.md).

The llama.cpp builds support MTP speculative decode.
Timings are read from the `llama-server` response `timings` (or its request log) for
llama.cpp, and vLLM's Prometheus metrics for vLLM. `llama-bench` is not used.

## Contents

- [methodology.md](methodology.md) - measurement methods, memory measurement, VRAM headroom rule, caveats
- [engine-notes/](engine-notes/) - per-engine notes (flags, features, quirks), one file per engine
- [test-prompts.md](test-prompts.md) - the actual prompt texts used for timing runs (a ~10k opencode session-context timing prompt; a ~60K long-context refactor prompt)
- [rig1-3060.md](rig1-3060.md) - Rig 1 hardware and build info
- [rig2-3090.md](rig2-3090.md) - Rig 2 hardware and build info
- [issues.md](issues.md) - engine and tool-level issues found during testing
- [models/model-card-skeleton.md](models/model-card-skeleton.md) - template for the model cards (recommended configs, per-config commands, notes, long-context table)
- [models/rig1-3060/](models/rig1-3060/) - Rig 1 model pages (recommended configs per model)
- [models/rig2-3090/](models/rig2-3090/) - Rig 2 model pages (recommended configs per model)
- [experiments/](experiments/) - transferability studies of low-level inference knobs (engine/arch-specific tuning evaluated against the recommended stacks)
- [benchmarks/shoko-logs/](benchmarks/shoko-logs/) - agentic coding benchmark (reproduce the Shoko-WebUI logs-page rewrite + log download)

Each model page carries its full experiment log in the matching `archive/<model>.md` alongside it.

## Rig 1 results

Headline tables list only usable configs (full context, no rejected/OOM setups); all tested
quants, including archived ones, are on the model pages ([Contents](#contents) above).
YaRN-extended rows raise context past the native window; engine labels are per-row on the
model pages.

| Model | Quant | Full-ctx support | Prefill t/s | Decode t/s |
| --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 262144 | 1909 | **76** |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 524288 (YaRN 2x) | 2063 | **52** |
| Qwen3.8-Flash-Next | UD-IQ3_XXS | 81920 | 362 | **21.4** |
| KAT-Coder-V2.5-Dev | APEX-I-Compact | 262144 | 1587 | **66** |
| Qwen3.8-27B (Swift-1.5) | IQ2_XS | 81920 (q4_0 KV) | 467 | **35.6** |
| Gemma4-26B-A4B | Q4_K_M | 262144 | 1623 | **52** |

All rows here are measured on the 10k opencode session prompt ([test-prompts.md](test-prompts.md)).

## Rig 2 results

Headline tables list only usable configs (full context, no rejected/OOM setups); all tested
quants, including archived ones, are on the model pages ([Contents](#contents) above).
YaRN-extended rows raise context past the native window. llama.cpp rows use q8_0 KV under the
22 GB cap; vLLM rows pin their KV pool by bytes to stay under the cap; engine labels are
per-row on the model pages.

| Model | Quant | ctx | Prefill t/s | Decode t/s |
| --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 262144 | 4686 | **214** |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 524288 (YaRN 2x) | 3925 | **154** |
| KAT-Coder-V2.5-Dev | APEX-I-Compact | 262144 | 4591 | **163** |
| Qwen3.8-27B | W4A16-AutoRound-fast | 150000 | 2430 | **113.0** |
| Qwen3.8-27B | W4A16-AutoRound-fast | 250000 | 2408 | **87.9** |
| Qwen3.8-27B (Swift-1.5) | Swift-1.5-INT4 | 150000 | 2417 | **116.9** |
| Qwen3.8-27B (Swift-1.5) | Swift-1.5-INT4 | 250000 | 2394 | **94.3** |

## Coding benchmark (shoko-logs)

A separate, agentic benchmark under [benchmarks/shoko-logs/](benchmarks/shoko-logs/):
from a clean Shoko-WebUI base commit, a model must reproduce the upstream logs-page
rewrite (server-side search + infinite-scroll pagination) and log download against a
backend API it discovers itself. Scored by build gates (tscheck/lint/build, 5 pts)
plus a 95-point behavior rubric vs a reference diff.

- Protocol, rubric, and prompts: [benchmarks/shoko-logs/README.md](benchmarks/shoko-logs/README.md)
- Results: [benchmarks/shoko-logs/scorecard.md](benchmarks/shoko-logs/scorecard.md)

## References

External repositories referenced on these pages.

- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) - upstream (`stock`)
- [GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp) - moe-cache fork (dynamic CUDA expert cache), branch `moe-cache`
- [ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) - ik-llama.cpp performance fork
- [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) - vLLM 0.29.0 container stack (Rig 2 Qwen3.8-27B W4A16 and Swift-1.5-INT4; all rows re-measured 2026-09-30 on the ~10k opencode prompt)
- [da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments](https://github.com/da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments) - source of the long-context refactor prompt and of the tuning experiments tested in [experiments/](experiments/)

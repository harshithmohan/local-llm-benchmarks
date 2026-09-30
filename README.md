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

Three **llama.cpp** builds plus one **vLLM** stack are used across the rigs, labeled as such
throughout these pages:

- **moe-cache fork** ([GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp),
  branch `moe-cache`, build b11608-2b8088c2a) - dynamic CUDA expert cache
  (`--moe-expert-cache-size`), no profile/trace step; while enabled it overrides
  `-ncmoe` placement. The fastest 35B engine on both rigs at 256k (and both rigs' at 512k),
  and the live KAT-Coder config; flags and the `--experimental-logs` validation recipe are in
  [engine-notes/moe-cache-fork.md](engine-notes/moe-cache-fork.md).
- **Upstream (stock)** ([ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)) -
  Rig 1: v0.5.0-dev d834d44 since the 2026-09-26 container rebuild (older stock rows
  measured on v0.4.0-dev 30b6a75); Rig 2: v0.5.0-dev build 11146 (7fe450e193). No fork
  features (no expert cache). Still the fallback where the fork is unavailable, but the
  fork now leads on both rigs - including Rig 2, where at 256k no expert offload is needed
  (the fork's edge is simply faster decode and lower workspace VRAM) and at 512k its expert
  cache is what carries the window.
- **ik-llama.cpp** ([ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp),
  build 1aaf710 (v1; older rows 3bb386e), Rig 1) - Ilya Kawrakow's performance fork; so far tested on the Rig 1
  Qwen3.6-35B-A3B IQ4_XS quant. Loses to stock at the native 256k window; at YaRN-extended
  context the moe-cache fork now wins 512K, while ik keeps the furthest plain-llama.cpp
  reach (~852K vs stock ~736K). Results live in each model's page
  ([models/rig1-3060/qwen36-35b-a3b.md](models/rig1-3060/qwen36-35b-a3b.md));
  llama.cpp and ik results are not interchangeable - engine labels are per-row; flag
  syntax in [engine-notes/ik-llama.md](engine-notes/ik-llama.md).
- **vLLM** ([syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen),
  vLLM 0.29.0) - the Rig 2 Qwen3.8-27B W4A16 stack, MTP with two KV modes: fp8 at 150000
  (4 drafts) and KVarN 4/2-bit at 250000 (slower decode), both with pinned pools. Its
  DFlash2 profile is archived. Engine labels are per-row on the model pages - llama.cpp and
  vLLM results are not interchangeable.

The llama.cpp builds support MTP speculative decode; the vLLM stack runs MTP.
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

## Headline results (Rig 1, t/s, q8_0 KV)

Headline tables list only usable configs (full context, no rejected/OOM setups). All
tested quants - including archived ones - are in the model pages: [Contents](#contents) above.
YaRN-extended rows raise context past the native window.

| Model | Quant | Full-ctx support | Prefill t/s | Decode t/s | Notes |
| --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 262144 | 1909 | **76** | Fastest at 256k; moe-cache fork (GenerelSchwerz), cache 64 + MTP, -b/-ub 6144; 10k opencode session prompt; caches the fused gate_up expert layout the other engines do not |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 524288 (YaRN 2x) | 2063 | **52** | Extended (in use); moe-cache fork, cache 48 + MTP off, -b/-ub 6144; 10k opencode session prompt |
| Qwen3.8-Flash-Next | UD-IQ3_XXS | 81920 | 362 | **21.4** | Fastest Flash-Next quant; moe-cache fork, cache 48 + MTP off, `-b/-ub 1024`; 10k opencode session prompt; 60K refactor 341 / 13.1 |
| KAT-Coder-V2.5-Dev | APEX-I-Compact | 262144 | 1587 | **66** | qwen35moe; moe-cache fork, cache 80 + MTP, -b/-ub 3072; 10k opencode session prompt; 1374 t/s prefill on the ~60K refactor prompt |
| Qwen3.8-27B (Swift-1.5) | IQ2_XS | 81920 (q4_0 KV) | 467 | **35.6** | Dense qwen35 (no MoE split); stock, MTP on, default `-b/-ub`; q4_0 KV is what fits the 12 GB cap; 60K refactor 383 / 24.4 |

All rows here are measured on the 10k opencode session prompt ([test-prompts.md](test-prompts.md)).

## Headline results (Rig 2, t/s, 22 GB cap)

Headline tables list only usable configs (full context, no rejected/OOM setups). All
tested quants - including archived ones - are in the model pages: [Contents](#contents) above.
YaRN-extended rows raise context past the native window. llama.cpp rows use q8_0 KV under
the 22 GB cap; the
vLLM rows pin their KV pool by bytes to stay under the cap.

| Model | Quant | ctx | Prefill t/s | Decode t/s | Notes |
| --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 262144 | 4686 | **214** | Full ctx at 22182 MiB; moe-cache fork, MTP on, `-b/-ub 4096`; 10k opencode session prompt |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 524288 (YaRN 2x) | 3925 | **154** | Extended (in use); moe-cache fork, cache 168 + MTP on, `-b/-ub 8192`, 22230 MiB |
| Qwen3.8-27B | W4A16-AutoRound-fast | 150000 | 2430 | **113.0** | vLLM, MTP 4 drafts, fp8 KV, pinned pool (`MAX_LEN=150000`, `MAX_SEQS=4`); single pass, `INT8_ACT=int8`; 21992 MiB |
| Qwen3.8-27B | W4A16-AutoRound-fast | 250000 | 2408 | **87.9** | vLLM, MTP 3 drafts, KVarN 4/2-bit KV, pinned pool (`CTX=huge`, `MAX_LEN=250000`); single pass, `INT8_ACT=int8`; 21234 MiB; ~2x slower decode on the 60K refactor |
| Qwen3.8-27B (Swift-1.5) | Swift-1.5-INT4 | 150000 | 2417 | **116.9** | vLLM fine-tune quant on the same MTP fp8 stack (4 drafts, pinned pool, server-configured sampling); single pass, `INT8_ACT=int8`; 22510 MiB; fewer thinking tokens, early-stopping coding answers |
| Qwen3.8-27B (Swift-1.5) | Swift-1.5-INT4 | 250000 | 2394 | **94.3** | vLLM, same fine-tune on the KVarN 4/2-bit KV profile, pinned pool; single pass, `INT8_ACT=int8`; 22052 MiB |

Long-context figures above (KAT-Coder) are the ~60K refactor run (fork 1374 prefill /
51.2 decode, measured 2026-09-30).

## Headline takeaways

1. Prefill throughput is the single biggest win everywhere: +104-137% on the 35B.
2. The expert cache is a strong win for MoE models that need expert offload: the
   GenerelSchwerz dynamic cache takes IQ4_XS to 76 t/s at 256k (+35%) / 52 at 512k,
   KAT-Coder to 66 t/s on the 10k prompt, UD-IQ4_XS to 154 t/s at Rig 2 512k (cache 168),
   and Flash-Next UD-IQ3_XXS to 21.4 t/s decode at
   80k (cache 48) - far ahead of the same fork's `-ncmoe` configs (~13 t/s). It needs
   enough slots: sub-group-width caches lose to no cache.
3. KV cache at q8_0 is cheap on both arches (10.6 KiB/token on the 35B, 4.9 on Flash-Next);
   context is limited by compute buffers, which scale with `-ub` on Flash-Next.
4. For coding use (opencode via llama-swap), the recommended setup on the 35B is the
   moe-cache fork on both rigs: Rig 1 IQ4_XS at 256k (cache 64, MTP on, `-b/-ub 6144`) -
   ~+35% decode over stock - and, past the native window, the same fork at 512k (cache 48,
   MTP off, YaRN 2x, `-b/-ub 6144`); Rig 2 UD-IQ4_XS at 256k (MTP on, `-b/-ub 4096`)
   - ~+11% decode and ~1 GB less VRAM than stock, with no cache needed - and at 512k the
   same fork with the expert cache (cache 168, MTP on, `-b/-ub 8192`). Stock remains the
   fallback when that engine is unavailable. See the model pages for exact commands.

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

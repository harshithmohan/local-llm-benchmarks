# local-llm-benchmarks

Benchmark reports for running local LLMs on two consumer GPUs, using four builds
of [llama.cpp](https://github.com/ggml-org/llama.cpp): the
[Codacus fork](https://github.com/thecodacus/llama.cpp) (branch `perf`),
upstream llama.cpp, [ik-llama.cpp](https://github.com/ikawrakow/ik_llama.cpp), and the
[moe-cache fork](https://github.com/GenerelSchwerz/llama.cpp) (branch `moe-cache`).
One Rig 2 model also has a
[vLLM](https://github.com/syv-ai/HyperQwen) container stack.

## Rigs

- **Rig 1:** RTX 3060 12GB + i7-12700, 128 GB RAM - hardware and build info in
  [rig1-3060.md](rig1-3060.md)
- **Rig 2:** RTX 3090 24GB + Ryzen 7 5700X, 32 GB RAM - hardware and build info in
  [rig2-3090.md](rig2-3090.md)

Both rigs were tested with the same Codacus fork build (b10818-27c54b4bb, branch
`perf` - see [Inference engines](#inference-engines)); Rig 1 first benchmarked 2026-09-10.
Measurement methodology and env-var reference: [methodology.md](methodology.md).
Known issues and gotchas: [issues.md](issues.md).

## Inference engines

Four **llama.cpp** builds plus one **vLLM** stack are used across the rigs, labeled as such
throughout these pages:

- **Codacus fork** ([thecodacus/llama.cpp](https://github.com/thecodacus/llama.cpp), branch `perf`,
  build b10818-27c54b4bb) - adds prefill patches and a VRAM-resident expert cache;
  env vars and flags are defined in [methodology.md](methodology.md).
- **moe-cache fork** ([GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp),
  branch `moe-cache`, build b11608-2b8088c2a) - dynamic CUDA expert cache
  (`--moe-expert-cache-size`), no profile/trace step; while enabled it overrides
  `-ncmoe` placement. Rig 1's fastest 35B engine at 256k and 512k, and the live KAT-Coder
  config; flags and the `--experimental-logs` validation recipe are in
  [methodology.md](methodology.md).
- **Upstream (stock)** ([ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)) -
  Rig 1: v0.5.0-dev d834d44 since the 2026-09-26 container rebuild (older stock rows
  measured on v0.4.0-dev 30b6a75); Rig 2: v0.4.0-dev build 10809 (5266f24da7). No fork
  features (no expert cache; the fork env vars are no-ops). The config of choice where
  the fork has nothing to add - e.g. every Rig 2 config at ncmoe 0, and Flash-Next on
  Rig 1.
- **ik-llama.cpp** ([ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp),
  build 1aaf710 (v1; older rows 3bb386e), Rig 1) - Ilya Kawrakow's performance fork; so far tested on the Rig 1
  Qwen3.6-35B-A3B IQ4_XS quant. Loses to stock at the native 256k window; at YaRN-extended
  context the moe-cache fork now wins 512K, while ik keeps the furthest plain-llama.cpp
  reach (~852K vs stock ~736K). Results live in each model's page
  ([models/rig1-3060/qwen36-35b-a3b.md](models/rig1-3060/qwen36-35b-a3b.md));
  llama.cpp and ik results are not interchangeable - engine labels are per-row.
- **vLLM** ([syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen),
  vLLM 0.29.0) - the Rig 2 Qwen3.8-27B W4A16 stack, MTP with two KV modes: fp8 at 150000
  (4 drafts) and KVarN 4/2-bit at 250000 (slower decode), both with pinned pools. Its
  DFlash2 profile is archived. Engine labels are per-row on the model pages - llama.cpp and
  vLLM results are not interchangeable.

The llama.cpp builds support MTP speculative decode; the vLLM stack runs MTP.
Timings are read from `llama-server` request logs (llama.cpp) or vLLM's Prometheus metrics
(vLLM); `llama-bench` covered the initial prefill/decode sweeps.

## Contents

- [methodology.md](methodology.md) - env vars, measurement methods, memory measurement, VRAM headroom rule, caveats
- [test-prompts.md](test-prompts.md) - the actual prompt texts used for timing runs and traces (C# and React/TS timing prompts; a C++ prompt for routing-trace tests)
- [rig1-3060.md](rig1-3060.md) - Rig 1 hardware and build info
- [rig2-3090.md](rig2-3090.md) - Rig 2 hardware and build info
- [issues.md](issues.md) - Codacus fork/tool-level issues found during testing
- [models/rig1-3060/](models/rig1-3060/) - Rig 1 model pages (best configs per model)
- [models/rig2-3090/](models/rig2-3090/) - Rig 2 model pages (best configs per model)
- [experiments/](experiments/) - transferability studies of low-level inference knobs (engine/arch-specific tuning evaluated against the recommended stacks)
- [benchmarks/shoko-logs/](benchmarks/shoko-logs/) - agentic coding benchmark (reproduce the Shoko-WebUI logs-page rewrite + log download)

Each model page carries its full experiment log in the matching `-archive.md` alongside it.

## Headline results (Rig 1, t/s, q8_0 KV)

Headline tables list only usable configs (full context, no rejected/OOM setups). All
tested quants - including archived ones - are in the model pages: [Contents](#contents) above.
YaRN-extended rows raise context past the native window; see the YaRN caveat in
[methodology.md](methodology.md).

| Model | Quant | Full-ctx support | Prefill t/s | Decode t/s | Notes |
| --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 262144 | 355.1 | **72.0** | Fastest at 256k; moe-cache fork (GenerelSchwerz), cache 48 + MTP; caches the fused gate_up layout the Codacus cache cannot |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 524288 (YaRN 2x) | 363.2 | **60.8** | Extended (in use); moe-cache fork, cache 48 + MTP off |
| Qwen3.8-Flash-Next | UD-IQ3_XXS | 230400 practical | 157.1 | **18.1** | Fastest Flash-Next quant; MTP on |
| KAT-Coder-V2.5-Dev | APEX-I-Compact | 262144 | ~344 | **~76** | qwen35moe; moe-cache fork, cache 80 + MTP; ~609 t/s prefill on the ~60K refactor prompt |
| Qwen3.8-27B (Swift-1.5) | IQ2_XS | 90000 (q4_0 KV) | 300.1 | 32.9 | Dense qwen35 (no MoE split); MTP on; q4_0 KV is what fits the 12 GB cap |

## Headline results (Rig 2, t/s, 22 GB cap)

Headline tables list only usable configs (full context, no rejected/OOM setups). All
tested quants - including archived ones - are in the model pages: [Contents](#contents) above.
YaRN-extended rows raise context past the native window (see the YaRN caveat in
[methodology.md](methodology.md)). llama.cpp rows use q8_0 KV under the 22 GB cap; both
vLLM rows pin their KV pool by bytes to stay under the cap.

| Model | Quant | ncmoe | ctx | Prefill t/s | Decode t/s | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 0 | 262144 | 2375.8 | **165.1** | Full ctx at 22065 MiB; MTP on (stock); cache-compatible if ever needed |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 6 | 524288 (YaRN 2x) | 1656.7 | 89.9 | Extended (in use); MTP off |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 25 | 1048576 (YaRN 4x) | 871.8 | 49.4 | Extended max (1M) - achieved on this rig; MTP off |
| Qwen3.8-27B | W4A16-AutoRound-fast | n/a (vLLM) | 150000 | 1672.7 | 103.3 | MTP 4 drafts, fp8 KV, pinned pool (`MAX_LEN=150000`, `MAX_SEQS=4`); single pass, `INT8_ACT=int8`; 21990 MiB |
| Qwen3.8-27B | W4A16-AutoRound-fast | n/a (vLLM) | 250000 | 1716.6 | 92.7 | MTP, KVarN 4/2-bit KV, pinned pool (`CTX=huge`, `MAX_LEN=250000`); single pass, `INT8_ACT=int8`; 21736 MiB; ~2x slower decode on the 60K refactor |
| Qwen3.8-27B (Swift-1.5) | Swift-1.5-INT4 | n/a (vLLM) | 150000 | 1621.5 | 96.1 | Fine-tune quant on the same MTP fp8 stack (4 drafts, pinned pool, server-configured sampling); single pass, `INT8_ACT=int8`; 22510 MiB; fewer thinking tokens, early-stopping coding answers |
| Qwen3.8-27B (Swift-1.5) | Swift-1.5-INT4 | n/a (vLLM) | 250000 | 1683.0 | 86.7 | Same fine-tune on the KVarN 4/2-bit KV profile, pinned pool; single pass, `INT8_ACT=int8`; 22052 MiB |

Messy-prompt figures above (KAT-Coder) are now the ~60K refactor run (fork 608.7 prefill /
49.06 decode, stock 572.8 / 38.33, measured 2026-09-28); the retired ~116K run is on the
model page archive.

## Headline takeaways

1. Prefill patches are the single biggest win everywhere: +104-137% on the 35B, and
   ~+55-63% on the recommended Flash-Next quant (UD-IQ3_XXS); the wider range (+183% AD,
   +656% archived Q3_K_XL) is other Flash-Next quants.
2. The expert cache is a strong win for MoE models that need expert offload: the Codacus CSV-profile
   cache gave the traced 35B 256k row +26% decode; the GenerelSchwerz dynamic cache takes
   IQ4_XS to 72.0 t/s at 256k (+31%) / 60.8 at 512k, and KAT-Coder to ~76 t/s (+59%). It is
   weak or a net loss for Flash-Next at 12 GB VRAM (512 experts, flat routing traffic), and
   it needs enough slots: sub-group-width caches lose to no cache.
3. KV cache at q8_0 is cheap on both arches (10.6 KiB/token on the 35B, 4.9 on Flash-Next);
   context is limited by compute buffers, which scale with `-ub` on Flash-Next.
4. For coding use (opencode via llama-swap), the recommended setup on the 35B is the
   moe-cache fork: IQ4_XS at 256k (cache 48, MTP on) - ~+31% decode over stock - and, past
   the native window, the same fork at 512k (cache 48, MTP off, YaRN 2x) - ~+43% decode
   over ik. Stock remains the fallback when that engine is unavailable. See the model pages
   for exact commands.

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
- [thecodacus/llama.cpp](https://github.com/thecodacus/llama.cpp) - Codacus fork, branch `perf`
- [GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp) - moe-cache fork (dynamic CUDA expert cache), branch `moe-cache`
- [ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) - ik-llama.cpp performance fork
- [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) - vLLM 0.29.0 container stack (Rig 2 Qwen3.8-27B W4A16 and Swift-1.5-INT4; all rows re-measured 2026-09-27 on the post-rename container)
- [da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments](https://github.com/da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments) - source of the messy-code refactor prompt and of the tuning experiments tested in [experiments/](experiments/)

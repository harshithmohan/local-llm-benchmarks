# local-llm-benchmarks

Benchmark reports for running local LLMs on two consumer GPUs, using two builds
of [llama.cpp](https://github.com/ggml-org/llama.cpp): the
[Codacus fork](https://github.com/thecodacus/llama.cpp) (branch `perf`) and upstream.

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

Two **llama.cpp** builds are used across both rigs, labeled as such throughout these pages:

- **Codacus fork** ([thecodacus/llama.cpp](https://github.com/thecodacus/llama.cpp), branch `perf`,
  build b10818-27c54b4bb) - adds the prefill patches (`GGML_CUDA_REGISTER_HOST=1`,
  `GGML_SCHED_PREFETCH_EXPERTS=1`) and the VRAM-resident expert cache
  (`--moe-cache-profile` / `--moe-cache-slots`). Feature details in
  [methodology.md](methodology.md).
- **Upstream (stock)** ([ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)) -
  Rig 1: v0.4.0-dev 30b6a75; Rig 2: v0.4.0-dev build 10809 (5266f24da7). No fork features
  (no expert cache; the fork env vars are no-ops). The config of choice where the fork has
  nothing to add - e.g. every Rig 2 config at ncmoe 0, and IQ4_XS at 256k on Rig 1.

Both builds support MTP speculative decode. Timings are read from `llama-server` request
logs; `llama-bench` covered the initial prefill/decode sweeps.

## Contents

- [methodology.md](methodology.md) - env vars, measurement methods, VRAM headroom rule, caveats
- [test-prompts.md](test-prompts.md) - the actual prompt texts used for timing runs and traces (C#, React/TS, C++)
- [rig1-3060.md](rig1-3060.md) - Rig 1 hardware and build info
- [rig2-3090.md](rig2-3090.md) - Rig 2 hardware and build info
- [issues.md](issues.md) - Codacus fork/tool-level issues found during testing
- [models/rig1-3060/qwen36-35b-a3b.md](models/rig1-3060/qwen36-35b-a3b.md) - Qwen3.6-35B-A3B on Rig 1; full experiment log in [models/rig1-3060/qwen36-35b-a3b-archive.md](models/rig1-3060/qwen36-35b-a3b-archive.md)
- [models/rig1-3060/qwen38-flash-next.md](models/rig1-3060/qwen38-flash-next.md) - Qwen3.8-Flash-Next on Rig 1; full experiment log in [models/rig1-3060/qwen38-flash-next-archive.md](models/rig1-3060/qwen38-flash-next-archive.md)
- [models/rig2-3090/qwen36-35b-a3b.md](models/rig2-3090/qwen36-35b-a3b.md) - Qwen3.6-35B-A3B on Rig 2 (22 GB cap)

## Headline results (Rig 1, t/s, q8_0 KV)

Headline tables list only usable configs (full context, no rejected/OOM setups). All
tested quants - including archived ones - are in the model pages: [Contents](#contents) above.

| Model | Quant | Full-ctx support | Prefill t/s | Decode t/s | Notes |
| --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | UD-Q4_K_M | 262144 (with cache) | 268.6 | **38.8** | Cache + MTP stack at 256k (40 slots at ub 512); quality vs IQ4 untested |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 262144 | 525.7 | **49.4** | Fastest plain decoder; MTP on (stock); cache incompatible (fused gate_up) |
| Qwen3.8-Flash-Next | UD-IQ3_XXS | 230400 practical | 157.1 | **18.1** | Fastest Flash-Next quant; MTP on |
| Qwen3.8-Flash-Next | AD-Q4_K_M-M64 | 230400 practical | 154.7 | **13.1** | Add REGISTER_HOST for prefill; MTP off |

## Headline results (Rig 2, t/s, q8_0 KV, 22 GB cap)

Headline tables list only usable configs (full context, no rejected/OOM setups). All
tested quants - including archived ones - are in the model pages: [Contents](#contents) above.

| Model | Quant | ncmoe | ctx | Prefill t/s | Decode t/s | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 0 | 262144 | 2375.8 | **165.1** | Full ctx at 22065 MiB; MTP on (stock); cache-compatible if ever needed |

## Headline takeaways

1. Prefill patches (`GGML_CUDA_REGISTER_HOST=1` + `GGML_SCHED_PREFETCH_EXPERTS=1`) are the
   single biggest win everywhere: +104-137% on the 35B, +183-656% on Flash-Next.
2. The expert cache is a strong win for the 35B models (+25-45% decode), weak or a net
   loss for Flash-Next at 12 GB VRAM (512 experts, flat routing traffic).
3. KV cache at q8_0 is cheap on both arches (10.6 KiB/token on the 35B, 4.9 on Flash-Next);
   context is limited by compute buffers, which scale with `-ub` on Flash-Next.
4. For coding use (opencode via llama-swap), the recommended setup is UD-Q4_K_M at
   `-c 131072..262144` with 80/52 cache slots - see the model pages for exact commands.

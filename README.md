# local-llm-benchmarks (two rigs: RTX 3060 + RTX 3090)

- Rig 1: RTX 3060 12GB + i7-12700, 128 GB RAM
- Rig 2: RTX 3090 24GB + Ryzen 7 5700X, 32 GB RAM - Qwen3.6-35B-A3B benchmarked ([rig2-3090.md](rig2-3090.md))

Tested (Rig 1): 2026-09-10, build b10818-27c54b4bb (branch `perf` of the
[Codacus fork](https://github.com/thecodacus/llama.cpp)).
Measurement methodology and env-var reference: [methodology.md](methodology.md).
Known issues and gotchas: [issues.md](issues.md).

## Headline results (Rig 2, decode t/s, q8_0 KV, 22 GB cap)

| Quant | ncmoe | ctx | Best measured decode | Notes |
| --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B UD-IQ4_XS | 0 | 262144 | **165.1** w/ MTP (stock) | Full ctx at 22065 MiB; cache-compatible if ever needed |
| Qwen3.6-35B-A3B IQ4_XS-4.19bpw | 0 | 230400 | 178.1 w/ MTP (stock) | Archived: faster at reduced ctx, no cache ever |

All experts fit on the 3090's GPU (ncmoe 0-12) - decode is 3-4x Rig 1. See
[models/rig2-3090/qwen36-35b-a3b.md](models/rig2-3090/qwen36-35b-a3b.md) for full tables and configs.

## Headline results (Rig 1, decode t/s, q8_0 KV)

| Model | Quant | Full-ctx support | Best measured decode | Notes |
| --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B UD-Q4_K_M | 21.1G | 262144 (with cache) | **38.8** @ 256k | Cache + MTP stack at 256k (40 slots at ub 512); quality vs IQ4 untested |
| Qwen3.6-35B-A3B IQ4_XS | 17.3G | 262144 | **49.4** @ 256k w/ MTP (stock) | Fastest plain decoder + MTP; cache incompatible (fused gate_up) |
| Qwen3.8-Flash-Next UD-IQ3_XXS | 76.3G | 230400 practical | **18.1** @ 230400, MTP | Fastest Flash-Next quant |
| Qwen3.8-Flash-Next AD-Q4_K_M-M64 | 88.0G | 230400 practical | **13.1** @ 230400 | Add REGISTER_HOST for prefill |

The 35B family and Flash-Next are different models - see the two tables in
[comparison.md](comparison.md), which are deliberately not mixed.

## Contents

- [methodology.md](methodology.md) - env vars, measurement methods, VRAM headroom rule, caveats
- [test-prompts.md](test-prompts.md) - the actual prompt texts used for timing runs and traces (C#, React/TS, C++)
- [rig1-3060.md](rig1-3060.md) - Rig 1 hardware and build info
- [rig2-3090.md](rig2-3090.md) - Rig 2 hardware, results, and configs
- [issues.md](issues.md) - Codacus fork/tool-level issues found during testing
- [comparison.md](comparison.md) - final cross-model tables (35B at 262144; Flash-Next at 230400)
- [models/rig1-3060/qwen36-35b-a3b.md](models/rig1-3060/qwen36-35b-a3b.md) - IQ4_XS / UD-Q4_K_M (same model; UD-Q6_K archived); full experiment log in [models/rig1-3060/qwen36-35b-a3b-archive.md](models/rig1-3060/qwen36-35b-a3b-archive.md)
- [models/rig1-3060/qwen38-flash-next.md](models/rig1-3060/qwen38-flash-next.md) - UD-IQ3_XXS / AD-Q4_K_M-M64 (UD-Q3_K_XL archived); full experiment log in [models/rig1-3060/qwen38-flash-next-archive.md](models/rig1-3060/qwen38-flash-next-archive.md)
- [models/rig2-3090/qwen36-35b-a3b.md](models/rig2-3090/qwen36-35b-a3b.md) - all three quants on the 3090 (22 GB cap)

## Headline takeaways

1. Prefill patches (`GGML_CUDA_REGISTER_HOST=1` + `GGML_SCHED_PREFETCH_EXPERTS=1`) are the
   single biggest win everywhere: +104-137% on the 35B, +183-656% on Flash-Next.
2. The expert cache is a strong win for the 35B models (+25-45% decode), weak or a net
   loss for Flash-Next at 12 GB VRAM (512 experts, flat routing traffic).
3. KV cache at q8_0 is cheap on both arches (10.6 KiB/token on the 35B, 4.9 on Flash-Next);
   context is limited by compute buffers, which scale with `-ub` on Flash-Next.
4. For coding use (opencode via llama-swap), the recommended setup is UD-Q4_K_M at
   `-c 131072..262144` with 80/52 cache slots - see the model pages for exact commands.

# local-llm-benchmarks

Benchmark reports for running local LLMs on two consumer GPUs, using two builds
of [llama.cpp](https://github.com/ggml-org/llama.cpp): the
[Codacus fork](https://github.com/thecodacus/llama.cpp) (branch `perf`) and upstream.
One Rig 2 model also has a
[vLLM](https://github.com/syv-ai/qwen38-27b-rtx3090) container stack.

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

Two **llama.cpp** builds plus one **vLLM** stack are used across the rigs, labeled as such
throughout these pages:

- **Codacus fork** ([thecodacus/llama.cpp](https://github.com/thecodacus/llama.cpp), branch `perf`,
  build b10818-27c54b4bb) - adds the prefill patches (`GGML_CUDA_REGISTER_HOST=1`,
  `GGML_SCHED_PREFETCH_EXPERTS=1`) and the VRAM-resident expert cache
  (`--moe-cache-profile` / `--moe-cache-slots`). Feature details in
  [methodology.md](methodology.md).
- **Upstream (stock)** ([ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)) -
  Rig 1: v0.4.0-dev 30b6a75; Rig 2: v0.4.0-dev build 10809 (5266f24da7). No fork features
  (no expert cache; the fork env vars are no-ops). The config of choice where the fork has
  nothing to add - e.g. every Rig 2 config at ncmoe 0, and IQ4_XS at 256k on Rig 1.
- **vLLM** ([syv-ai/qwen38-27b-rtx3090](https://github.com/syv-ai/qwen38-27b-rtx3090),
  vLLM 0.28.0) - the Rig 2 Qwen3.8-27B W4A16 stack, MTP with two KV modes: fp8 at 150000
  (4 drafts) and KVarN 4/2-bit at 250000 (slower decode), both with pinned pools. Its
  DFlash2 profile is archived. Engine labels are per-row on the model pages - llama.cpp and
  vLLM results are not interchangeable.

The llama.cpp builds support MTP speculative decode; the vLLM stack runs MTP.
Timings are read from `llama-server` request logs (llama.cpp) or vLLM's Prometheus metrics
(vLLM); `llama-bench` covered the initial prefill/decode sweeps.

## Contents

- [methodology.md](methodology.md) - env vars, measurement methods, VRAM headroom rule, caveats
- [test-prompts.md](test-prompts.md) - the actual prompt texts used for timing runs and traces (C#, React/TS, C++)
- [rig1-3060.md](rig1-3060.md) - Rig 1 hardware and build info
- [rig2-3090.md](rig2-3090.md) - Rig 2 hardware and build info
- [issues.md](issues.md) - Codacus fork/tool-level issues found during testing
- [models/rig1-3060/qwen36-35b-a3b.md](models/rig1-3060/qwen36-35b-a3b.md) - Qwen3.6-35B-A3B on Rig 1; full experiment log in [models/rig1-3060/qwen36-35b-a3b-archive.md](models/rig1-3060/qwen36-35b-a3b-archive.md)
- [models/rig1-3060/qwen38-flash-next.md](models/rig1-3060/qwen38-flash-next.md) - Qwen3.8-Flash-Next on Rig 1; full experiment log in [models/rig1-3060/qwen38-flash-next-archive.md](models/rig1-3060/qwen38-flash-next-archive.md)
- [models/rig1-3060/katcoder-v2.5-dev.md](models/rig1-3060/katcoder-v2.5-dev.md) - KAT-Coder-V2.5-Dev on Rig 1; full experiment log in [models/rig1-3060/katcoder-v2.5-dev-archive.md](models/rig1-3060/katcoder-v2.5-dev-archive.md)
- [models/rig2-3090/qwen36-35b-a3b.md](models/rig2-3090/qwen36-35b-a3b.md) - Qwen3.6-35B-A3B on Rig 2 (22 GB cap); full experiment log in [models/rig2-3090/qwen36-35b-a3b-archive.md](models/rig2-3090/qwen36-35b-a3b-archive.md)
- [models/rig2-3090/qwen38-27b.md](models/rig2-3090/qwen38-27b.md) - Qwen3.8-27B on Rig 2 (22 GB cap); full experiment log in [models/rig2-3090/qwen38-27b-archive.md](models/rig2-3090/qwen38-27b-archive.md)

## Headline results (Rig 1, t/s, q8_0 KV)

Headline tables list only usable configs (full context, no rejected/OOM setups). All
tested quants - including archived ones - are in the model pages: [Contents](#contents) above.
YaRN-extended rows raise context past the native window; answer quality at those lengths
is not validated.

| Model | Quant | Full-ctx support | Prefill t/s | Decode t/s | Notes |
| --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 262144 | 525.7 | **49.4** | Fastest plain decoder; MTP on (stock); cache incompatible (fused gate_up) |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 524288 (YaRN 2x) | 332.5 | 37.1 | Extended; MTP off, ncmoe 34 (7 GPU experts) |
| Qwen3.6-35B-A3B | IQ4_XS-4.19bpw | 753664 (YaRN 2.875x) | 282.0 | 32.3 | Extended max; MTP off, ncmoe 99 |
| Qwen3.8-Flash-Next | UD-IQ3_XXS | 230400 practical | 157.1 | **18.1** | Fastest Flash-Next quant; MTP on |
| Qwen3.8-Flash-Next | AD-Q4_K_M-M64 | 230400 practical | 154.7 | **13.1** | Add REGISTER_HOST for prefill; MTP off |
| KAT-Coder-V2.5-Dev | APEX-I-Compact | 262144 | 338.5 | **47.7** | qwen35moe; ncmoe 28 (hard floor with MTP); MTP on; ~517 t/s prefill on a 116K prompt |

## Headline results (Rig 2, t/s, 22 GB cap)

Headline tables list only usable configs (full context, no rejected/OOM setups). All
tested quants - including archived ones - are in the model pages: [Contents](#contents) above.
YaRN-extended rows raise context past the native window; answer quality at those lengths
is not validated. llama.cpp rows use q8_0 KV under the 22 GB cap; both vLLM rows pin their
KV pool by bytes to stay under the cap.

| Model | Quant | ncmoe | ctx | Prefill t/s | Decode t/s | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 0 | 262144 | 2375.8 | **165.1** | Full ctx at 22065 MiB; MTP on (stock); cache-compatible if ever needed |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 6 | 524288 (YaRN 2x) | 1656.7 | 89.9 | Extended; MTP off |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 15 | 786432 (YaRN 3x) | 1181.9 | 65.2 | Extended; MTP off |
| Qwen3.6-35B-A3B | UD-IQ4_XS | 25 | 1048576 (YaRN 4x) | 871.8 | 49.4 | Extended max (1M); MTP off |
| Qwen3.8-27B | W4A16-AutoRound-fast | n/a (vLLM) | 150000 | 1124 | 113 | vLLM 0.28.0 + MTP 4 drafts, fp8 KV, pinned pool (`MAX_LEN=150000`, `MAX_SEQS=4`); 22289 MiB |
| Qwen3.8-27B | W4A16-AutoRound-fast | n/a (vLLM) | 250000 | 960 | 86 | vLLM 0.28.0 + MTP, KVarN 4/2-bit KV, pinned pool (`CTX=huge`, `MAX_LEN=250000`); 22340 MiB; ~2.3x slower decode at 116K |

## Headline takeaways

1. Prefill patches (`GGML_CUDA_REGISTER_HOST=1` + `GGML_SCHED_PREFETCH_EXPERTS=1`) are the
   single biggest win everywhere: +104-137% on the 35B, +183-656% on Flash-Next.
2. The expert cache is a strong win for the 35B models (+25-45% decode), weak or a net
   loss for Flash-Next at 12 GB VRAM (512 experts, flat routing traffic).
3. KV cache at q8_0 is cheap on both arches (10.6 KiB/token on the 35B, 4.9 on Flash-Next);
   context is limited by compute buffers, which scale with `-ub` on Flash-Next.
4. For coding use (opencode via llama-swap), the recommended setup on the 35B is IQ4_XS
   (stock, MTP on) - it beats every quant tested at every context; the larger quants and
   the expert cache are archived. See the model pages for exact commands.

## References

External repositories referenced on these pages.

- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) - upstream (`stock`)
- [thecodacus/llama.cpp](https://github.com/thecodacus/llama.cpp) - Codacus fork, branch `perf`
- [syv-ai/qwen38-27b-rtx3090](https://github.com/syv-ai/qwen38-27b-rtx3090) - vLLM 0.28.0 container stack (Rig 2 Qwen3.8-27B W4A16)
- [da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments](https://github.com/da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments) - source of the messy-code refactor prompt

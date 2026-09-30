# Qwen3.8-27B (Rig 1) - experiment archive

Main page: [Qwen3.8-27B (Rig 1)](../qwen38-27b.md). Methodology: [methodology.md](../../../methodology.md).
Model-specific issues: [issues.md](../../../issues.md).

`Quants:` `IQ2_XS` (Swift-1.5 fine-tune) - the only quant on this rig.

## Setup

Re-run from scratch on the **stock** engine (the model is dense, so the moe-cache fork's
expert cache has nothing to act on) at **ctx 81920** (was 90000), q4_0 KV, embedded MTP
head on, ~10k opencode session prompt ([test-prompts.md](../../../test-prompts.md)).
The tuning axis was `-b/-ub`; the served config sets neither, so the defaults are
`-b 2048 -ub 512`.

## `-b/-ub` sweep (cache n/a, ctx 81920, q4_0 KV, MTP on, 10k prompt, second pass)

| `-b/-ub` | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| 512 | 467.8 | 36.6 | 11474 MiB |
| 1024 | 471.6 | 34.9 | 11826 MiB |
| 2048 | OOM | - | - |
| 3072 | OOM | - | - |
| 4096 | OOM | - | - |

Prefill is flat from 512 to 1024 (~+1%, within run-to-run noise): this hybrid SSM +
attention arch does not scale prefill with `-ub` the way a plain transformer does, so the
default `-ub 512` is already optimal and no `-b/-ub` flag is set in the config.

`-ub ≥ 2048` fails at load - the compute-buffer reservation cannot be satisfied:

    ggml_backend_cuda_buffer_type_alloc_buffer: allocating 960.33 MiB on device 0: cudaMalloc failed: out of memory
    ggml_gallocr_reserve_n_impl: failed to allocate CUDA0 buffer of size 1006977152
    graph_reserve: failed to allocate compute buffers
    llama_init_from_model: failed to initialize the context: failed to allocate compute pp buffers
    common_speculative_init_result: failed to create MTP context

## Headline (ctx 81920, default `-b/-ub`, 10k prompt, cold, 3 passes)

| pass | prefill t/s | decode t/s |
| --- | --- | --- |
| 1 (discarded) | 470.7 | 32.6 |
| 2 | 467.4 | 36.6 |
| 3 | 466.5 | 34.7 |

Measured value (mean of passes 2-3): **prefill 467 / decode 35.6**, VRAM 11474 MiB
(~814 MiB free).

## Long-context refactor benchmark (~60K prompt, ctx 81920, 2 passes)

| pass | prefill t/s | decode t/s |
| --- | --- | --- |
| 1 (discarded) | 384.6 | 24.7 |
| 2 | 383.5 | 24.4 |

Measured value: **prefill 383.5 / decode 24.4**, VRAM 11472 MiB. Prompt n=59751.

## Conclusions

- Stock engine; the fork adds nothing for a dense model. Native 262144 is out of reach on
  the 12 GB cap - q4_0 KV at ctx 81920 is the chosen operating point.
- Default `-b 2048 -ub 512` is optimal: prefill does not improve with a larger `-ub` and
  `-ub ≥ 2048` OOMs.
- Embedded MTP stays on (no separate draft model; draft KV q8_0).

# Unlocking the GA102 FP/BF16 issue rate: gpu-unlock and long-context prefill on an RTX 3090

> **Scope note:** every post-change number on this page was measured on 2026-10-23 with the unlock active from boot. The pre-change numbers are the published rows on the model cards, measured on the same rig, same prompts, same configs, with the module absent. The module changes GPU issue-rate state, not the model or the engine, so the comparison is config-matched rather than a re-tune.

[gpu-unlock](https://github.com/Zagitta/gpu-unlock) is an early-load Linux kernel module that raises the hidden FP/BF16 FMA issue rate on GA102/GA103/GA104/GA106 before the NVIDIA driver binds. It is not a driver patch and does not change clocks, power limits or memory bandwidth. This page answers one question: **does the unlocked issue rate show up in the inference workloads measured here, and where?**

## TL;DR

**Yes, and only in long-context prefill.** Enabling the module on the RTX 3090 lifts prefill on the Qwen3.8-27B vLLM stack by **+13.5% at ~60K and +16.0% at ~120K** (fp8 KV, 176128 context), and by **+11.3% / +16.4%** on the KVarN 262144 profile. The Swift-1.5 fine-tune on the same container replicates it (+10.5% / +14.2% on the same two profiles). The ~10K prompt is flat to slightly negative (−1.6% / −2.7%, inside run noise).

Isolating the part of prefill that scales with context — the extra per-token time over the ~10K baseline — gives **1.33x–1.68x**, which brackets the module repo's own FP16 (1.35x) and BF16 (1.80x) GEMM speedups. That is the signature of an issue-rate change: the work that scales with sequence length gets faster, the fixed and bandwidth-bound work does not.

Two negative controls behave as expected:

- **Decode** does not improve. Differences track MTP draft acceptance run-to-run, not the unlock.
- **The 35B MoE** (llama.cpp, expert-streaming) does not improve at all: −0.5% / +2.8% prefill, −2.1% decode at ~60K, all inside the ±2–4% single-run noise. Its prefill is dominated by MoE expert traffic and its decode by memory bandwidth, neither of which the issue rate touches.

**Verdict:** keep it enabled. It is free at inference time, survives driver updates, and is a real long-context prefill win on the dense 27B path. Record the unlock state alongside engine versions: a pre-unlock and a post-unlock number for the same config are **not comparable**.

## What the module changes

On GA10x, the FP32 and FP/BF16 FMA pipes share issue slots, and the shipped speed-selector state halves the FP/BF16 issue rate. The module writes SS0 = `0x88888888` (full BF16 rate) and SS1 = `0x8` (IMLA4), performs a function-level reset, and hands the GPU to the NVIDIA driver in the unlocked state. It runs from the initramfs before `nvidia` binds, which is why the write sticks.

The module repo's reference measurement is a 8192³ GEMM at 450 W: FP16 87.46 → 118.39 TFLOPS (1.35x), BF16 87.50 → 157.41 (1.80x), TF32 42.58 → 82.61 (1.94x). Those are pure-compute ceilings; inference sees a smaller, workload-dependent share, which is what the tables below quantify.

## Setup

Rig 2: RTX 3090 (GA102, 24 GB). The module is installed as a DKMS package plus an initramfs early-load entry, and opted in on the kernel command line with `gpu_unlock.targets=all`.

Install follows the module repo's distro instructions. Two things are easy to get wrong: the module must load from the **initramfs**, before the NVIDIA driver binds (loading it later does nothing), and the opt-in parameter must be a **separate** command-line token. On Arch-family systems the packaged hook covers mkinitcpio only, so a dracut setup also needs the repo's dracut config installed.

Verification (all three, not just "module is loaded"):

- `/proc/cmdline` contains `gpu_unlock.targets=all` as its own parameter.
- The initramfs contains `gpu_unlock.ko` and `rd.driver.pre=gpu_unlock`.
- The kernel log reports `gpu_unlock: unlocked` before the driver binds.

## Measurement method

Same protocol as the model cards ([methodology.md](../methodology.md)):

- vLLM rows: `/v1/completions`, 512 generated tokens, the checkpoint's default sampling (temperature 1.0, top_p 0.95, top_k 20), **cold load**, prefix caching disabled (`--no-enable-prefix-caching`) with `cached=0` asserted from `vllm:prompt_tokens_cached_total`; the recorded pass is the second one after load. Prefill and decode come from the server's Prometheus counters (`prompt_tokens_total / request_prefill_time_seconds`, `generation_tokens_total / request_decode_time_seconds`), not from wall-clock.
- llama.cpp rows: the `llama-server` response `timings`, same 512-token generation, cold load, second pass recorded.
- Prompts are the standard timing set: the ~10K opencode session context and the deterministic ~60K / ~120K refactor prompts ([test-prompts.md](../test-prompts.md)).
- Single run per cell. The rig's run-to-run spread on these configs is ±2–4%, which is why small deltas below are reported as noise rather than wins.

Configs are unchanged from the model cards:

- **27B, 176128:** fp8 KV, 4 chained MTP drafts, `MAX_SEQS=4`, 6.8 GB pinned pool, `INT8_ACT=int8`, `EMBED_UVA=1`.
- **27B, 262144:** KVarN 4/2-bit KV, 3 drafts, 5.3 GB pinned pool, `KVARN_FP16_DEQUANT=1`, `INT8_ACT=int8`, `EMBED_UVA=1`.
- **35B MoE, 262144:** moe-cache fork, UD-IQ4_XS, q8_0 KV, cache 0 + `--phase-aware-workspace`, `-b/-ub 4096`, MTP.

## Results

### Qwen3.8-27B, 176128 (fp8 KV, 4 drafts)

| prompt | prefill before | prefill after | Δ prefill | decode before | decode after | accept before → after |
| --- | --- | --- | --- | --- | --- | --- |
| ~10K | 2465 | 2426 | −1.6% | 120.6 | 103.7 | 61.9% → 56.2% |
| ~60K | 1610 | 1828 | **+13.5%** | 86.7 | 119.4 | 46.6% → 71.8% |
| ~120K | 1130 | 1311 | **+16.0%** | 91.3 | 89.1 | 63.1% → 58.7% |

Prefill t/s; decode t/s. Post-change VRAM 21870 MiB, unchanged.

### Qwen3.8-27B, 262144 (KVarN 4/2-bit KV, 3 drafts)

| prompt | prefill before | prefill after | Δ prefill | decode before | decode after | accept before → after |
| --- | --- | --- | --- | --- | --- | --- |
| ~10K | 2403 | 2339 | −2.7% | 101.8 | 88.4 | 60.3% → 55.4% |
| ~60K | 1686 | 1877 | **+11.3%** | 64.0 | 57.1 | 47.1% → 40.1% |
| ~120K | 1235 | 1438 | **+16.4%** | 49.2 | 48.8 | 49.8% → 54.5% |

Prefill t/s; decode t/s. Post-change VRAM 22036 MiB (vs 21756 MiB before), still under the cap.

### Qwen3.6-35B-A3B, 262144 (moe-cache fork) — negative control

| prompt | prefill before | prefill after | Δ prefill | decode before | decode after | Δ decode |
| --- | --- | --- | --- | --- | --- | --- |
| ~10K | 5258 | 5233 | −0.5% | 189 | 193.5 | +2.4% |
| ~60K | 4247 | 4364 | +2.8% | 146.8 | 143.7 | −2.1% |

Prefill t/s; decode t/s. VRAM 21894 → 21894 MiB. All deltas are inside the rig's single-run noise.

### Swift-1.5-Qwen3.8-27B — replication on the same container

The fine-tune is the same dense 27B stack, so it should see the same effect. It does:

| profile | prompt | prefill before | prefill after | Δ prefill | decode before | decode after | accept before → after |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 176128 fp8 | ~10K | 2433 | 2427 | −0.3% | 107.7 | 106.8 | 54.2% → 56.5% |
| 176128 fp8 | ~60K | 1590 | 1756 | **+10.5%** | 99.9 | 100.3 | 58.5% → 62.7% |
| 176128 fp8 | ~120K | 1122 | 1293 | **+15.3%** | 95.9 | 94.9 | 68.9% → 67.1% |
| 262144 KVarN | ~10K | 2374 | 2346 | −1.2% | 97.6 | 84.0 | 58.9% → 50.3% |
| 262144 KVarN | ~60K | 1595 | 1821 | **+14.2%** | 67.8 | 67.3 | 56.0% → 56.3% |
| 262144 KVarN | ~120K | 1228 | 1429 | **+16.4%** | 53.9 | 58.1 | 58.9% → 68.9% |

Prefill t/s; decode t/s. Peak VRAM unchanged (~22.0 GB fp8, ~21.9 GB KVarN, both inside the 22 GB budget). The decode spread again follows acceptance (the 262144 ~10K row dropped 9 points of acceptance and 14% decode together), not the unlock.

### The context-dependent component

Total prefill time per token is roughly `fixed + c·context`. The ~10K row is the baseline where `c·context` is small; differencing it out isolates the part the unlock should affect:

| profile | prompt pair | context-dependent prefill speedup |
| --- | --- | --- |
| 27B fp8 176128 | 10K → 60K | **1.60x** |
| 27B fp8 176128 | 10K → 120K | **1.37x** |
| 27B KVarN 262144 | 10K → 60K | **1.68x** |
| 27B KVarN 262144 | 10K → 120K | **1.47x** |
| Swift fp8 176128 | 10K → 60K | **1.39x** |
| Swift fp8 176128 | 10K → 120K | **1.33x** |
| Swift KVarN 262144 | 10K → 60K | **1.68x** |
| Swift KVarN 262144 | 10K → 120K | **1.44x** |

Computed as `(1/R₁₀ₖ − 1/R_ctx)_before / (1/R₁₀ₖ − 1/R_ctx)_after` from the prefill rates above. These sit between the repo's FP16 and BF16 GEMM ratios, which is the expected place for a mixed attention/GEMM workload.

## Why the gain lands where it does

- **Long-context prefill is issue-bound.** Attention over 60K–120K tokens is a large number of small FMA-heavy operations per token; raising the FMA issue rate cuts exactly the portion of prefill time that grows with context. The effect compounds with prompt length, which is why 120K gains slightly more than 60K in percentage terms.
- **~10K prefill is not.** At 10K the run is dominated by the fixed prompt-processing and the INT8 Marlin linear layers; the attention share is too small for a ~1.4–1.8x issue-rate change to clear noise. The small negative deltas are not a regression, just run variance.
- **Decode is bandwidth-bound at batch 1.** Each token reads the weights and the KV cache; issue rate is not the limiter. The large decode swings in the 27B tables (86.7 → 119.4 at 60K, 101.8 → 88.4 at 10K) follow MTP acceptance, which moves several points between boots on its own. There is no controlled acceptance-matched decode comparison here, so no decode claim is made.
- **The 35B MoE is the control that proves the mechanism.** Its prefill streams experts from host/VRAM and its decode is memory-bound; both are untouched. If the module had changed clocks, power or memory behaviour, this row would have moved too.

## Caveats

- **Single run per cell.** The prefill deltas at 60K/120K (+11–16%) are far outside the ±2–4% spread and reproduce across two boots and two KV profiles; the 10K deltas and every decode delta are not.
- **Acceptance is not controlled.** The 27B decode comparison is confounded by MTP acceptance moving between the before and after boots. Treat decode as unchanged pending an acceptance-matched run.
- **Pre-change rows are historical.** They come from the model cards measured before the module was installed, on the same rig and configs but different boots. The 35B control and the flat 10K rows are the evidence that the comparison is otherwise like-for-like.
- **The 27B, the Swift-1.5 fine-tune and the 35B were re-tested.** KAT-coder runs the same MoE stack as the 35B and is expected to be unaffected, but its card was not re-run.
- **Rig 1 is also in the module's target list** (GA106). Its unlock state has not been checked, so its published numbers should be assumed pre-unlock until verified.
- **The module repo's GEMM figures are not this workload.** They bound what the hardware can do, not what any particular model will see; the 1.33–1.68x context-dependent ratios above are the inference-level result.

## Reproduce / revert

Reproduce by installing the module as in **Setup**, booting with `gpu_unlock.targets=all`, confirming the three verification signals, then running the standard protocol against the configs on the [27B card](../models/rig2-3090/qwen38-27b.md) and [35B card](../models/rig2-3090/qwen36-35b-a3b.md).

Revert by removing `gpu_unlock.targets=all` from `/etc/kernel/cmdline`, regenerating the boot entry and initramfs, and rebooting. The module becomes inert without the parameter; the DKMS package can stay installed. After reverting, re-measure before comparing against the post-unlock rows on this page.

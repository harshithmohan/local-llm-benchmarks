# Unlocking the GA102 FP/BF16 issue rate on an RTX 3090

[gpu-unlock](https://github.com/Zagitta/gpu-unlock) is an early-load Linux kernel module that raises the hidden FP/BF16 FMA issue rate on GA102/GA103/GA104/GA106 before the NVIDIA driver binds. It is not a driver patch and does not change clocks, power limits or memory bandwidth.

The unlock is part of the rig's measured configuration, not a per-run knob: it is always on, so the current model-card rows already include it.

## What the module changes

On GA10x, the FP32 and FP/BF16 FMA pipes share issue slots, and the shipped speed-selector state halves the FP/BF16 issue rate. The module writes SS0 = `0x88888888` (full BF16 rate) and SS1 = `0x8` (IMLA4), performs a function-level reset, and hands the GPU to the NVIDIA driver in the unlocked state. It runs from the initramfs before `nvidia` binds, which is why the write sticks.

The module repo's reference measurement is an 8192³ GEMM at 450 W: FP16 1.35x, BF16 1.80x, TF32 1.94x over the locked state. Those are pure-compute ceilings; inference sees a smaller, workload-dependent share.

## Where the gain lands

- **Long-context prefill on the dense 27B vLLM path improves.** Attention over long prompts is a large number of small FMA-heavy operations per token; raising the FMA issue rate cuts exactly the portion of prefill time that grows with context.
- **~10K prefill is flat.** At that size the run is dominated by fixed prompt-processing and the linear layers; the attention share is too small for the issue-rate change to clear run noise.
- **Decode does not improve.** At batch 1 it is bandwidth-bound; observed decode differences track MTP draft acceptance, not the unlock.
- **The 35B MoE does not improve.** Its prefill streams experts and its decode is memory-bound, neither of which the issue rate touches. It is the negative control that confirms the mechanism.

**Verdict:** keep it enabled. It is free at inference time, survives driver updates, and is a real long-context prefill win on the dense 27B path.

## Setup

Rig 2: RTX 3090 (GA102, 24 GB). The module is installed as a DKMS package plus an initramfs early-load entry, and opted in on the kernel command line with `gpu_unlock.targets=all`.

Install follows the module repo's distro instructions. Two things are easy to get wrong: the module must load from the **initramfs**, before the NVIDIA driver binds (loading it later does nothing), and the opt-in parameter must be a **separate** command-line token. On Arch-family systems the packaged hook covers mkinitcpio only, so a dracut setup also needs the repo's dracut config installed.

Verification (all three, not just "module is loaded"):

- `/proc/cmdline` contains `gpu_unlock.targets=all` as its own parameter.
- The initramfs contains `gpu_unlock.ko` and `rd.driver.pre=gpu_unlock`.
- The kernel log reports `gpu_unlock: unlocked` before the driver binds.

## Caveats

- The unlock state is part of the measurement context: a pre-unlock and a post-unlock number for the same config are **not comparable**.
- The effect is outside single-run noise at long context and inside it at ~10K and on decode.
- The module repo's GEMM figures are hardware ceilings, not this workload's result.
- Rig 1 is also in the module's target list (GA106) and is unlocked at boot; see [rig1-3060.md](../rig1-3060.md).

## Reproduce / revert

Reproduce by installing the module as in **Setup**, booting with `gpu_unlock.targets=all`, and confirming the three verification signals. Then run the standard protocol from [methodology.md](../methodology.md) against the current configs on the [27B card](../models/rig2-3090/qwen38-27b.md) and [35B card](../models/rig2-3090/qwen36-35b-a3b.md).

Revert by removing `gpu_unlock.targets=all` from `/etc/kernel/cmdline`, regenerating the boot entry and initramfs, and rebooting. The module becomes inert without the parameter; the DKMS package can stay installed. Re-measure after reverting before comparing against the current rows.

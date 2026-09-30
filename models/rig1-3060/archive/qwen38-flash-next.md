# Qwen3.8-Flash-Next (Rig 1) - experiment archive

Fresh experiment log. Flash-Next was re-benchmarked from scratch on the
[moe-cache fork](../../../engine-notes/moe-cache-fork.md) at c 81920; earlier
fork measurements were retired with that engine and are not carried over.

Main card: [qwen38-flash-next.md](../qwen38-flash-next.md).
Methodology: [methodology.md](../../../methodology.md); issues: [issues.md](../../../issues.md).

Quants:

- `UD-IQ3_XXS` (76.32 GiB, 3 shards)

## Setup

- Engine: moe-cache fork ([GenerelSchwerz/llama.cpp](../../../engine-notes/moe-cache-fork.md),
  branch `moe-cache`, build b11608-2b8088c2a). Expert cache is opt-in and CUDA-only.
- Quant: `UD-IQ3_XXS`, 3 shards + a shared MTP sidecar (Q4_K_M 1.91 GB / Q8_0 2.79 GB).
- Context 81920 (tuned down from the 262144 native window); q8_0 KV; `-t 12`.
- Protocol: raw `/v1/completions`, `n_predict 512`, `cache_prompt false`, `ignore_eos true`,
  measured on the second pass; VRAM is the per-process `llama-server` allocation.
- Prompt: the ~10k opencode session-context prompt unless stated.

## Expert cache vs ncmoe (baseline, superseded)

The first pass of this re-run swept `--n-cpu-moe` on the same fork - the wrong axis, because
the fork's whole point is `--moe-expert-cache-size`, which *overrides* CPU-MoE placement.
Recorded here only as the baseline the cache is measured against (10k prompt, MTP via the
Q8_0 sidecar on CPU, `-b/-ub 2048`, `--load-mode mmap`):

| ncmoe | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| 48 | 156.0 | 12.72 | 8810 MiB |
| 47 | 175.1 | 12.63 | 9772 MiB |
| 46 | 195.6 | 12.96 | 10734 MiB |

`-b/-ub 4096` OOMs in this shape. Every cache config below beats this on both axes.

## Draft (MTP) placement

The shared MTP head is a separate model; its placement is a real variable on a 12 GB card.
First cache runs used `-ngld 0` (draft on CPU) because leaving it on the GPU OOMs the draft
load itself (`cudaMalloc failed: out of memory` allocating ~2.6 GB) once the main model +
cache fill VRAM. With the draft on CPU, MTP still loses to no-MTP because drafting competes
with the target's CPU expert work:

| config | MTP | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- |
| cache 48, `-b/-ub 512` | on (Q8_0, CPU) | 233.6 | 17.90 | 11178 MiB |
| cache 48, `-b/-ub 512` | off | 251.3 | **20.34** | 10700 MiB |
| cache 16, `-b/-ub 512` | on (Q8_0, GPU) | 244.5 | 15.20 | 10930 MiB |
| cache 40, `-b/-ub 512` | on (Q4_K_M, GPU) | OOM | - | - |

MTP off everywhere after this.

## Cache size

`--moe-expert-cache-size N` keeps N expert slabs per expert tensor (48 expert tensors here).
At 80k the ceiling is 48 slots; each slot is ~1.98 MB, so the pool is ~4.6 GB. `-b/-ub 512`,
MTP off:

| cache | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| 32 | 234.5 | 16.28 | 9730 MiB |
| 48 | 251.3 | 20.34 | 10700 MiB |
| 56 | 251.3 | 21.64 | 11372 MiB |
| 64 | OOM | - | - |

## `-b/-ub`

The compute buffer scales with `-ub` on this arch, so `-ub` and the cache size trade VRAM.
MTP off:

| cache | `-b/-ub` | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- |
| 48 | 512 | 251.3 | 20.34 | 10700 MiB |
| 48 | 1024 | 365.9 | 20.13 | 11366 MiB |
| 48 | 1280 | OOM | - | - |
| 48 | 1536 | OOM | - | - |
| 48 | 2048 | OOM | - | - |
| 56 | 512 | 251.3 | 21.64 | 11372 MiB |
| 56 | 768 | 315.4 | 21.01 | 11706 MiB |
| 56 | 1024 | OOM | - | - |

`-b/-ub 1024` at cache 48 is the best balance (much higher prefill, ~same decode).

## `--load-mode`

| load-mode | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| none | 251.3 | 20.34 | 10700 MiB |
| mmap | 89.9 | 12.57 | 10702 MiB |

`mmap` page-faults dominate: ~2.6x slower decode. `--load-mode none` (expert source allocated
in RAM) is required; `--lazy-mode on` keeps the 51B n-gram embedding table file-backed.

## Feature flags

At cache 48/56, MTP off:

| flag | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| (none) | 251.3 | 20.34 | 10700 MiB |
| `--ple-prefetch` | 251.1 | 20.51 | 10700 MiB |
| `--moe-early-router` | 249.1 | 20.64 | 11398 MiB |
| `--backend-sampling --decode-overlap --decode-boundary-overlap` | 248.5 | **22.04** | 11492 MiB |

PLE prefetch, early router, and the decode-overlap pair all measure within run-to-run noise
(a dedicated A/B on the 35B, which shares the engine, confirms the same); the overlap pair is
kept because it is free.

## Cache-path validation

One `--experimental-logs` pass on the recommended config (cache 48, `-b/-ub 1024`, overlap):
`moe-grouped-decode registered=48 covered=48 calls=6239 ready=6239 completed=6239`, with
`fallback=0 rollback=0 prepare_error=0 finish_error=0` and `upload_errors=0`;
`slot_capacity=2304` (= 48 tensors x 48 slots), `payload_capacity_bytes` 4.56 GB. Clean run.

## Long-context refactor benchmark (~60K prompt)

The ~60K refactor prompt at 80k on the recommended config (cache 48, `-b/-ub 1024`, MTP off,
overlap): prefill 341.5 t/s, decode 13.07 t/s (n=59751), VRAM 11492 MiB. Survives with the
792 MB headroom the 10k config leaves - no OOM on the large prompt.

## Conclusions

- The expert cache is the dominant lever on this model: it turns the ~13 t/s `-ncmoe`
  baseline into 20-22 t/s decode, with `--moe-expert-cache-size 48` + `-b/-ub 1024` the best
  prefill/decode balance at 80k.
- MTP does not pay at 12 GB: the draft cannot share the GPU with the cache, and a CPU draft
  costs more than it recovers.
- `--load-mode none` is mandatory; `mmap` loses ~2.6x decode. `--lazy-mode on` is required to
  keep the 51B n-gram embedding table off the hot path.
- Remaining knobs (`--ple-prefetch`, `--moe-early-router`) are neutral; decode overlap is a
  small, keepable win.

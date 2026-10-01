# Qwen3.8-Flash-Next (Rig 1) - experiment archive

Fresh experiment log. Flash-Next was re-benchmarked from scratch on the
[moe-cache fork](../../../engine-notes/moe-cache-fork.md) at c 81920; earlier
fork measurements were retired with that engine and are not carried over.

Main card: [qwen38-flash-next.md](../qwen38-flash-next.md).
Methodology: [methodology.md](../../../methodology.md); issues: [issues.md](../../../issues.md).

Quants:

- `UD-IQ3_XXS` (76.32 GiB, 3 shards)
- `GSQ-RCO Q2_0` (66.4 GB, 2 shards: 37.6 GB weights + 28.8 GB n-gram table)

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
overlap): prefill 341.5 t/s, decode 13.07 t/s (n=59751), VRAM 11492 MiB. No OOM on the
large prompt.

## GSQ-RCO Q2_0 (2.40 bpw)

A second quant, tested on the same fork, ctx, flags (q8_0 KV, MTP off, `--load-mode none
--lazy-mode on`, overlap) and protocol as UD-IQ3_XXS. Two shards: 37.6 GB of weights + a
28.8 GB n-gram table (66.4 GB total), per-tensor mixed types with the expert tensors mostly
in Q2_0 and the n-gram table in IQ4_NL.

### Cache size (10k prompt, `-b/-ub 1024`)

| cache | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| 48 | 441.8 | 23.89 | 9426 MiB |
| 64 | 440.7 | 24.63 | 10578 MiB |
| 72 | 435.9 | 24.81 | 10866 MiB |
| 80 | 435.6 | 25.65 | 11442 MiB |
| 84 | crash on first request | - | - |
| 88 | crash on first request | - | - |

Q2_0 slabs are smaller than IQ3_XXS's, so the cache ceiling is higher (80 vs 48) and every
cache size beats the UD quant at lower VRAM. Cache 84 and 88 load (server health check
passes) but the process dies on the first inference request - the slot-sizing trap the
large-prompt check exists to catch. At cache 64, `-b/-ub 2048` measured 441.4 / 24.79 at the
same 10578 MiB, so `-ub` is free here and does not move prefill.

### Long-context refactor benchmark (~60K prompt)

At cache 80 / `-b/-ub 1024` (n=59751, cold load): prefill 406.9 t/s, decode 14.66 t/s,
VRAM 11442 MiB. No OOM.

### MTP (shared head) on GSQ

The GSQ quant's smaller slabs leave room for the shared MTP head on the GPU, which the UD
quant never could. Q4_K_M head (1.91 GB), cache 48, ctx 81920, `-b/-ub 1024`, `--spec-type
draft-mtp --spec-draft-n-max 2`, q8_0 draft KV. Two runs each:

| prompt | prefill t/s | decode t/s | draft accept | VRAM |
| --- | --- | --- | --- | --- |
| 10k opencode | 426 | 35.2 / 34.3 | 82% / 81% | 11818 MiB |
| ~60K refactor | 398 | 23.3 / 25.1 | 76% / 81% | 11818 MiB |

MTP turns 25.7 into ~35 t/s at 10k and 14.7 into ~24 t/s at 60K. Cache 48 is the ceiling with
the head resident: `--spec-draft-n-max 3` and `4` both OOM the upstream, and the Q8_0 head
does not fit.

### Context ceiling with MTP

Can ctx grow past 80k? KV is cheap on this model - only the 12 Qwen Sparse Attention layers
carry it, the 36 Gated DeltaNet layers hold a constant state - so the limit is a target
compute-buffer OOM (the server reports `failed to allocate compute pp buffers`, ~402 MiB at
96k), not KV. ctx is paid for out of the same 12 GB budget as the MTP head and the expert
cache.

| ctx | cache | -ub | 10k prefill/decode | 60K prefill/decode | VRAM | loads |
| --- | --- | --- | --- | --- | --- | --- |
| 81920 | 48 | 1024 | 426 / 34.3-35.2 | 398 / 23.3-25.1 | 11818 MiB | yes |
| 98304 | 40 | 1024 | 388 / 33.2 | 390 / 23.8-24.4 | 11728 MiB | yes |
| 98304 | 48 | 512 | 310 / 37.2 | - | 11404 MiB | yes |
| 98304 | 44 | 1024 | | | | no |
| 98304 | 48 | 768 | | | | no |
| 114688 | 40 / 32 | 1024 | | | | no |
| 131072 | 40 / 32 | 1024 | | | | no |

96k is the hard ceiling; 112k fails at every workable cache. The balanced 96k point is cache
40: 60K is unchanged (390/24) while 10k gives up ~9% prefill and ~3-6% decode. Keeping cache
48 and halving `-ub` to 512 also fits and holds decode, but costs ~27% prefill, so it is not
worth it for long-context work. The 96k / cache-40 shape is the recommended config.

### Rejected: ngram-mod and --fit

- `ngram-mod` (draftless prompt-lookup, ~16 MB, no draft model): 24/48/64 gave 20.5 t/s at
  10k; 24/3/12 gave 24.4/14.8; 24/12/48 gave 19.6/14.5. Even 65% draft acceptance at 60K
  produced no gain. Never beat the no-spec baseline; kept off.
- `--fit on --fit-target 1024`: `--fit` only adjusts *unset* arguments, and here the only one
  is the context - it picked `n_ctx` 61440 at the same decode. A conservative ctx sizer, not
  a tuner. Forced off.

## Conclusions

- The expert cache is the dominant lever on this model: it turns the ~13 t/s `-ncmoe`
  baseline into 20-22 t/s decode, with `--moe-expert-cache-size 48` + `-b/-ub 1024` the best
  prefill/decode balance at 80k.
- MTP placement decides it: on `UD-IQ3_XXS` the head never fits beside the cache at 12 GB,
  and a CPU draft costs more than it recovers. On `GSQ-RCO Q2_0` the smaller slabs leave room
  for the Q4_K_M head on the GPU, and MTP lifts decode from 25.7 to ~35 t/s at 80k/cache 48.
  Dropping the cache to 40 frees the compute buffer for a 96k context - the ceiling with the
  head resident - at 388/33 (10k) and 390/24 (60K).
- `--load-mode none` is mandatory; `mmap` loses ~2.6x decode. `--lazy-mode on` is required to
  keep the 51B n-gram embedding table off the hot path.
- Remaining knobs (`--ple-prefetch`, `--moe-early-router`) are neutral; decode overlap is a
  small, keepable win.
- `GSQ-RCO Q2_0` is the faster quant on this rig: at cache 80 it does 436/25.7 at 10k and
  407/14.7 at 60K (vs 362/21.4 and 341/13.1 for UD-IQ3_XXS) at lower VRAM; with the MTP head
  it does 388/33 and 390/24 at 96k (or 426/35 and 398/24 at 80k/cache 48), the best config on
  the page. It is a 2.40 bpw quant, so this is a speed/VRAM win - the GSQ-RCO model card
  reports a lower task-average quality than IQ3_XXS (89.07 vs 92.57).

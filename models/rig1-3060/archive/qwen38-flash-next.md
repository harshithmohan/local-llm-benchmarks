# Qwen3.8-Flash-Next (Rig 1) - experiment archive

Fresh experiment log. Flash-Next was re-benchmarked from scratch on the
[moe-cache fork](../../../engine-notes/moe-cache-fork.md) at c 81920; earlier
fork measurements were retired with that engine and are not carried over.

Main card: [qwen38-flash-next.md](../qwen38-flash-next.md).
Methodology: [methodology.md](../../../methodology.md); issues: [issues.md](../../../issues.md).

Quants:

- `UD-IQ3_XXS` (76.32 GiB, 3 shards)
- `GSQ-RCO Q2_0` (66.4 GB, 2 shards: 37.6 GB weights + 28.8 GB n-gram table)
- `GSQ-RCO Coder IQ1_M` (58.4 GB, 2 shards: 29.6 GB pruned weights + 28.8 GB n-gram table)

## Setup

- Engine: moe-cache fork ([GenerelSchwerz/llama.cpp](../../../engine-notes/moe-cache-fork.md),
  branch `moe-cache`, build b11608-2b8088c2a). Expert cache is opt-in and CUDA-only.
- Quants: the three listed above; the MTP head is a separate sidecar (`UD-IQ3_XXS` uses the
  shared Q4_K_M 1.91 GB / Q8_0 2.79 GB head, `GSQ-RCO Q2_0` the ggml-org Q4_0 head).
- Context 81920 (tuned down from the 262144 native window); q8_0 KV; `-t 12`.
- Protocol: raw `/v1/completions`, `n_predict 512`, `cache_prompt false`, `ignore_eos true`,
  measured on the second pass; VRAM is the per-process `llama-server` allocation.
- Prompt: the ~10k opencode session-context prompt unless stated.

## UD-IQ3_XXS (76.32 GiB, 3 shards)

The following sections record this quant.

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

### MTP (Q4_0 head) on GSQ

The GSQ-RCO release ships no MTP head of its own, so the head used here is the official
[ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF)
`Q4_0` head (2.2 GB), loaded against the Q2_0 weights. Same flags as the shared-head run
(ctx 81920, `-b/-ub 1024`, `--spec-type draft-mtp --spec-draft-n-max 2`, q8_0 draft KV).

| prompt | cache | prefill t/s | decode t/s | draft accept | VRAM |
| --- | --- | --- | --- | --- | --- |
| 10k opencode | 40 | 428.9 | 35.13 | 86% | 10974 MiB |
| 10k opencode | 48 | 426.9 | 31.83 | 69% | 11550 MiB |

At 80k the cache-40 point is the one to use: it matches the shared Q4_K_M head at 80k/cache 48
(~35 t/s) while using ~0.8 GB less VRAM (10974 vs 11818 MiB). At the same cache 48 the Q4_0
head drafts worse (69% vs 81-82%) and is slower (31.8 vs 34.3-35.2). `--spec-draft-n-max 3`/`4`
were not retested with this head.

### Parameter ablation (Q4_0 head, ctx 81920)

Single-variant changes on the 80k / cache-40 Q4_0-head base (10k prompt, pass 2). The positive
deltas are within single-run noise; the losses are unambiguous.

| variant | prefill t/s | decode t/s | Δ decode | VRAM |
| --- | --- | --- | --- | --- |
| base (cache 40) | 428.9 | 35.13 | - | 10974 MiB |
| `--ple-prefetch` | 426.7 | 36.29 | +1.16 | 10974 MiB |
| `-C ff -Cb ffff` | 428.3 | 35.84 | +0.71 | 10974 MiB |
| `-t 8 --threads-batch 16` | 428.8 | 34.71 | -0.42 | 10974 MiB |
| `-ctk f16 -ctv f16` @cache 31 | 430.4 | 34.35 | -0.78 | 11386 MiB |
| `--ctx-checkpoints 0` | 434.7 | 33.61 | -1.52 | 10974 MiB |
| `--phase-aware-workspace` | 426.2 | 33.54 | -1.59 | 9432 MiB |
| `--live-context-workspace` | 426.0 | 31.48 | -3.65 | 9876 MiB |
| `--experimental-logs` | 427.2 | 31.02 | -4.11 | 10974 MiB |
| `--moe-early-router` | 427.2 | 29.61 | -5.52 | 10974 MiB |
| `-b 8192` | 426.3 | 27.86 | -7.27 | 10974 MiB |
| `--spec-default -C ff -Cb ffff` | 427.5 | 26.71 | -8.42 | 10974 MiB |

`--ple-prefetch` and `-C ff -Cb ffff` are the only positive changes and both are small enough
to be noise; every other knob costs decode. `-b 8192` and `--spec-default` also draft far
harder (up to 688 launches vs ~375) and still lose. The upstream `GGML_CUDA_MOE_EARLY_ROUTER=1`
env is this fork's `--moe-early-router`; `-kvo` is on by default, so passing it is a no-op.

### `-ub` / draft ubatch (Q4_0 head, cache 40)

Prefill scales with `-ub`, and on this fork the MTP draft context inherits the target `-ub`;
`--spec-draft-ubatch-size` (`-ubd`) sizes the draft context's own ubatch instead. With the
Q4_0 head at cache 40 (10k prompt, steady-state median of repeated passes):

| ctx | `-b/-ub` | `-ubd` | prefill t/s | prefill best | decode t/s | VRAM | result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 81920 | 1024 | 0 | 428 | 429 | 34 | 10974 MiB | baseline |
| 81920 | 1536 | 0 | - | - | - | 11744 MiB | loads, crashes mid-decode |
| 81920 | 1536 | 512 | **505** | **507** | 34 | 11534 MiB | works |
| 81920 | 1792 | 0 / 512 | - | - | - | - | load fails: `failed to allocate compute pp buffers` |
| 98304 | 1024 | 0 | 427 | 428 | 35 | 11460 MiB | works |
| 98304 | 1280 | 512 | - | - | - | 11740 MiB | loads, first-decode OOM |
| 98304 | 1536 | 512 | - | - | - | - | load fails at cache 40; cache 36/32 load 11836 MiB then first-decode OOM |

Capping the draft ubatch below `-ub` is what makes `-ub 1536` viable; uncapped it loads and
then dies mid-decode. At 80k that is ~+18% prefill over `-ub 1024` (505 vs 428) for ~+560 MiB,
with decode unchanged. At 96k only `-ub 1024` survives: `-ub 1280`/`1536` load then OOM on the
decode, and trimming the expert cache (40→36→32) does not lower the resident footprint (the
loader clamps the cache at 96k), so a bigger `-ub` cannot be bought with cache here. The
recommended config therefore trades 96k for 80k and takes the `-ub` bump.

The figures above are steady-state medians from 3 cold loads x 4 passes (2026-10-05), measured
after the model store was moved to local NVMe storage. Earlier figures on this page were taken
with the store on a FUSE-backed user share, which depressed and destabilised prefill (up to
~2x between passes of one config); those figures are relative-comparable but understated in
absolute terms. On local storage the recommended config read 504.8-507.0 t/s across the three
loads (±0.4%), stable from the second pass on.

### Context ceiling (Q4_0 head)

With the Q4_0 head and `-ub` held at 1024, ctx 98304 runs at the same cache 40 as above:

| ctx | cache | 10k prefill/decode | VRAM | result |
| --- | --- | --- | --- | --- |
| 98304 | 40 | 427 / 35 | 11460 MiB | works |
| 98304 | 44 | - | 11748 MiB (loaded) | first decode OOM: `CUDA error: out of memory` (ggml-cuda.cu:117) |
| 98304 | 48 | - | - | load fails: `failed to allocate compute pp buffers` |

96k costs ~0.5 GB more than 80k at the same cache and the same decode, so 96k / cache 40 is
the largest ctx that works; 44 is the first cache size that dies. The card now carries the
faster 80k / `-ub 1536` shape instead (see `-ub` / draft ubatch above): 16k less ctx for
~+18% prefill.

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
worth it for long-context work. The 96k / cache-40 shape was the best point with the shared
head; the config carried on the card uses the Q4_0 head at 80k / `-ub 1536` (see `-ub` /
draft ubatch above).

### Rejected: ngram-mod and --fit

- `ngram-mod` (draftless prompt-lookup, ~16 MB, no draft model): 24/48/64 gave 20.5 t/s at
  10k; 24/3/12 gave 24.4/14.8; 24/12/48 gave 19.6/14.5. Even 65% draft acceptance at 60K
  produced no gain. Never beat the no-spec baseline; kept off.
- `--fit on --fit-target 1024`: `--fit` only adjusts *unset* arguments, and here the only one
  is the context - it picked `n_ctx` 61440 at the same decode. A conservative ctx sizer, not
  a tuner. Forced off.

## GSQ-RCO Coder IQ1_M (29.6 GB weights, pruned to 256 experts)

A third quant on the same fork, same ctx/flags (q8_0 KV, `--load-mode none --lazy-mode on`,
overlap) and protocol. It is a different checkpoint, not a re-quant of the two above: the
"Coder" release removes 256 of the base's 512 experts per layer and stores the retained
weights at 3.5 bpw (1.89 bpw effective over the original transformer). Two shards: a
29.6 GB transformer shard plus the same 28.8 GB n-gram shard as `GSQ-RCO Q2_0`. No MTP
head ships with it. The n-gram/PLE plumbing and sampling are identical, so prefill tracks
the other quants; decode is lower (half the expert pool resident).

### Fork compatibility: `GGML_CUDA_DISABLE_FUSION=1`

Out of the box the fork loads the model (health check passes) but the first request dies:
`ggml_cuda_graph_evaluate_and_capture: op not supported ffn_moe_gate-N (MUL_MAT_ID)` ->
`llama_decode failed, ret = -3` -> process exit. The 512-expert quants are unaffected; the
256-expert layout makes the fork's cached-expert path build a MoE-gate node that CUDA graph
capture rejects. `GGML_CUDA_DISABLE_GRAPHS=1` did not help; `GGML_CUDA_DISABLE_FUSION=1`
avoids the fused node and the model serves normally. All numbers below use that env
(issues.md §6).

### Cache size (10k prompt, ctx 98304, `-b/-ub 1024`)

| cache | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| 16 | 461.1 | 16.73 | 9130 MiB |
| 24 | 460.1 | 17.91 | 9896 MiB |
| 32 | 460.2 | 18.97 | 10636 MiB |
| 40 | 458.3 | 19.94 | 11316 MiB |
| 48 | crash on first request | - | - |

Cache scales decode cleanly to the 96k VRAM ceiling at 40.

### Context ceiling (10k prompt)

| ctx | cache | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- |
| 65536 | 48 | 463.2 | 20.45 | 11286 MiB |
| 98304 | 40 | 458.3 | 19.94 | 11316 MiB |
| 131072 | 32 | 458.9 | 18.93 | 11512 MiB |
| 196608 | 16 | 457.9 | 16.88 | 11758 MiB |
| 262144 | 16 | crash on first request | - | - |

Ctx is paid for out of the same budget as the cache, so each doubling costs cache and
decode tracks cache. 96k/cache 40 and 128k/cache 32 are the balanced points; 64k buys the
fastest decode (20.4) if context is not needed; the ceiling is ~192k at cache 16.

### MTP (shared 512-expert head)

The base model's shared Q4_K_M MTP head does load against the coder and drafts correctly -
72% acceptance at cache 16/96k (draft 419, accepted 301) - but it adds ~1.9 GB and forces
the cache down: at 96k, cache 24 + MTP does not fit, and cache 16 + MTP (16.55 t/s) is no
better than cache 16 without MTP (16.73). MTP is not a win here.

### Long-context refactor benchmark (~60K prompt)

At cache 40 / 96k (n=59751, cold load): prefill 437.1 t/s, decode 12.64 t/s, VRAM
11310 MiB. No OOM. (64k/cache 48: 443/12.95; 128k/cache 32: 439/12.42.)

### Quality

The Coder card reports SWE-bench Verified 75.60 (91.3% of the 82.80 base) and
LiveCodeBench v6 86.28 (98.7% of 87.43). It is the pruned-expert, coder-targeted release;
for general use the card points at the unpruned `GSQ-RCO` quants.

## Conclusions

- The expert cache is the dominant lever on this model: it turns the ~13 t/s `-ncmoe`
  baseline into 20-22 t/s decode, with `--moe-expert-cache-size 48` + `-b/-ub 1024` the best
  prefill/decode balance at 80k.
- MTP placement decides it: on `UD-IQ3_XXS` the head never fits beside the cache at 12 GB,
  and a CPU draft costs more than it recovers. On `GSQ-RCO Q2_0` the smaller slabs leave room
  for the MTP head on the GPU, and MTP lifts decode from 23.9 to ~35 t/s. The shared Q4_K_M
  head reached 35.2 at 80k/cache 48 (11818 MiB) and 33 at 96k/cache 40; the Q4_0 head - the
  one available for this quant - reaches 35.0 at 96k/cache 40 with ~0.4 GB less VRAM
  (11460 MiB) and 35.1 at 80k/cache 40 (10974 MiB).
- A bigger `-ub` is the last prefill lever, but it only pays at 80k and only with the draft
  ubatch capped: `-ub 1536 --spec-draft-ubatch-size 512` gives ~+18% prefill over `-ub 1024`
  (505 vs 428) for ~+560 MiB, decode unchanged. Uncapped it loads then crashes on
  the first decode; `-ub 1792`/`2048` fail at load. At 96k only `-ub 1024` survives (a bigger
  `-ub` loads then OOMs on the first decode, and trimming the expert cache does not help), so
  the card trades 96k for 80k to take the bump.
- `--load-mode none` is mandatory; `mmap` loses ~2.6x decode. `--lazy-mode on` is required to
  keep the 51B n-gram embedding table off the hot path.
- Remaining knobs are neutral or negative: `--ple-prefetch` (+1.2) and CPU affinity (+0.7) are
  within noise, while `-b 8192`, `--spec-default`, `--moe-early-router`, `--experimental-logs`,
  `--live-context-workspace`, `--phase-aware-workspace`, f16 KV and `--ctx-checkpoints 0` all
  cost decode. Decode overlap is kept because it is free.
- `GSQ-RCO Q2_0` is the faster quant on this rig: at cache 80 it does 436/25.7 at 10k and
  407/14.7 at 60K (vs 362/21.4 and 341/13.1 for UD-IQ3_XXS) at lower VRAM; with the MTP head
  it does 428/35 at 96k/cache 40 and 429/35 at 80k/cache 40 (the shared head reached 388/33
  and 390/24 at 96k, or 426/35 and 398/24 at 80k/cache 48). It is a 2.40 bpw quant, so this is a speed/VRAM win - the
  GSQ-RCO model card reports a lower task-average quality than IQ3_XXS (89.07 vs 92.57).
- `GSQ-RCO Coder IQ1_M` runs (with `GGML_CUDA_DISABLE_FUSION=1`) but is the slowest quant
  tested here: 458/19.9 at 96k/cache 40, and the only one whose expert cache needs the fusion
  workaround. It is a pruned coder checkpoint (256 experts, 1.89 bpw effective), not a
  re-quant, so its decode is not directly comparable with the 512-expert quants - it trades
  speed for size and a code/agentic quality target.

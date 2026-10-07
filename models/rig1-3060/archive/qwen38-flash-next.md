# Qwen3.8-Flash-Next (Rig 1) - experiment archive

Fresh experiment log. Flash-Next was re-benchmarked from scratch on the
[moe-cache fork](../../../engine-notes/moe-cache-fork.md) at c 81920; earlier
fork measurements were retired with that engine and are not carried over. The
`GSQ-RCO Q2_0` fork config itself moved here on 2026-10-06, when the main card
switched that quant to the Strata pack engine on the same weights.

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
cache fill VRAM. With the draft on CPU, MTP still loses to no-MTP - the cache-48 / `-b/-ub 512`
baseline without MTP is 251.3 / 20.34 in Cache size below - because drafting competes with the
target's CPU expert work:

| config | MTP | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- |
| cache 48, `-b/-ub 512` | on (Q8_0, CPU) | 233.6 | 17.90 | 11178 MiB |
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
| 48 | 1024 | 365.9 | 20.13 | 11366 MiB |
| 48 | 1280, 1536, 2048 | OOM | - | - |
| 56 | 768 | 315.4 | 21.01 | 11706 MiB |
| 56 | 1024 | OOM | - | - |

The two `-b/-ub 512` rows are the Cache size baselines above. `-b/-ub 1024` at cache 48 is the
best balance (much higher prefill, ~same decode).

## `--load-mode`

Against `none` (251.3 / 20.34, Cache size above):

| load-mode | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| mmap | 89.9 | 12.57 | 10702 MiB |

`mmap` page-faults dominate: ~2.6x slower decode. `--load-mode none` (expert source allocated
in RAM) is required; `--lazy-mode on` keeps the 51B n-gram embedding table file-backed.

## Feature flags

At cache 48/56, MTP off, against the cache-48 baseline above (251.3 / 20.34):

| flag | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
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

### Recommended config (moe-cache fork, retired 2026-10-06)

The shape the main card carried for this quant before the Strata pack engine replaced it
(80k ctx, cache 40, Q4_0 MTP head, `-b/-ub 1536` with the draft ubatch capped at 512):

    llama-server --port PORT \
      -m <models>/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
      --ctx-size 81920 -ngl all -fit off \
      --moe-expert-cache-size 40 \
      --spec-draft-model <models>/mtp-Qwen3.8-Flash-Next-Q4_0.gguf \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --lazy-mode on --no-mmproj-offload --threads 12 --parallel 1 \
      --backend-sampling --decode-overlap --decode-boundary-overlap \
      --cache-ram 0 \
      -b 1536 -ub 1536 --spec-draft-ubatch-size 512 \
      --temp 1.0 --top-k 20 --min-p 0.0

Measured: 505 / 34 at 11534 MiB - the `-ub` table below carries it with the local-NVMe spread.

### Cache size (10k prompt, `-b/-ub 1024`)

| cache | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| 48 | 441.8 | 23.89 | 9426 MiB |
| 64 | 440.7 | 24.63 | 10578 MiB |
| 72 | 435.9 | 24.81 | 10866 MiB |
| 80 | 435.6 | 25.65 | 11442 MiB |
| 84 | crash on first request | - | - |

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

Cache 48 is the ceiling with
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
| 98304 | 1280 | 512 | - | - | - | 11740 MiB | loads, first-decode OOM |
| 98304 | 1536 | 512 | - | - | - | - | load fails at cache 40; cache 36/32 load 11836 MiB then first-decode OOM |

Capping the draft ubatch below `-ub` is what makes `-ub 1536` viable; uncapped it loads and
then dies mid-decode. At 80k that is ~+18% prefill over `-ub 1024` (505 vs 428) for ~+560 MiB,
with decode unchanged. At 96k only `-ub 1024` survives (its measurement is the 98304 / cache-40
row below): `-ub 1280`/`1536` load then OOM on the
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
| 98304 | 40 | 427 (best 428) / 35 | 11460 MiB | works |
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
| 98304 | 40 | 1024 | 388 / 33.2 | 390 / 23.8-24.4 | 11728 MiB | yes |
| 98304 | 48 | 512 | 310 / 37.2 | - | 11404 MiB | yes |
| 98304 | 44 | 1024 | | | | no |
| 98304 | 48 | 768 | | | | no |
| 114688 | 40 / 32 | 1024 | | | | no |
| 131072 | 40 / 32 | 1024 | | | | no |

96k is the hard ceiling; 112k fails at every workable cache. The balanced 96k point is cache
40: against the 80k / cache-48 row in "MTP (shared head) on GSQ" (426 / 398), 60K is unchanged
(390/24) while 10k gives up ~9% prefill and ~3-6% decode. Keeping cache
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
| 131072 | 32 | 458.9 | 18.93 | 11512 MiB |
| 196608 | 16 | 457.9 | 16.88 | 11758 MiB |
| 262144 | 16 | crash on first request | - | - |

Ctx is paid for out of the same budget as the cache, so each doubling costs cache and
decode tracks cache. 96k/cache 40 (the cache-size row above) and 128k/cache 32 are the balanced
points; 64k buys the fastest decode (20.4) if context is not needed; the ceiling is ~192k at
cache 16.

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

### Strata pack engine

The same checkpoint runs on the engine the `GSQ-RCO` quants serve on, and a pack is
checkpoint-bound: `native_experts.txt` records the expert count and the absolute offsets into
the source shard (`n_expert 256` here against the base's 512), so the coder needs its own pack
(`<pack>/coder-iq1_m`) and its own expert profile - the engine ships
`expert-profile-coder.bin`, half the size of the 512-expert one. The shared MTP runtime from the
base's checkpoint loads unchanged.

Sizing inverts the expert count: the coder resolves a **smaller** prompt chunk (3200) than the
base (6144 at a 200000 window, 8192 at 150000), because the chunk is what the expert cache can
lend and the coder's cache holds 1387 slots against the base's 2670. Two compounding causes:

- each expert blob is about twice as large (largest blob 2.66 MB against 1.38 MB), because the
  quant keeps half the experts at ~3.5 bits: 98 MiB per expert over a 23.4 GiB arena against
  63 MiB over 31.6 GiB;
- less VRAM reaches the cache: 3.57 GiB free against 4.30, from the native projections
  (2018.88 against 1376.20 MiB), the Q5_K output head (497 against 417), the embedding
  (322 against 260) and the draft reserve (218 against 184).

The engine clamps an oversized pin instead of rejecting it - `prompt chunk 3328 -> 1664 tokens so
its buffers fit in every expert cache` - so a pin has to sit below the ceiling rather than be
trimmed after a failed load. Of the pins tested, 3072, 3136, 3200 and 3216 were accepted
unclamped, 3248 is the last accepted one, and 3264 halves to 1632. Measured at `--prefill 3200`,
the largest accepted value with margin, on a 200000 window:

| prompt | prefill t/s | decode t/s | drafts accepted | expert cache hit |
| --- | --- | --- | --- | --- |
| 10k opencode | 932.8 | 30.3 | 75% (250/333) | 67.5% |
| ~60K refactor | 950.2 | 28.4 | 68% (213/311) | 68.5% |

Both passes reached the full 512-token window with `cache_n` 0. Against `GSQ-RCO Q2_0` on the
same engine and window (200000, chunk 6144: 1058.5 / 39.6 at 10k and 1020.5 / 39.9 at 60K) the
coder gives up 12% prefill and 23% decode at 10k, and 7% and 29% at 60K - the half-sized expert
pool costs decode far more than prefill, and the lower hit rate (68% against 78%) is the
mechanism. The same 10k prompt at the auto chunk (3072) and the default checkpoint interval
measured 965.4 / 28.6, inside run-to-run spread at this size.

`--prompt-cache-every` is pinned to the chunk (3200) as on the base quants. In a measurement
(`--prompt-cache 0`) no checkpoints are written at all - every pass logged `0 checkpoints` - so
the interval costs nothing measurable in these single-shot rows; it is a growing-session setting,
where checkpoints snap to chunk boundaries. On the served shape (default conversation cache) the
same 10k prompt logs `4 checkpoints`, so the pin is what the engine snapshots at.

## Spec window and min-p sweep (Strata, `GSQ-RCO Q2_0`)

The `GSQ-RCO Q2_0` card runs this quant on the Strata pack engine, so the speculative pair was
tuned there: `--spec T` (verify window) x `--spec-min-p F` (draft acceptance floor), `T` in
2/3/4 and `F` in 0.0/0.5. `T = 1` is not available here - a native (IQ) pack refuses to start
without `--spec T` with `T >= 2`.

Protocol differs from the fork rows above: Strata serves no raw `/v1/completions`, so each row
is a `/v1/chat/completions` pass on the ~10k prompt with `--prompt-cache 0`, and only a pass
reporting `cache_n` 0 and `predicted_n` 512 is recorded. ctx 81920, `--kv int8`, MTP on. The
recorded pass is the second one; the first is page-in and appears in the spread note below.

| `--spec` | `--spec-min-p` | prefill t/s | decode t/s | drafts | accepted | acceptance | VRAM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.0 | 1063.7 | 42.7 | 315 | 196 | 62.2% | 11350 MiB |
| 2 | 0.5 | 1058.6 | 43.5 | 235 | 173 | 73.6% | 11350 MiB |
| 3 | 0.0 | 1059.0 | 41.4 | 510 | 258 | 50.6% | 11358 MiB |
| 3 | 0.5 | 1058.3 | 43.6 | 330 | 218 | 66.1% | 11358 MiB |
| 4 | 0.0 | 1059.4 | 37.3 | 687 | 282 | 41.0% | 11362 MiB |
| 4 | 0.5 | 1058.5 | 44.1 | 397 | 260 | 65.5% | 11362 MiB |

- The floor is the lever, not the window. At `--spec-min-p 0.0` the verify window is always the
  full `--spec`, so a wider window only buys more rejected drafts: `--spec 4` falls to 37.3 t/s
  at 41.0% acceptance. At `0.5` the window is truncated to the leading drafts that clear the
  floor, and decode is flat across the window width here (43.5 / 43.6 / 44.1 t/s) while
  acceptance still swings 66-74%.
- Accepted tokens per token decoded is *highest* in the worst row (0.55 at `4 / 0.0` against
  0.51 at `4 / 0.5`) - the
  [judge MTP by tok/s, not acceptance rate](../../../tuning.md#judge-mtp-by-toks-not-acceptance-rate)
  rule again.
- `--spec 4 --spec-min-p 0.5` stays (44.1 t/s); `--spec 3 --spec-min-p 0.5` (43.6) is within the
  +-10-15% MTP decode noise. Prefill is unaffected by either knob (1058-1064 t/s), and VRAM
  grows only 12 MiB from `--spec 2` to `--spec 4`.

## Context size and prompt-chunk ladder (Strata, `GSQ-RCO Q2_0`)

`--prefill auto` sizes its chunk from what the expert cache can lend, and the cache shrinks as
the KV grows - so raising `--max-context` eventually costs prompt *read* speed, not decode.
This swept ctx to find where the chunk steps down. One cold load per ctx, `--kv int8`, MTP on,
`--prompt-cache 0`. Both the chosen chunk and the slots it borrows are named in the startup
line, so rows marked *probe* come from the load alone; *full* rows also ran the prompt set below.

| `--max-context` | VRAM free | expert-cache slots | prompt chunk | slot loan | rows |
| --- | --- | --- | --- | --- | --- |
| 81920 | 6.02 GiB | 4008 | 8192 | 3071 (3.95 GiB) | full |
| 102400 | 5.73 | 3777 | 8192 | 3071 (3.95) | full |
| 122880 | 5.43 | 3545 | 8192 | 3071 (3.95) | full |
| 133120 | 5.28 | 3428 | 8192 | 3071 (3.95) | probe |
| 143360 | 5.13 | 3311 | 6144 | 2427 (3.12) | probe |
| 153600 | 4.98 | 3196 | 6144 | 2427 (3.12) | full |
| 194560 | 4.38 | 2733 | 6144 | 2427 (3.12) | probe |
| 198656 | 4.32 | 2685 | 4096 | 1782 (2.29) | probe |
| 204800 | 4.23 | 2617 | 4096 | 1782 (2.29) | probe |
| 229376 | 3.87 | 2337 | 4096 | 1782 (2.29) | probe |
| 262144 | 3.40 | 1966 | 3072 | 1460 (1.88) | probe |

Speeds on the *full* rows, prefill / decode t/s. Every pass reports `cache_n` 0 and
`predicted_n` 512, and the recorded pass is the second one (the first is page-in):

| `--max-context` | chunk | ~10k | ~60K (59802) | ~98k (98623) | ~148k (149266) |
| --- | --- | --- | --- | --- | --- |
| 81920 | 8192 | 1058.6 / 44.1 | 1089.6 / 41.2 | - | - |
| 102400 | 8192 | 1056.5 / 41.5 | 1085.6 / 42.1 | 1065.9 / 42.2 | - |
| 122880 | 8192 | 1059.4 / 40.3 | 1087.4 / 42.6 | 1062.3 / 40.6 | - |
| 153600 | 6144 | 1056.3 / 42.5 | 1013.4 / 39.7 | 948.5 / 38.3 | 890.3 / 37.2 |

- **The chunk, not the context, is what costs.** Both 10k and 60K rows are flat from 80k to
  120k ctx (<0.5%), and every config loads to the same 11362 MiB with prompts ending at
  11492-11514 MiB. The 150k config's own 98k prefill reproduces to 5 ms across two passes
  (103983 / 103978 ms, 104 s apart), so the loss is not thermal or run-to-run: it is the
  smaller chunk, chosen because the loan that fits a 6144-token chunk stops fitting the cache.
  The served window at the end of this section is the other half: with the cache pinned so the
  chunk and loan cannot move, a wider window still reads the same prompt ~8% slower.
- **Where the steps fall.** The engine picks the largest size on its fixed list
  (`8192, 6144, 4096, 3072, 2048, ...`) whose per-chunk buffers leave >= 128 cache slots free and
  take at most 90% of them (85% when under 90% of the expert bytes are pinned host RAM):
  8192 holds to ~134k ctx, 6144 to ~198k, 4096 to ~261k, and 3072 only above that. The rule
  reproduces all 11 rows, including the 198656 pair (2685 slots against the 2697 that 6144
  needs).
- The 81920 config this ladder was built around sat just under the 8192 -> 6144 step, which is
  why it kept the widest chunk; the config served now (150000, with an explicit `8192`) is at the
  end of this section. A 190k-class config would still read in 6144-token chunks.
- **The cap is a share of the resident cache, not of free VRAM.** Forcing `--expert-cache 3248`
  at 122880 steps the chunk down to 6144 (loan 2427) even though 866 MiB is free - 0.90 x 3248 =
  2923 < 3071, so the percentage is the test that binds. Holding the 8192 chunk therefore means
  holding >= ~3413 resident slots (>= ~3233 at the 95% cap), and since the window is what sizes
  the cache, that is what fixes the affordable ctx.

### The loan cap

`STRATA_PREFILL_LEND_PCT` raises the share of the expert cache the prompt path may borrow, which
moves the chunk bands without touching the engine. Load-only probes, `--kv int8`, MTP on:

| `--max-context` | slots | chunk @90% | chunk @95% |
| --- | --- | --- | --- |
| 153600 | 3196 | 6144 | 6144 |
| 204800 | 2617 | 4096 | 6144 |
| 262144 | 1966 | 3072 | 4096 |

- **Where the bands move.** The 8192 -> 6144 step goes from ~134k to ~150k ctx and the
  6144 -> 4096 step from ~198k to ~210k; 4096 only stops fitting at ~1876 slots (~270k ctx),
  past the end of the native window, so 3072 never comes back. 153600 (the 8192 loan fits
  neither way) and 229376 (95% of 2337 slots still is not enough for 6144) are unchanged, and
  where the chosen chunk does not change at all the env does nothing.
- **What the wider loan buys.** At ctx 204800 the ~148k prompt (149266 tokens) reads in
  167603 ms / 890.6 t/s at 6144 x 95% against 178367 ms / 836.8 t/s at 4096 x 90% (+6.4%), with
  decode inside noise and the same footprint (474 MiB free). It tracks the chunk, not the
  context - 890.6 matches the 153600 + 90% row's 890.3 - and leaves a more relevant resident set
  (decode hit rate 77.6% against 70.8%).
- **The served config does not use the env.** It pins the chunk with an explicit `--prefill
  8192`, which only has to fit and never consults the percentage, so the window can be 150000
  where `auto` would step down to 6144.

### The chunk costs more the longer the prompt

One cold load per context, three prompts on each (10k = 10507, 60k = 59802, 120k = 119344
tokens), `--spec 4 --spec-min-p 0.5`, `--kv int8`, MTP on, `--prompt-cache 0`; every recorded
pass reports `cache_n` 0 and `predicted_n` 512 (prefill / decode t/s). The 150000 row is the
retired shape; 200000 and 250000 are the two served ones.

| `--max-context` | chunk | ~10k | ~60K | ~120k |
| --- | --- | --- | --- | --- |
| 150000 (retired) | 8192 | 1072.2 / 39.8 | 1065.0 / 41.0 | 973.9 / 38.8 |
| 200000 (served default) | 6144 | 1058.5 / 39.6 | 1020.5 / 39.9 | 928.5 / 37.2 |
| 250000 (served overflow) | 4096 | 973.4 / 38.1 | 946.3 / 37.1 | 864.0 / 35.0 |

- The step down from 8192 at 150000 to 4096 at 250000 - window and chunk together - costs 9.2%
  prefill at 10k and 11.3% at 120k, of which the chunk alone is -4.7% and -7.0% between the two
  served tiers at 120k. A 208000 measurement of the same shape as the served default (1052.8 /
  1016.7 / 923.1) agreed within 0.5%, so it is not shown separately.
- **A longer prompt costs ~9-12% at every chunk** - 1072 -> 974, 1059 -> 929, 973 -> 864 from
  10k to 120k - so this is attention over the prompt, not cache sizing, and it is independent of
  the chunk.
- **Decode tracks the resident set, not the prompt.** It goes 39.6 / 39.9 / 37.2 on the 2670-slot
  cache against 38.1 / 37.1 / 35.0 on the 2104-slot one (decode expert-cache hit rate 69-73%
  across these passes). Treat an individual cell as noise: 2000-token generations on the same
  119344-token prompt put the tiers at 43.2 / 42.0 / 40.3 t/s with a +-14% spread *within* each
  tier, so only a difference that holds across prompt sizes reads as a tier cost.
- Decode carries MTP acceptance variance (65-73% of drafts accepted across these runs), so read
  a few percent as noise.

### The served windows

Two entries run since 2026-10-07. The default is 200000 ctx with an explicit `--prefill 6144` and
`--prompt-cache-every 6144`; the overflow is 250000 ctx with an explicit `--prefill 4096` and
`--prompt-cache-every 4096`. Both pin the chunk because `--prefill auto` steps down with the
window: at 200000 the auto cache lands on 2670 slots, and 0.90 x 2670 = 2403 is under the 2427
slots a 6144-token chunk needs, so `auto` would take 4096. An explicit chunk only has to fit
(2427 + 128 <= 2670) and is not subject to the percentage at all - with no such variable set
anywhere the cold loads report `the prompt path borrows 2427 / 1782 CUDA0 cache slots`, 474 / 476
MiB free, 11364 / 11362 MiB after load and 11514 / 11510 under requests. At 250000 the pin is
redundant (`auto` lands on 2104 slots, and 0.90 x 2104 = 1894 >= 1782 already holds 4096); it is
there for uniformity. Before this the served shape was 150000 with `--prefill 8192`, and before
that 81920 with `--prefill auto`.

- **What retires the 8192 chunk is the miss, not the rate.** Its edge is prefill only (the chunk
  table above), decode is equal, and a cached turn pays nothing: +6.5 s per full re-prefill at
  120k, under 0.3 s per cached turn. The wider windows buy more.
- **The window itself costs, and free VRAM does not buy the chunk back.** Against the same 8192
  chunk at 122880 (3545 slots) the step 122880 -> 149000 reads 10k 1059.4 -> 1072.2, 60K 1087.4
  -> 1065.0, 120k 1056.3 -> 973.9: the window, not the chunk, which is 8192/3071 either way.
  Pinning the cache at 3300 so that chunk and loan stay fixed while only `--max-context` moves
  gave the same 8.1% (1056.8 -> 971.7 on the ~119k prompt), and free VRAM is not the driver -
  122880 reads that prompt the same (1057.6 / 1056.8) with 476 and 798 MiB free. The mechanism is
  not linear in ctx either (the 6144 pair is flat from 153600 to 208000), so the working rule is
  to size `--max-context` to what you serve.
- **Where the chunk stops fitting sets the ceiling.** An explicit chunk needs `chunk/2 + 128`
  cache slots and the cache shrinks about 1.13 slots per 100 ctx, so 8192 holds to ~153k, 6144 to
  ~210k and 4096 to ~267k. 262144 would fit a 4096 chunk with 56 slots to spare, so 250000 is the
  served overflow with margin rather than the native maximum.
- Decode reads a few percent under the 81920-era rows (44.1 at 10k) because the smaller cache
  holds fewer experts, and the two 120k passes ran 122510 / 122548 ms, so the prefill at least is
  not drift.

### Growing sessions: what the conversation cache costs

Every row above is a cold, cache-free read (`--prompt-cache 0`). A real session does not resend a
full prompt, it grows, so this ran one request per turn, each carrying a longer prefix of the same
~248k-token corpus (10k start, +6k per turn, 256 tokens generated per turn; one cold load per
arm, ctx 200000 with the 6144 chunk against ctx 250000 with the 4096 chunk).

- **Checkpoints land on chunk boundaries, so the default cache cadence is coarse.** With the
  default `--prompt-cache-every 16384`, the youngest checkpoint a turn can resume from is the
  largest multiple of the prompt chunk below the prompt, so the effective step is
  `ceil(16384 / chunk) x chunk` - 18432 on a 6144 chunk, 16384 on a 4096 chunk. The first three
  turns have no checkpoint at all (full reads of 9.9k / 16k / 22k), and after that a
  *6000-token* turn re-reads 14738 (6144 arm) / 13611 (4096 arm) tokens on average - **2.46x /
  2.27x the new tokens**, cycling ~9k, ~15k, ~21k.
- **Pinning `--prompt-cache-every` to the chunk is the fix.** On the 6144 arm `cache_n` then
  advances in exact 6144 steps, the re-read falls to 8525-9878 (mean 8901, **1.48x**), and the
  23-turn ladder goes from 555 s to 416 s (-25%) with every turn in 16.5-19.8 s instead of
  16.5-34.5 s. The turn at 142k reads in 12026 ms against 19755 ms (-39%) even though the smaller
  batches read slightly slower per token (708.9 against 742.5 t/s); decode (37.4 t/s), hit rate
  (74-76%) and VRAM (11494 MiB) do not move. The 4096 arm behaves the same way: the shared ladder
  goes 565 s -> 413 s and the eight extension turns 330 s -> 241 s (sum 896 s -> 654 s), re-read
  mean 13611 -> 7877 (**2.27x -> 1.31x**), and no extension turn exceeds 34 s against 48-55 s
  before. The grid cannot be finer than one chunk, so the chunk size is the optimum value.
- **Depth, not the window, is what a session pays.** Same policy, same arm size: the read runs
  1026 t/s over the first 30k, 960 at 30-60k, 862 at 60-90k, 787 at 90-120k and 752 at 120-150k
  on the 6144 chunk (-27% to 142k), against 964 / 879 / 810 / 734 / 698 on the 4096 chunk at
  250000, which continues 626 (150-200k) and 540 (200-300k), -45% end to end. At equal depth the
  6144 chunk is ~5% faster per token. A session driven into the extension therefore pays 29-55 s
  per turn for its last 90k (worst 55.2 s at 220k, reading 25459 tokens at 545 t/s).
- The amplification is the step size against the grid: a turn that adds more material, or reaches
  further back, re-reads proportionally less of it - the 2.46x above is the small-step case a
  coding agent hits when it appends one file to a conversation it keeps resending.

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
  speed for size and a code/agentic quality target. On the pack engine it reaches 932.8/30.3 at
  10k and 950.2/28.4 at 60K on a 200000 window, against 1058.5/39.6 and 1020.5/39.9 for
  `GSQ-RCO Q2_0` on the same engine and window.

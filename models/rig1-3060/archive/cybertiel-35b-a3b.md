# Cyber-Tiel-Coder-35B-A3B (Rig 1) - experiment archive

Fresh experiment log - first measurement of this model on the rig, all on the [moe-cache fork](../../../engine-notes/moe-cache-fork.md) at ctx 262144.

Main card: [cybertiel-35b-a3b.md](../cybertiel-35b-a3b.md). Methodology: [methodology.md](../../../methodology.md); issues: [issues.md](../../../issues.md).

Quants:

- `UD-IQ4_XS` (16.88 GiB, 18119934272 bytes, single file) + `mmproj-Cyber-Tiel-Coder-35B-A3B-BF16.gguf` (902822016 bytes) - **the shipped quant** on this rig.
- `UD-Q4_K_XL` (21.19 GiB, 22749880640 bytes, single file), same mmproj - a copy of the Rig 2 quant moved onto the rig and swept on 2026-10-27. **Not shipped**: it is slower than `UD-IQ4_XS` at every prompt size (see [Q4_K_XL (staged, not shipped)](#q4_k_xl-staged-not-shipped---10k-cache-sweep--120k-check)), so it is only kept as the switch target if a future quality need justifies the loss.

## Setup

- Engine: moe-cache fork (`/usr/local/bin/engine/moe-cache-llama.cpp/llama-server`), Rig 1 (RTX 3060 12 GB), `--threads 12`, `--parallel 1`, q8_0 KV (`--cache-type-k/-v q8_0`), MTP via `--spec-type draft-mtp --spec-draft-n-max 2` with q8_0 draft KV, mmproj on CPU (`--no-mmproj-offload`, `--image-min-tokens 1024`), `--load-mode none`.
- Server log confirms the embedded MTP head: `MTP recurrent-plane policy: draft depth = 2, total planes = 3, direct rollback horizon = 2, full-shape GPU replay = disabled`.
- Protocol: raw `/v1/completions`, `cache_prompt:false`, `ignore_eos:true`, n_predict 512, second pass recorded, one cold load per config ([methodology.md](../../../methodology.md) §Measurement methods). Prompts: `scripts/opencode-10k-prompt.txt` (10502 tokens), and the long-context generator at 79 / 157 / 330 repeats.

## 10k opencode prompt - expert-cache sweep

`-b/-ub 6144` and `-b/-ub 4096`, cache bisected against a two-pass run because a cache that serves pass 1 can still fail `graph_reserve` on pass 2.

| `-b/-ub` | cache | prefill t/s | decode t/s | VRAM | Result |
| --- | --- | --- | --- | --- | --- |
| 6144 | 64 | 2224 | 60.1 / 60.5 | 10800 MiB | ok |
| 6144 | 72 | 2208 | 55.7 / 60.6 | 11372 MiB | ok |
| 6144 | **76** | 2195 / 2207 | 63.7 / 64.6 | 11626 MiB | ok (shipped) |
| 6144 | 78 | 2203 | 63.6 / 55.7 | 11624 MiB | ok |
| 6144 | 80 | 2031 | 59.0 | 10612 @ load | **OOM on pass 2** |
| 4096 | 87 | 2026 / 2035 | 70.5 / 67.0 | ~11730 MiB | ok |
| 4096 | 88 | 2050 / 2034 | 66.4 / 68.9 | 11798 MiB | ok (ceiling) |
| 4096 | 89 | - | - | - | **fails** |

Bisection path at 4096: 94 fail -> 85 ok -> 89 fail -> 87 ok -> 88 ok, 89 fail. At 6144 a single 80 load serves one pass then dies on the second:

    ggml_backend_cuda_buffer_type_alloc_buffer: allocating 1296.50 MiB on device 0: cudaMalloc failed: out of memory
    ggml_gallocr_resize_shared_entry: failed to allocate shared CUDA0 workspace of size 1296.50 MiB
    graph_reserve: failed to allocate compute buffers
    srv  decode: Compute error. off = 0, n_batch = 6144, ret = -2

Each slab costs ~67 MiB here, and dropping 6144 -> 4096 frees enough pp-buffer space for +12 slabs (76 -> 88) because the buffer scales with ub, not ctx.

End-to-end at this workload size the two shapes are equivalent: 10k prompt + 512 generated tokens is 4.77 s prefill + 7.98 s decode = **12.75 s** at 6144/cache 76, and 5.14 + 7.56 = **12.71 s** at 4096/cache 88. The 4096 shape only wins when generation dominates (+5.4% decode for -7.2% prefill), which is not the opencode shape, so cache 76 + `-b/-ub 6144` ships.

## Long-context rows (shipped config)

Shipped config: cache 76 + `--phase-aware-workspace`, `-b/-ub 6144`. Cold load per prompt.

| prompt | prompt_n | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- |
| ~60K | 59751 | 1768 | 52.5 | 11624 MiB |
| ~120K | 119293 | 1364 | 42.8 | 11624 MiB |
| ~250K | 252039 | 905 / 902 | 27.8 / 26.1 | 11626 MiB |

Near-full-window check: the 330-repeat prompt (887682 chars, 252039 tokens = 96% of the 262144 window) prefills twice with `truncated = 0` and no OOM, so the shipped config holds at the top of the window as well. Not a recorded decode row - it is a stability check.

## Q4_K_XL (staged, not shipped) - 10k cache sweep + 120K check

`UD-Q4_K_XL` (21.19 GiB) run through the **same** setup as the IQ4_XS config above - only the model file differs - to see whether the heavier quant is a candidate for this card. Every row here, including the IQ4_XS re-baselines, comes from one session on 2026-10-27, so the cross-quant deltas below are same-session and valid.

### `-b/-ub 6144` - 10k prompt cache sweep

| cache | prefill t/s | decode t/s (pass 1 / pass 2) | MTP accept (pass 2) | VRAM | Result |
| --- | --- | --- | --- | --- | --- |
| 48 | 2095 | 48.4 / 49.5 | 292/436 (67%) | 10094 MiB | ok |
| 56 | 2081 | 54.6 / 51.8 | 291/440 (66%) | 10668 MiB | ok |
| **60** | **2058 / 2072** | 56.6 / 50.6 · 56.6 / 58.4 | 290/441 · 305/411 | 10916 MiB | **ok - ceiling** (measured twice) |
| 61 | 1962 | 53.7 / - | 283/453 | - | **fails pass 2**, mid-decode at 4358 tokens |
| 62 | - | - | - | - | **OOM on pass 1** |
| 64 | - | - | - | - | **OOM on pass 1** |

The pass-2 failure at 61 is the same trap as the IQ4_XS 6144 sweep (`graph_reserve` compute-buffer allocation inside a prefill chunk), and 62/64 die outright - so 60 is the true ceiling, not a margin.

### `-b/-ub 4096` - 10k prompt cache sweep

| cache | prefill t/s | decode t/s (pass 1 / pass 2) | MTP accept (pass 2) | VRAM | Result |
| --- | --- | --- | --- | --- | --- |
| **66** | **1800** | 56.7 / 55.1 | 295/431 (68%) | 11342 MiB | **ok - ceiling** |
| 67 | 1736 | 52.4 / - | 284/454 | - | **fails pass 2** at 4096 tokens |
| 68 / 70 / 72 | - | - | - | - | **OOM on pass 1** |

### Same-session IQ4_XS re-baseline

| quant/config | prefill t/s | decode t/s (pass 1 / pass 2) | MTP accept (pass 2) | VRAM |
| --- | --- | --- | --- | --- |
| IQ4_XS cache 76, 6144 (shipped) | 2221 | 57.8 / 62.6 | 303/413 (73%) | 10842 MiB |
| IQ4_XS cache 88, 4096 | 2050 | 64.7 / 68.8 | 288/444 (65%) | 11350 MiB |

### 120K long-context check

Both rows are cold loads at ctx 262144, `--phase-aware-workspace`, two passes, `prompt_n` 119293 (the 157-repeat prompt). Peak VRAM is the max per-process `llama-server` allocation sampled once a second across the whole pass, so it includes the prefill peak - the binding constraint here.

| cache | prefill t/s (run 1 / run 2) | decode t/s (pass 1 / pass 2) | MTP accept | peak VRAM | headroom of 12288 |
| --- | --- | --- | --- | --- | --- |
| 60 | 1321 / 1317 | 37.2 / 36.6 · 35.9 / 35.4 | 65-70% | 11700 MiB | 588 MiB |
| **56** | **1322 / 1322** | 35.8 / 36.8 | 72-77% | **11450 MiB** | **838 MiB** |

Cache 60 serves the 120K prompt on two independent cold loads (four passes, no OOM), so the 10k ceiling does hold at long context - it is simply thin, with 588 MiB left while the prompt-side buffers are at full size.

### Best Q4_K_XL config on this rig, and why it does not ship

**Best config: cache 56 + `--phase-aware-workspace`, `-b/-ub 6144`.** Dropping 60 -> 56 costs nothing measurable (prefill 1322 vs 1317-1321 at 120K, decode inside the same 35-37 t/s band, acceptance higher if anything) and buys 250 MiB of long-context headroom. 4096 is not worth it at all: it only buys 6 extra slabs (60 -> 66) and gives up 13% prefill.

    llama-server --port PORT \
      -m <models>/Cyber-Tiel-Coder-35B-A3B-MTP-UD-Q4_K_XL.gguf \
      --mmproj <models>/mmproj-Cyber-Tiel-Coder-35B-A3B-BF16.gguf \
      --image-min-tokens 1024 \
      --ctx-size 262144 -ngl all -fit off \
      --moe-expert-cache-size 56 --phase-aware-workspace \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      -b 6144 -ub 6144 \
      --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --presence-penalty 0.0 --repeat-penalty 1.0

Against the shipped IQ4_XS config (same session, best pass per row):

| prompt | IQ4_XS c76, 6144 | Q4_K_XL c56, 6144 | Δ prefill | Δ decode |
| --- | --- | --- | --- | --- |
| 10k | 2221 / 62.6 | 2081 / 51.8 | -6.3% | -17% (noisy: Q4 passes span 50.6-58.4) |
| 120K | 1364 / 42.8 (earlier session) | 1322 / 36.8 | -3.1% | -14% |

End-to-end at the opencode shape (10502-token prompt + 512 generated): IQ4_XS cache 76 = 4.73 s + 8.18 s = **12.91 s**; Q4_K_XL cache 56 = 5.05 s + 9.88 s = **14.93 s** (~+16%).

The penalty is structural, not a tuning miss: slab cost is close (Q4 ~72 MiB/slab vs IQ4 ~67) but Q4_K_XL gives up 18 cache slots at 6144 (ceiling 60 vs 78-79) and 22 at 4096 (66 vs 88), which is ~800 MiB of fixed extra allocation from the larger non-resident expert weights. So `UD-IQ4_XS` stays the shipped quant on this rig and Q4_K_XL is retained only as the switch target if a quality need appears; switching back means the 60 (10k) / 56 (120K) ceilings above, not cache 76.

## Observations

- Decode tracks MTP draft acceptance, not cache size: acceptance ran 61-73% across these runs (e.g. 280/459 on the 250K pass 2, mean len 2.22), and single passes moved as much as 63.6 -> 55.7 t/s at identical settings. Read decode as one recorded pass, not a median; treat sub-5% deltas with caution. Prefill held within ±1.5% and is the trustworthy half.
- Against [Qwen3.6-35B-A3B](../qwen36-35b-a3b.md) on the same card (cache 80, 83.5 t/s at 10K), Cyber-Tiel is ~23% slower to decode at 10K and ~17% at 60K, while prefill is slightly ahead at every depth (+7% at 10K, +5% at 60K, +4% at 120K). The gap narrows with prompt depth (decode 64.2 -> 52.5 -> 42.8 versus 83.5 -> 63.1 -> 48.1) because acceptance and cache residency matter less once attention dominates.
- Vision is wired like the other `qwen35moe` entries on this rig: its own mmproj, encoder pinned to CPU, 1024-token image floor. The timings above carry the mmproj loaded but were measured on text-only prompts.
- No immediate-EOS event on any pass (all `predicted_n` 512, `cache_n` 0), unlike the rare behaviour recorded for Qwen3.6-35B on this prompt ([issues.md](../../../issues.md) §5).
- Both quants need the ubatch-first, cache-second order from [tuning.md](../../../tuning.md): every Q4_K_XL ceiling cost at least one cold load to find, and the failure signatures split into a first-pass OOM (one slot too high) and a mid-prefill `graph_reserve` death one slot below it - the same pattern the IQ4_XS sweep hit, so treat any cache ceiling here as one-below-the-crash.

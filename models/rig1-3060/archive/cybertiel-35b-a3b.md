# Cyber-Tiel-Coder-35B-A3B (Rig 1) - experiment archive

Fresh experiment log - first measurement of this model on the rig, all on the [moe-cache fork](../../../engine-notes/moe-cache-fork.md) at ctx 262144.

Main card: [cybertiel-35b-a3b.md](../cybertiel-35b-a3b.md). Methodology: [methodology.md](../../../methodology.md); issues: [issues.md](../../../issues.md).

Quants:

- `UD-IQ4_XS` (16.88 GiB, 18119934272 bytes, single file) + `mmproj-Cyber-Tiel-Coder-35B-A3B-BF16.gguf` (902822016 bytes)

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

## Observations

- Decode tracks MTP draft acceptance, not cache size: acceptance ran 61-73% across these runs (e.g. 280/459 on the 250K pass 2, mean len 2.22), and single passes moved as much as 63.6 -> 55.7 t/s at identical settings. Read decode as one recorded pass, not a median; treat sub-5% deltas with caution. Prefill held within ±1.5% and is the trustworthy half.
- Against [Qwen3.6-35B-A3B](../qwen36-35b-a3b.md) on the same card (cache 80, 83.5 t/s at 10K), Cyber-Tiel is ~23% slower to decode at 10K and ~17% at 60K, while prefill is slightly ahead at every depth (+7% at 10K, +5% at 60K, +4% at 120K). The gap narrows with prompt depth (decode 64.2 -> 52.5 -> 42.8 versus 83.5 -> 63.1 -> 48.1) because acceptance and cache residency matter less once attention dominates.
- Vision is wired like the other `qwen35moe` entries on this rig: its own mmproj, encoder pinned to CPU, 1024-token image floor. The timings above carry the mmproj loaded but were measured on text-only prompts.
- No immediate-EOS event on any pass (all `predicted_n` 512, `cache_n` 0), unlike the rare behaviour recorded for Qwen3.6-35B on this prompt ([issues.md](../../../issues.md) §5).

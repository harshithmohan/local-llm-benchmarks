# Cyber-Tiel-Coder-35B-A3B (Rig 2) - experiment archive

First measurement of this model on the rig, all on the [moe-cache fork](../../../engine-notes/moe-cache-fork.md) (build 11997, commit f3f31a788) at ctx 262144.

Main card: [cybertiel-35b-a3b.md](../cybertiel-35b-a3b.md). Methodology: [methodology.md](../../../methodology.md); issues: [issues.md](../../../issues.md).

Quants:

- `UD-Q4_K_XL` (22749880640 bytes, 21.19 GiB, single file) + `mmproj-Cyber-Tiel-Coder-35B-A3B-BF16.gguf` (902822016 bytes)

## Setup

- Engine: moe-cache fork (`~/llama-swap/bin/moe-cache-llama.cpp/llama-server`, build 11997 / f3f31a788), Rig 2 (RTX 3090 24 GB, 22 GB budget), `--threads 8`, `--parallel 1`, q8_0 KV, MTP via `--spec-type draft-mtp --spec-draft-n-max 2` with q8_0 draft KV, mmproj on CPU (`--no-mmproj-offload`, `--image-min-tokens 1024`), `--load-mode none`, `--reasoning-preserve`, `-b/-ub 4096`, `--phase-aware-workspace`.
- Direct launch on host port 8081 (no `gpu-pl-run` wrapper, so the runs measured at the 370 W full limit as the rig policy requires). Load time ~13 s from page cache.
- Server log confirms the embedded MTP head: `MTP recurrent-plane policy: draft depth = 2, total planes = 3, direct rollback horizon = 2, full-shape GPU replay = disabled`.
- Protocol: raw `/v1/completions`, `cache_prompt:false`, `ignore_eos:true`, n_predict 512, second pass recorded, one cold load per config ([methodology.md](../../../methodology.md) §Measurement methods). Prompts: `scripts/opencode-10k-prompt.txt` (10502 tokens), long-context generator at 79 / 157 repeats.
- Reference for every comparison below is the neighbouring 35B on this rig, [Qwen3.6-35B-A3B](../qwen36-35b-a3b.md) `UD-IQ4_XS` (16.96 GiB), cache 0 all-resident + `--phase-aware-workspace`, `-b/-ub 4096`: 10K 5258 / 189, ~60K 4247 / 146.8, ~120K 3292 / 115.2, VRAM 21894 MiB.

## Placement: no cache flag does not load

Without `--moe-expert-cache-size`:

    srv    load_model: failed to create_context with model '.../Cyber-Tiel-Coder-35B-A3B-MTP-UD-Q4_K_XL.gguf'
    srv    operator(): cleaning up before exit...
    srv  llama_server: exiting due to model loading error

21.19 GiB of weights + q8_0 KV for 262144 + the compute buffers do not fit the 22 GB budget, so some expert weights have to be host-resident. Every row below therefore runs the expert cache, which is a different placement from the reference 35B - that config is the smallest 35B quant on the rig (16.96 GiB) and still runs every expert on the GPU.

## Expert-cache ladder (10K opencode prompt)

| cache | prefill t/s | decode t/s | VRAM | Result |
| --- | --- | --- | --- | --- |
| no flag | - | - | - | **load fails** (`failed to create_context`) |
| 144 | 3195.8 | 133.4 | 17798 MiB | ok |
| 156 | 3276.1 | 133.7 | 18620 MiB | ok |
| 162 | 3326.8 | 135.8 | 19114 MiB | ok |
| 165 | 3371.0 | 143.5 | 19360 MiB | ok |
| 168 | 3387.5 | 133.2 | 19604 MiB | ok |
| **192** | 3763.0 / 3766.3 | 147.1 / 148.9 | 21260 MiB | ok (shipped) |
| 200 | 3920.2 | 144.8 / 141.7 | 21994 MiB | ok (max fit inside the 22 GB budget) |
| 208 | 4083.2 | 162.4 | 22570 MiB | ok, but **over the 22 GB budget** |

Notes on the ladder:

- Prefill rises monotonically with cache size (3196 -> 4083 t/s from 144 to 208): CPU-resident experts cost prompt processing, not just decode, so the ladder is a prefill ladder as much as a decode one. The 152-168 stretch is flat within noise; the jump is between 168 and 192.
- Decode does not separate 192 from 200 or 208 beyond the rig's documented drift (see the main card): 147-149 at 192, 142-145 at 200, 162 at 208 on a single pass. The 208 pass-2 number is an outlier, not a trend - its pass 1 was 144.4.
- 208 at 22570 MiB sits outside the rig's 22 GB ± 250 MB budget even though it serves two passes cleanly, so it is boundary data only.
- Cache values were validated with at least two passes ([issues.md](../../../issues.md) §8: a cache can serve pass 1 and fail `graph_reserve` on pass 2); nothing on the ladder OOMed at request time, only the flag-less load failed.

## Long-context rows

| cache | prompt | prompt_n | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- | --- | --- |
| 168 | ~60K | 59751 | 3312 | 117.0 | 19602 MiB |
| 168 | ~120K | 119293 | 2782 | 80.1 | 19602 MiB |
| **192** | ~60K | 59751 | 3600 | 121.6 | 21254 MiB |
| **192** | ~120K | 119293 | 2964 | 96.3 | 21254 MiB |

The cache matters more as the prompt grows: 168 -> 192 buys +9% prefill and +4% decode at ~60K, and +7% prefill with +20% decode at ~120K, because the 120K pass touches far more experts per token.

## Against the reference 35B on this rig

| prompt | Cyber-Tiel Q4_K_XL | Qwen3.6-35B UD-IQ4_XS | delta |
| --- | --- | --- | --- |
| 10K prefill | 3766 | 5258 | -28% |
| 10K decode | 148.9 | 189 | -21% |
| ~60K prefill | 3600 | 4247 | -15% |
| ~60K decode | 121.6 | 146.8 | -17% |
| ~120K prefill | 2964 | 3292 | -10% |
| ~120K decode | 96.3 | 115.2 | -16% |

Reading: the same 35B-A3B architecture and the same card, so this is mostly a quant-and-placement delta rather than a slate verdict - Q4_K_XL is 4.23 GiB heavier than the reference quant, and it is the only one of the two that cannot keep every expert on the GPU. MTP acceptance was comparable to the reference's runs (61-68% on these passes, mean len 2.1-2.6), so speculative decode is not where the gap comes from.

## Observations

- Load from warm page cache is ~13 s; the file is 21.19 GiB and the host has 32 GB RAM, so concurrent app traffic plus this model leaves little room for the page cache - expect slower cold loads after the model has been evicted.
- MTP acceptance on the 10K prompt: 271-311 accepted of 437-482 drafted (61-68%), mean len 2.12-2.55 - in the same band the reference 35B records on this rig.
- No immediate-EOS event on any pass (`predicted_n` 512, `cache_n` 0 everywhere) and `truncated = 0` at 119293 tokens.
- Near-full-window (~250K) stability was not run on this rig; the largest recorded prompt here is 119293 tokens.

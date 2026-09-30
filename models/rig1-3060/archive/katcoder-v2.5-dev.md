# KAT-Coder-V2.5-Dev (Rig 1) - experiment archive

Fresh experiment log. KAT-Coder-V2.5-Dev was re-benchmarked from scratch on the
[moe-cache fork](../../../engine-notes/moe-cache-fork.md) at c 262144; earlier
measurements were retired with that engine and are not carried over.

Main card: [katcoder-v2.5-dev.md](../katcoder-v2.5-dev.md).
Methodology: [methodology.md](../../../methodology.md); issues: [issues.md](../../../issues.md).

Quants:

- `APEX-I-Compact` (16.24 GiB, single file, Q4_K_M / file_type 15)

## Setup

- Engine: moe-cache fork (GenerelSchwerz/llama.cpp, branch `moe-cache`). Expert cache is
  opt-in and CUDA-only; while enabled it overrides `--n-cpu-moe` placement.
- Quant: `APEX-I-Compact`, single file, embedded MTP head (no separate draft file).
- Context 262144 (native); q8_0 KV; `-t 12`; `--load-mode none`.
- Protocol: raw `/v1/completions`, `n_predict 512`, `cache_prompt false`, `ignore_eos true`,
  measured on the second pass; VRAM is the per-process `llama-server` allocation.
- Prompt: the ~10k opencode session-context prompt unless stated.

## `-b/-ub` sweep (prefill)

Cache 80, ctx 262144, MTP on, 10k prompt, second-pass:

| `-b/-ub` | prefill t/s | decode t/s | VRAM |
| --- | --- | --- | --- |
| 512 | 676 | 62.3 | 11034 MiB |
| 1024 | 991 | 66.6 | 11162 MiB |
| 1536 | 1257 | 61.7 | 11284 MiB |
| 2048 | 1339 | 70.0 | 11410 MiB |
| 3072 | 1582 | 62.3 | 11656 MiB |
| 4096 | OOM | - | - |

Prefill scales with `-ub` (the compute buffer is ubatch-bound on this arch); decode is
ubatch-independent (~62-70, MTP-acceptance noise). 4096 OOMs, so 3072 is the largest fitting
ubatch at cache 80. A headline re-run at 3072 measured prefill 1588 / 1586 and decode
67.0 / 65.7.

## Long-context refactor benchmark (~60K prompt)

The ~60K refactor prompt (n=59751) at the recommended config (cache 80, `-b/-ub 3072`, MTP
on, cold load): prefill 1374 t/s, decode 51.2 t/s, VRAM 11636 MiB. Survives with ~650 MiB
headroom - no OOM on the large prompt.

## Conclusions

- `-b/-ub 3072` is the prefill-maximizing setting at cache 80: prefill 1587 vs 1339 at 2048
  and 676 at 512; 4096 OOMs.
- Decode is ubatch-independent (~66 t/s on the 10k prompt), driven by MTP acceptance.
- The expert cache holds the full 262144 window with MTP inside 12 GB (~11.6 GiB, ~650 MiB
  free).

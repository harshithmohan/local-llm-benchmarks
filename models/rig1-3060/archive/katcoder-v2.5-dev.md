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
ubatch-independent (~62-70, MTP-acceptance noise). 4096 OOMs with the draft ubatch at the
target `-ub`, so 3072 is the largest fitting ubatch without the draft cap (see below). A
headline re-run at 3072 measured prefill 1588 / 1586 and decode 67.0 / 65.7.

## `--spec-draft-ubatch-size` - unlocking `-ub 4096` (2026-10-03)

The `-b/-ub 4096` row above OOMs because the MTP draft context inherits the target `-ub`.
Capping the *draft* ubatch below the target makes 4096 fit, on the fork
(`--spec-draft-ubatch-size`, [engine-notes](../../../engine-notes/moe-cache-fork.md)):

| config | VRAM | 10k prefill | 10k decode | 60K prefill | 60K decode |
| --- | --- | --- | --- | --- | --- |
| `-ub 3072`, MTP on (previous) | 11656 MiB | 1579 | 73.1 | 1372 | 53.4 |
| `-ub 4096 --spec-draft-ubatch-size 3072`, MTP on | 11774 MiB | 1663 / 1683 | 68.5 / 64.3 | 1430 / 1438 | 50.6 / 52.6 |
| `-ub 4096`, MTP off | 9964 MiB | 1761 | 55.3 | 1521 | 40.9 |

The 10k row is two cold-loaded runs; decode is the noisy column (MTP acceptance varies
run-to-run).

- The draft cap lifts the target-ub ceiling: 4096 now loads, serves the 60K prompt, and
  holds the full 262144 cache inside 12 GB (11774 MiB, ~510 MiB free).
- Prefill +5.5% (1663-1683 vs 1579); decode is statistically indistinguishable (64-68 vs
  73 in one run, but the previous 3072 config itself ranges 62-73 across runs).
- MTP beats MTP-off at the same `-ub 4096` (~64-68 vs 55.3 decode) for ~1.8 GiB more VRAM.
- Validated with one `--experimental-logs` pass: `moe-grouped-decode` calls 8977 after the
  first recorded pass (9915 cumulative after the 60K pass), with `fallback`, `rollback`,
  `prepare_error`, `finish_error`, and `upload_errors` all 0.

## Long-context refactor benchmark (~60K prompt)

The ~60K refactor prompt (n=59751) at the recommended config (cache 80, `-b/-ub 4096`,
`--spec-draft-ubatch-size 3072`, MTP on, cold load): prefill 1434 t/s, decode 51.6 t/s, VRAM
11774 MiB. Survives with ~510 MiB headroom - no OOM on the large prompt.

## Conclusions

- `-b/-ub 4096` with `--spec-draft-ubatch-size 3072` is the prefill-maximizing setting at
  cache 80: prefill ~1673 vs 1579 at 3072 (MTP on) and 1761 at 4096 (MTP off). Plain
  `-ub 4096` OOMs with the draft ubatch at the target `-ub`; the draft cap is what makes it fit.
- Decode is ubatch-independent (~64-73 on the 10k prompt), driven by MTP acceptance.
- The expert cache holds the full 262144 window with MTP inside 12 GB (~11.5 GiB, ~510 MiB
  free at `-ub 4096`).

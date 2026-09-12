# Qwen3.8-27B (Rig 2) - experiment archive

Measurements behind [qwen38-27b.md](qwen38-27b.md) (main file: UD-Q4_K_S at c 155648).
Protocol identical: coding prompts C#+React averaged, second-pass prefill, recommended
sampling, cold load, q8_0 KV, `--threads 8 --threads-batch 16`, 22 GB VRAM cap
(22 GB +- 250 MB, desktop reserve). Methodology in [methodology](../../methodology.md);
gotchas in [issues](../../issues.md).
Model card: [unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF).

Quants:

- `UD-Q4_K_S` (15.36 GB, ~4.55 bpw) - the only quant tested

Routing profiles: none - dense model, no MoE layers, so the fork's
`--moe-cache-profile`/`--moe-cache-slots` have nothing to work on.

## Max context probe (stock)

VRAM at load, default params (q8_0 KV, MTP n-max 2, `--threads-batch 16`):

| ctx | VRAM used | verdict |
| --- | --- | --- |
| 122880 | 20651 MiB | fits |
| 131072 | 21019 MiB | fits |
| 147456 | 21757 MiB | fits |
| 152576 | 21987 MiB | fits |
| **155648** | **22127 MiB** | adopted - largest with a real reserve (~400 MiB under 22528) |
| 159744 | 22311 MiB | too thin (~215 MiB reserve) |
| 163840 | 22495 MiB | over - no reserve (33 MiB under the line) |
| 180224 | 23233 MiB | over |
| 196608 | 23971 MiB | over |
| 212992+ | load fails | MTP context allocation fails |

- q8_0 KV costs ~0.045 MiB/token on the ~16 full-attention layers, so the ceiling is
  ~155k, not the native 262144.
- `-ngld 0` (draft head on CPU) is a no-op for this model: byte-identical VRAM at every
  ctx tested. There is no separate `-md` draft - the MTP head is embedded - so the
  draft-offload knob has nothing to move.

## Speed at c 155648 (stock)

| pass | prompt | prefill t/s | decode t/s | acceptance | mean len |
| --- | --- | --- | --- | --- | --- |
| second | C# | 1064.8 | 59.7 | 0.664 | 2.33 |
| second | React | 974.6 | 63.6 | 0.742 | 2.48 |
| avg | C#+React | **1019.7** | **61.6** | 0.703 | 2.41 |

Cold load, single slot (`--parallel 1`), 512 gen, timings from the `llama-server`
request log. VRAM 22127 MiB at load. A second n-max 2 session (below) read 63.1 t/s -
run-to-run decode varies by a few t/s with sampled acceptance, so compare within a
table only.

## `--threads-batch` sensitivity (stock, c 155648)

Short C#+React passes were noise-bound (per-tb spread smaller than the run-to-run
spread), so the check was repeated on a 7369-token prompt (React text x24), second pass:

| `--threads-batch` | long-prompt prefill t/s |
| --- | --- |
| 8 | 1247.7 |
| 16 | 1244.7 |
| 32 | 1241.2 |

Flat within 0.5%. With `-ngl 999` the model is fully offloaded; prefill is GPU-bound and
the CPU batch threads only feed it. Generation uses `--threads`, not `--threads-batch`.
No reason to change from the default 16. (Note `llama-bench` in this build has no
threads-batch option, hence the server-side long-prompt method.)

## MTP `--spec-draft-n-max` sweep (stock, c 155648)

Same-session second-pass C#+React averages (this build's default is n-max 3):

| n-max | C# decode | React decode | avg decode | acceptance | mean len | VRAM |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 57.5 | 55.5 | 56.5 | 0.819 | 1.82 | 21977 MiB |
| 2 | 63.9 | 62.2 | **63.1** | 0.752 | 2.50 | 22127 MiB |
| 3 | 55.8 | 67.3 | 61.5 | 0.630 | 2.95 | 22277 MiB |
| 4 | 61.2 | 58.0 | 59.6 | 0.547 | 3.19 | 22427 MiB |

- n-max 1's second pass hit an early EOS, so its row is first-pass C#+React (the most
  accepted but only 1.82 tokens/step).
- Same inverted-U as the 35B: decode peaks at n-max 2. Acceptance falls as n-max rises
  while the accepted run lengthens; n-max 3's wide C#/React spread (55.8 vs 67.3) is
  sampled-acceptance noise.
- VRAM rises ~150 MiB per extra draft token; n-max 4 at 155648 is within ~100 MiB of the
  cap, another reason to keep n-max 2.

## `-b`/`-ub` (compute buffer vs prefill) (stock, c 122880)

Larger ubatch trades VRAM for prefill. 7369-token prompt, second pass (the desktop
session used ~400 MiB in this series):

| `-b`/`-ub` | prefill t/s | VRAM used |
| --- | --- | --- |
| 2048 / 512 | 1299.3 | 21030 MiB |
| 4096 / 1024 | 1319.0 | 21430 MiB |
| 8192 / 2048 | 1339.2 | 22232 MiB |

- ub 512 -> 2048 buys only +3.1% prefill for +1.2 GiB of compute buffer; decode is
  per-token and does not move.
- At the 155648 ceiling it is unaffordable: the base config already sits at ~22440 MiB
  in a 400 MiB desktop (22127 MiB at the 86 MiB baseline), so even ub 1024 (+400 MiB)
  would cross 22528. The winner keeps the default 512.

## `--threads` sweep (stock, c 155648)

C# prompt, second pass (only the CPU-side slice uses threads, so a small effect was
expected):

| `--threads` | prefill t/s | decode t/s | acceptance |
| --- | --- | --- | --- |
| 6 | 1095.4 | 59.3 | 0.592 |
| 8 (winner) | 1064.8 | 59.7 | 0.664 |
| 12 | 1094.2 | 61.6 | 0.636 |

Flat within run-to-run noise (the 8 row is the headline session). The model is GPU-bound
with `-ngl 999`; `--threads` only feeds it. Keep 8. One session hit the 1-token warm-up
transient on the second pass and had to be repeated.

## Messy-code refactor (stock, c 155648)

Winner config (MTP n-max 2), single `/v1/chat/completions` pass, no warm-up, ~116K-token
prompt, 512 gen:

| prompt tokens | prefill t/s | decode t/s | acceptance | mean len | finish | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| 116277 | 809.8 | 28.9 | 0.411 | 1.82 | length | 22440 MiB |

- Prefill and decode both fall off vs the short-prompt headline: prefill 1019.7 -> 809.8
  (-21%), decode 61.6 -> 28.9 (-53%). MTP acceptance drops 0.703 -> 0.411 (230/560), so
  the draft head does less useful work at long context as well as the attention/SSM cost
  rising.
- The decode regression is steeper than the 35B-A3B's on the same task (-37%): the MoE
  only activates ~3B params per token, this dense model runs ~27B.
- No crash or early EOS; the run hit the 512-token cap.
- Measured in a desktop session (Hyprland) using ~400 MiB, so VRAM read 22440 MiB total
  (~88 MiB under the 22528 line) vs 22127 MiB in the headline's 86 MiB-desktop session.
  The config is identical; only the desktop baseline moved.

## KV cache type: q8_0 vs f16 (stock)

Second-pass C#+React at c 77824 (f16's practical ceiling):

| KV type | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- |
| q8_0 | 1050.1 | 64.1 | 19000 MiB |
| f16 | 1051 | 65.5 | 21018 MiB |

- Throughput is identical - the KV read is not the bottleneck at these speeds. The only
  real difference is memory: f16 costs ~2 GiB more at the same context.
- That drops the context ceiling from 155648 (q8_0) to ~98304 (f16 loads at 22460 MiB
  with almost no reserve; fails at 122880). With no quality harness to justify trading
  ~37% of the context for f16 precision, q8_0 stays.

## `--load-mode none` (stock, c 155648)

Adding `--load-mode none` to the winner: VRAM 22508 MiB and C# decode 60.6 t/s
(acceptance 0.623), indistinguishable from the headline 59.7 t/s. The flag only changes
the load path; steady-state VRAM and throughput are unchanged. Not needed here.

## Warm-up note

Across sessions, the first raw `/completion` call (and occasionally a second) after load
returned a single token (`stop processing: n_tokens = prompt`, eval time 0.00 ms) before
steady-state runs produced the full 512. Treated as a load/first-use transient and
discarded, per the cold-load-then-second-pass convention.

## Conclusions

- UD-Q4_K_S at c 155648 with MTP n-max 2 is the recommended config: 61.6 t/s decode
  (prefill 1019.7, acceptance 0.703), 22127 MiB.
- Stock only. Dense model - the Codacus fork's MoE-specific features do not apply.
- 155648 is the context ceiling (native 262144 does not fit); `-ngld 0` does not buy
  more.
- `--threads-batch` is irrelevant here (GPU-bound); MTP n-max 2 is the decode peak.
- `--threads` 6/8/12 is likewise flat, and `-b`/`-ub` above the default 512 does not fit
  under the cap at 155648. The defaults are already the practical optimum.
- f16 KV runs at the same speed as q8_0 but cuts the context ceiling to ~98304, so q8_0
  stays. `--load-mode none` changes nothing steady-state.

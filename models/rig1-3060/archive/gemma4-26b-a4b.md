# Gemma4-26B-A4B (Rig 1) - experiment archive

This archive holds the supporting measurements and experiments behind the main card
([gemma4-26b-a4b.md](../gemma4-26b-a4b.md)): the expert-cache/ubatch sweep, the cache
frontier, companion-flag probes, and the pre-change stock baseline. The recommended
config lives on the main card only. Methodology in [methodology](../../../methodology.md);
gotchas in [issues](../../../issues.md).
Model card: [HauhauCS/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-MTP](https://huggingface.co/HauhauCS/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-MTP).

Quants:

- `Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-Q4_K_M.gguf` (15.6 GiB) - the only
  quant this release ships; the model is quantization-aware-trained for ~4-bit, so
  Q4_K_M is the intended precision.
- MTP draft head `mtp-gemma-4-26B-A4B-it.gguf` (240 MiB, `gemma4-assistant` arch) - a
  separate 4-layer head that shares the target's KV cache (no separate draft prefill).

Arch facts (`gemma4`, from the GGUF metadata): native ctx 262144; 30 layers in a 25:5
sliding-window:global hybrid - 25 SWA layers (window 1024, 8 KV heads, head dim 256) and
5 global layers at indices 5/11/17/23/29 (2 KV heads, head dim 512, freq base 1e6);
128 routed experts / 8 active per token, expert FFN 704, embedding 2816. q8_0 KV at
262144 is ~2.7 GiB.

## Expert-cache + ubatch sweep (moe-cache fork, ctx 262144, MTP on, 10k prompt)

All rows: q8_0 KV, `--cache-type-k/-v-draft q8_0`, cold load, second pass. VRAM is the
post-run reading against the 12288 MiB cap. "comp" = `--moe-early-router
--phase-aware-workspace --live-context-workspace`; "ovl" = `--backend-sampling
--decode-overlap --decode-boundary-overlap`.

| Config | prefill t/s | decode t/s | VRAM MiB | fits |
| --- | --- | --- | --- | --- |
| cache 32 | 600.6 | 46.6 | 10954 | yes |
| cache 32, `-b/-ub 1024` | 937.7 | 57.0 | 11169 | yes |
| cache 32, comp | 600.0 | 55.0 | 8727 | yes |
| cache 32, ovl | 596.5 | 38.4 | 10993 | reject - decode-overlap hurts |
| cache 40 | 600.9 | 64.7 | 11857 | reject - ~430 MiB headroom |
| cache 32, comp, `-b/-ub 1024` | 934.6 | 48.2 | 8779 | yes |
| cache 36, comp, `-b/-ub 1024` | 931.8 | 54.4 | 9227 | yes |
| cache 44, comp, `-b/-ub 1024` | ~933 | 56-58 | 10091 | yes |
| cache 48, comp, `-b/-ub 1024` | 932.9 | 50.7 | 10599 | yes |
| cache 52, comp, `-b/-ub 1024` | 933.4 | 59.5 | 11015 | yes |
| cache 40, comp, `-b/-ub 2048` | ~1286 | 48-57 | 9749 | yes |
| cache 44, comp, `-b/-ub 2048` | ~1280 | 52-56 | 10197 | yes |
| cache 48, comp, `-b/-ub 2048` | 1288.9 | 53.1 | 10705 | yes |
| cache 40, comp, `-b/-ub 4096` | 1612-1626 | 37-53 | 9961 | yes |
| cache 44, comp, `-b/-ub 4096` | 1619-1623 | 45.7-52.8 | 10409 | **picked** |
| cache 45, comp, `-b/-ub 4096` | 1619.5 (pass 1) | - | - | crash on pass 2 |
| cache 46, comp, `-b/-ub 4096` | - | - | 11409 | no |
| cache 48, comp, `-b/-ub 4096` | - | - | 11497 | no |
| cache 44, comp, `-b/-ub 5120/6144/8192` | - | - | - | no (500, compute buffer) |
| cache 48 (no comp) | - | - | 11786 | no |

Findings:

- Decode is noisy (±10-15% run-to-run on the same config); prefill is stable. Prefill
  scales near-linearly with ubatch (1024 ~933, 2048 ~1286, 4096 ~1620) for ~200 MiB per
  doubling; decode is ubatch-independent within the acceptance noise.
- The comp trio both raises decode and frees ~1.4-2 GiB, enabling a larger ubatch/cache;
  `ovl` (decode-overlap) is a net loss at this config.
- The moe-cache fork's `--moe-expert-cache-size` overrides `--n-cpu-moe` placement while
  enabled, so no `--n-cpu-moe` is set.
- Larger cache raises decode (cache 40 no-comp = 64.7 vs 46.6 at 32) but VRAM is the
  binding constraint; at `-b/-ub 4096` the stable ceiling is cache 44 (45 crashes, 46+
  fails to fit).

## Companion-flag isolation (cache 44, `-b/-ub 4096`)

Each flag alone was tried at the picked cache/ubatch: no-comp 11831 (no fit),
`--moe-early-router` only 11831 (no fit), `--phase-aware-workspace` only 11765 (no fit),
`--live-context-workspace` only 11355 (no fit); the full trio 10409 (fit). The saving is
synergistic - no single flag suffices at cache 44.

## Dynamic-cache validation (`--experimental-logs`)

One instrumented pass on the picked config (cache 44, `-b/-ub 4096`, comp), 10k prompt:
`moe-grouped-decode calls=6480-7410 fallback=0 rollback=0 prepare_error=0 finish_error=0
required_unsupported=0 strategy_switches=0`, `moe-cache-phase upload_errors=0`, and
`decode_grouped=7410 cache_hits=101026 cache_misses=19703` = **83.7% hit rate** - the
grouped cache path is genuinely engaged, not merely a VRAM-placement effect.

## Long-context refactor benchmark (~60K prompt)

Same config as the main card, unified protocol (raw `/v1/completions`, two-pass,
`ignore_eos: true`, prompt_n 66786): prefill 1278 t/s, decode 35.5 t/s, VRAM 10857 MiB.
Passed with headroom, no OOM.

## Pre-change stock baseline (ctx 65536, 10k prompt)

Before the migration the entry ran upstream `llama-server` at ctx 65536 with
`--n-cpu-moe 20`, q8_0 KV, MTP on: 10k prompt = 777 prefill / 34.4 decode t/s (MTP
acceptance 283/454 ~ 62%); a ~67K-token prompt was rejected (HTTP 400, exceeds ctx 65536).
The moe-cache fork at ctx 262144 is ~2x prefill and ~+50% decode versus this baseline
while serving the full native window.

## Conclusions

- Recommended: moe-cache fork, ctx 262144 (native), cache 44, `-b/-ub 4096`, comp trio,
  MTP on, q8_0 KV - 1623 prefill / 52 decode t/s (10k), 10409 MiB.
- Cache 44 is the ceiling at `-b/-ub 4096`; dropping to `-b/-ub 1024` allows cache 52 and
  a higher decode but roughly halves prefill, so ubatch 4096 is the better balance.
- No `--rope-scaling` is needed (262144 is the model's native window).

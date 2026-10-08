# Qwen3.6-35B-A3B (Rig 2) - experiment archive

This archive holds the measurements behind the main card
([qwen36-35b-a3b.md](../qwen36-35b-a3b.md)): the stock base reference, the fork
`-b/-ub` sweep at 262144, and the fork expert-cache sweep at 524288 (YaRN 2x). All numbers
are on the current ~10k opencode session-context timing prompt ([test-prompts.md](../../../test-prompts.md)), measured under the protocol
in [methodology.md](../../../methodology.md) §Measurement methods (raw `/v1/completions`,
two-pass, second pass recorded, `cache_prompt: false`, `ignore_eos: true`, q8_0 KV, cold
load, `--threads 8`, 22 GB VRAM cap). Gotchas in [issues.md](../../../issues.md).

Engines: **stock** = upstream llama-server v0.5.0-dev build 11146 (7fe450e193);
**moe-cache fork** = GenerelSchwerz `moe-cache`, build b11608-2b8088c2a for the original
sweeps and b11814-28d73c87c for the 2026-10-08 re-tune below. The 262144 rows
are cold-loaded with all experts on GPU; the 524288 rows run YaRN 2x and need the fork's
expert cache (all-on-GPU does not fit).

Quants:

- `UD-IQ4_XS` - the tested quant (separate gate/up/down expert tensors). The 262144 rows
  keep all experts on GPU (nothing to cache); the 524288 rows use the expert cache.

Other quants on the model cards (`IQ4_XS-4.19bpw`, `UD-Q4_K_M`) were not re-tested this
round.

## Stock (upstream) - 262144 base reference

MTP-off rows run `-b`/`-ub` at the listed value; MTP-on rows likewise (the fork/stock MTP
macro is `--spec-type draft-mtp --spec-draft-n-max 2` with q8_0 draft KV).

| MTP | `-b`/`-ub` | prefill t/s | decode t/s | VRAM used | acceptance | fits |
| --- | --- | --- | --- | --- | --- | --- |
| off | 2048 | 4787.0 | 120.3 | 21274 MiB | n/a | yes |
| off | 4096 | 5021.1 | 120.3 | 22512 MiB | n/a | yes (cap edge) |
| off | 6144 | 4847.3 | 117.7 | 23814 MiB | n/a | over cap |
| off | 8192 | - | - | - | n/a | alloc fail |
| on | 512 | 2869.2 | 193.2 | 21982 MiB | 0.881 | yes |
| on | 2048 | 4193.8 | 194.9 | 23824 MiB | 0.899 | over cap |

- The stock ceiling is tight: MTP off maxes at `-b/-ub 4096` (22512 MiB, ~16 MiB under the
  22 GB line) and MTP on maxes at `-b/-ub 512`. Anything larger is over the cap or fails to
  allocate.
- MTP-on decode is flat (193-195) across the fitting range; the `-b/-ub` only moves prefill.

## moe-cache fork - 262144 `-b/-ub` sweep

| MTP | `-b`/`-ub` | prefill t/s | decode t/s | VRAM used | acceptance | fits |
| --- | --- | --- | --- | --- | --- | --- |
| off | 2048 | 4529.9 | 132.5 | 20264 MiB | n/a | yes |
| off | 4096 | 4883.9 | 132.4 | 20478 MiB | n/a | yes |
| off | 6144 | 5025.5 | 132.1 | 20756 MiB | n/a | yes |
| off | 8192 | 4933.5 | 132.1 | 21162 MiB | n/a | yes |
| on | 512 | 2977.6 | 217.0 | 21470 MiB | 0.869 | yes |
| on | 2048 | 4334.5 | 214.9 | 21776 MiB | 0.899 | yes |
| on | 4096 | 4686.2 | 214.1 | 22182 MiB | 0.896 | yes |
| on | 6144 | 4769.4 | 216.9 | 22734 MiB | 0.922 | over cap |
| on | 8192 / ub 2048 | 4487.0 | 219.7 | 21776 MiB | 0.893 | yes |

- `-ub` is the prefill lever: MTP-on prefill steps 2978 (ub 512) -> 4335 (ub 2048) ->
  4686 (ub 4096), then flattens (ub 6144 = 4769, but over cap). Decode is ubatch-independent
  (214-220 t/s across every fitting ub). MTP-off prefill peaks at ub 6144 (5026) and eases
  off at ub 8192 (4934).
- `-b` above `-ub` is inert: `-b 8192 -ub 2048` matches `-b 2048 -ub 2048` (4487 vs 4335
  prefill, 219.7 vs 214.9 decode, both within single-run noise; identical 21776 MiB).
- The fork uses ~1-3 GB less VRAM than stock at the same flags (e.g. ub 2048 MTP off: 20264
  vs 21274) and decodes ~10% faster (MTP on: ~215 vs ~194; MTP off: ~132 vs ~120), which is
  what lets it reach a larger ubatch inside the cap. The expert cache is not involved (no
  CPU expert layers).

## moe-cache fork - 524288 (YaRN 2x) expert-cache sweep

`--rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144`. With all experts on GPU the
window no longer loads, so expert placement moves to the fork's cache
(`--moe-expert-cache-size N`; it overrides `-ncmoe`, so no `-ncmoe` is used). Each slot
costs ~57 MiB.

| MTP | cache | `-b`/`-ub` | prefill t/s | decode t/s | VRAM used | acceptance | fits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| off | 128 | 8192 | 3808.9 | 105.4 | 17106 MiB | n/a | yes |
| off | 200 | 8192 | 4503.8 | 121.2 | 21186 MiB | n/a | yes |
| on | 64 | 4096 | 3178.0 | 109.4 | 15242 MiB | 0.859 | yes |
| on | 96 | 2048 | 2404.3 | 122.0 | 16754 MiB | 0.864 | yes |
| on | 96 | 4096 | 3307.3 | 125.9 | 17160 MiB | 0.588 | yes |
| on | 112 | 4096 | 3319.8 | 141.4 | 18158 MiB | 0.769 | yes |
| on | 128 | 4096 | 3176.7 | 135.3 | 19000 MiB | 0.566 | yes |
| on | 128 | 8192 | 3691.0 | 141.4 | 19812 MiB | 0.722 | yes |
| on | 160 | 8192 | 3892.5 | 149.3 | 21730 MiB | 0.664 | yes |
| on | 168 | 8192 | 3925.3 | 154.0 | 22230 MiB | 0.713 | yes |
| on | 176 | 8192 | 4006.0 | 152.0 | 22574 MiB | 0.718 | borderline (46 MiB over the 22 GB line) |
| on | 180 | 4096 | 3691.8 | 153.9 | 22008 MiB | 0.593 | yes |
| on | 184 | 8192 | 4077.1 | 173.1 | 23072 MiB | 0.824 | over cap |
| on | 192 | 8192 | 4169.1 | 172.0 | 23570 MiB | 0.799 | over cap |

- The all-on-GPU config fails to load here (`unspecific error: upstream command exited
  prematurely`): the 524288 q8_0 KV plus the full expert set does not fit the card.
  Enabling the expert cache is what makes the window load at all.
- Cache size is the decode lever: 64 -> 168 slots lifts MTP-on decode 109 -> 154. MTP on
  beats off at any cache (cache 200 MTP off = 121 vs cache 168 MTP on = 154).
- `-ub 8192` is the largest that loads; `-ub 16384` (cache 160) OOMs (`failed to fit params
  ... n_gpu_layers already set by user to 999`). `-ub 8192` also adds ~200 t/s prefill over 4096.
- Acceptance is noisy (0.57-0.86): sampling is stochastic (temp 0.6) and the MTP head tracks
  the sampled text, not the config, so decode tracks cache size more than acceptance. Cache
  168 ub 8192 repeated at 3992 / 156.7 / 22230 MiB (acceptance 0.799).
- `--experimental-logs` on cache 168 ub 8192: `moe-grouped-decode calls=9538`,
  `fallback=0 rollback=0 prepare_error=0 finish_error=0 upload_errors=0`, `populated_slots`
  5031 of `slot_capacity` 6888 (= 41 layers x 168).
- Over the cap / failed: cache 184 (23072 MiB) and 192 (23570 MiB); cache 160 with `-ub 16384` OOMs.

## Rejected configs (over the 22 GB cap or failed to load)

| engine | MTP | `-b`/`-ub` | VRAM used | verdict |
| --- | --- | --- | --- | --- |
| stock | off | 6144 | 23814 MiB | over cap |
| stock | off | 8192 | - | alloc fail |
| stock | on | 2048 | 23824 MiB | over cap |
| moe-cache fork | on | 6144 | 22734 MiB | over cap |

## Long-context refactor (~60K prompt)

Same configs, the ~60K-token refactor prompt (prompt_n 59751), q8_0 KV, cold load,
`ignore_eos: true`:

| engine | MTP | `-b`/`-ub` | prefill t/s | decode t/s | VRAM used | acceptance |
| --- | --- | --- | --- | --- | --- | --- |
| stock | off | 2048 | 3808.2 | 87.8 | 21274 MiB | n/a |
| moe-cache fork | off | 6144 | 4229.3 | 97.2 | 20756 MiB | n/a |
| moe-cache fork | on | 4096 | 3890.7 | 154.0 | 22182 MiB | 0.797 |
| moe-cache fork | on | cache 168 / ub 8192 | 3587.1 | 131.2 | 22230 MiB | 0.835 |

- The fork MTP-off row keeps the best prefill (4229 vs 3891) but gives up ~37% decode
  (97.2 vs 154.0); MTP acceptance eases from ~0.90 on the 10k prompt to 0.797 here.
- The stock row trails the fork on both columns at the same ubatch (3808/87.8).

## b11814 re-tune (2026-10-08) - `--phase-aware-workspace` and the expert cache

This card fits the model at 256k, so the expert cache can only cost decode; the question was
whether `--phase-aware-workspace` (releases prompt-only workspace before decode) is free here.
10k prompt, 4-6 passes, one cold load per config, GPU verified idle before every load:

| 256k config (MTP on) | prefill t/s | decode t/s | peak VRAM |
| --- | --- | --- | --- |
| cache 0 (shipped) | 4971 | **220.9** | 22933 MiB |
| cache 0 + `--phase-aware-workspace` | 4983 | **222.8** | 22946 MiB |
| cache 128 + `--phase-aware-workspace` | 3058 | 164.2 | 14456 MiB |
| cache 168 + `--phase-aware-workspace` | 3380 | 188.5 | 16870 MiB |

- The cache is a straight loss on this card: 128/168 slabs cost ~25%/15% decode against
  cache 0 while freeing up to 8.5 GB. `--phase-aware-workspace` costs nothing (within
  acceptance noise) and frees ~1.3 GiB (22267 -> 20941 MiB at load).
- Batch ceiling: `-b/-ub 6144` and 8192 with `--phase-aware-workspace` both load
  (4900 / 4812 prefill, peak 22588 / 23244 MiB - past the 22 GB budget), while 8192 without
  the flag aborts (SIGABRT, core dump, 23628 MiB). 4096 stays the ceiling.

At 524288 (YaRN 2x), expert-cache ladder, cold load, peak VRAM measured during decode:

| config | 10K prefill/decode | ~60K prefill/decode | ~120K prefill/decode | peak VRAM |
| --- | --- | --- | --- | --- |
| cache 168 | 3808 / 163.7 | 3484.4 / 125.1 | 2850 / 100.2 | 22768 MiB |
| cache 168 + `--phase-aware-workspace` | 3716 / 164.1 | 3442 / 126.9 | - | 20950 MiB |
| cache 200 + `--phase-aware-workspace` | 3984 / 169.8 | 3590.5 / 129.7 | 2901 / 102.2 | 22714 MiB |
| cache 224 + `--phase-aware-workspace` | - | - | - | OOM at load (24050 MiB) |

- At cache 168 the flag is throughput-neutral (inside acceptance noise) and buys headroom
  (22768 -> 20950 MiB peak); that headroom carries cache 168 -> 200 for ~+3% prefill /
  ~+4% decode at the same peak.
- cache 224 OOMs at load (`cuMemCreate`), so 200 is the practical ceiling.

Long-context on the shipped 256k shape (cache 0 + `--phase-aware-workspace`, prompt_n 59751
and 119293, every pass `cache_n` 0 / `predicted_n` 512): ~60K 3944.5 prefill / 154.6 decode /
21980 MiB; ~120K 3083.4 / 113.2 / 21980 MiB. Prefill falls ~2.2x from 10K to 120K depth.

## Conclusions

- **Config of choice at 262144:** moe-cache fork, MTP on, `--phase-aware-workspace`,
  `-b/-ub 4096` - ~223 t/s decode / 4983 prefill within the 22 GB cap.
- The fork beats stock with all experts on GPU, without using the expert cache: ~+11% decode
  and ~1 GB less workspace VRAM, which buys the larger prefill ubatch. Stock's MTP-on config
  cannot exceed `-b/-ub 512` inside the cap.
- MTP on is the decode pick (+63% over MTP off at equal ubatch); MTP off only wins prefill
  by ~7% and uses less VRAM.
- Rejected as over-cap: fork MTP ub 6144; stock MTP ub 2048; stock MTP-off ub 6144
  (stock MTP-off ub 8192 fails to allocate).
- **Config of choice at 524288 (YaRN 2x):** moe-cache fork, MTP on,
  `--moe-expert-cache-size 200` + `--phase-aware-workspace`, `-b/-ub 8192` - ~170 t/s decode /
  3984 prefill at 22714 MiB. All-on-GPU does not fit; the cache is what makes the window load,
  and 224 slabs OOM at load.

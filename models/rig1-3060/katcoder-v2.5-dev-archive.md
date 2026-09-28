# KAT-Coder-V2.5-Dev (Rig 1) - experiment archive

This archive holds supporting measurements and experiments not on the main card
([katcoder-v2.5-dev.md](katcoder-v2.5-dev.md)): rejected configs, sweeps, retired
quants, and old-protocol baselines. Where a table reproduces a main-card headline
result, the archive mirrors it; the main card remains authoritative.
Model card:
[gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF](https://huggingface.co/gbuzhf/KAT-Coder-V2.5-Dev-MTP-GGUF).
Methodology in [methodology](../../methodology.md); model-specific issues in
[issues](../../issues.md).

Quants:

- `APEX-I-Compact` (16.24 GiB, single file, Q4_K_M / file_type 15) - the only quant tested

Routing profiles: none traced for this model.

## MoE split (ncmoe) ladder (llama-server, c 262144, MTP n-max 2, q8_0 KV, stock)

Second-pass C#+React averaged, prompt caching disabled (`cache_prompt:false`); cold load per
config.

| ncmoe | result | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- |
| 24 | OOM (compute pp buffers) | - | - | - | - |
| 26 | OOM (compute buffers) | - | - | - | - |
| 27 | OOM (compute buffers) | - | - | - | - |
| 28 | fits | 338.5 | 47.7 | 0.71 | 11729 MiB |
| 32 | fits | 317.9 | 40.9 | 0.60 | 10411 MiB |

- 24/26/27 fail at context creation; adding `-b 512 -ub 512` does not rescue them with MTP
  on, so 28 is the floor at full ctx.
- Per-prompt at ncmoe 28: C# prefill 356.10 / decode 45.69 / acceptance 0.659; React
  320.93 / 49.72 / 0.762.
- Per-prompt at ncmoe 32: C# 344.63 / 39.53 / 0.573; React 291.18 / 42.32 / 0.633.

## MTP sweep (c 262144, second-pass C#+React averaged)

MTP-on rows at ncmoe 28; MTP-off rows at their lowest fitting ncmoe.

| Config | prefill t/s | decode t/s | acceptance | mean len | VRAM used |
| --- | --- | --- | --- | --- | --- |
| MTP on, n-max 1 | 338.4 | 47.0 | 0.806 | 1.8 | 11665 MiB |
| MTP on, n-max 2 | 338.5 | **47.7** | 0.71 | 2.45 | 11729 MiB |
| MTP on, n-max 3 | 340.4 | 43.8 | 0.568 | 2.7 | 11791 MiB |
| MTP off, ncmoe 24 | 391.9 | 45.2 | - | - | 10963 MiB |
| MTP off, ncmoe 28 | 362.1 | 42.5 | - | - | 9647 MiB |

- n-max 2 is the peak (inverted U, same shape as the 35B): n-max 1 accepts more (0.81) but
  averages only 1.8 tokens/step; n-max 3 rejects the third draft token too often (0.57).
- MTP off raises short-prompt prefill (no draft compute) but loses ~11% decode at the same
  ncmoe, and the freed draft VRAM only buys ncmoe 24 (45.2) - still below MTP-on at 28.
- The draft context costs ~2 GB: MTP off at ncmoe 28 is 9647 MiB vs 11729 with MTP on.
- VRAM per draft token is ~63 MiB (n-max 1 -> 2 -> 3: 11665 -> 11729 -> 11791).

## Messy-code refactor (retired ~116K prompt)

Winner config, cold load, ONE timed `/v1/chat/completions` pass, `max_tokens` 512,
`ignore_eos:true`.

| Quant | MTP | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | on | 517.13 | 36.08 | 0.814 | 11729 MiB |

- 116,257-token prompt; decode 36.08 vs the 47.7 headline is the attention cost over ~116K
  cached KV tokens (-24%), with normal acceptance (mean len 2.63).
- Prefill 517.13: the ~192/~155-token coding prompts sit in the small-batch regime where
  per-request overhead dominates, so their 338.5 is not the model's saturated prefill. On
  this long prompt the model matches the 35B IQ4_XS (522.16), i.e. the same arch prefills
  at the same rate once the batch is large.
- No crash and no EOS quirk: `qwen35moe` is safe on the near-repetitive prompt (the PLE
  n-gram path is `qwen4exp`-only).

## Messy-code refactor (~60K prompt, 2026-09-28)

Cold load, ONE timed `/v1/chat/completions` pass, `max_tokens` 512, `ignore_eos:true`,
q8_0 KV. Replaces the retired ~116K run above (the benchmark moved to ~60K on 2026-09-27).

| Quant | Engine | MTP | ncmoe | cache | prompt tokens | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| APEX-I-Compact | moe-cache fork | on | 28 | 80 | 59760 | 608.70 | 49.06 | 275/470 (0.59) | 11077 MiB |
| APEX-I-Compact | stock | on | 28 | - | 59760 | 572.79 | 38.33 | 288/446 (0.65) | 11781 MiB |

- Fork holds ~+6% prefill and ~+28% decode at ~60K; both fully prefill cold
  (`cached_tokens` 0).

## Method note: slot KV cache vs the second-pass protocol

The shared protocol measures on the SECOND pass so the first pass can warm mmap page cache.
Re-sending the identical prompt hits the slot's KV prefix cache - the second pass logged a
4-token prompt, which would fake the prefill. All KAT runs therefore set
`cache_prompt:false` in the payload so the measure pass performs a full re-prefill. Weight
page cache is irrelevant here because the config uses `--load-mode none` (eager load), so
there is nothing for the warm-up pass to warm; the only effect of `cache_prompt:false` is to
defeat the KV hit.

## moe-cache fork (GenerelSchwerz) expert-cache sweep (c 262144, MTP on, q8_0 KV)

The fork's dynamic CUDA expert cache overrides `--n-cpu-moe` placement: cold experts stay in
host RAM and only `--moe-expert-cache-size` slabs per expert tensor are GPU-resident. Cold
load, second-pass, C#+React averaged, `cache_prompt:false`.

| cache | prefill t/s | decode t/s | VRAM used |
| --- | --- | --- | --- |
| 0 (control) | 345.4 | 51.8 | 11105 MiB |
| 32 | 322.8 | 56.8 | 7727 MiB |
| 64 | 319.4 | 73.6 | 9629 MiB |
| 80 | 342.4 | 78.1 | 11029 MiB |
| 80 (repeat) | 344.1 | 73.4 | 11029 MiB |
| 88 | 360.5 | 75.4 | 11353 MiB |
| 96 | 368.2 | 78.4 | 11531 MiB |
| 128 / 160 / 192 | - | - | OOM at spawn |

- Cache 80 is the pick: ~76 t/s decode (two samples 73.4/78.1) with ~1.26 GiB free; 96 matches
  the decode but leaves only ~430 MiB, below the headroom rule.
- The cache-0 control (51.8) already beats the stock binary (47.7) - the fork tracks a newer
  upstream, so part of the gain is engine, not cache.
- Per-prompt at cache 80: C# 378-395 prefill / 73.5-79.9 decode; React 294-296 / 73.2-76.4.

## Conclusions

- Best config on this rig: `APEX-I-Compact`, moe-cache fork + MTP n-max 2, ncmoe 28, cache 80,
  c 262144 -> ~76 t/s decode (prefill ~344 short-prompt, acceptance ~0.75), 11029 MiB. Stock +
  MTP (47.7 t/s, 11729 MiB) is the fallback where the fork engine is unavailable.
- ncmoe 28 is the hard floor with MTP at full ctx; 32 costs ~14% decode for ~1.3 GB.
- MTP is a net win despite ~2 GB of draft context.
- Not probed: the Codacus CSV-profile cache (it needs a VRAM-resident profile pack; at ncmoe 28
  only ~560 MiB is free). The moe-cache fork needs no pack and wins here.

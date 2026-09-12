# KAT-Coder-V2.5-Dev (Rig 1) - experiment archive

This archive holds supporting measurements and experiments not on the main card
([katcoder-v2.5-dev.md](katcoder-v2.5-dev.md)): rejected configs, sweeps, superseded
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

## Messy-code refactor (single-pass)

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

## Method note: slot KV cache vs the second-pass protocol

The shared protocol measures on the SECOND pass so the first pass can warm mmap page cache.
Re-sending the identical prompt hits the slot's KV prefix cache - the second pass logged a
4-token prompt, which would fake the prefill. All KAT runs therefore set
`cache_prompt:false` in the payload so the measure pass performs a full re-prefill. Weight
page cache is irrelevant here because the config uses `--load-mode none` (eager load), so
there is nothing for the warm-up pass to warm; the only effect of `cache_prompt:false` is to
defeat the KV hit.

## Conclusions

- Best config on this rig: `APEX-I-Compact`, stock + MTP n-max 2, ncmoe 28, c 262144 ->
  47.7 t/s decode (prefill 338.5 short-prompt / 517 saturated, acceptance 0.71),
  11729 MiB.
- ncmoe 28 is the hard floor with MTP at full ctx; 32 costs ~14% decode for ~1.3 GB.
- MTP is a net win despite ~2 GB of draft context.
- Not probed: the Codacus-fork expert cache (would need an all-CPU ncmoe to free room for a
  pack; at ncmoe 28 only ~560 MiB is free).

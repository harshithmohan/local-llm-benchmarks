# Swift-1.5-Qwen3.8-27B (Rig 2) - experiment archive

> **Retired-prompt note:** rows below were measured with the retired timing prompts (short
> C#/React, pre-2026-09-29; and the retired ~116K long-context prompt) unless a section says
> otherwise. The current timing prompt is the single ~10k-token opencode session context
> ([test-prompts.md](../../../test-prompts.md)); the two are not directly comparable.

This archive is the experiment log for
[swift-qwen38-27b.md](../swift-qwen38-27b.md), the Swift-1.5 fine-tune of Qwen3.8-27B. It
shares the vLLM stack, profiles, and architecture with the base
[`W4A16-AutoRound-fast` archive](qwen38-27b.md); that page carries the shared container/pool
setup, the retired profiles, the base quant's rows, and the full arch notes. This page records
what is specific to the fine-tune: the checkpoint port (a separate study,
[../../../experiments/qwen38-27b-swift-1.5-int4.md](../../../experiments/qwen38-27b-swift-1.5-int4.md)),
its retired timing rows, and the `INT8_ACT=int8` change applied to both Swift profiles.

vLLM protocol: single pass per boot, timing from the vLLM server metrics
([engine-notes/vllm.md](../../../engine-notes/vllm.md)), pool pinned by bytes,
`INT8_ACT=int8`, cold load. Methodology in [methodology](../../../methodology.md); gotchas in
[issues](../../../issues.md). Model card:
[ukisai/Swift-1.5-Qwen3.8-27b-INT4](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b-INT4).

Quants:

- `Swift-1.5-INT4` - vLLM, current recommended (see the model page)

## Port and checkpoint preparation

The fine-tune is the LLM Compressor AWQ+GPTQ (`compressed-tensors`, W4A16 sym g128) export of
`ukisai/Swift-1.5-Qwen3.8-27b-INT4`. It drops into the same prepare + serve path as the base
checkpoint once one ignored MTP entry is removed; the full procedure, the AutoRound export
that did not port, and the head/drafter requantization are in the
[port study](../../../experiments/qwen38-27b-swift-1.5-int4.md). Two differences from the base
to carry over:

- The drafter is rebuilt on the fine-tune's own output distribution: a 40,960-token draft
  vocabulary (~25.9k tokens) instead of the base model's (~54k), so the drafted head is not
  shared with the base build.
- The export declares an FP8 static `kv_cache_scheme`; the fp8 profile matches it and the
  KVarN profile overrides it without complaint.

Both Swift profiles were later updated to serve `INT8_ACT=int8` (the int8 Marlin activation
stack adopted from the base [Arc-repo transfer study](../../../experiments/qwen38-27b-da3dsoul-arc-transfer.md));
the model-page env blocks already include it.

## vLLM short-prompt rows (retired C#/React prompts, 2026-09-27)

`INT8_ACT=int8` served throughout (Swift build `641274bd`/`4f4a6a1f`); retired short C#/React
prompts averaged, single pass, requests routed through llama-swap. Superseded by the
~10k-prompt rows on the model page.

| Quant | Spec | ctx | KV | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Swift-1.5-INT4 | MTP | 150000 | fp8 | 1621.5 | 96.1 | ~0.47 | 22510 MiB |
| Swift-1.5-INT4 | MTP | 250000 | KVarN k4v2 | 1683.0 | 86.7 | ~0.49 | 22052 MiB |

- Swift single pass C# 1714.0 / 92.5, React 1528.9 / 99.6. Unguarded React naturally stops
  early: it emitted EOS at 339 tokens (decode 128.8, acceptance 0.899) - the fine-tune
  finishes coding answers without padding, unlike the base model which must be held to 512
  with `ignore_eos`. The 512-guarded React pass is what fed the table for protocol parity.
- One-boot data: the base led short decode at both contexts here (150k 103.3 vs 96.1; 250k
  92.7 vs 86.7), with Swift close behind on prefill (1621.5 vs 1672.7; 1683.0 vs 1716.6). On
  the current ~10k prompt the order flips (Swift ahead on decode).
- Decode swings +-5-10% run to run; prefill is +-0.5% stable. The base archive carries the
  fuller protocol notes.

## Long-context refactor (vLLM, retired ~116K prompt)

A deliberately near-repetitive ~116K-token refactor prompt; Swift fp8 is a 3-run mean, KVarN a
single pass:

| Quant / engine | Spec | ctx | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| Swift-1.5-INT4 / vLLM | MTP | 150000 | 757.4 | 62.4 | 0.444 | 22704 MiB |
| Swift-1.5-INT4 / vLLM | MTP (KVarN) | 250000 | 836.0 | 32.4 | 0.512 | 22388 MiB |

- Near-parity with the base quant on the fp8 profile (757.4 / 62.4 vs 746.7 / 63.8) and ahead
  on the single-pass KVarN reading (836.0 / 32.4 vs 784.4 / 27.5, +6.6% prefill, +17.8%
  decode).
- All ran the full 512 (`ignore_eos: true`); no crash or EOS quirk. Acceptance 0.444 (fp8) /
  0.512 (KVarN).

## Long-context refactor (~60K prompt, retired single-pass rows)

Single-pass, cache-cold rows measured 2026-09-27, before the protocol unification;
superseded by the current rows on the model page.

| Quant | Engine | ctx | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- | --- |
| Swift-1.5-INT4 | vLLM | 150000 | 1617.3 | 78.9 | 0.447 | 22510 MiB |
| Swift-1.5-INT4 | vLLM | 250000 | 1698.5 | 41.9 | 0.369 | 22052 MiB |

- Cache-cold, cold load, vLLM server metrics; fp8 150k decoded fastest and the KVarN 250k
  profile dropped to ~42 t/s once KV bandwidth dominates.

## Key arch notes

Shared with the base model (full notes in the [base archive](qwen38-27b.md)): hybrid SSM +
attention with only ~16 of 65 layers owning a growing KV cache; 4 KV heads x 256 key/value
length; embedded MTP (`nextn_predict_layers=1`); vLLM W4A16 fp8 at 150000 / KVarN 4/2-bit at
250000.

Fine-tune-specific:

- The drafter is rebuilt on the fine-tune's own output distribution (~25.9k tokens vs the base
  model's ~54k), so the draft head is not shared with the base build.
- At 150000 the fine-tune runs ~520 MiB heavier than the base quant (22510 vs 21992 MiB),
  ~18 MiB under the 22528 cap - that margin is what pins it to the same cap-safe profiles.

## Conclusions

- The fine-tune serves on the same recommended profiles as the base: `Swift-1.5-INT4` fp8 at
  150000 and KVarN 4/2-bit at 250000, both under the 22 GB cap.
- On the current ~10k opencode prompt it edges the base on decode at both contexts (116.9 vs
  113.0 at 150k; 94.3 vs 87.9 at 250k); the retired short-prompt protocol had the base ahead,
  so treat the gap as prompt-dependent.
- The port is a checkpoint-preparation exercise, not an engine-tuning one; no launch flag
  changed ([port study](../../../experiments/qwen38-27b-swift-1.5-int4.md)).

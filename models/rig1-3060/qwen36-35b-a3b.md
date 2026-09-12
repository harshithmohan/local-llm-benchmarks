# Qwen3.6-35B-A3B (Rig 1) - best configs

Clean summary. Full experiment log: [qwen36-35b-a3b-archive.md](qwen36-35b-a3b-archive.md).
Model cards: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(`UD-*` quants); [byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF) (`IQ4_XS-4.19bpw`).
Context covered: 262144 for the headline configs (204800 and 131072 runs are in the
archive - dropped because this model's speed barely changes with context: 204800 was
within 6-9% of 262144, and the only thing 200k buys is 1-2 extra cache slots at the cost
of 57k tokens of window). For more than the native window, an extended-context YaRN
probe (IQ4_XS reaches ~736K) is tabulated under the extended-context results below; the
underlying probes are in the archive.

## Measured results at c 262144 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV)

| Quant | binary | MTP | ncmoe | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | stock | on | 28 | n/a | 525.7 | **49.4** |

The row uses the current protocol: coding prompts (C# + React, ~308 tokens each) averaged,
second-pass measurement (first pass warms mmap page cache, discarded), recommended
sampling (temp 1.0, top_p 0.95, top_k 20, min_p 0.0; presence_penalty 1.5), cold load.
Prefill is prompt-size-bound: compare rows to each other, not to llama-bench pp numbers or
archived rows.

Reading:

- The Codacus fork adds nothing for IQ4_XS at 256k: no expert cache is possible (fused
  gate_up) and the prefill patches are noise at 256k prefill - stock is the config.
- The larger quants (UD-Q4_K_M, UD-Q6_K) are archived - see Alternatives below.
- Best config: see the blocks below.

## Measured results at extended context (YaRN, q8_0 KV)

Same protocol as above; every row extends past the native 262144 window with
`--rope-scaling yarn --rope-scale <ctx/262144> --yarn-orig-ctx 262144` (2.0 at 512K,
2.875 at 736K). Two regimes: at 512K the q8_0 KV alone is ~5.3 GiB and IQ4_XS's smaller
weights leave ~7 experts on GPU (ncmoe 34); at 736K all experts must go to CPU (ncmoe 99).

| Quant | binary | MTP | ncmoe | cache slots | ctx | prefill t/s | decode t/s | VRAM (load) | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | stock | off | 34 | n/a | 524288 | 332.5 | **37.1** | 11037 MiB | clean; 7 GPU expert layers |
| IQ4_XS | stock | off | 99 | n/a | 753664 | 282.0 | 32.3 | 11525 MiB | edge |

- Two regimes: fastest is 512K with GPU-resident experts (332.5 prefill / 37.1 decode,
  11037 MiB); maximum reach is 736K with all-CPU experts (282.0 / 32.3, 11525 MiB). The
  512K->736K step costs ~15% prefill and ~13% decode.
- MTP loses at extended ctx: the ~2.3 GiB draft context evicts the GPU expert layers
  (36.3 with MTP vs 37.1 without), so every extended row here is MTP-off.
- Ceiling: ~736K usable, 752K loads (~170 MiB free, unmeasured), 768K OOM; the larger
  quants do not reach this far (fuller sweep in the archive).
- Long-range retrieval quality under YaRN was **not validated** (needs a >262144-token
  needle and a slow full prefill), so extended-context answer quality is unproven.

## Best config per quant

### IQ4_XS - fastest at large ctx (winner)

Stock binary + MTP, at full 256k:

    llama-server --port PORT \
      -m <models>/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      --n-cpu-moe 28 --ctx-size 262144 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --reasoning-preserve

-> 49.4 t/s decode @ 262144 (prefill 525.7, acceptance 0.67-0.70). The Codacus fork has
nothing to add for this quant: no cache possible (fused gate_up), and the prefill patches
do nothing at 256k prefill - stock is the config.

### IQ4_XS - extended context via YaRN (512K fastest, 736K max)

For more than the native 262144 window, IQ4_XS is the extended-context quant: its smaller
weights keep ~7 experts on GPU at 512K (ncmoe 34) and it reaches 736K where UD-Q4_K_M
stops at ~672K. MTP stays off - the draft context evicts the GPU experts and loses more
than it gains.

Fastest, 524288 (7 experts on GPU):

    llama-server -m <models>/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      --n-cpu-moe 34 --ctx-size 524288 -ngl 999 \
      --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --reasoning-preserve -b 512 -ub 512

-> 37.1 t/s decode @ 524288 (prefill 332.5), 11037 MiB at load. Same flags plus
`--spec-type draft-mtp --spec-draft-n-max 2` and draft KV q8_0 give 36.3 (acceptance
~0.60): the ~2.3 GiB draft context pushes the GPU experts to CPU, so MTP loses here.

Maximum reach, 753664 (all experts on CPU):

    llama-server -m <models>/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      --n-cpu-moe 99 --ctx-size 753664 -ngl 999 \
      --rope-scaling yarn --rope-scale 2.875 --yarn-orig-ctx 262144 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --reasoning-preserve -b 512 -ub 512

-> 32.3 t/s decode @ 753664 (prefill 282.0), 11525 MiB at load - edge (~370 MiB free).
704K-752K sit between; 752K loads tight, 768K OOMs at context creation. Long-range
retrieval quality under YaRN was **not validated** - that needs a >262144-token needle
and a slow full prefill.

## Alternatives (archived)

IQ4_XS is faster at every measured context, so the larger quants are archived here:

- UD-Q4_K_M: best 256k was the Codacus-fork expert cache + MTP (40 slots, 38.8 decode,
  prefill 268.6) - still below IQ4_XS stock+MTP (49.4) and cache-bound, and it tops out at
  ~672K where IQ4_XS reaches ~736K. Headline rows and the messy run are in the archive.
- UD-Q6_K: weakest 35B quant at large ctx in every measured config.

## Messy-code refactor benchmark (real-task ~116K prompt)

One-time real-task speed test of the messy-code refactor prompt (see
[test-prompts.md](../../test-prompts.md), generated by `scripts/generate-messy-prompt.py`,
seed 42, 116,259 prompt tokens), the IQ4_XS 256K headliner plus the two extended-context
IQ4_XS recipes, q8_0 KV, cold load, single-run protocol (ONE timed pass, no warm-up;
/v1/chat/completions, max_tokens 512, `ignore_eos: true` per the new messy-prompt rules
in test-prompts.md):

| Quant | binary | MTP | ncmoe | ctx | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | stock | on | 28 | 262144 | n/a | 522.16 | 32.63 |
| IQ4_XS | stock | off | 34 | 524288 | n/a | 491.48 | 23.33 |
| IQ4_XS | stock | off | 99 | 753664 | n/a | 452.04 | 21.97 |

- Single-pass redo (2026-09): the original two-pass numbers (IQ4_XS 518.69/32.54)
  predate the single-run protocol. The redo confirms them: every value matches within
  single-run noise, and the row uses `--load-mode none` (eager weight load), so there
  was no mmap page-in effect to warm anyway. Old and new numbers are interchangeable
  for comparison purposes.
- IQ4_XS: MTP acceptance 0.652 (mean len 2.30), VRAM 11797 MiB at load (under the
  12 GB cap), /v1/chat/completions. No crash: the near-repetitive prompt is safe on
  qwen35moe (the PLE n-gram crash risk is qwen4exp-only). No EOS quirk either - the
  qwen35moe arch decodes normally on /completion and /v1/chat/completions.
- Decode is 32.63 t/s at 256K vs the 49.4 headline on 308-token prompts, with MTP
  acceptance normal: the gap is attention cost over 116K cached KV tokens, not an MTP
  failure. The 308-token prompt protocol stays unchanged for headline numbers.
- Chat-endpoint gotchas vs the raw /completion protocol: a closed ``` fence at prompt end
  makes the model emit EOS immediately in raw /completion (end-of-turn); n_predict is
  ignored by /v1/chat/completions (use max_tokens).
- Extended-context rows (IQ4_XS, YaRN, MTP off): the same 116,259-token prompt runs
  491.48/23.33 at 512K (ncmoe 34, 11037 MiB) and 452.04/21.97 at 736K (ncmoe 99,
  11525 MiB). The 256K MTP-on row's higher decode (32.63) reflects MTP plus the smaller
  allocated KV; every row decoded the full 512 tokens (finish_reason "length").

## Key arch notes

None specific to this model - general notes in [methodology.md](../../methodology.md).

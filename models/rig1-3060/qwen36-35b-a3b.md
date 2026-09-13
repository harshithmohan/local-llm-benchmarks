# Qwen3.6-35B-A3B (Rig 1) - best configs

Clean summary. Full experiment log: [qwen36-35b-a3b-archive.md](qwen36-35b-a3b-archive.md).
Model cards: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(`UD-*` quants); [byteshape/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF) (`IQ4_XS-4.19bpw`).
Context covered: 262144 for the headline configs (204800 and 131072 runs are in the
archive - dropped because this model's speed barely changes with context: 204800 was
within 6-9% of 262144, and the only thing 200k buys is 1-2 extra cache slots at the cost
of 57k tokens of window). For more than the native window, an extended-context YaRN probe is tabulated
under the extended-context results below - IQ4_XS reaches ~736K on stock and ~852K on
ik-llama.cpp; the underlying probes are in the archive (stock) and in the notes below
(ik).

## Measured results at c 262144 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV)

| Quant | binary | MTP | ncmoe | cache slots | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | stock | on | 28 | n/a | 525.7 | **49.4** |

The row uses the current protocol: coding prompts (C# ~192 tokens, React ~155 tokens) averaged,
second-pass measurement (first pass warms mmap page cache, discarded), recommended
sampling (temp 1.0, top_p 0.95, top_k 20, min_p 0.0; presence_penalty 1.5), cold load.
Prefill is prompt-size-bound: compare rows to each other, not to llama-bench pp numbers or
archived rows.

Reading:

- The Codacus fork adds nothing for IQ4_XS at 256k: no expert cache is possible (fused
  gate_up) and the prefill patches are noise at 256k prefill - stock is the config.
- ik-llama.cpp (build 3bb386e) was also tested at 256k and loses to stock (best ik row
  311.6 prefill / 47.5 decode with MTP; MTP-off probe 358.7/45.0), so it gets no table
  row here. Notably MTP acceptance is higher on ik (0.81-0.84 vs stock's 0.67-0.70) but
  does not convert to throughput, and the ik MTP draft context does not fit with deeper
  GPU packs (ncmoe 18/24 + MTP fail at init; the 256k MTP ceiling is ncmoe 28).
- The larger quants (UD-Q4_K_M, UD-Q6_K) are archived - see Alternatives below.
- Best config: see the blocks below.

## Measured results at extended context (YaRN, q8_0 KV)

Same protocol as above; every row extends past the native 262144 window with
`--rope-scaling yarn --rope-scale <ctx/262144> --yarn-orig-ctx 262144` (2.0 at 512K,
2.875 at 736K). Two regimes: at 512K the q8_0 KV alone is ~5.3 GiB and IQ4_XS's smaller
weights leave experts on GPU; at 736K most/all experts go to CPU. All rows are MTP off -
on stock the draft context evicts the GPU expert layers, on ik it eats the KV headroom
(fits only on the lean 512K split, where it loses on prefill - see below).

| Quant | binary | MTP | ncmoe | cache slots | ctx | prefill t/s | decode t/s | VRAM (load) | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | ik | off | 28 | n/a | 524288 | 322.0 | **41.0** | 11747 MiB | ik best at 512K; stock 512K (ncmoe 34) = 332.5/37.1 @11037 MiB |
| IQ4_XS | ik | off | 36 | n/a | 753664 | 262.4 | **34.7** | 11361 MiB | ik best at 736K; stock 736K (ncmoe 99) = 282.0/32.3 @11525 MiB |
| IQ4_XS | ik | off | 41 | n/a | 851968 | 240.2 | 32.4 | 11153 MiB | ik max, serves fine |

- Fastest at 512K is ik (322.0 prefill / 41.0 decode, 11747 MiB, +10.5% decode over
  stock's 37.1; stock keeps the prefill edge at 332.5); fastest at 736K is ik with 5
  GPU experts left (262.4 / 34.7, +7.4% decode over stock's all-CPU 32.3).
- ik lean/sweep probes (no table rows): at 512K, ncmoe 34 = 289.4/37.3 @9379 MiB and
  deeper packs (26) OOM; at 736K, all-CPU ncmoe 41 = 252.8/33.0 @10037 MiB. The ik
  ceiling sweep on all-CPU experts: 786432 (scale 3.0) = 255.0/32.8 @10409 MiB, 851968
  (scale 3.25) = 240.2/32.4 @11153 MiB = ik max measured, both serve fine.
- ik's per-GPU-expert-layer cost at 736K is ~265 MiB vs ~437 MiB on stock, so ik packs
  ~4 more experts on GPU at equal VRAM - the main reason for the extended decode lead.
- Ceiling: stock reaches ~736K usable (752K loads tight, 768K OOM at context creation);
  ik extends the usable reach to 851968 (YaRN scale 3.25, all-CPU experts, 11153 MiB).
  On ik 917504 (scale 3.5) LOADS at 11897 MiB but crashes on the first request (runtime
  CUDA OOM in the decode cublas path - loads-fine is not proof of serviceability near
  the ceiling, [issues.md](../../issues.md)); 983040 (scale 3.75) OOMs at init. On ik,
  ncmoe 34 at 736K also crashes at init (cublasCreate OOM).
- The 512K->736K step on stock costs ~15% prefill and ~13% decode.
- MTP at extended ctx is a loser on both engines, for different reasons: on stock it
  fits but loses (36.3 with MTP vs 37.1 without - the ~2.3 GiB draft context evicts the
  GPU expert layers); on ik it fits only at the lean split (512K, ncmoe 34: 269.6
  prefill / 41.8 decode, 11729 MiB, acceptance ~0.76-0.82 - decode ~parity with the
  MTP-off ncmoe 28 config at 41.0, prefill much worse) and does not fit at the best
  split (ncmoe 28 fails at init: the draft context eats the KV headroom) nor at 736K
  even all-CPU (ncmoe 41: the per-step recurrent speculative checkpoint init OOMs the
  main KV alloc, 782 MiB). MTP also accompanies slower ik prefill in every pairing
  measured (256k: 311.6 MTP-on vs 358.7 MTP-off; 512K: 269.6 vs 322.0 - splits differ,
  so treat as indicative, not a controlled A/B). MTP stays off in every extended
  recommendation.
- ik-specific: ncmoe values above the 41 layer count clamp to 41 (all-CPU experts) -
  ncmoe 99 behaves identically to 41 on ik.
- Long-range retrieval quality under YaRN was **not validated** - see [methodology.md](../../methodology.md).

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

### IQ4_XS - extended context via YaRN (ik 512K fastest, ik 852K max)

For more than the native 262144 window, IQ4_XS is the extended-context quant: ik-llama.cpp
wins decode at every extended point and reaches ~852K where stock stops at ~736K. MTP stays
off - on stock it fits but loses (draft context evicts the GPU experts), on ik it fits
only at the lean 512K split and loses on prefill.

    ik-llama-server -m <models>/Qwen3.6-35B-A3B-IQ4_XS-4.19bpw.gguf \
      -ncmoe <ncmoe> --ctx-size <ctx> -ngl 999 \
      --rope-scaling yarn --rope-scale <ctx/262144> --yarn-orig-ctx 262144 \
      -ctk q8_0 -ctv q8_0 -fa 1 \
      --threads 12 --parallel 1 \
      -b 512 -ub 512

| ctx | rope-scale | ncmoe | GPU experts |
| --- | --- | --- | --- |
| 524288 | 2.0 | 28 | 13 |
| 753664 | 2.875 | 36 | 5 |
| 851968 | 3.25 | 41 | 0 |

-> Speeds in the extended-context table above (41.0 t/s decode at 512K, 34.7 at 736K,
32.4 at 852K - the maximum measured serving context on this rig; 917504 loads but
crashes on the first request, 983040 OOMs at init). MTP stays off: it fits only on the
lean 512K split (`-ncmoe 34` + `--spec-type mtp:n_max=2 -ctkd q8_0 -ctvd q8_0`: 41.8
decode, 269.6 prefill, 11729 MiB, acceptance ~0.76-0.82 - decode parity, prefill much
worse). `rope-scale` must equal ctx/262144 exactly - `--ctx-size` is clamped to
`n_ctx_train * rope-scale`.

Variants and limits (lean/sweep probes, no table rows): at 512K, ncmoe 34 = 289.4/37.3
@9379 MiB and deeper packs (26) OOM; at 736K, all-CPU ncmoe 41 = 252.8/33.0 @10037 MiB
and ncmoe 34 crashes at init (cublasCreate OOM).

Stock alternatives (superseded by ik, kept for the prefill edge and engine comparison):
524288 with the stock binary, `--n-cpu-moe 34` -> 37.1 t/s decode (prefill 332.5),
11037 MiB; 753664 with `--n-cpu-moe 99` -> 32.3 t/s decode (prefill 282.0), 11525 MiB -
edge (~370 MiB free). 704K-752K sit between on stock; 752K loads tight, 768K OOMs at
context creation.

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
- Decode is 32.63 t/s at 256K vs the 49.4 headline on the ~192/~155-token coding prompts,
  with MTP acceptance normal: the gap is attention cost over 116K cached KV tokens, not an
  MTP failure. The coding-prompt protocol stays unchanged for headline numbers.
- Chat-endpoint gotchas vs the raw /completion protocol: a closed ``` fence at prompt end
  makes the model emit EOS immediately in raw /completion (end-of-turn); n_predict is
  ignored by /v1/chat/completions (use max_tokens).
- Extended-context rows (IQ4_XS, YaRN, MTP off): the same 116,259-token prompt runs
  491.48/23.33 at 512K (ncmoe 34, 11037 MiB) and 452.04/21.97 at 736K (ncmoe 99,
  11525 MiB). The 256K MTP-on row's higher decode (32.63) reflects MTP plus the smaller
  allocated KV; every row decoded the full 512 tokens (finish_reason "length").

## Key arch notes

- ik-llama.cpp specifics on this model: ncmoe clamps at the 41 layer count (values above
  = all-CPU experts); the per-GPU-expert-layer VRAM cost at extended ctx is ~265 MiB vs
  ~437 MiB on stock (ik keeps ~4 more experts on GPU at equal VRAM); MTP acceptance is
  higher on ik (0.81-0.84 vs 0.67-0.70) yet decode is slower at 256k; ik's extended
  ceiling fails past 852K with a runtime CUDA OOM crash on first request rather than a
  clean init-time rejection. ik-llama.cpp flags/notes: [methodology.md](../../methodology.md);
  gotchas: [issues.md](../../issues.md).
- None specific to this model otherwise - general notes in [methodology.md](../../methodology.md).

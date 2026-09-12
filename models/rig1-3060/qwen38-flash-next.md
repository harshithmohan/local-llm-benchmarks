# Qwen3.8-Flash-Next (Rig 1) - best configs

Different model family from Qwen3.6-35B-A3B: arch `qwen4exp` (Codacus fork cache-supported),
176.94B params despite the misleading `512x56B` size label, ~3B active per token, hybrid
Mamba2 + attention (1 full-attn layer per 4). Full experiment log:
[qwen38-flash-next-archive.md](qwen38-flash-next-archive.md). Methodology in
[methodology](../../methodology.md); model-specific issues in [issues](../../issues.md).
Model cards: [unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF)
(`UD-*` quants); [AtomicChat/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/AtomicChat/Qwen3.8-Flash-Next-GGUF) (`AD-*`).

Quants tested: `UD-IQ3_XXS` (76.32 GiB, 3 shards) - the recommended one;
`AD-4.27bpw-Q4_K_M-M64` (88.02 GiB, 33 shards).

## Measured results at c 230400 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV, Codacus fork)

| Quant | MTP | ncmoe | prefill t/s | decode t/s | VRAM free after req |
| --- | --- | --- | --- | --- | --- |
| UD-IQ3_XXS | on | 99 | 157.1 | **18.1** | ~860 MB |
| AD-Q4_K_M-M64 | off | 99 | 154.7 | 13.1 | ~770 MB |

204800 was measured and dropped from this table: same speed class but 25k fewer tokens
of window for zero cost - 230400 is the recommended setting (256k loads but is not
usable in practice, see the archive).

All rows on the Codacus fork; env vars REGISTER_HOST on; second-pass measurement
(first pass warms mmap page cache, discarded); recommended sampling (temp 1.0,
top_p 0.95, top_k 20, min_p 0.0, presence_penalty 0.0); cold load. ncmoe 99 clamps to
48 (the model's total MoE layer count) - same behavior. MTP acceptance at the
recommended temperature: 0.90-0.94.



## Best config per quant

### UD-IQ3_XXS - winner (fastest Flash-Next quant)

Best config: MTP on, ncmoe 99, c 230400. ncmoe 47 (one GPU-expert layer + MTP) is
equivalent within single-run noise on decode and prefill, for ~1 GB less headroom -
not worth it (ncmoe 46 OOMs with the draft context):

    GGML_CUDA_REGISTER_HOST=1 \
    llama-server -m <models>/Qwen3.8-Flash-Next-UD-IQ3_XXS-00001-of-00003.gguf \
      -ngl 99 --n-cpu-moe 99 -fa on \
      -c 230400 -ctk q8_0 -ctv q8_0 -b 512 -ub 512 \
      --load-mode mmap -fit off -np 1 --threads 12 \
      -md <models>/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf \
      -ngld 0 --spec-type draft-mtp --spec-draft-n-max 2

-> 18.1 t/s @ 230400 (acceptance 0.90-0.94; prefill 157.1), ~860 MB free - the
practical ceiling (256k loads but is not usable in practice, see the archive).
`--threads 12` (llama.cpp's default on this CPU) is the tested best; 6 and 8 lose
~7-10% decode with identical acceptance (see the archive's threads sweep).

### AD-Q4_K_M-M64

Same config as the measured table plus one env var (zero VRAM cost, +183% prefill):

    GGML_CUDA_REGISTER_HOST=1 \
    llama-server -m <models>/Qwen3.8-Flash-Next-AD-4.27bpw-Q4_K_M-M64-00001-of-00033.gguf \
      --n-cpu-moe 99 --ctx-size 230400 -ngl 999 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode mmap -fit off --threads 6 --parallel 1 \
      -b 512 -ub 512

-> 13.1 t/s @ 230400 (prefill 154.7), ~770 MB free - the practical ceiling (256k loads
but is not usable in practice). `--threads 6` is as originally run; the IQ3_XXS threads
sweep below suggests 12 is faster, but it was not re-tested for AD.

Its only argument might be quantization quality (bpw 4.27 vs IQ3_XXS's 3.06) - never
tested, treat as an unverified alternative. On speed it loses to IQ3_XXS in every
measured config on this rig.

## Alternatives (archived)

UD-Q3_K_XL was dropped from this page: at large ctx it never beats the other two
(ties at 204800) - see the archive for its full history.

## Messy-code refactor benchmark (real-task ~116K prompt, single-pass)

One-time real-task stability/speed test of the messy-code refactor prompt (see
[test-prompts.md](../../test-prompts.md), 116,226 prompt tokens, IQ3_XXS winner
config, q8_0 KV, cold load, ONE timed pass - no warm-up, per the single-run
messy-prompt protocol), decoded with `ignore_eos: true` (gotcha below):

| Quant | MTP | ignore_eos | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- |
| UD-IQ3_XXS | on | yes | 82.89 | 3.33 |

- Prefill 82.89 vs the 157.1 headline (-47%): the cold single-pass includes first-pass
  NVMe page-in of the 76 GiB weight set (mmap lazy-loads - the server start itself is
  fast, the page-in lands inside the first prefill) plus the known first-request MTP
  slowness (issues.md). This is the single-pass convention going forward; the two-pass
  headline above is not directly comparable.
- Decode 3.33 vs the 18.1 headline (-82%), MTP acceptance 0.854 (mean len 2.70) vs
  0.90-0.94 headline: attention cost over ~116K cached KV tokens is far heavier on
  this hybrid arch than on the 35B at the same prompt (which only lost ~30% decode,
  30.3 vs 49.4).
- Immediate-EOS gotcha: raw /completion returns 1 token with stop_type eos on this
  prompt - twice, including after the trailing closed ``` fence was neutralized with
  a nonce, so it is not the 35B-era fence trigger. Timing runs need
  `ignore_eos: true`; with it the model decoded the full 512 tokens of real refactor
  output. See issues.md. Decode-only follow-up passes via a KV-hit nonce re-send are
  valid (the 3.33 above came from such a re-send: 512 tokens over ~116K cached KV,
  4-token prefill).
- No crash: the qwen4exp PLE n-gram path did not fire on the near-repetitive prompt.
  VRAM 10867 MiB at load, ~1.4 GB under the 12 GB cap.

## Key arch notes

- The compute buffer scales with `-ub` on this arch (indexer): ub 2048 needs ~3.5x the
  compute of ub 512 at large ctx. The `-ub 512` trick is what unlocks large contexts,
  not KV savings (KV is only ~4.9 KiB/token).
- The expert cache is weak or a net loss on every quant at 12 GB VRAM: 512 experts with
  flat routing traffic means even 30 slots cover only ~19% of traffic, and the pack
  (~86-118 MiB/slot) competes with compute buffers. Keep GPU expert layers instead.
- Prefill patches (REGISTER_HOST) matter more here than on the 35B: this model streams
  ~10x more expert bytes per token.

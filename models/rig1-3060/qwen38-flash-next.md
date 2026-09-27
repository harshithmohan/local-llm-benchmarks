# Qwen3.8-Flash-Next (Rig 1) - best configs

Different model family from Qwen3.6-35B-A3B: arch `qwen4exp` (Codacus fork cache-supported),
176.94B params despite the misleading `512x56B` size label, ~3B active per token, hybrid
Mamba2 + attention (1 full-attn layer per 4). Full experiment log:
[qwen38-flash-next-archive.md](qwen38-flash-next-archive.md). Methodology in
[methodology](../../methodology.md); model-specific issues in [issues](../../issues.md).
Model card: [unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF)
(`UD-*` quants).

Quants tested: `UD-IQ3_XXS` (76.32 GiB, 3 shards) - the recommended one.

## Measured results at c 230400 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q8_0 KV, Codacus fork)

| Quant | MTP | ncmoe | prefill t/s | decode t/s | VRAM free after req |
| --- | --- | --- | --- | --- | --- |
| UD-IQ3_XXS | on | 99 | 157.1 | **18.1** | ~860 MB |

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
      -ngld 0 --spec-type draft-mtp --spec-draft-n-max 2 \
      --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.0

-> 18.1 t/s @ 230400 (acceptance 0.90-0.94; prefill 157.1), ~860 MB free - the
practical ceiling (256k loads but is not usable in practice, see the archive).
`--threads 12` (llama.cpp's default on this CPU) is the tested best; 6 and 8 lose
~7-10% decode with identical acceptance (see the archive's threads sweep).

## Alternatives (archived)

- UD-Q3_K_XL was dropped from this page: at large ctx it never beats the other two
  (ties at 204800) - see the archive for its full history.
- AD-Q4_K_M-M64 was dropped from this page: it loses to IQ3_XXS in every measured config
  on this rig, and has no MTP (an AD + shared MTP head accepted only ~0.71 and decoded
  slower than no-MTP). Its only argument is quantization quality (bpw 4.27 vs 3.06) -
  never tested. Full config and numbers in the archive.

## Messy-code refactor benchmark (real-task ~60K prompt, re-run pending, single-pass)

*Retired 2026-09-27: the ~116K-prompt run is archived in
[qwen38-flash-next-archive.md](qwen38-flash-next-archive.md). Re-run on the new ~60K
prompt pending.*

## Key arch notes

- The compute buffer scales with `-ub` on this arch (indexer): ub 2048 needs ~3.5x the
  compute of ub 512 at large ctx. The `-ub 512` trick is what unlocks large contexts,
  not KV savings (KV is only ~4.9 KiB/token).
- The expert cache is weak or a net loss on every quant at 12 GB VRAM: 512 experts with
  flat routing traffic means even 30 slots cover only ~19% of traffic, and the pack
  (~86-118 MiB/slot) competes with compute buffers. Keep GPU expert layers instead.
- Prefill patches (REGISTER_HOST) matter more here than on the 35B: this model streams
  ~10x more expert bytes per token.

# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-01 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`UD-IQ3_XXS` and `GSQ-RCO Q2_0` (`qwen4exp`, native ctx 262144, 512 experts, separate
shared MTP head). 177B total = 125B compute + 51B n-gram embedding table +
4B MTP; 48 layers =
12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared
expert per token. Model cards:
[unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF) (`UD-*` quants),
[ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ3_XXS | 81920 | moe-cache fork | off | 362 | **21.4** | 11496 MiB | cache 48, `-b/-ub 1024` |
| GSQ-RCO Q2_0 + MTP | 98304 | moe-cache fork | on | 388 | **33** | 11728 MiB | cache 40, Q4_K_M head, `-b/-ub 1024` |

## Configs

### UD-IQ3_XXS 80k - moe-cache fork, cache 48 + `-b/-ub 1024`

    llama-server --port PORT \
      -m <models>/Qwen3.8-Flash-Next-UD-IQ3_XXS-00001-of-00003.gguf \
      --ctx-size 81920 -ngl all -fit off \
      --moe-expert-cache-size 48 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --lazy-mode on --no-mmproj-offload --threads 12 --parallel 1 \
      --backend-sampling --decode-overlap --decode-boundary-overlap \
      --cache-ram 0 \
      -b 1024 -ub 1024 \
      --temp 1.0 --top-k 20 --min-p 0.0

### GSQ-RCO Q2_0 96k + MTP - moe-cache fork, cache 40 + `-b/-ub 1024`

    llama-server --port PORT \
      -m <models>/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
      --ctx-size 98304 -ngl all -fit off \
      --moe-expert-cache-size 40 \
      --spec-draft-model <models>/mtp-Qwen3.8-Flash-Next-shared-Q4_K_M.gguf \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --lazy-mode on --no-mmproj-offload --threads 12 --parallel 1 \
      --backend-sampling --decode-overlap --decode-boundary-overlap \
      --cache-ram 0 \
      -b 1024 -ub 1024 \
      --temp 1.0 --top-k 20 --min-p 0.0

## Notes

- **MTP is off on UD-IQ3_XXS.** The shared MTP head does not fit alongside that quant's
  expert cache at 12 GB; it does fit on GSQ-RCO (below).
- **`--load-mode none` and `--lazy-mode on` are required.**
- GSQ-RCO Q2_0 is a two-shard quant: pass shard 1 of 2 and the pair loads together (shard 2
  is the n-gram table). Without MTP, cache 84 and above load but crash on the first request;
  cache 80 is the ceiling at 80k (436/25.7).
- **MTP pays on GSQ, not on UD-IQ3_XXS.** The GSQ quant's smaller expert slabs leave room
  for the shared MTP head on the GPU. The recommended 96k config (cache 40) runs 388/33 at
  10k and 390/24 at 60K; at 80k with cache 48 it is faster still (426/35 and 398/24) if you
  do not need the extra context. Draft acceptance is 76-82%. `--spec-draft-n-max 3` and `4`
  OOM; the Q8_0 head does not fit.
- **96k is the ctx ceiling with MTP.** KV is cheap here - only the 12 Qwen Sparse Attention
  layers carry it - so the limit is a compute-buffer OOM, not KV: 112k fails at cache 40 and
  32, and 96k needs cache <=40 (cache 48 only fits with `-ub 512`, at ~27% prefill cost).
- `--spec-type ngram-mod` (draftless prompt lookup) was tested at several values
  (24/48/64, 24/3/12, 24/12/48) and never beat the no-spec baseline (10k 19.6-24.4 vs 25.7;
  60K 14.1-14.8). `--fit` is not used.

## Long-context refactor benchmark (~60K prompt)

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) ~60K-token Python
file of 79 near-identical legacy templates. Same protocol as the recommended configs
([methodology.md](../../methodology.md) §Measurement methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UD-IQ3_XXS | 81920 | moe-cache fork | off | 341 | **13.1** | 11492 MiB | cache 48, `-b/-ub 1024` |
| GSQ-RCO Q2_0 + MTP | 98304 | moe-cache fork | on | 390 | **24** | 11728 MiB | cache 40, Q4_K_M head, `-b/-ub 1024` |

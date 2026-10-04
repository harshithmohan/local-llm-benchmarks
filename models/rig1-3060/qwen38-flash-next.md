# Qwen3.8-Flash-Next (Rig 1) - recommended configs

Updated: 2026-10-04 · [full experiment log](archive/qwen38-flash-next.md) · [methodology](../../methodology.md)

`GSQ-RCO Q2_0` (`qwen4exp`, 2.40 bpw, native ctx 262144, 512 experts, a separate MTP head
from the ggml-org repo - the GSQ-RCO release ships none). 177B total = 125B compute + 51B
n-gram embedding table + 4B MTP; 48 layers =
12 x (3 x Gated DeltaNet -> MoE + 1 x Qwen Sparse Attention -> MoE), 10 routed + 1 shared
expert per token. Model card:
[ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) (`GSQ-RCO` quants);
MTP head: [ggml-org/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF).

## Recommended configs

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSQ-RCO Q2_0 + MTP | 81920 | moe-cache fork | on | 464 | **31** | 11534 MiB | cache 40, Q4_0 head, `-b/-ub 1536`, draft ubatch 512 |

## Configs

### GSQ-RCO Q2_0 80k + MTP - moe-cache fork, cache 40 + `-b/-ub 1536` (draft ubatch 512)

    llama-server --port PORT \
      -m <models>/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
      --ctx-size 81920 -ngl all -fit off \
      --moe-expert-cache-size 40 \
      --spec-draft-model <models>/mtp-Qwen3.8-Flash-Next-Q4_0.gguf \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --lazy-mode on --no-mmproj-offload --threads 12 --parallel 1 \
      --backend-sampling --decode-overlap --decode-boundary-overlap \
      --cache-ram 0 \
      -b 1536 -ub 1536 --spec-draft-ubatch-size 512 \
      --temp 1.0 --top-k 20 --min-p 0.0

## Notes

- **`--load-mode none` and `--lazy-mode on` are required.**
- GSQ-RCO Q2_0 is a two-shard quant: pass shard 1 of 2 and the pair loads together (shard 2
  is the n-gram table). Without MTP, cache 84 and above load but crash on the first request;
  cache 80 is the ceiling at 80k (436/25.7).
- **MTP is the point of this quant.** The GSQ quant's smaller expert slabs leave room for the
  MTP head on the GPU: at 80k/cache 40 the recommended config runs 464/31 (best 507;
  draft acceptance ~85%), roughly double the no-MTP decode (23.9-25.7). `--spec-draft-n-max 3`
  and `4` OOM; the Q8_0 head does not fit.
- **A bigger `-ub` buys prefill at 80k, but only with the draft ubatch capped.** `-ub 1536`
  is ~+18% prefill over `-ub 1024` (464 vs 394 warm median) for ~+560 MiB; uncapped it loads
  then crashes on the first decode, so `--spec-draft-ubatch-size 512` is required. `-ub 1792`
  and `2048` fail at load (`failed to allocate compute pp buffers`).
- **96k is the ctx ceiling, but only at `-ub 1024`.** KV is cheap here (only the 12 Qwen
  Sparse Attention layers carry it), so the binding limit is the compute buffer: 96k/cache 40
  runs 428/35.0 at 11460 MiB, but `-ub 1280` and `1536` load and then OOM on the first
  decode, and trimming the expert cache (40→36→32) does not lower the resident footprint.
  Cache 44 loads but OOMs on the first decode; cache 48 fails at load.
- **Prefill on this shape is noisy**: repeated passes of one config ranged 188-507 t/s, so
  the prefill column is a warm median, not a precise figure.
- `--spec-type ngram-mod` (draftless prompt lookup) was tested at several values
  (24/48/64, 24/3/12, 24/12/48) and never beat the no-spec baseline (10k 19.6-24.4 vs 25.7;
  60K 14.1-14.8). `--fit` is not used.
- Single-knob ablations on this shape (see archive): `--ple-prefetch` and CPU affinity are
  within noise; `-b 8192`, `--spec-default`, `--moe-early-router`, `--experimental-logs` and
  `--live-context-workspace` all cost decode.

## Long-context refactor benchmark (~60K prompt)

Real-task timing test of a long-context code-refactor task ([test-prompts.md](../../test-prompts.md)):
a fixed refactor instruction wraps a deterministically generated (seed 42) ~60K-token Python
file of 79 near-identical legacy templates. Same protocol as the recommended configs
([methodology.md](../../methodology.md) §Measurement methods): q8_0 KV, cold load.

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| not yet run | - | - | - | - | - | - | - |

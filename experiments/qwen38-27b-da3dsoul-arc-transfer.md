# Qwen3.8-27B on an RTX 3090: testing da3dsoul's Arc-repo experiments

Transferability study: which of the low-level experiments from
[Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments](https://github.com/da3dsoul/Qwen3.8-vLLM-KVarN-MTP-Arc-Experiments)
(an Intel Arc Pro B70) hold on a consumer RTX 3090 running the same model under
vLLM, one experiment at a time, with measured results.

This is a companion to [models/rig2-3090/qwen38-27b.md](../models/rig2-3090/qwen38-27b.md):
the model page carries the recommended configs and headline numbers, this page carries
the experiment-by-experiment verdicts and the reasoning behind what did and did not
transfer. It is kept in-repo rather than as a one-off reply because the conclusions
(which knobs are architecture-specific, which are worth adopting) apply to any CUDA
deployment of this stack.

## TL;DR

Of the five experiments, **one is worth adopting**: `INT8_ACT=int8` (the container's
int8 Marlin activation path), which lifts prefill **+83% at short context and +39% on a
140k prompt** for a ~9-10% decode cost — a clear win for long-prompt work. Everything
else is a no-op or a rejection:

- The reference repo's headline results are **XPU-specific** and do not transfer. Its
  fp8 lm_head/drafter surgery assumes **native fp8 weights**, which sm86 (the 3090) does
  not have; our image already ships the int8/int4 quantization that is correct here.
- The prefix-cache retention fix and the MTP/batching knobs are **already correct in the
  current image** (the retention var is redundant; 2048 batched tokens and every MTP
  default are already optimal).
- The KVarN `g64`/`k4v4` tile variants all **cost KV capacity with no speed or
  acceptance gain**.

The one net configuration change that came out of this work is unlocked by the shipped
int4 head/drafter: it frees enough VRAM to raise the pool pin and fit **MAX_LEN=170000
instead of 150000** (+13.3%) under the cap (a boot measurement, not yet wired into the
recommended config). Note this is a **local finding from the container's own int4
build**, not something the reference repo suggested — the repo's contribution was the
fp8 idea we rejected. The broader lesson is that low-bit tuning here is bounded by the
**sm86 int8/int4 path**, not the fp8 path the reference hardware measured.

## Setup and baselines

The reference stack is the [syv-ai/qwen38-27b-rtx3090](https://github.com/syv-ai/qwen38-27b-rtx3090)
container (vLLM 0.28.0, `dbirks/Qwen3.8-27B-W4A16-AutoRound` weights), on a 24 GB
RTX 3090 under a 22528 MiB usage cap. Two profiles are used throughout:

- `CTX=long` — fp8 KV, 4 chained MTP drafts, max len 150000, pool pinned at 5.4 GiB.
- `CTX=huge` — KVarN `kvarn_k4v2_g128` KV, 3 drafts, max len 250000, pool pinned at
  3.91 GiB.

Headline numbers these experiments compare against:

| Profile | prefill | decode | acceptance | VRAM |
| --- | --- | --- | --- | --- |
| CTX=long (fp8, 150k, 4 drafts) | 1124 t/s | 113 t/s | ~0.54 | 22289 MiB |
| CTX=huge (KVarN, 250k, 3 drafts) | 960 t/s | 86 t/s | ~0.58 | 22340 MiB |

Every result below is measured with the same protocol as the model page: timings read
from vLLM's own server metrics, single pass, recommended sampling, cold load, and the
first request after each boot discarded.

## Experiments

### 1. Prefix-cache retention interval (MTP first-turn re-prefill fix) — not needed on this build

- **Source:** the upstream repo's `KNOWN-ISSUES.md`; the reference workaround turned a
  266 s first follow-up turn into 14 s and 0 → 194,432 cached tokens on a 116K-class
  prompt.
- **What it was meant to fix:** with MTP, the draft cache lookup was reported to check
  one scheduler block below the single sparse Mamba checkpoint, so the first follow-up
  turn of every conversation re-prefilled in full. An earlier measurement on our
  container saw "prefix caching on but inert (`cached=0` on re-sends)" on `CTX=long`.
- **How it is exposed:** on vLLM 0.28.0 this is not a CLI flag but the env var
  `VLLM_PREFIX_CACHE_RETENTION_INTERVAL`, read by `vllm/envs.py` and validated in
  `vllm/v1/core/kv_cache_coordinator.py` (a positive multiple of the scheduler block
  size, printed at boot as "Setting attention block size to N tokens"). The reference
  repo's nightly (0.28.1rc1.dev) exposes it as a CLI flag instead. No rebuild needed
  either way.
- **Result:** the current image already caches MTP follow-up turns correctly on both
  profiles — the retention var is a **no-op** here. Re-sending the same 139,686-token
  prompt:

  | Profile | block size | send 1 (cold) | send 2 (re-send) | cached | TTFT |
  | --- | --- | --- | --- | --- | --- |
  | CTX=long (fp8, 4 drafts) baseline | 848 | 139686 tok / 230.4 s = 606 t/s | 1462 tok / 2.81 s = 49,685 t/s | 138,224 | 230.4 s → 3.1 s |
  | CTX=long + `…RETENTION_INTERVAL=848` | 848 | 139686 tok / 229.9 s = 608 t/s | 1462 tok / 2.82 s = 49,456 t/s | 138,224 | 230.2 s → 3.1 s |
  | CTX=huge (KVarN, 3 drafts) baseline | 2048 | 139686 tok / 180.7 s = 773 t/s | 422 tok / 1.14 s = 122,304 t/s | 139,264 | 181.2 s → 1.6 s |
  | CTX=huge + `…RETENTION_INTERVAL=2048` | 2048 | 139686 tok / 178.6 s = 782 t/s | 422 tok / 1.14 s = 122,177 t/s | 139,264 | 179.1 s → 1.5 s |

  `vllm:prefix_cache_hits_total` = 2 × 138,224 and
  `vllm:prompt_tokens_cached_total` = 276,448 on CTX=long confirm the re-send is a
  genuine cache hit, not a formatting artifact. Setting the var left block size, pool
  size (150,769 / 259,057), VRAM (21,105 / 21,515 MiB) and all timings unchanged; the
  var was verified to reach the vLLM process.
- **Verdict:** does not transfer as a *fix* because the fix is already present in this
  image — the earlier `cached=0` note is stale. Do **not** add the env var to the
  best-config blocks (it costs nothing but is redundant). Re-verify the `cached=0`
  premise against the current image before citing it elsewhere.

### 2. lm_head / MTP-drafter weight quantization — fp8 does not transfer; int4 is what already ships

- **Source:** the reference repo's `scripts/checkpoint-quant-surgery/`; its results were
  fp8 lm_head → +22.2% KV pool, + fp8 drafter → +29.3% combined, +6-12% decode,
  ~+0.05% WikiText-2 ppl. Those were measured on an Intel B70 (XPU, **native fp8**).
- **The fp8 premise does not carry to this rig.** The 3090 is sm86, which has no native
  fp8 *weight* path; its low-precision compute is int8 tensor cores. The 27B container
  reflects this: it deliberately ships **int8** lm_head/embed/MTP for the base
  checkpoint and an **int4-GPTQ** fast/single-user variant, and mentions fp8 only for
  the KV cache (FlashInfer). Re-running the fp8 surgery here would only dequantize
  fp8→bf16 at load and give up the memory-bandwidth win that *is* the entire result. So
  the experiment was reframed to the question that actually applies: **is the shipped
  head/drafter quantization the right one?**
- **Measured** on the CTX=long protocol (5.4 GiB pin, MAX_LEN 150000, 4 drafts;
  short = C#+React averaged, 512 gen; long = cold 139,686-token prefill). The base dir
  (int8 head/embed/MTP) vs the fast dir (int4-GPTQ head/embed/MTP + 40k draft head);
  both already carry the 40k-token draft vocabulary:

  | checkpoint (head / drafter) | model load | steady VRAM vs cap | pool | short decode | acceptance |
  | --- | --- | --- | --- | --- | --- |
  | int8 head+embed+MTP | 14.86 GiB | **22,797 MiB — OVER 22,528 cap** | 150,769 | 103.5 | 0.48-0.51 |
  | int4 fast head+embed+MTP | 13.97 GiB | **21,835 MiB — fits** | 150,769 | 110.0 | 0.51-0.53 |
  | int4 fast, 6.5 GB pin | 13.97 GiB | 22,215 MiB — fits | **170,776** | 111.7 | 0.48-0.56 |

  The pin is fixed KV bytes, so bit-width does not change the pool at a fixed pin — it
  changes the **free memory**. The int8 build load is ~0.9 GiB heavier and lands
  269 MiB **over** the cap at CTX=long; the int4 build fits with room to spend, and that
  room converts to context: raising the pin to 6.5 GB (engine clamped to 6.05 GiB free)
  fits **MAX_LEN=170000 / pool 170,776** under the cap — **+13.3% context (150k→170k)**
  versus the int8-limited baseline. A 180k attempt refused (needs 6.35 GiB, only
  6.05 available; est. max 171,296).
- **Drafter-only knobs** (the container's `prepare/quant_mtp.py`): `--bits 4` and
  `--keep-fc`. The `--keep-fc` option (leave `mtp.fc` in BF16, the exclusion Qwen's own
  FP8 export and NVIDIA ModelOpt both make) is only meaningful on top of a
  *smaller-than-shipped* scheme — the shipped build already quantizes `mtp.fc` to the
  same width as the rest of the drafter, and int8 is already over the cap, so an
  int8+keep-fc build is strictly larger still. No variant of the int8 family fits the
  cap at CTX=long, so these were not promoted to boots.
- **Verdict:** keep the shipped **int4 fast** head/embed/MTP quantization as the
  CTX=long default — it is not merely faster, it is the *only* one of the two that fits
  the 22,528 MiB cap, and it is what unlocks 170k context. Do not run the fp8 surgery on
  this hardware. The determinant is the sm86 int8/int4 path, not the fp8 path the
  reference measured.

### 3. int8 Marlin activation stack (`INT8_ACT` / `INT8_LAYERS` / `PREFILL_ATTN`) — works (prefill), adopt `INT8_ACT=int8`

- **Source:** the container repo (its batch launcher defaults to `INT8_ACT=int8`,
  `INT8_LAYERS=mlp`); not tested in the reference repo, which quantized KV/lm_head/
  drafter, not Marlin GEMM inputs.
- **Why it should help:** prefill is compute-bound at every batch size; the W4A8 Marlin
  path (weights int4, activations int8 per token, int8 tensor cores) is 4x the MMA rate.
  Decode-side it buys nothing at batch 1.
- **Result on the MTP `CTX=long` baseline** (short = C#+React averaged at 512 gen;
  long = cold 139,686-token prefill; timings from server metrics):

  | Cell | short prefill t/s | short decode t/s | 140k prefill t/s | VRAM |
  | --- | --- | --- | --- | --- |
  | (a) baseline W4A16 | 1,095 | 113.0 | 699 | 21,113 MiB |
  | (b) `INT8_ACT=int8` (all linears) | **2,006** (+83%) | 102.5 (−9%) | **973** (+39%) | 21,517 MiB |
  | (c) `INT8_ACT=int8 INT8_LAYERS=mlp` | 1,615 (+48%) | 102.2 (−10%) | 878 (+26%) | 21,285 MiB |
  | (d) (c) + `PREFILL_ATTN=int8` | 1,605 | 105.4 | 873 | 21,285 MiB |

  Output stayed coherent in every cell; acceptance held (~0.50-0.57 short).
- **Verdict:** adopt **`INT8_ACT=int8`** — the full default layer set is the biggest
  prefill win (+83% short, +39% at 140k) and the same as `mlp` on quality trade. Unlike
  the reference dflash2 numbers, decode here costs ~9-10% (not "unchanged"); on an MTP
  stack the W4A8 GEMM slightly slows the batch-1 decode path while massively speeding
  prefill. `PREFILL_ATTN=int8` adds nothing measurable on top (within noise on both
  short and 140k) — leave it off.
- **Caveat:** `INT8_LAYERS` must be `mlp` or the full default; the container's own docs
  note `mlp|linear_attn` crashes (inductor codegen bug). Also note the container's
  caveat that the added-token peak may need the pool pin (`EXTRA_ARGS
  --kv-cache-memory`) to boot — our first cell failed without it.

### 4. KVarN `g64` / `k4v4` tile variants — no gain, do not adopt

Tested on CTX=huge with the pool pinned at the same 3.91 GiB as the baseline; each
variant overrides `--kv-cache-dtype`/`--block-size` via `EXTRA_ARGS`, MAX_LEN lowered
only where the pinned pool cannot fit the standard 250000. Coding prompts C#+React,
+512 gen (temperature 1.0 / top_p 0.95 / top_k 20), first request discarded.

| variant | MAX_LEN | block | pool tokens | short prefill | short decode | 140k prefill | acceptance | VRAM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `kvarn_k4v2_g128` (baseline) | 250000 | 2048 | 259,057 | 822 | 93.0 | 791 | ~0.58 | 22,071 MiB |
| `kvarn_k4v4_g128` | 195000 | 1664 | 197,932 | 823 | 94.6 | 771 | ~0.59 | 21,941 MiB |
| `kvarn_k4v2_g64` | 240000 | 1920 | 246,857 | 830 | 97.2 | 814 | ~0.62 | 21,635 MiB |
| `kvarn_k4v4_g64` | 188000 | 1536 | 190,724 | 839 | 91.1 | 787 | ~0.55 | 21,593 MiB |

- **Pool:** every variant costs KV capacity because each deviates from the tuned
  k4v2_g128 layout. `k4v4` stores 4-bit *values* (2x the V bytes) so it loses the most —
  24-26% fewer tokens, forcing MAX_LEN down (k4v4_g128 would not boot at 250000; the
  pinned pool only fits ~192-200k). `g64` doubles per-tile scale overhead for a smaller
  ~5% loss.
- **Speed:** all four are within run noise of each other on short prefill/decode and
  140k cold prefill. The k4v2_g64 row posts the best-looking numbers (97.2 decode, 814
  prefill) but the spread across repeated baseline runs is comparable, so this is not a
  real ranking.
- **Acceptance:** `k4v4` does **not** recover MTP acceptance here either — the
  reference's tiny-context hint does not hold at scale; all rows sit at the baseline
  ~0.55-0.62.
- **Verdict:** keep `kvarn_k4v2_g128` at 128. No variant buys speed or acceptance, and
  every one trades away usable context. The bit-width/group knobs are technically
  parameterised but the default tile is the only one worth serving.

### 5. Smaller knobs — most are no-ops at this power cap

Tested on the CTX=long MTP baseline (fp8 KV, 4 drafts, 5.4 GiB pinned pool,
`MAX_LEN=150000`); coding prompts C#+React, +512 gen, temperature 1.0 / top_p 0.95 /
top_k 20, first request discarded after each boot.

**`--max-num-batched-tokens`** (launcher hardcodes 2048; passable via `EXTRA_ARGS`):

| value | boots? | short prefill | short decode | 140k prefill | pool |
| --- | --- | --- | --- | --- | --- |
| 2048 (default) | yes | 1,095 | 113.0 | 699 | 150,769 |
| 4096 | yes | 1,107 | 110.9 | 697 | 150,769 |
| 8192 | yes, but dies at first long prefill | 1,117 | 110.5 | — (OOM) | 150,769 |

The container's engine-initialisation claim ("4096 and 8192 do not boot") does not
reproduce: both come up and reach `/health`, at the identical 150,769-token pool. What
is true is that **8192 cannot serve a 140k prefill** — the first long request OOMs the
engine (`torch.OutOfMemoryError` in the GDN chunk kernel, 90 MiB shy of the transient
floor) because the larger chunk inflates the activation peak the pool does not leave
room for. 4096 is neutral on the short prompts and the 140k cold prefill (within run
noise), so there is no reason to move off 2048; keep the default.

**MTP acceptance tuning** (all at 2048, same protocol):

| knob | short decode | acceptance | note |
| --- | --- | --- | --- |
| baseline | 110.9 | ~0.527 | `DRAFT_SAMPLE=probabilistic` (default) |
| `DRAFT_SAMPLE=greedy` | 107.8 | 0.479 | ~3% slower, lower acceptance — as documented |
| `VLLM_DRAFT_TEMP_SCALE=0.8` | 106.4 | ~0.497 | sharpening the draft hurts |
| `VLLM_DRAFT_TEMP_SCALE=1.2` | 112.7 | ~0.544 | within noise of baseline; no gain |
| `VLLM_DRAFT_TOPK_TOPP=0` | 110.3 | ~0.503 | disabling truncation: baseline in repeat, and one run emitted garbage tool-call tokens — no gain, occasional correctness hazard |

None beat the defaults. `greedy` drafts are slower at temperature > 0 exactly as the
sampler patch documents; `VLLM_DRAFT_TEMP_SCALE` was already reported as no-gain in the
patch itself, and this reproduces it. `VLLM_DRAFT_TOPK_TOPP=0` is the only setting that
ever posted a faster number (140 t/s on one run) — that run also produced a broken
tool-call instead of the answer, and the repeat landed back on baseline, so it is noise
plus a quality hazard. **Do not change any of these.**

`int4_per_token_head` KV @256k (`alternative.sh`): experimental, only for the
dflash2/off paths — low priority since DFlash2 is retired. Not tested.

## Not applicable on CUDA / rejected

- All `KVARN_FA_*`, `KVARN_DECODE_CONFIG`, `KVARN_FUSED_*`, grf_mode and XPU-graph
  knobs — Intel XPU kernel-routing fixes, no CUDA equivalent needed.
- Context extension via `--hf-overrides max_position_embeddings` +
  `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` — the 250k ceiling here is VRAM, not RoPE.
- `turboquant_4bit_nc` (chunked-prefill scratch OOMs), CPU offload, DSpark drafter,
  `VLLM_MARLIN_TUNE` (no win at 250 W), int4 lm_head (rejected for quality on the
  reference hardware).

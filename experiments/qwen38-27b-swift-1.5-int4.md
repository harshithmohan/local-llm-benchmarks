# Qwen3.8-27B on an RTX 3090: porting the Swift-1.5-INT4 fine-tune onto the vLLM stack

Port study: bringing the [Swift-1.5-Qwen3.8-27b-INT4](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b-INT4) fine-tune (LLM Compressor AWQ+GPTQ, compressed-tensors) onto the same [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) serving stack used for the base checkpoint, and recording which step of the port is load-bearing.

This is a companion to [models/rig2-3090/swift-qwen38-27b.md](../models/rig2-3090/swift-qwen38-27b.md): the model page carries the measured Swift configs and headline numbers, this page carries the porting procedure, the checkpoint-level boot blocker hit on the way, and the pre-benchmark sanity checks. It is kept in-repo because the findings (which exports are portable, which config entries block a boot, how the heads/drafter are requantized) apply to any same-arch fine-tune dropped onto this stack, not just Swift-1.5.

## TL;DR

The **INT4 (LLM Compressor GPTQ) export ports cleanly**; its AutoRound sibling does not. One checkpoint-level issue had to be fixed before the engine would boot, and it lives in the model directory rather than in any launch knob:

1. **The export's ignore list blacklists the entire MTP head.** Swift-1.5 ships its MTP module as BF16 and declares `re:^mtp.*` in `quantization_config.ignore`. The prepare pipeline requantizes that head to int8 in place, so the ignore entry then makes vLLM build an *unquantized* drafter embedding and fail at load with `no parameter named 'embed_tokens.weight_packed' in Qwen3_5MultiTokenPredictor`. Removing that single ignore entry is the fix. The pipeline already strips exact-name ignores (`mtp.fc`, the seven `mtp.layers.0.*` linears) but not a blanket regex.

After that, both profiles boot and serve (fp8 at 150000, KVarN at 250000), MTP speculative decoding is active with the rebuilt draft head, and the fine-tune tracks the base quant closely — the measured rows are on the model page. The port is a checkpoint-preparation exercise, not an engine-tuning one: no launch flag changed.

The one step the port left out was **head precision**: the heads were requantized to int8 and stopped there, which is what kept the fp8 profile over the rig's VRAM budget. Experiment 6 runs the calibration pass that takes them to the int4-GPTQ pair the base build uses, and that requantized directory (`Swift-1.5-INT4-fast`) is the build both served profiles now point at.

## Setup

Same rig and stack as the model page: RTX 3090 under a 22528 MiB cap, the [syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) container (vLLM 0.29.0 for the port itself; the experiment-6 requantization and the current served rows are on vLLM 0.31.0), two profiles:

- `CTX=long` — fp8 KV, 4 chained MTP drafts, `MAX_LEN=150000`, pool pinned by bytes.
- `CTX=huge` — KVarN `kvarn_k4v2_g128` KV, 3 drafts, `MAX_LEN=250000`, pool pinned by bytes.

The base checkpoint, weights and requantization notes are on the [model page](../models/rig2-3090/qwen38-27b.md); this experiment only covers the fine-tune's own port.

## Experiments

### 1. Checkpoint triage — the INT4 export ports, the AutoRound export does not

ukisai publishes three Swift-1.5-27B exports. Two were examined:

| Export | Quantization | `config_groups` | Ports? |
| --- | --- | --- | --- |
| Swift-1.5-…-INT4 | LLM Compressor AWQ smoothing + GPTQ, compressed-tensors `pack-quantized`, W4A16 sym g128 actorder static | present (`group_0` Linear) | **yes** |
| Swift-1.5-…-W4A16-AutoRound | Intel AutoRound, `quant_method: auto-round`, packing `auto_round:auto_gptq` | **absent** | no |

The prepare pipeline's head requantizer deep-copies `config_groups.group_0` to clone the body scheme onto the heads; an AutoRound config has no `config_groups` at all, so the step has nothing to clone, and the AutoRound packing form is also outside the Marlin int8 patch stack the W4A16 path expects. The INT4 export is structurally the same shape as the base (`compressed-tensors` / `pack-quantized`, group-128 symmetric), so it drops into the same prepare + serve path. It was the one chosen; its own single-seed eval also led the three exports.

The export is a 5-shard body plus `model_mtp.safetensors` (the BF16 MTP head, one file, so the pipeline's one-shard assertion holds), and declares an FP8 static `kv_cache_scheme` (per-tensor scales for the full-attention layers). No `g_idx` tensors — the body is plain group-128. The prepare step adds `model_extra_tensors.safetensors` to carry the rebuilt draft head.

### 2. Head and drafter requantization

The export quantizes only `Linear` targets, so the LM head, token embedding and the MTP head ship BF16. The prepare pipeline requantizes them in place, writing the same `weight_packed`/`weight_scale`/`weight_shape` triples the base build uses:

- `lm_head` + `embed_tokens` → int8, group 128.
- MTP module → int8 (same treatment).
- A 40,960-token draft head is built from a draft-vocabulary id list counted over the fine-tune's own output distribution (`build_draft_vocab.py`), stored as packed int32 + fp16 scales in `model_extra_tensors.safetensors`, with the id map alongside as `mtp_draft_vocab_ids.pt`. That distribution is much narrower than the base model's, so its drafter is not shared with the AutoRound build.

The cloned head groups (`group_1` lm_head, `group_2` embed, `group_3` mtp) inherit `actorder: static` from the body group, but the written head tensors carry no `g_idx`, so `actorder` is reset to `null` on those three groups — matching the base config.

This is the int8 form, which is where the port stopped. The base checkpoint serves an int4-GPTQ version of the same three heads; the fine-tune keeps 953 MB more head weight because of it, and that difference is the difference between fitting the rig's VRAM cap and not. Experiment 6 is that step.

### 3. The unquantized-MTP ignore trap (boot blocker)

The export's `quantization_config.ignore` contains a single entry the base config does not: **`re:^mtp.*`**. It is correct for the *shipped* checkpoint (upstream's MTP head is BF16 and ignored), and wrong the moment the prepare pipeline requantizes that head.

vLLM resolves a quant method per module prefix. With the blanket ignore in place, `get_scheme_dict("mtp.embed_tokens")` returns `None`, the drafter's `embed_tokens` is built as an unquantized `VocabParallelEmbedding`, and the load then fails because the checkpoint ships packed weights:

```
ValueError: There is no module or parameter named 'embed_tokens.weight_packed' in
Qwen3_5MultiTokenPredictor. The available parameters belonging to embed_tokens
(VocabParallelEmbedding) are: {'embed_tokens.weight'}
```

The failure surfaces only at the *drafter* load (after the main model loads fine), which makes it look like a code/patch problem rather than a config one. It is the config: the `re:^mtp.*` entry must be deleted for a requantized MTP head. The pipeline's own ignore cleanup removes exact names (`mtp.fc` and the seven `mtp.layers.0.*` projections) but does not match this regex, so it survives the prepare step and the fix is a one-line config edit.

    # before
    "ignore": [ ..., "re:^mtp.*" ]
    # after (requantized MTP head)
    "ignore": [ ... ]

### 4. Verification and boot validation

`verify.sh --no-server` passes on the prepared directory — all model checks, including head-requant geometry, the draft head, the safetensors shard count, and no tensor duplicated across shards. Both serve profiles then boot and serve: fp8 at 150000 and KVarN at 250000. The `CTX=huge` boot also answers the one open question about the export's declared `kv_cache_scheme`: KVarN selects its own 4/2-bit layout and does **not** object to the checkpoint advertising an FP8 static KV scheme, so no config change was needed there; the fp8 profile is the one that matches the export's native scheme.

MTP speculative decoding is active on both profiles with the rebuilt draft head, and math-reasoning and code prompts returned correct, well-formed answers. The timed rows (which also carry the later `INT8_ACT=int8` change) are on the model page.

### 5. Post-measurement config change

Both Swift profiles were later updated to serve `INT8_ACT=int8`, the int8 Marlin activation stack adopted from the [Arc-repo transfer study](qwen38-27b-da3dsoul-arc-transfer.md). The model-page rows already include it; the env blocks there are the ones to copy. It does not change the port, but it does change the served config, so it is noted here for provenance.

### 6. Head precision — the int4 fast head, the step the port skipped

The base checkpoint's servable build is its **`-fast` variant**: an int4-GPTQ `lm_head` and an int4 MTP module. The fine-tune's port took the same three components to **int8** and stopped there (experiment 2). That choice is what kept it out of the rig's 22528 MiB budget until this step:

| Component | Fine-tune, as ported | Base `-fast` | Delta |
| --- | --- | --- | --- |
| `lm_head` (own shard) | int8, 1291.3 MB | int4, 655.6 MB | −635.7 MB |
| MTP module (`mtp.fc`, 7 linears, norms) | int8, 431.4 MB | int4, 219.0 MB | −212.4 MB |
| Draft head (`model_extra_tensors`) | int8, 213.0 MB | int4, 108.1 MB | −104.9 MB |
| **Total** | **1935.7 MB** | **982.7 MB** | **−953.0 MB** |

Those weights are resident, so the whole difference lands in peak VRAM, and the build as ported did exceed the rig's cap: the fp8 profile peaked at 22988 MiB against the 22528 MiB budget (~460 MiB over) and the KVarN profile at 22656 MiB (~128 MiB over). The head bytes are engine-independent - the same footprints reproduce on the older vLLM pin - so the overage was a property of the build, not of the engine version.

The int8 heads are not an export defect. The fine-tune ships `lm_head`, `embed_tokens` and the MTP module in BF16, and the port's requantizer is what picks a precision. int8 is the data-free choice; the base's `-fast` gets int4 out of a GPTQ calibration pass over the model's own hidden states, and the fine-tune has to be put through the same pass. That is the self-distillation calibration chain, run against the fine-tune itself:

    # prompt set (chat, code, Danish instruction + reasoning, math) -> data/prompts.jsonl
    python drafter/collect_prompts.py            # 6765 prompts, 3123 of them thinking
    # the model's own outputs over those prompts -> data/gen.jsonl
    MODEL=<models>/Swift-1.5-INT4 python drafter/gen_data.py --limit 1500
    # final-RMSNorm hidden states for every generated token -> data/hidden.npy
    MODEL=<models>/Swift-1.5-INT4 python drafter/capture.py --limit 1500
    # MTP Hessians over the held-out split -> runs/h1/mtp_hessians.pt
    MODEL=<models>/Swift-1.5-INT4 python drafter/train_mtp.py --out <models>/Swift-1.5-INT4 \
        --eval-only 1 --dump-hessians runs/h1/mtp_hessians.pt
    # int4 GPTQ lm_head into a variant dir (other shards hardlinked), calibrated on those rows
    python drafter/gptq_lm_head.py <models>/Swift-1.5-INT4 <models>/Swift-1.5-INT4-fast \
        --bits 4 --calib-rows 300000
    # the draft head *is* 40,960 lm_head rows - re-cut it from the requantized head
    python prepare/build_draft_vocab.py <models>/Swift-1.5-INT4-fast \
        --ids prepare/draft_vocab_ids.json

The 1500 prompts produced 1,074,828 tokens in 28 minutes, and 1,470,750 hidden rows. The calibration also reports the head's own damage: GPTQ int4 holds KL 0.0026 to the BF16 head where round-to-nearest int4 gives 0.0060 - the same protocol that put the base build's int4 head at 0.0029. The `train_mtp.py` pass records the acceptance baseline the rebuilt draft head has to hold: 0.824 at draft depth 1, 1.74 tokens per step.

The MTP module is the one component still at int8: the requantizer that takes it to int4 (`requant_mtp_gptq.py`) reads it from `model_extra_tensors.safetensors`, where the base keeps it, while this checkpoint gives it its own `model_mtp.safetensors` - and the int8 module costs no acceptance (`prepare/quant_mtp.py`). It is ~212 MB of the table's 953 MB, and both profiles sit inside the budget without it.

Both profiles were then re-measured on the requantized build, cold, with prefix caching off:

| Profile | As ported (int8 heads) | Requantized (int4 heads) | Peak VRAM |
| --- | --- | --- | --- |
| 150000 fp8, 4 drafts | 2438 / 114.0 | 2460 / **121.0** | 22988 -> 22188 MiB |
| 250000 KVarN k4v2, 3 drafts | 2385 / 97.9 | 2377 / **102.7** | 22656 -> 21918 MiB |

Prefill is unchanged, decode reads ~5% higher at 10k and at ~120K (less head weight read per step), and acceptance is level on the fp8 profile and a few points higher on the KVarN one. The served profiles point at the requantized directory, so the model page's rows are the int4 build.

Experiment 2 is the record of what the port did at the time; this is the step it left out, and the reason the fine-tune carried ~950 MB more head weight than the base build it is measured against - ~740 MB of it recoverable without touching the body or the KV cache.

## Not applicable / rejected

- **Intel AutoRound Swift-1.5 export** — no `config_groups` for the head requantizer to clone, and `auto_round:auto_gptq` packing is outside the Marlin W4A16 patch stack. Rejected at triage (see experiment 1).
- **The export's FP8 `kv_cache_scheme`** — left in place. The fp8 profile matches it natively and the KVarN profile overrides it without complaint, so there was no reason to strip it. (The base checkpoint ships `kv_cache_scheme: null`; that is a difference, not a problem.)

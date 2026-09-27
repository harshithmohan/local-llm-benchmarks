# Qwen3.8-27B (Rig 1) - best configs

Dense 27B from the Qwen3.8 family (arch `qwen35`): hybrid SSM + attention, only every
4th layer full attention (`full_attention_interval=4`), embedded MTP head. Not a MoE,
so there is no expert split (`--n-cpu-moe` / `-ncmoe` do not apply) and the Codacus-fork
expert cache has nothing to cache. Native context 262144. Model card:
[ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF)
(Swift-1.5 fine-tune). Methodology in [methodology](../../methodology.md);
model-specific issues in [issues](../../issues.md).

Quants tested: `IQ2_XS` of the **Swift-1.5 fine-tune** ([ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF), 2-bit) - the only quant on this rig. `IQ2_XS` on its own only names the quant format: every file measured here is the Swift-1.5 fine-tune, not the base model.

## Measured results at c 90000 (llama-server, coding prompts C#+React averaged, second-pass, + 512 gen, q4_0 KV, stock v0.5.0-dev 1ab7e5ad)

| Quant | MTP | prefill t/s | decode t/s | acceptance | VRAM used |
| --- | --- | --- | --- | --- | --- |
| IQ2_XS | on | 300.1 | **32.9** | 0.62 | 11707 MiB |

All rows use the current protocol: coding prompts (C# ~192 tokens, React ~155 tokens)
averaged, second-pass measurement (the first pass warms the mmap page cache and is
discarded; the measured pass carries a prompt nonce so it re-prefills instead of reusing
the slot's KV prefix), MTP n-max 2, q4_0 KV, cold load, stock binary. Requests carry
prompt + `max_tokens` only: sampling is decided by the served config, never overridden
per request ([methodology.md](../../methodology.md)). Prefill on these short prompts is
batch-bound - compare across pages only within the same prompt size.

Reading:

- 90000 is the largest context that fits the 12 GB cap at q4_0 KV; the model's native
  262144 window is out of reach on this GPU.
- Per-prompt: C# 315.3 / 32.2 (acceptance 0.599), React 284.8 / 33.5 (acceptance 0.641).

## Best config per quant

### IQ2_XS (Swift-1.5 fine-tune) - winner (only quant on this rig)

Stock binary + MTP, q4_0 KV at c 90000:

    llama-server -m <models>/Swift-1.5-Qwen3.8-27B-GSQ-RCO-IQ2_XS.gguf \
      --ctx-size 90000 -ngl 999 \
      --cache-type-k q4_0 --cache-type-v q4_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads 12 --parallel 1 \
      --spec-type draft-mtp --spec-draft-n-max 2 \
      --cache-type-k-draft q8_0 --cache-type-v-draft q8_0 \
      --reasoning-preserve

-> 32.9 t/s decode @ 90000 (prefill 300.1 short-prompt, acceptance 0.62), 11707 MiB.

## Alternatives (archived)

None - only one quant (`IQ2_XS`) tested on this rig; no config ladder measured yet.

## Messy-code refactor benchmark (real-task ~60K prompt, not yet run)

Not yet run on this rig (see [test-prompts.md](../../test-prompts.md) for the prompt and
its single-pass protocol).

## Key arch notes

- Hybrid SSM + attention: only ~16 of 65 layers own a growing KV cache
  (`full_attention_interval=4`), so context is cheaper than on a same-size dense
  transformer and the SSM state is constant-size. q4_0 KV is used to reach the context
  that fits the 12 GB cap.
- Embedded MTP (`nextn_predict_layers=1`): no separate draft model needed; the draft KV
  is q8_0. Observed acceptance on the coding prompts is ~0.60-0.64.
- Dense 27B: every token runs all ~27B parameters, so decode is bounded by weight
  bandwidth - unlike the 35B-A3B MoE, there is no active-parameter discount.

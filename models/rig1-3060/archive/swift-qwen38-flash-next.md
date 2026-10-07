# Swift-1.5-Qwen3.8-Flash-Next (Rig 1) - experiment archive

The Swift-1.5 fine-tune of Qwen3.8-Flash-Next, first benchmarked 2026-10-08 on the Strata pack
engine - the same engine that serves the base model's Q2_0. Everything here was measured on
one rig under one engine; there are no llama.cpp rows for this checkpoint.

Main card: [swift-qwen38-flash-next.md](../swift-qwen38-flash-next.md). Base model:
[qwen38-flash-next.md](../qwen38-flash-next.md) and its
[archive](qwen38-flash-next.md).
Methodology: [methodology.md](../../../methodology.md); issues: [issues.md](../../../issues.md).

Quants:

- `GSQ-RCO IQ2_XS` (68.1 GB, 2 shards: 39.8 GB + 28.4 GB, the per-layer embedding table in
  shard 1)

## Setup

- Engine: [Strata](https://github.com/Niko1221/Strata) 0.1.40.2, the standalone pack engine
  ([engine-notes/strata.md](../../../engine-notes/strata.md)) - not a `llama-server` build.
- Pack: built for this checkpoint alone; the base model's `--base` reuse is refused, because it
  needs every tensor in shard 1 and this split breaks at layer 13.
- Config: 200000 context, `--kv int8`, `--expert-cache auto`, `--prefill 6144`,
  `--prompt-cache-every 6144`, MTP `--spec 4 --spec-min-p 0.5`.
- Protocol: Strata's own `/v1/chat/completions` (a chat template is always applied), with
  `--prompt-cache 0` in the engine args for every measurement pass; recorded pass is the second
  after one cold load; VRAM is the per-process engine allocation.
- Prompts: the ~10k opencode session-context prompt, then the generated ~60K / ~120K
  long-context refactor prompts ([test-prompts.md](../../../test-prompts.md)).

## The shard layout is not the base model's

The checkpoint ships as two shards whose files raise an obvious question - the split is not
where the base model's is. Per-shard GGUF headers:

| | Swift shard 1 | Swift shard 2 | Base Q2_0 shard 1 | Base Q2_0 shard 2 |
| --- | --- | --- | --- | --- |
| `split.no` | 0 | 1 | 0 | 1 |
| tensors | 342 | 882 | 1223 | 1 |
| tensor bytes | 39,777,505,536 | 28,363,637,504 | 37,613,062,656 | 28,800,138,240 |
| blocks | layers 0-13 | layers 13-47 | layers 0-47 | - |
| non-block tensors | output head, hyper-connections, token embedding, per-layer embedding table | none | same minus the table | per-layer embedding table only |

So the numbering is right - each file's `split.no` matches its name, and the architecture
metadata sits in shard 1 - but the *boundary* is different: Swift 1.5 carries the 28.8 GB
per-layer embedding table in shard 1 and breaks at layer 13, where the base model keeps all 48
layers in shard 1 and puts the table alone in shard 2. Layer 13 straddles the two: shard 1
holds its `attn_gate`/`attn_qkv`, shard 2 the other 23 tensors of that layer (all
`ffn_*_exps`, `ffn_*_shexp`, `hc_*`, `ssm_*`). That is an attention-vs-MoE cut, not expert rows
split across shards, so it does not hit the expert-split limitation that keeps Swift's `Q2_0`
out of the supported sizes.

The practical consequence is `--ple-gguf`, which the engine resolves by finding
`per_layer_token_embd.weight` among the shards beside `--native`: shard 2 for the base model
and Unsloth's `UD-Q4_K_XL`, **shard 1 for Swift**. The official Strata inspector on the folder
agrees with the header table (exit 0, "this is setup's `--family swift --model IQ2_XS`") and
summarizes the checkpoint: 68.14 GB, 176.94 B weights, 3.08 bits/weight overall; routed experts
120.80 B / 35.45 GB / 2.35 bpw (IQ2_S 52%, Q2_0 32%, IQ2_XXS 13%, IQ1_M 3%); per-layer
embedding table 51.23 B / 28.87 GB / 4.51 bpw (IQ4_NL).

## Pack

`tools/iq_pack.py --gguf <shard1> --out <pack>`, no `--base`. What it reported:

- `index.txt`: 1079 tensors, 302 served natively, 0 in `extra.bin`, arena 1.43 GiB.
- `conversions.json`: 96 tensors converted to the engine's form (96 exact, 0 rounded;
  max |err| 0).
- tokenizer: 248320 vocab, 247587 merges, `pre` qwen35, eos 248046 / pad 248044 / bos 248044.
- `native_experts.txt`: 512 experts, 35,454,976,000 bytes of expert rows; layers 0-12 point at
  shard 1 (no shard column) and layers 13-47 at shard 2.

The per-layer embedding table is never part of a pack (`per_layer_token_embd.weight` is on the
tool's not-in-pack list) and is read from the GGUF shard given to `--ple-gguf`.

## First reply

Cold load: experts 33.02 GiB at 3.25 GiB/s, expert cache 2590 slots / 3.49 GiB of VRAM
(1,510,400 B per expert blob), 476 MiB of VRAM free with everything loaded, per-process VRAM
11,360 MiB. A one-sentence question returned `finish_reason: stop` with a reply in
`reasoning_content` plus `content`, 65 prompt / 60 completion tokens, a complete `timings`
block (`cache_n` 0, draft 42 accepted of 37 - the MTP head of the base model drafts this
checkpoint correctly).

## The 10k prompt ends on a tool call, not on the limit

| pass | prefill t/s | decode t/s | `cache_n` | `predicted_n` | finish |
| --- | --- | --- | --- | --- | --- |
| 1 | 961.9 | 46.9 | 0 | 344 | `tool_calls` |
| 2 | 1003.5 | 46.5 | 0 | 305 | `tool_calls` |

Both passes stop around 300-350 tokens with `content` null and a handful of
`grep`/`read`/`glob` tool calls, e.g. a `grep` for `react-window`/`@tanstack/react-virtual`
against a project path that only exists inside the prompt's story. The reasoning tail says it
is about to search the codebase - it is imitating the tool-call format the 10k prompt itself
documents. Suppression did not work: `tool_choice: "none"` still returned `tool_calls` (312
predicted, 1007.9 prefill, 44.7 decode, 111 characters of content, 3 calls), and an empty
`tools` array still returned `tool_calls` (324 predicted, 1004.4 prefill, 45.2 decode, 0
characters, 3 calls).

The base model's 200000 config on the identical payload, in contrast, ends at
`finish_reason: length` with `predicted_n` 512 (960.7 prefill / 41.3 decode, `content` empty,
no tool calls): it spends the whole window inside `reasoning_content`. The early stop is
therefore a property of this fine-tune, and the accepted reading is that the 10k row's decode
covers ~305 tokens rather than the full window. The generated long-context prompts do not
trigger it - 60K and 120K both reach 512.

## The prompt chunk: `auto` lands on 5632, the served config pins 6144

Engine-reported chunk lines and the cache slots the prompt path borrows (2590-slot cache):

| `--prefill` | engine line | loan |
| --- | --- | --- |
| 8192 | `prompt chunk 8192 -> 4096 tokens so its buffers fit in every expert cache` | 1811 slots (2.43 GiB) |
| `auto` | `prompt chunk auto: 5632 tokens, a 351-slot ring` | 2260 slots (3.04 GiB) |
| 6144 | (no clamp) | 2454 slots (3.30 GiB) |

`auto` stops at 5632 because it only takes a chunk whose buffers stay inside 90% of the
resident cache (2260/2590 = 87%); an explicit chunk skips that rule and only has to fit, which
is how 6144 lands at 95%. 8192 does not fit at all, and the halving rule tests 4096 next, so
6144 is reachable only as an explicit pin. Paired runs, same server, same prompts, recorded
pass second:

| prompt | 5632 prefill / decode | 6144 prefill / decode | prefill delta |
| --- | --- | --- | --- |
| ~10k | 942.3, 997.8 / 45.3, 47.9 | 961.9, 1003.5 / 46.9, 46.5 | +1.3% on the pass means |
| ~60K | 980.1, 976.6 / 42.4, 41.9 | 993.3, 994.4 / 41.5, 40.6 | +1.6% |
| ~120K | 948.4, 942.1 / 41.7, 46.3 | 961.0, 956.4 / 40.7, 42.7 | +1.4% |

Both 6144 passes beat both 5632 passes at every length, so the ~1.5% is the boundary count
(9.7 chunks against 10.6 at 60K, 19.4 against 21.2 at 120K) rather than run noise. Decode is
unaffected - the loan is a prompt-path ring, and decode gets the whole 2590-slot cache back in
both cases (it ran 41-48 t/s and hit 67-75% on both). The config therefore pins 6144 with
`--prompt-cache-every 6144`.

## Long-context rows

4802-token/59802-token/119344-token prompts, cold load, second pass, `--prompt-cache 0`:

| prompt | prefill t/s | decode t/s | `cache_n` | `predicted_n` | finish | decode hit rate |
| --- | --- | --- | --- | --- | --- | --- |
| ~60K pass 1 | 993.3 | 41.5 | 0 | 512 | `length` | 70.5% |
| ~60K pass 2 | 994.4 | 40.6 | 0 | 512 | `length` | 74.0% |
| ~120K pass 1 | 961.0 | 40.7 | 0 | 512 | `length` | 75.3% |
| ~120K pass 2 | 956.4 | 42.7 | 0 | 512 | `length` | 69.6% |

Every pass reported `0 checkpoints`, i.e. the prompt was genuinely re-read each time (`0 reused
+ all read`), and both large prompts serve as the stability check.

## Against the base model's Q2_0 at the same window

Both on Strata at 200000, `--kv int8`, MTP on, same prompts:

| prompt | Swift IQ2_XS | Base Q2_0 | delta |
| --- | --- | --- | --- |
| ~10k | 1004 / 46.5 | 1058 / 44.2 | -5.1% prefill |
| ~60K | 994 / 40.6 | 1045 / 42.4 | -4.9% |
| ~120K | 956 / 42.7 | 1008 / 41.8 | -5.2% |

The fine-tune reads prompts ~5% slower than the base model's Q2_0 under the same engine and
window. That is at odds with the engine project's own note that Swift 1.5's IQ2_XS measures
"the same speed as the original's", though that was a 32K greedy 256-token run on a different
card. The expert mix differs (this checkpoint is IQ2_S-heavy at 2.35 bpw over the routed
experts), and the 10k caret applies to the cell above but not to the two long prompts.

## Conclusions

- Swift-1.5-Qwen3.8-Flash-Next is supported by Strata at `IQ2_XS` and runs at 200000 on one
  12 GB card with the base model's MTP head, ~11000 MiB of VRAM and ~476 MiB free.
- The served shape is `--prefill 6144` + `--prompt-cache-every 6144`, with `--prefill auto`
  landing on 5632. Pinning 6144 costs nothing measurable in decode and buys ~1.5% prefill.
- Prefill is ~5% slower than the base model's Q2_0 on the same engine, window and prompts;
  decode is in the same band.
- The ~10k opencode prompt ends on a tool call at ~305-350 tokens for this fine-tune. It is a
  property of the prompt, not of the model: the generated ~60K and ~120K prompts reach the full
  512-token window.

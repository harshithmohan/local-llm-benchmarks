# Tuning methodology

How the recommended configs on the model pages were arrived at: which knobs to sweep, in what
order, and the rules that decide a winner. This is the tuning layer between two other pages -
measurement protocol (request shape, two-pass rule, VRAM, stability check) is in
[methodology.md](methodology.md), and the per-engine flag vocabularies are in
[engine-notes/](engine-notes/).

Scope: both rigs, every engine. Engine labels are per-row and results are not interchangeable
across engines. Representative sweeps live in the model pages and their `archive/<model>.md`
logs; this page only states the procedure and the rules.

## Sweep order

Some settings are fixed starting points, not knobs: q8_0 KV (q4_0 only if VRAM absolutely
forces it - see [KV cache type](#kv-cache-type)), full offload (`-ngl all`), `--threads` (12 on
Rig 1, 8 on Rig 2), and the model card's server-side sampling. Start there, then sweep - each
step constrains the next, and doing them out of order wastes cold loads:

1. **`-b`/`-ub`** - the prefill lever; find the largest ubatch that loads and serves.
2. **Expert-cache size** - the decode lever; raise it to the VRAM ceiling once `-ub` is fixed.
3. **MTP placement** - the draft head competes with cache slabs for the same VRAM.
4. **Feature/companion flags** - isolate each; keep only the free wins.
5. **Large-prompt stability check** - a passing health check is not proof of serviceability.

Then record the winning config and its cold-load numbers.

## Part A - common tuning parameters

These exist on every engine (flag names differ; see the equivalence table in Part B).

### Context size and YaRN rope scaling

- The native window comes from the GGUF. Whether it fits is decided by KV + compute buffer +
  expert-cache slabs together, never by one of them.
- KV is cheap on the hybrid/MoE architectures here: qwen35moe is ~10.6 KiB/token at q8_0
  (~2.7 GiB for 262144, ~5.3 GiB for 524288). On qwen4exp only the sparse-attention layers carry
  KV; on the dense hybrid-SSM family only the full-attention layers do - the rest hold fixed
  state.
- To extend past native, use YaRN: `--rope-scaling yarn --rope-scale N --yarn-orig-ctx 262144`,
  where `--rope-scale` **must equal ctx / 262144 exactly**. These GGUFs carry no YaRN metadata
  (partial rotary, `rope.freq_base` 10000000), so extension is CLI-only.
- Throughput is roughly flat from native up to the usable ceiling; only VRAM headroom falls.
- Ceiling per architecture (llama.cpp, q8_0 KV) - the binding limit differs by arch:

  | Arch (models) | Native | Usable ceiling | What binds |
  | --- | --- | --- | --- |
  | qwen35moe (Qwen3.6-35B-A3B, KAT-Coder) | 262144 | stock ~672-736K; fork 843776 (all-CPU); ik 851968 | KV + expert-cache slabs + compute |
  | qwen4exp (Qwen3.8-Flash-Next) | 262144 | ~96k with MTP; ~192k at cache 16 without | compute buffer, not KV |
  | dense hybrid SSM (Qwen3.8-27B, Swift-1.5) | 262144 | 155648 (q8_0) / ~98304 (f16) | KV on the ~16 full-attn layers |
  | gemma4 (Gemma4-26B) | 262144 | native fits | - |
  | Rig 1 dense (Swift-1.5-27B) | 262144 | 81920 | 12 GB VRAM; q4_0 KV needed |

### KV cache type

- **Always start at q8_0; this is not a swept knob.** q8_0 is throughput-neutral vs f16 and
  roughly halves KV, so it is the right default for every llama.cpp row here.
- **q4_0 only as a forced fallback** when the model + context genuinely cannot fit otherwise - it
  costs quality. It is what reaches 80k on the Rig 1 dense 27B under 12 GB, and is not used
  anywhere q8_0 fits.
- **f16 doubles KV** and roughly halves the ceiling; not used on these rigs.
- MTP draft KV is `q8_0` (`--cache-type-k-draft q8_0 --cache-type-v-draft q8_0`).
- vLLM uses fp8 or KVarN 4/2-bit KV pools instead (Part B).

### `-b` / `-ub` (batch / ubatch)

- `-ub` is the compute unit and **the prefill lever**; the compute arena is sized by
  `min(n_ctx, n_ubatch)`. `-b` above `-ub` only changes chunking/logical buffers and is inert
  for throughput.
- **Prefill scales with `-ub`; decode is ubatch-independent.** Sweep `-ub` up until it OOMs on
  load or on the first large request, then step back one.
- Raising `-ub` raises the compute buffer and **lowers the expert-cache ceiling** - the two
  compete for the same VRAM. The usual sequence is ubatch first (prefill), then cache (decode).
- Exception: **hybrid SSM+attention models (Rig 1 dense 27B) do not scale prefill with `-ub`** -
  the default `-b 2048 -ub 512` is the winner there.
- `-b/-ub 8192` has passed a health check then died on the first inference (qwen35moe fork), so
  treat it as an upper bound, not a setting.

### MTP / speculative decode

- Enabled with `--spec-type draft-mtp` (embedded head) or `-md/--model-draft` (separate file).
  Always pass the type flag: without it the embedded head is dead weight.
- `--spec-draft-n-max` is an **inverted-U**: 2 is the typical winner (1 and 3+ lose on one side
  or the other), and 3/4 can OOM. Each extra draft token costs ~150 MiB.
- `--spec-draft-p-min` (default 0.0) **buys acceptance, not speed**. Raising it lifts draft
  acceptance sharply but decode stays flat - the card rule is *judge by tok/s, not acceptance
  rate*.
- MTP is a **net loss at extended context** once the draft context evicts GPU expert layers or
  eats KV headroom; drop it there.
- On the moe-cache fork, the draft context's own ubatch can OOM after a passing health check even
  when the target `-ub` is fine - cap it with `--spec-draft-ubatch-size` (Part B).

## Part B - engine / fork-specific parameters

### llama.cpp - stock (and the flags shared with the moe-cache fork)

- `-b/--batch-size` default 2048, `-ub/--ubatch-size` default 512.
- `-fa/--flash-attn` default `auto`; `-lm/--load-mode` default `auto`; `-cram/--cache-ram` default
  8192 MiB; `--reasoning-preserve`.
- `-ncmoe/--n-cpu-moe N` keeps the first N layers' MoE weights on CPU; `-ngl all` offloads
  everything else.
- `--spec-type draft-mtp` with `--spec-draft-n-max` (default 3) / `--spec-draft-n-min`;
  `-md/--model-draft` for a separate head. Other types: `draft-simple`, `draft-eagle3`,
  `draft-dflash`, `draft-dspark`, `ngram-*`. The old `--draft`/`--draft-max` are removed.
- `--fit on` only adjusts *unset* args and picks a conservative `n_ctx` at the same decode - it
  is a sizer, not a tuner; forced off in these configs.

### moe-cache fork only

[GenerelSchwerz/llama.cpp](https://github.com/GenerelSchwerz/llama.cpp), branch `moe-cache`.
Adds a dynamic CUDA expert cache on top of stock; the flags below do not exist elsewhere.

- `--moe-expert-cache-size N` (slabs per expert tensor, per device) / `--moe-expert-cache-mib
  MiB` / `--moe-expert-cache-layers N[,N-M]`. Default 0 = off.
- While the cache is enabled it **overrides `--n-cpu-moe` placement** - tuning `-ncmoe` is the
  wrong axis on this fork.
- **A sub-routed-width cache is a net loss**: below ~32 slots the cache thrashes while cache-off
  keeps whole expert layers resident; it only pays from roughly the routed width upward. Raise it
  to the VRAM ceiling.
- Slot cost is quant-dependent (e.g. ~73 MiB/slot at Q4_K_M vs ~99 MiB/slot at Q6_K on the same
  arch); VRAM is roughly linear in slots.
- `--spec-draft-ubatch-size N` (env `LLAMA_ARG_SPEC_DRAFT_UBATCH`; default 0 inherits the target
  `-ub`) - the fix for the draft-context OOM above. Cap the *draft* ubatch while keeping the
  target `-ub` large; a cap well below the target costs draft throughput, so it can be a net
  loss even when it fits (see the KAT-Coder and Qwen3.6-35B results).
- Fork companions, all default off: `--moe-early-router`, `--ple-prefetch`, `--decode-overlap`,
  `--decode-boundary-overlap`, `--phase-aware-workspace`, `--live-context-workspace`
  (`--backend-sampling` is an upstream flag). These are config- and arch-dependent - a free win
  on one model, a loss on another - so isolate each before adopting a bundle.
- `GGML_CUDA_DISABLE_FUSION=1` is needed only for a pruned 256-expert layout whose cached-expert
  path builds a `ffn_moe_gate` (`MUL_MAT_ID`) node CUDA graph capture rejects; 512-expert quants
  are unaffected. `GGML_CUDA_DISABLE_GRAPHS=1` does not help.
- Validate a dynamic-cache run with one `--experimental-logs` pass: `moe-grouped-decode` calls
  > 0 and `fallback` / `rollback` / `prepare_error` / `finish_error` / `upload_errors` all 0.

### ik-llama.cpp only

[ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp). Same protocol, different
syntax and feature set:

- MTP is `--spec-type mtp:n_max=2` (draft KV via `-ctkd`/`-ctvd`); stock's `--spec-type
  draft-mtp` is **not** accepted. `--spec-type SPEC[:k=v,...]` can be repeated for a supported
  two-stage chain (e.g. an `ngram-*` stage plus `mtp`).
- `-fa/--flash-attn` **takes a value** (`on|off|auto|0|1`), default on; a bare `-fa` errors.
  `-no-fa/--no-flash-attn` disables it.
- `-gap/--graph-attn-precision` sets flash-attn precision under `-sm graph` (default f16).
- No `--load-mode`, no `--moe-expert-cache-*`, no `--reasoning-preserve`.
- `-cram/--cache-ram` prompt cache is on by default (8192 MiB) with similarity knobs; protocol
  payloads pass `cache_prompt: false`, so the two-pass rule still applies.
- `-ncmoe` clamps at the model's layer count (e.g. 99 == 41, all-CPU).
- ik's per-GPU-expert VRAM cost can be lower than stock, so it may pack a few more experts at the
  same VRAM and reach a slightly larger context.

### vLLM only

[syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) container stack, Rig 2. Different config
surface and different timing source (Prometheus metrics, not the llama-server `timings`).

- KV modes: fp8 (e.g. 150k) vs KVarN 4/2-bit (e.g. 250k, slower decode). k4v4 stores 2x the V
  bytes; a g64 group doubles scale overhead - neither buys speed or acceptance. DFlash2 is
  retired for MTP.
- `INT8_ACT=int8` is the one adopted knob: large prefill gain (+83% short, +39% at 140k) for a
  ~9-10% decode cost. `INT8_LAYERS=mlp` is smaller; `PREFILL_ATTN=int8` is a no-op.
- `--max-num-batched-tokens` is the ubatch analogue: 4096 neutral, **8192 boots but OOMs the
  first 140k prefill** - keep 2048.
- `MAX_SEQS` / `GPU_UTIL` vs byte-pinned pool (`--kv-cache-memory`); `KV_MEM` is ignored on the
  MTP branch.
- Draft: `DRAFT_TOKENS` 4 (fp8) / 3 (KVarN); `DRAFT_SAMPLE=greedy`,
  `VLLM_DRAFT_TEMP_SCALE`, `VLLM_DRAFT_TOPK_TOPP=0` are all no-gain or hazardous - leave them.
- `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` permits contexts past native RoPE but risks NaN - do not
  add it without checking.
- `VLLM_PREFIX_CACHE_RETENTION_INTERVAL` is a no-op on this image.

### Strata only

The pack engine ([Strata](engine-notes/strata.md)) runs the same speculative pair as llama.cpp
under different names, but its acceptance floor doubles as a **width** control: at
`--spec-min-p 0.0` the verify window is always the full `--spec`, while any non-zero floor
truncates it to the leading drafts that clear the floor.

- `--spec T` is the `--spec-draft-n-max` analogue, and `T >= 2` is structural rather than a
  tuning choice: a native (IQ) pack refuses to start at `--spec 1`, and `--mtp` is ignored
  below 2.
- Sweep `--spec` and `--spec-min-p` together and report both. Because the floor decides how
  much of the window is used, raising `--spec` at the default `0.0` can cost decode instead of
  gaining it - the default floor is not automatically the safe value at a wide window.

Measured rows, one model and quant: [Flash-Next archive](models/rig1-3060/archive/qwen38-flash-next.md).

### Flag equivalence

| Concept | stock llama.cpp | moe-cache fork | ik-llama.cpp | vLLM | Strata |
| --- | --- | --- | --- | --- | --- |
| Context | `-c/--ctx-size` | same | same | `MAX_LEN` | `--max-context` |
| KV quant | `-ctk/-ctv` | same | same | KV mode (fp8 / KVarN) | `--kv fp16/int8/q4_0/k8v4` |
| ubatch | `-ub` | same | same | `--max-num-batched-tokens` | `--prefill auto[:N]` |
| Expert placement | `-ncmoe` | `--moe-expert-cache-size` (overrides `-ncmoe`) | `-ncmoe` | `GPU_UTIL` / pinned pool | `--expert-cache N/auto` |
| MTP | `--spec-type draft-mtp --spec-draft-n-max` | same + `--spec-draft-ubatch-size` | `--spec-type mtp:n_max=` | `DRAFT_TOKENS` | `--mtp DIR --spec T --spec-min-p F` |
| Sampling | `--temp/--top-k/--min-p` | same | same | `--temp/--top-p/--top-k` | `--temperature/--top-k/--top-p` |

## Rules of thumb

### A passing health check is not proof of serviceability

A config can load, pass its health check, and still die on the **first large request** because
compute buffers grow with context and the draft/attention workspaces are allocated late. Always
run the ~60K long-context prompt before recording a decode number. Both failure modes occur:
clean load-time OOM (KAT-Coder Rig 2 `-ub 16384`), and load-then-crash (Flash-Next cache 84/88;
qwen35moe `-ub 8192`; the draft-context OOM).

### Cache vs ubatch: they compete for the same VRAM

Raising `-ub` raises the compute buffer and lowers the expert-cache ceiling; raising cache lowers
the ubatch ceiling. Sweep ubatch first (prefill), then cache to the ceiling (decode). When
headroom exists the order can flip (Rig 2 KAT-Coder: prefill-max ubatch, then cache 200).

### Judge MTP by tok/s, not acceptance rate

Higher acceptance routinely does not mean higher throughput. `--spec-draft-p-min 0.5` raised
acceptance from ~77% to ~89% with no decode gain; a larger expert cache beat a smaller one
*despite lower acceptance*. Report decode, and treat acceptance as diagnostic only.

### Noise: cold loads, cache warm-up, seed variance

- Use cold-load, second-pass numbers; the first raw call can return a 1-token transient.
- A dynamic expert cache keeps warming for 2+ passes - report the 3rd+ pass, not just the 2nd.
- Prefill is stable (~+-0.5%); **decode is the noisy column** (MTP is seed-dependent, +-10-15%
  run-to-run; vLLM decode +-5-10%). Take several samples and use the median.
- Compare numbers within one page/table/session; cross-page and cross-session comparisons are
  approximate.

## Per-architecture quirks

- **qwen4exp (Flash-Next):** near-repetitive prompt text can hit an EOS/crash path; only the
  sparse-attention layers carry KV, so the compute buffer binds the context, not KV;
  `--lazy-mode on` keeps the large n-gram table file-backed; `--ple-prefetch` is neutral.
- **qwen35moe (Qwen3.6-35B-A3B, KAT-Coder):** decodes normally on both raw and chat
  endpoints; the fork can rarely return EOS as the first token on the 10k prompt (retry decodes
  normally, cache-independent).
- **Pruned 256-expert layout:** needs `GGML_CUDA_DISABLE_FUSION=1` on the fork (see Part B).
- **Hybrid SSM+attention:** prefill does not scale with `-ub` (Rig 1 dense 27B).
- **Embedded MTP draft context:** can OOM on the first large prefill after a passing health
  check; cap `--spec-draft-ubatch-size` (fork). The cap is not free: it unblocked `-ub 4096`
  on KAT-Coder (+5.5% prefill) but lost ~3% prefill at `-ub 8192` on Qwen3.6-35B vs the
  shipped `-ub 6144` - measure both sides.
- **ik-llama.cpp:** `-ncmoe` clamps at the layer count.

## Validating a config before recording it

1. Cold-load through the rig endpoint and confirm the load's per-process VRAM is under the cap.
2. Run the timing prompt on the second pass; capture both prefill and decode.
3. Run the ~60K long-context prompt (large-prompt stability check) and confirm a full decode.
4. For the fork's expert cache, run one `--experimental-logs` pass and check the counters.
5. Unload and confirm the GPU is idle before the next config.

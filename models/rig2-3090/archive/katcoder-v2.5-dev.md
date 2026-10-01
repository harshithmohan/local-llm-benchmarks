# KAT-Coder-V2.5-Dev (Rig 2) - experiment archive

This archive holds the measurements behind the main card
([katcoder-v2.5-dev.md](../katcoder-v2.5-dev.md)): the ported Rig 1 config as a starting
point, the `-b/-ub` prefill sweep, the expert-cache decode sweep, and the large-prompt
headroom check, all at ctx 262144. Numbers are on the ~10k opencode session-context timing
prompt ([test-prompts.md](../../../test-prompts.md)) unless stated, measured under the
protocol in [methodology.md](../../../methodology.md) §Measurement methods (raw
`/v1/completions`, `cache_prompt: false`, `ignore_eos: true`, q8_0 KV, cold load,
`--threads 8`, 22 GB VRAM cap). Gotchas in [issues.md](../../../issues.md).

Engine: **moe-cache fork** = GenerelSchwerz `moe-cache` build b11608-2b8088c2a.

Quants:

- `APEX-I-Compact` (16.24 GiB, single file, Q4_K_M / file_type 15, embedded MTP head).

## Setup

- Context 262144 (native), q8_0 KV, `-fit off`, `--load-mode none`, MTP on
  (`--spec-type draft-mtp --spec-draft-n-max 2`), `--threads 8`.
- The expert cache is enabled (`--moe-expert-cache-size N`); it overrides expert placement,
  so no `--n-cpu-moe` is used.
- VRAM is the per-process `llama-server` allocation; the 22 GB cap leaves ~2 GB on the
  24 GB card for the desktop.

## Warm-up

The dynamic expert cache keeps warming for two passes after a cold load: prefill rises until
the cache stops churning, so the second pass alone is not steady-state here. Each row below
reports the warmed value (3rd+ pass); decode warms faster but is MTP-acceptance-driven and
noisy (temp 1.0), so decode carries ~±5-8% single-run noise.

## `-b/-ub` sweep at cache 80 (10k prompt)

| `-b`/`-ub` | prefill t/s | decode t/s | VRAM | fits |
| --- | --- | --- | --- | --- |
| 3072 (Rig 1 value) | 2709 | ~105 | 11824 MiB | yes |
| 8192 | 3638 | ~104 | 13582 MiB | yes |
| 12288 | 4430 | ~109 | 15256 MiB | yes |
| 14336 | 4415 | ~103 | 16038 MiB | yes |
| 16384 | - | - | - | fail to load |

- Prefill scales with `-ub` (the compute buffer is ubatch-bound on this arch), reaching
  ~4430 t/s at 12288 and plateauing (14336 unchanged within noise); 16384 fails to load.
- Decode is ubatch-independent (~103-109, MTP-acceptance noise).

## Expert-cache sweep at `-b/-ub 12288` (10k prompt)

| cache | prefill t/s | decode t/s | VRAM | headroom | slots |
| --- | --- | --- | --- | --- | --- |
| 80 (Rig 1 value) | 4430 | ~109 | 15256 MiB | ~7.3 GB | 3277 / 3280 (saturated) |
| 168 | 4433 | ~147 | 20458 MiB | ~2.0 GB | 6136 / 6888 |
| 184 | 4504 | ~142 | 21272 MiB | ~1.2 GB | - |
| 200 (recommended) | 4591 | ~163 | 22204 MiB | ~0.32 GB | 5512 / 8200 |

- Cache size is the decode lever: 80 -> 200 takes decode ~109 -> ~163 with no prefill cost.
  At cache 80 the cache is saturated (3277/3280 slots) and thrashes; at 200 it settles at
  5512/8200 slots (41 layers x 200).
- Cache 200 is the fastest and sits ~320 MiB from the 22 GB cap, so it was taken through
  the large-prompt check below before being adopted; it holds (see the headroom check).
- 184 and 168 decode the same within noise.

## Long-context refactor benchmark (~60K prompt)

The ~60K refactor prompt (prompt_n 59751) at the recommended config (cache 200,
`-b/-ub 12288`, MTP on, cold load): prefill 3701 t/s, decode 126 t/s, VRAM 22204 MiB. The
same prompt at cache 168 measured prefill 3597 / decode 118 / VRAM 20496 MiB.

### Headroom check (cache 200)

Cache 200 leaves only ~320 MiB of the 22 GB cap free, so it was checked against the large
prompts before adoption. It survives: peak VRAM 22204 MiB = 324 MiB of the 22528 MiB cap
free, server stayed up, no request failed.

| Prompt | tokens | cache | prefill t/s | decode t/s |
| --- | --- | --- | --- | --- |
| 10k opencode (warm) | 10455 | 200 | 4591 | 163 |
| ~60K refactor | 59751 | 200 | 3701 | 126 |
| ~60K refactor | 59751 | 168 | 3597 | 118 |
| ~116K retired variant | 116226 | 200 | 2938 | 104 |

Peak VRAM stayed 22204 MiB across the ~60K and ~116K prompts (38 MiB above the 22166 MiB
post-load figure) - consistent with KV being preallocated at ctx and the compute buffer
being ubatch-bound, not prompt-bound. Nothing grows into the margin on a longer prompt, so
the rule's predicted OOM does not occur at these lengths.

## Validation

`--experimental-logs` at the recommended config (cache 200, `-b/-ub 12288`):
`moe-grouped-decode calls=9026`, `fallback=0 rollback=0 prepare_error=0 finish_error=0
upload_errors=0`, `populated_slots` 5512 of `slot_capacity` 8200 (41 x 200). At cache 80 /
`-ub 3072` the same check gave `calls=9921`, all-zero errors, and a saturated `3277/3280`
slots.

## Conclusions

- The Rig 1 config (cache 80, `-b/-ub 3072`) leaves ~10 GB of the 22 GB cap unused on Rig 2;
  both the ubatch and the cache are scale levers here.
- Prefill maxes at `-b/-ub 12288` (~4430 t/s; 16384 fails to load).
- The expert cache is the decode lever: cache 80 -> 200 takes ~109 -> ~163 t/s. Cache 200
  passed the large-prompt checks (~60K/~116K) with ~320 MiB of the cap free.
- Config of choice on Rig 2: **cache 200, `-b/-ub 12288`** - 4591 t/s prefill / ~163 t/s
  decode at 22204 MiB; 3701 / 126 on the ~60K refactor prompt. Cache 168 (~2 GB margin) is
  the fallback if more headroom is wanted.

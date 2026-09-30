# ik-llama.cpp

[ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) - Ilya Kawrakow's
performance fork of llama.cpp. Rig 1, binary `ik-llama-server`; build 1aaf710 (v1; older
rows measured on build 3bb386e).

Same measurement protocol as the llama.cpp builds; engine-specific differences:

- MTP flag syntax is canonical: `--spec-type mtp:n_max=2` (with draft KV `-ctkd`/`-ctvd`).
  Stock's `--spec-type draft-mtp` is **not** accepted. `--spec-type SPEC[:k=v,...]` is the
  canonical stage entry and can be repeated for a supported two-stage chain (e.g. a
  `ngram-*` stage plus `mtp`).
- `-fa/--flash-attn (auto|on|off|0|1)` - default **on**, and the flag **takes a value**;
  a bare `-fa` errors out with usage text. `-no-fa/--no-flash-attn` disables it.
- `-gap/--graph-attn-precision` - Flash-attn precision under `-sm graph` (default f16).
- `-b`/`-ub` defaults are 2048/512, as in upstream.
- No fork features: no `--load-mode`, no `--moe-expert-cache-*`, and no
  `--reasoning-preserve`.
- A `-cram/--cache-ram` prompt cache is on by default (default 8192 MiB; also
  `-crs/--cache-ram-similarity`, `-cram-n-min`). Protocol payloads pass `cache_prompt:
  false`, so slot KV reuse never fires - the second-pass rule is still required for the
  page-in of weights.

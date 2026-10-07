# vLLM

[syv-ai/HyperQwen](https://github.com/syv-ai/HyperQwen) container stack, vLLM 0.29.0, on
Rig 2. Used for the Qwen3.8-27B W4A16-AutoRound quant and the Swift-1.5-INT4 fine-tune
quant.

## Config

- MTP speculative decode, with two KV modes: fp8 KV at 150000 (4 drafts) and KVarN 4/2-bit
  KV at 250000 (slower decode) - both with pinned pools under the 22 GB cap. DFlash2
  (120000, int8 KV) is archived.
- `INT8_ACT=int8` for the W4A16-AutoRound run (see the model page for the full command).
- Engine labels are per-row: llama.cpp and vLLM results are not interchangeable.

## Measurement specifics

- Timings come from vLLM's **Prometheus metrics**, not the llama-server `timings` object;
  `llama-bench` is not used. Prefill = `prompt_tokens_total` / `request_prefill_time_seconds`;
  decode = `generation_tokens_total` / `request_decode_time_seconds`; acceptance =
  `spec_decode_num_accepted_tokens_total` / `spec_decode_num_draft_tokens_total`; VRAM is the
  per-process allocation, read from the compute-apps query - the process is `VLLM::EngineCore`.
- A row is two passes per boot on the shared timing prompt
  ([test-prompts.md](../test-prompts.md)), the second recorded. The served profiles run
  vLLM's default automatic prefix caching: the image's `PREFIX_CACHE` env only ever *adds*
  `--enable-prefix-caching`, so it cannot turn caching off, and a repeated identical send is
  served from cache (~99% `cached` on a measured re-send). The recorded pass therefore has to
  be made cold explicitly - run the bench container with `--no-enable-prefix-caching`
  appended to `EXTRA_ARGS` (it expands last on the launch line, so it wins) and assert
  `prompt_tokens_cached_total` 0. The ~120K rows on the two Rig 2 model pages were taken that
  way; the retired single-pass rows were cold by construction (fresh boot, first send).

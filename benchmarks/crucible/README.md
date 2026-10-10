# crucible — capability benchmark

A suite-level benchmark run with
[Crucible LLM](https://github.com/MadGoatHaz/crucible-llm), a third-party terminal
benchmarking tool that points at any OpenAI-compatible `/v1` endpoint. Unlike the
single-stream timing prompts in [`test-prompts.md`](../../test-prompts.md) — which measure
one shape's prefill and decode — Crucible exercises a model across capability axes
(long-context retrieval, deterministic reasoning, structured output) in a single headless run.
This suite records those axes (**C1, C2, C3**); Crucible's own timing and energy engines are
not used — see "Engines".

- Source: [MadGoatHaz/crucible-llm](https://github.com/MadGoatHaz/crucible-llm) (GPL-3.0).
- Latest release at the time of writing: **v0.1.3** (2026-10-05).
- The only precompiled release asset is `crucible-llm-linux-x86_64` — **Linux x86_64 only**
  (no macOS, no aarch64, no musl build). The binary is **not vendored** in this repo; build
  or download it separately.
- Timed-inference methodology: [methodology.md](../../methodology.md).
- Known issues and gotchas: [issues.md](../../issues.md).

## Engines

| Engine | Measures |
|---|---|
| **A · Speed** | single-stream decode t/s, prefill t/s, TTFT, ITL p50/p99, MTP ratio — **not used** (see below) |
| **B · Concurrency** | parallel-stream sweep 1 → 32, and the practical sweet spot — **not used** (see below) |
| **C1 · NIAH** | needle-in-a-haystack: 7 context sizes (2k → 128k) × 11 depths = 77 cells |
| **C2 · Reasoning** | 13 deterministic math / logic / code challenges, strict checkers (no LLM-judge) |
| **C3 · Structured** | JSON compliance over 3 schema-complexity levels, plus the grammar speed penalty |
| **D · Energy** | GPU power/energy (NVIDIA NVML / AMD sysfs / Intel Level Zero), Joules/token, $/1M tokens — **not used** (see below) |
| **F · Flat Out** | 60 s at the concurrency sweet spot; the headline aggregate t/s — **not used** (see below) |

This suite records **C1, C2, C3** — capability only. Crucible's other engines are excluded:

- **A (speed)** drives a fixed ~45-token prompt, so its "prefill t/s" is just
  `prompt_tokens / TTFT` — a latency figure dominated by per-request overhead that never
  exercises the batch size — and **F (flat out)** at one stream merely restates A's decode rate
  over a 60 s window. Real prefill/decode timing is owned by the model cards, which use this
  repo's protocol at realistic prompt sizes.
- **B (concurrency)** sweeps parallel streams, outside this suite's single-stream scope.
- **D (energy)** reports a **whole-window** figure, not a per-token one: it integrates power
  over the entire run window (no request windowing, no idle subtraction) and adds a CPU term
  that is a flat 40 W estimate whenever the host's RAPL / Super-I/O reading is rejected. The
  same generation therefore reads ~1.7 J/token on a warm run and ~4.4 J/token on a cold one,
  purely because the model load fell inside the window. It is disabled with `--no-hardware`.

The launcher passes the recorded set explicitly, so a no-argument run never selects the other
engines.

## How to run

The suite launcher is [`run.sh`](run.sh); point it at the Crucible binary (it is not
vendored) and the target endpoint, then name the model under test and, optionally, the
engines:

    ./run.sh run <MODEL> [ENGINE ...]

With no engines named it runs the suite's set (**C1, C2, C3**) headless and writes a run log
under `results/<MODEL>/`:

    crucible-llm --headless --url <URL> --model <MODEL> --engine <ENGINE> ...

- `<URL>` is a rig's OpenAI-compatible `/v1` endpoint (the same direct endpoint the timing
  runs use); `<MODEL>` is a bare rig model id (Crucible can also discover ids via
  `/v1/models`).
- The default UI is a TUI; `--headless` / `--json` make it non-interactive.
- **The capability verdicts (C1 / C2 / C3) go to stderr**, which `run.sh` tees to
  `results/<MODEL>/run.log`; keep that log. Crucible's `--export` file carries only stream
  metrics from its timing engines, which this suite does not run, so the export is not used.

## Protocol deviations

Crucible does **not** follow this repo's inference-timing protocol
([methodology.md](../../methodology.md)). Its numbers come from its own client-side
harness and are therefore **NOT comparable to the model-card timing rows** — read them as
their own capability measurements, not as prefill/decode rows:

- It drives `POST /v1/chat/completions` with `stream:true` + `include_usage:true`, so a
  chat template is **always** applied — whereas this repo's timing methodology uses raw
  `/v1/completions`.
- It sends its **own** sampling params: `temperature:0`, `max_tokens:256`. This repo's rule
  is server-side sampling only; this is an **acknowledged exception** for this suite.
- Generation is capped per engine with no CLI override (NIAH 64, structured 256, reasoning
  512 tokens). The caps are tight for a reasoning model, and Crucible's engines differ in how
  they treat the reasoning channel: **C1 (NIAH) counts reasoning chunks** as part of the
  answer, while **C3 (structured) reads only content chunks** — so a thinking model emits an
  empty body and fails C3 outright. This suite therefore runs **C1 and C3 with thinking
  disabled** (the server is started with `--reasoning off`); **C2** keeps the model's default,
  since it is meant to exercise reasoning.
- TTFT / ITL are measured by Crucible's **own client cycle clock** (`quanta`), not read
  from the server `timings` object.
- Cold cache is approximated by prepending a **unique random prefix** (`--nocache`), not by
  `cache_prompt:false`.
- Token counts come from the server's `usage.completion_tokens` (authoritative), with a
  `chars/4` estimate flag as a fallback.
- It requires a model id (bare rig ids); `/v1/models` discovery is available.

## Results

Canonical results live in [scorecard.md](scorecard.md) — one row per model + engine set.
Per-model detail (engine results, capability verdicts, run time) is in
[`scorecards/<model>.md`](scorecards/); raw run logs under `results/` are transient, deleted
once their numbers are recorded.

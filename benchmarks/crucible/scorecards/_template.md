# <model-id> — crucible results

Parameter set: <serving config, e.g. kv-q8 / engine + quant>. Endpoint: <rig / direct>.
Binary: crucible-llm <version>.

> Engines run: C1, C2, C3 (suite set).

## Run

**<date>** · wall-clock <min> min · suite set <list> (thinking on/off per engine).

## Engine results

| Engine | Metric | Result |
|---|---|---|
| C1 · NIAH | cells passed | / 77 |
| C2 · Reasoning | challenges passed | / 13 |
| C3 · Structured | JSON-compliance level | / grammar penalty |

## Capability verdicts

- **Long-context retrieval (C1):** <which context sizes / depths pass or fail>.
- **Reasoning (C2):** <challenges missed, if any>.
- **Structured output (C3):** <highest schema level reached; grammar penalty>.

## Notes

<deviations from a default run, thinking on/off, `--nocache` behaviour, anything anomalous>.

Raw run log: `results/<model-id>/` (deleted once this card is recorded).

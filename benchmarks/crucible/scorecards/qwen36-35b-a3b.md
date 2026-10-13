# Qwen3.6-35B-A3B — crucible results

Updated: 2026-10-13 · model cards: [Rig 1](../../models/rig1-3060/qwen36-35b-a3b.md) · [Rig 2](../../models/rig2-3090/qwen36-35b-a3b.md) · [suite README](../README.md)

| Quant | KV cache | ctx | C1 NIAH | C2 reasoning | C3 structured | Notes |
|---|---|---|---|---|---|---|
| UD-IQ4_XS | q8_0 | 262144 | 35 / 35 (100.0%) | 13 / 13 (100.0%) | 3 / 3 compliant (+11.4% penalty) | — |
| UD-IQ4_XS | q4_0 | 262144 | 35 / 35 (100.0%) | 13 / 13 (100.0%) | 3 / 3 compliant (-0.4% penalty) | — |

## Notes

Both rows are on Crucible v0.1.5 with the suite's pinned C1 ladder (16k → 256k × 5 depths = 35 cells at a 262144 context), so C1 is `/ 35` here and not comparable to the retired v0.1.3 rows, which were scored `/ 77` on Crucible's own 2k → 128k default ladder.

C1 is at ceiling (35/35) on both rows — no cell fails on either KV type, including the 256k cells, so this comparison can only show degradation, not improvement.

C3 is 3/3 compliant on both rows (0 `truncated_by_reasoning`); the grammar penalty differs in sign (+11.4% vs -0.4%) but varies run to run and is not comparable between rows.

C2 is at ceiling on both rows (13/13). The first q4_0 pass reported 12/13; that pass was re-run (C2 only) and solved the full 13-challenge bank, so no engine separates the two KV types here — both are at ceiling on all three.

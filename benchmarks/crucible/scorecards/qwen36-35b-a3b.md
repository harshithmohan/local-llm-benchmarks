# Qwen3.6-35B-A3B — crucible results

Updated: 2026-10-13 · model cards: [Rig 1](../../models/rig1-3060/qwen36-35b-a3b.md) · [Rig 2](../../models/rig2-3090/qwen36-35b-a3b.md) · [suite README](../README.md)

> **Deprecated (2026-10-13).** Measured on Crucible **v0.1.3**. v0.1.5 changes the capability protocol, so these figures are **not comparable** to a current-binary run; re-measure before comparing.

| Quant | KV cache | ctx | C1 NIAH | C2 reasoning | C3 structured | Notes |
|---|---|---|---|---|---|---|
| UD-IQ4_XS | q8_0 | 262144 | 77 / 77 (100.0%) | 11 / 13 (84.6%) | 2 / 3 compliant, 1 partial (+0.0% penalty) | — |
| UD-IQ4_XS | q4_0 | 262144 | 77 / 77 (100.0%) | 10 / 13 (76.9%) | 2 / 3 compliant, 1 partial (+11.0% penalty) | — |

## Notes

C1 is at ceiling (77/77) on both rows: with the fixed protocol no cell fails, so this comparison can only show degradation, not improvement.

C3 reached the same 2/3 compliant + 1 partial level on both rows while the penalty figure differed (+0.0%, +11.0%), so the compliance level is stable and the penalty varies run to run on a 256-token task.

C2 is 11/13 on the q8_0 row and 10/13 on the q4_0 row.

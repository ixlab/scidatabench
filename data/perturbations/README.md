# Perturbation sets

Rewritten SciDataBench requests: the same task in different words, one set per phase. Each set holds the scenarios the rewrite applies to. A scenario file has the same format as in `../scidatabench/`; only the request of the perturbed phase differs, and, for Phase 3, the gold value and unit.

| Folder | Phase | Rewrite | Example | Scenarios |
|---|---:|---|---|---:|
| `phase1-catalogue-synonym/` | 1 | The quantity term is replaced by a catalogue synonym. | small mammal box trapping → rodent live-capture grids | 124 |
| `phase2-anchor-duration/` | 2 | The retrieval window is restated as an anchor plus a duration. | from 2002 through 2017 → over the 16 calendar years beginning in 2002 | 120 |
| `phase3-alternate-unit/` | 3 | The answer is requested in a different unit; the gold value is converted accordingly. | cubic feet per second → cubic metres per second | 88 |
| `phase4-method-paraphrase/` | 4 | The name of the analytical method is replaced by a description of it. | two-sided Mann-Whitney-Wilcoxon test → two-sided rank-based two-sample test for a difference in location | 59 |

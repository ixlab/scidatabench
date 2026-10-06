# Supplementary Material

Supplementary material for the SciDataBench paper. Each section is one
Markdown file and can be read on its own.

| | Section | What it contains |
|---|---|---|
| S1 | [Phase 1 Key Schema](S1_phase1_key_schema.md) | How Phase 1 is scored, and the identifier keys graded on each of the 15 platforms |
| S2 | [Phase 2 Result Equivalence](S2_phase2_result_equivalence.md) | Per-platform merge unit, record key and compared columns; USGS route folding; canonicalisation; verdicts |
| S3 | [Threshold Sensitivity](S3_threshold_sensitivity.md) | Pass rates and model ordering when each grading threshold is moved |
| S4 | [Cost and Pricing](S4_cost_and_pricing.md) | Per-model token prices and how cost is computed |
| S5 | [Per-Model Results](S5_per_model_results.md) | Pass rate, tool calls and tokens for each model, by phase and by platform |
| S6 | [Results Without USGS](S6_leave_usgs_out.md) | Model comparison on SciDataBench with USGS scenarios removed |

## Contents by subsection

**S1. Phase 1 Key Schema**
- [S1.1 Scoring rule](S1_phase1_key_schema.md#s11-scoring-rule)
- [S1.2 What the agent is shown](S1_phase1_key_schema.md#s12-what-the-agent-is-shown)
- [S1.3 Key schema per platform](S1_phase1_key_schema.md#s13-key-schema-per-platform)

**S2. Phase 2 Result Equivalence**
- [S2.1 Merge specification](S2_phase2_result_equivalence.md#s21-merge-specification)
- [S2.2 Route folding (USGS)](S2_phase2_result_equivalence.md#s22-route-folding-usgs)
- [S2.3 Canonicalisation](S2_phase2_result_equivalence.md#s23-canonicalisation)
- [S2.4 Platform-specific handling](S2_phase2_result_equivalence.md#s24-platform-specific-handling)
- [S2.5 Verdicts](S2_phase2_result_equivalence.md#s25-verdicts)

**S3. Threshold Sensitivity**
- [S3.1 Phase 1: pass threshold τ](S3_threshold_sensitivity.md#s31-phase-1-pass-threshold-tau)
- [S3.2 Phase 2: pass criterion](S3_threshold_sensitivity.md#s32-phase-2-pass-criterion)
- [S3.3 Phases 3 and 4: relative tolerance δ](S3_threshold_sensitivity.md#s33-phases-3-and-4-relative-tolerance-delta)

**S4. Cost and Pricing** — a single table and the cost formula.

**S5. Per-Model Results**
- [S5.1 Pass rate](S5_per_model_results.md#s51-pass-rate-)
- [S5.2 Tool calls per scenario](S5_per_model_results.md#s52-tool-calls-per-scenario)
- [S5.3 Tokens per scenario](S5_per_model_results.md#s53-tokens-per-scenario-thousands)
- [S5.4 Token breakdown per scenario](S5_per_model_results.md#s54-token-breakdown-per-scenario-thousands)

**S6. Results Without USGS** — a single table.

## Related files in this repository

- The scenarios themselves, with the gold answer of every phase:
  [`data/`](../data)
- The graders that implement S1 and S2: [`grading/`](../grading)

## License

[CC BY 4.0](LICENSE).

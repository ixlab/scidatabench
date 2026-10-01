# S6. Results Without USGS

USGS contributes 160 of the 245 scenarios in SciDataBench. This section
repeats the overall comparison of the eight models after removing USGS,
leaving 85 scenarios (GBIF 51, NEON 23, EPA AQS 11).

*Overall* is the unweighted mean of the four phase pass rates (%). Pass rates
are computed as in the paper: a scenario with no record counts as a failure,
and Phase 2 is graded by result equivalence (S2). Models are ordered by the
overall pass rate on all four platforms.

| Model | All 4 | No USGS | Δ | Rank (All 4 → No USGS) |
|---|---:|---:|---:|---|
| Gemini 3.7 Flash | 60.92 | 54.71 | −6.21 | 1 → 2 |
| Gemini 3.1 Pro | 60.20 | 56.76 | −3.44 | 2 → 1 |
| Gemini 3 Flash | 53.47 | 48.53 | −4.94 | 3 → 3 |
| Qwen 3.6 27B | 45.41 | 45.59 | +0.18 | 4 → 5 |
| Gemini 2.5 Pro | 42.14 | 42.35 | +0.21 | 5 → 6 |
| Gemma 4 31B | 41.02 | 46.18 | +5.16 | 6 → 4 |
| GPT-OSS 120B | 28.78 | 32.94 | +4.17 | 7 → 7 |
| Gemini 2.5 Flash | 25.20 | 23.53 | −1.67 | 8 → 8 |

The rank correlation between the two orderings is Kendall's $\tau_b = 0.786$.
Three pairs change places:

| Pair | All 4 | No USGS |
|---|---:|---:|
| Gemini 3.1 Pro over Gemini 3.7 Flash | 60.20 vs 60.92 | 56.76 vs 54.71 |
| Gemma 4 31B over Qwen 3.6 27B | 41.02 vs 45.41 | 46.18 vs 45.59 |
| Gemma 4 31B over Gemini 2.5 Pro | 41.02 vs 42.14 | 46.18 vs 42.35 |

The remaining models keep their ranks: Gemini 3 Flash stays third, and
GPT-OSS 120B and Gemini 2.5 Flash stay seventh and eighth. The two models
that exchange first and second place are within 2.1 points of each other in
both views.

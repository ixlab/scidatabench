# S4. Threshold Sensitivity

Every phase turns a graded measurement into a verdict at a fixed cut (paper,
Section 2.2). This section reports how the pass rates and the ordering of
systems change when each cut is moved (paper, Section 3.3, *Threshold
sensitivity*).

**Method.**

- Each sweep re-scores the per-scenario measurements stored from the runs
  reported in the paper. No agent is re-run and no data is re-fetched.
- At the published setting, re-scoring reproduces the stored verdict for
  every scenario, with 0 disagreements. This was checked for Phases 1–4 on
  SciDataBench and for Phase 2 on SciDataBench-Onboard. For Phase 1 on
  SciDataBench-Onboard, the pass rates at the published setting equal those
  reported in the paper.
- A scenario with no record counts as a failure, as in the paper.
- In Phases 3 and 4, a scenario whose answer cannot be re-scored (an error,
  a missing answer, or a non-numeric value) keeps its published verdict at
  every setting.
- Rank stability is Kendall's $\tau_b$ between the ordering at a setting and
  the ordering at the published setting. A value below 1 with no listed
  reversal comes from ties.
- A reversal is a pair of systems whose strict order at a setting is the
  opposite of their strict order at the published setting.

Pass rates are percentages. The published setting is in bold. SciDataBench
has n = 245 scenarios. SciDataBench-Onboard has n = 210 and covers Phases 1
and 2 only; its skills are written as author · acquisition method, as in
Section 4 of the paper.

## S4.1 Phase 1: pass threshold $\tau$

### SciDataBench

| Model | 0.50 | 0.60 | 0.70 | 0.80 | **0.90** | 0.95 | 1.00 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3.7 Flash | 95.5 | 90.6 | 90.6 | 84.9 | **80.4** | 75.5 | 71.8 |
| Gemini 3.1 Pro | 91.0 | 84.1 | 83.3 | 80.4 | **76.3** | 71.0 | 69.4 |
| Gemini 3 Flash | 89.0 | 76.3 | 74.3 | 70.2 | **64.9** | 58.8 | 56.3 |
| Gemini 2.5 Pro | 80.8 | 68.2 | 65.7 | 54.7 | **47.3** | 42.9 | 40.4 |
| Gemini 2.5 Flash | 14.3 | 11.8 | 11.0 | 8.2 | **7.3** | 7.3 | 7.3 |
| Qwen 3.6 27B | 78.8 | 64.1 | 60.8 | 49.8 | **46.1** | 43.3 | 42.9 |
| Gemma 4 31B | 78.8 | 58.4 | 52.2 | 42.0 | **39.6** | 38.0 | 38.0 |
| GPT-OSS 120B | 69.8 | 48.6 | 45.7 | 31.0 | **27.3** | 26.1 | 25.7 |
| Kendall τ_b | 0.982 | 1.000 | 1.000 | 1.000 | 1.000 | 0.929 | 0.929 |

Reversals:

| Setting | Ranked higher | Ranked lower | At setting | At published |
|---|---|---|---:|---:|
| 0.95 | Qwen 3.6 27B | Gemini 2.5 Pro | 43.3 vs 42.9 | 46.1 vs 47.3 |
| 1.00 | Qwen 3.6 27B | Gemini 2.5 Pro | 42.9 vs 40.4 | 46.1 vs 47.3 |

### SciDataBench-Onboard

| Task agent | Skill | 0.50 | 0.60 | 0.70 | 0.80 | **0.90** | 0.95 | 1.00 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3 Flash | cold start | 62.9 | 41.0 | 32.4 | 22.4 | **18.1** | 16.7 | 16.7 |
| Gemini 3 Flash | G3 · search | 71.0 | 51.0 | 41.9 | 31.4 | **26.2** | 24.8 | 24.3 |
| Gemini 3 Flash | G3 · exec | 75.7 | 51.0 | 43.8 | 31.4 | **25.7** | 23.3 | 23.3 |
| Gemini 3 Flash | G3.7 · search | 75.7 | 58.6 | 50.0 | 34.8 | **28.6** | 25.7 | 24.3 |
| Gemini 3 Flash | G3.7 · exec | 76.2 | 61.4 | 52.9 | 38.1 | **32.9** | 29.5 | 29.5 |
| Gemini 3.7 Flash | cold start | 83.3 | 62.9 | 57.6 | 48.1 | **41.0** | 38.6 | 36.7 |
| Gemini 3.7 Flash | G3 · search | 85.7 | 66.7 | 61.0 | 50.0 | **42.9** | 40.0 | 39.0 |
| Gemini 3.7 Flash | G3 · exec | 85.2 | 64.3 | 57.1 | 44.8 | **38.1** | 34.8 | 33.8 |
| Gemini 3.7 Flash | G3.7 · search | 87.1 | 70.5 | 66.2 | 55.7 | **47.1** | 45.2 | 43.3 |
| Gemini 3.7 Flash | G3.7 · exec | 88.6 | 70.5 | 67.1 | 58.6 | **50.0** | 46.2 | 44.8 |
| Kendall τ_b |  | 0.899 | 0.932 | 0.956 | 0.989 | 1.000 | 1.000 | 0.989 |

Reversals:

| Setting | Ranked higher | Ranked lower | At setting | At published |
|---|---|---|---:|---:|
| 0.50 | Gemini 3 Flash, G3 · exec | Gemini 3 Flash, G3 · search | 75.7 vs 71.0 | 25.7 vs 26.2 |
| 0.50 | Gemini 3.7 Flash, G3 · exec | Gemini 3.7 Flash, cold start | 85.2 vs 83.3 | 38.1 vs 41.0 |
| 0.60 | Gemini 3.7 Flash, G3 · exec | Gemini 3.7 Flash, cold start | 64.3 vs 62.9 | 38.1 vs 41.0 |
| 0.70 | Gemini 3 Flash, G3 · exec | Gemini 3 Flash, G3 · search | 43.8 vs 41.9 | 25.7 vs 26.2 |

## S4.2 Phase 2: pass criterion

Each setting changes the cuts of the pass criterion (S3.5) as follows. A
dash means that the cut stays at its published value.

| Setting | $\epsilon_{\text{rec}}$ | $\epsilon_{\text{val}}$ | $\epsilon_{\text{tim}}$ | $\Omega$ | Verdicts counted as pass |
|---|---:|---:|---:|---:|---|
| published | – | – | – | – | PASS, OVER-BROAD |
| exact | 0 | 0 | 0 | – | PASS, OVER-BROAD |
| rec 0.05 | 0.05 | – | – | – | PASS, OVER-BROAD |
| rec 0.10 | 0.10 | – | – | – | PASS, OVER-BROAD |
| rec 0.20 | 0.20 | – | – | – | PASS, OVER-BROAD |
| val 0.05 | – | 0.05 | – | – | PASS, OVER-BROAD |
| tim 0.10 | – | – | 0.10 | – | PASS, OVER-BROAD |
| all 0.10 | 0.10 | 0.10 | 0.10 | – | PASS, OVER-BROAD |
| Ω = 10 | – | – | – | 10 | PASS, OVER-BROAD |
| Ω = 2 | – | – | – | 2 | PASS, OVER-BROAD |
| strict | – | – | – | – | PASS only |

### SciDataBench

| Model | **published** | exact | rec 0.05 | rec 0.10 | rec 0.20 | val 0.05 | tim 0.10 | all 0.10 | Ω = 10 | Ω = 2 | strict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3.7 Flash | **44.1** | 35.5 | 45.7 | 46.1 | 46.5 | 45.3 | 44.5 | 49.0 | 43.7 | 42.9 | 39.2 |
| Gemini 3.1 Pro | **46.5** | 38.4 | 48.2 | 48.6 | 49.4 | 47.8 | 46.9 | 51.4 | 45.7 | 44.9 | 41.2 |
| Gemini 3 Flash | **40.8** | 33.1 | 42.9 | 43.3 | 44.1 | 41.6 | 41.2 | 45.7 | 40.4 | 40.0 | 36.7 |
| Gemini 2.5 Pro | **20.4** | 17.6 | 20.8 | 21.6 | 22.9 | 20.4 | 20.4 | 22.4 | 20.0 | 20.0 | 20.0 |
| Gemini 2.5 Flash | **21.6** | 17.6 | 22.4 | 22.9 | 22.9 | 22.4 | 21.6 | 24.5 | 21.6 | 21.6 | 21.6 |
| Qwen 3.6 27B | **33.1** | 28.6 | 34.7 | 35.5 | 35.5 | 34.3 | 33.5 | 38.8 | 33.1 | 32.2 | 28.6 |
| Gemma 4 31B | **28.2** | 20.8 | 29.8 | 30.2 | 30.6 | 29.4 | 28.6 | 33.1 | 27.8 | 27.3 | 24.1 |
| GPT-OSS 120B | **32.2** | 26.5 | 33.9 | 34.3 | 35.5 | 33.1 | 32.7 | 37.1 | 32.2 | 31.4 | 27.8 |
| Kendall τ_b | 1.000 | 0.982 | 1.000 | 1.000 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Reversals: none.

### SciDataBench-Onboard

| Task agent | Skill | **published** | exact | rec 0.05 | rec 0.10 | rec 0.20 | val 0.05 | tim 0.10 | all 0.10 | Ω = 10 | Ω = 2 | strict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3 Flash | cold start | **53.8** | 51.9 | 55.2 | 55.7 | 57.1 | 54.3 | 53.8 | 56.7 | 51.9 | 51.0 | 49.5 |
| Gemini 3 Flash | G3 · search | **48.6** | 45.7 | 48.6 | 48.6 | 50.0 | 48.6 | 48.6 | 48.6 | 47.1 | 46.7 | 45.7 |
| Gemini 3 Flash | G3 · exec | **46.7** | 44.3 | 46.7 | 46.7 | 48.1 | 46.7 | 46.7 | 47.1 | 45.7 | 44.8 | 44.3 |
| Gemini 3 Flash | G3.7 · search | **63.3** | 60.5 | 64.3 | 64.3 | 65.2 | 63.3 | 63.3 | 64.3 | 61.4 | 60.5 | 59.0 |
| Gemini 3 Flash | G3.7 · exec | **63.8** | 59.0 | 65.2 | 65.2 | 66.2 | 63.8 | 63.8 | 65.7 | 61.9 | 60.5 | 58.6 |
| Gemini 3.7 Flash | cold start | **64.8** | 62.4 | 66.7 | 66.7 | 67.1 | 64.8 | 64.8 | 67.1 | 62.9 | 61.9 | 60.5 |
| Gemini 3.7 Flash | G3 · search | **51.4** | 48.6 | 51.4 | 51.4 | 51.9 | 51.4 | 51.4 | 51.9 | 49.5 | 49.0 | 48.1 |
| Gemini 3.7 Flash | G3 · exec | **46.7** | 45.2 | 46.7 | 46.7 | 47.1 | 46.7 | 46.7 | 47.6 | 45.2 | 44.8 | 42.9 |
| Gemini 3.7 Flash | G3.7 · search | **64.3** | 61.4 | 65.7 | 65.7 | 66.2 | 64.3 | 64.3 | 66.2 | 62.4 | 61.9 | 58.6 |
| Gemini 3.7 Flash | G3.7 · exec | **64.3** | 61.9 | 65.7 | 65.7 | 66.2 | 64.3 | 64.3 | 66.2 | 61.9 | 61.0 | 58.6 |
| Kendall τ_b |  | 1.000 | 0.932 | 1.000 | 1.000 | 0.965 | 1.000 | 1.000 | 0.989 | 0.966 | 0.965 | 0.824 |

Reversals:

| Setting | Ranked higher | Ranked lower | At setting | At published |
|---|---|---|---:|---:|
| exact | Gemini 3 Flash, G3.7 · search | Gemini 3 Flash, G3.7 · exec | 60.5 vs 59.0 | 63.3 vs 63.8 |
| strict | Gemini 3 Flash, G3.7 · search | Gemini 3 Flash, G3.7 · exec | 59.0 vs 58.6 | 63.3 vs 63.8 |
| strict | Gemini 3 Flash, G3.7 · search | Gemini 3.7 Flash, G3.7 · search | 59.0 vs 58.6 | 63.3 vs 64.3 |
| strict | Gemini 3 Flash, G3.7 · search | Gemini 3.7 Flash, G3.7 · exec | 59.0 vs 58.6 | 63.3 vs 64.3 |

## S4.3 Phases 3 and 4: relative tolerance $\delta$

### Phase 3

| Model | 0.5% | 1% | 2% | **5%** | 10% | 20% | 50% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3.7 Flash | 55.5 | 60.0 | 63.7 | **67.3** | 71.8 | 78.0 | 84.1 |
| Gemini 3.1 Pro | 52.7 | 56.7 | 60.0 | **65.3** | 68.6 | 73.1 | 79.2 |
| Gemini 3 Flash | 48.6 | 53.9 | 57.1 | **59.6** | 64.1 | 68.6 | 75.5 |
| Gemini 2.5 Pro | 46.5 | 52.2 | 55.9 | **60.0** | 64.1 | 70.2 | 78.8 |
| Gemini 2.5 Flash | 35.9 | 41.2 | 42.9 | **45.3** | 49.4 | 53.5 | 61.6 |
| Qwen 3.6 27B | 46.1 | 50.6 | 56.3 | **58.4** | 63.3 | 68.6 | 78.4 |
| Gemma 4 31B | 42.9 | 48.6 | 52.2 | **55.5** | 61.6 | 66.5 | 74.7 |
| GPT-OSS 120B | 28.6 | 31.8 | 34.7 | **36.3** | 39.2 | 41.6 | 46.5 |
| Kendall τ_b | 0.929 | 0.929 | 0.857 | 1.000 | 0.982 | 0.982 | 0.929 |

Reversals:

| Setting | Ranked higher | Ranked lower | At setting | At published |
|---|---|---|---:|---:|
| 0.5% | Gemini 3 Flash | Gemini 2.5 Pro | 48.6 vs 46.5 | 59.6 vs 60.0 |
| 1% | Gemini 3 Flash | Gemini 2.5 Pro | 53.9 vs 52.2 | 59.6 vs 60.0 |
| 2% | Gemini 3 Flash | Gemini 2.5 Pro | 57.1 vs 55.9 | 59.6 vs 60.0 |
| 2% | Qwen 3.6 27B | Gemini 2.5 Pro | 56.3 vs 55.9 | 58.4 vs 60.0 |
| 50% | Qwen 3.6 27B | Gemini 3 Flash | 78.4 vs 75.5 | 58.4 vs 59.6 |

### Phase 4

| Model | 0.5% | 1% | 2% | **5%** | 10% | 20% | 50% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3.7 Flash | 32.2 | 38.0 | 43.7 | **51.8** | 61.2 | 69.8 | 81.2 |
| Gemini 3.1 Pro | 31.4 | 37.1 | 41.6 | **52.7** | 59.6 | 66.9 | 75.9 |
| Gemini 3 Flash | 29.0 | 33.5 | 38.4 | **48.6** | 55.9 | 64.1 | 77.1 |
| Gemini 2.5 Pro | 26.1 | 31.0 | 34.7 | **40.8** | 47.3 | 53.1 | 65.3 |
| Gemini 2.5 Flash | 15.9 | 19.6 | 21.6 | **26.5** | 29.4 | 34.3 | 40.0 |
| Qwen 3.6 27B | 26.1 | 30.6 | 33.5 | **44.1** | 51.4 | 58.0 | 69.0 |
| Gemma 4 31B | 24.5 | 29.8 | 33.9 | **40.8** | 47.3 | 57.6 | 71.0 |
| GPT-OSS 120B | 12.7 | 16.3 | 17.6 | **19.2** | 20.8 | 22.0 | 26.9 |
| Kendall τ_b | 0.889 | 0.837 | 0.764 | 1.000 | 0.926 | 0.909 | 0.764 |

Reversals:

| Setting | Ranked higher | Ranked lower | At setting | At published |
|---|---|---|---:|---:|
| 0.5% | Gemini 3.7 Flash | Gemini 3.1 Pro | 32.2 vs 31.4 | 51.8 vs 52.7 |
| 1% | Gemini 3.7 Flash | Gemini 3.1 Pro | 38.0 vs 37.1 | 51.8 vs 52.7 |
| 1% | Gemini 2.5 Pro | Qwen 3.6 27B | 31.0 vs 30.6 | 40.8 vs 44.1 |
| 2% | Gemini 3.7 Flash | Gemini 3.1 Pro | 43.7 vs 41.6 | 51.8 vs 52.7 |
| 2% | Gemini 2.5 Pro | Qwen 3.6 27B | 34.7 vs 33.5 | 40.8 vs 44.1 |
| 2% | Gemma 4 31B | Qwen 3.6 27B | 33.9 vs 33.5 | 40.8 vs 44.1 |
| 10% | Gemini 3.7 Flash | Gemini 3.1 Pro | 61.2 vs 59.6 | 51.8 vs 52.7 |
| 20% | Gemini 3.7 Flash | Gemini 3.1 Pro | 69.8 vs 66.9 | 51.8 vs 52.7 |
| 50% | Gemini 3.7 Flash | Gemini 3.1 Pro | 81.2 vs 75.9 | 51.8 vs 52.7 |
| 50% | Gemini 3 Flash | Gemini 3.1 Pro | 77.1 vs 75.9 | 48.6 vs 52.7 |
| 50% | Gemma 4 31B | Qwen 3.6 27B | 71.0 vs 69.0 | 40.8 vs 44.1 |

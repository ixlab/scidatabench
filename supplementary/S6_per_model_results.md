# S6. Per-Model Results

The tables give the results of the eight models on SciDataBench by phase and
by platform: pass rate, tool calls and tokens. They underlie Figure 2 and
Table 2 of the paper.

- Every cell covers the published set of 245 scenarios (USGS 160, GBIF 51,
  NEON 23, EPA AQS 11), the same in every phase and for every model.
- Phase 2 is graded by result equivalence (S3).
- Each phase is run from the gold output of the phase before it (paper,
  Section 3.1).

## S6.1 Pass rate (%)

A scenario with no record counts as a failure. *Mean* is the unweighted mean
over the four phases.

| Model | P1 | P2 | P3 | P4 | Mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gemini 3.7 Flash | 80.4 | 44.1 | 67.3 | 51.8 | 60.9 |
| Gemini 3.1 Pro | 76.3 | 46.5 | 65.3 | 52.7 | 60.2 |
| Gemini 3 Flash | 64.9 | 40.8 | 59.6 | 48.6 | 53.5 |
| Gemini 2.5 Pro | 47.3 | 20.4 | 60.0 | 40.8 | 42.1 |
| Gemini 2.5 Flash | 7.3 | 21.6 | 45.3 | 26.5 | 25.2 |
| Qwen 3.6 27B | 46.1 | 33.1 | 58.4 | 44.1 | 45.4 |
| Gemma 4 31B | 39.6 | 28.2 | 55.5 | 40.8 | 41.0 |
| GPT-OSS 120B | 27.3 | 32.2 | 36.3 | 19.2 | 28.8 |

### By platform

| Model | Platform | n | P1 | P2 | P3 | P4 | Mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Gemini 3.7 Flash | USGS | 160 | 78.1 | 33.8 | 78.1 | 66.9 | 64.2 |
|  | GBIF | 51 | 88.2 | 62.7 | 51.0 | 27.5 | 57.4 |
|  | NEON | 23 | 87.0 | 87.0 | 26.1 | 13.0 | 53.3 |
|  | EPA AQS | 11 | 63.6 | 18.2 | 72.7 | 27.3 | 45.5 |
| Gemini 3.1 Pro | USGS | 160 | 73.1 | 38.1 | 73.1 | 63.8 | 62.0 |
|  | GBIF | 51 | 92.2 | 62.7 | 52.9 | 29.4 | 59.3 |
|  | NEON | 23 | 78.3 | 78.3 | 34.8 | 39.1 | 57.6 |
|  | EPA AQS | 11 | 45.5 | 27.3 | 72.7 | 27.3 | 43.2 |
| Gemini 3 Flash | USGS | 160 | 68.1 | 30.6 | 66.9 | 58.8 | 56.1 |
|  | GBIF | 51 | 72.5 | 60.8 | 45.1 | 29.4 | 52.0 |
|  | NEON | 23 | 47.8 | 78.3 | 39.1 | 34.8 | 50.0 |
|  | EPA AQS | 11 | 18.2 | 18.2 | 63.6 | 18.2 | 29.5 |
| Gemini 2.5 Pro | USGS | 160 | 38.1 | 15.0 | 65.6 | 49.4 | 42.0 |
|  | GBIF | 51 | 70.6 | 21.6 | 54.9 | 29.4 | 44.1 |
|  | NEON | 23 | 56.5 | 60.9 | 30.4 | 17.4 | 41.3 |
|  | EPA AQS | 11 | 54.5 | 9.1 | 63.6 | 18.2 | 36.4 |
| Gemini 2.5 Flash | USGS | 160 | 4.4 | 19.4 | 50.0 | 30.6 | 26.1 |
|  | GBIF | 51 | 7.8 | 15.7 | 47.1 | 19.6 | 22.5 |
|  | NEON | 23 | 17.4 | 52.2 | 8.7 | 17.4 | 23.9 |
|  | EPA AQS | 11 | 27.3 | 18.2 | 45.5 | 18.2 | 27.3 |
| Qwen 3.6 27B | USGS | 160 | 40.6 | 25.6 | 63.1 | 51.9 | 45.3 |
|  | GBIF | 51 | 68.6 | 43.1 | 52.9 | 21.6 | 46.6 |
|  | NEON | 23 | 43.5 | 73.9 | 34.8 | 43.5 | 48.9 |
|  | EPA AQS | 11 | 27.3 | 9.1 | 63.6 | 36.4 | 34.1 |
| Gemma 4 31B | USGS | 160 | 30.0 | 14.4 | 60.0 | 48.8 | 38.3 |
|  | GBIF | 51 | 78.4 | 62.7 | 52.9 | 27.5 | 55.4 |
|  | NEON | 23 | 13.0 | 52.2 | 26.1 | 26.1 | 29.3 |
|  | EPA AQS | 11 | 54.5 | 18.2 | 63.6 | 18.2 | 38.6 |
| GPT-OSS 120B | USGS | 160 | 21.2 | 25.0 | 38.1 | 21.9 | 26.6 |
|  | GBIF | 51 | 45.1 | 47.1 | 43.1 | 19.6 | 38.7 |
|  | NEON | 23 | 26.1 | 60.9 | 4.3 | 4.3 | 23.9 |
|  | EPA AQS | 11 | 36.4 | 9.1 | 45.5 | 9.1 | 25.0 |

## S6.2 Tool calls per scenario

The number of `run_python` and `run_bash` invocations, averaged over the
scenarios for which a record exists. In Phase 2, the count covers the tool
use while composing calls; the calls themselves are executed separately by
the grader and are not counted.

| Model | P1 | P2 | P3 | P4 |
| --- | ---: | ---: | ---: | ---: |
| Gemini 3.7 Flash | 6.4 | 4.4 | 11.9 | 13.9 |
| Gemini 3.1 Pro | 9.2 | 4.4 | 10.6 | 10.0 |
| Gemini 3 Flash | 10.1 | 5.9 | 7.3 | 7.9 |
| Gemini 2.5 Pro | 6.3 | 0.8 | 6.4 | 7.6 |
| Gemini 2.5 Flash | 1.7 | 1.8 | 5.9 | 4.9 |
| Qwen 3.6 27B | 14.7 | 6.9 | 8.1 | 11.4 |
| Gemma 4 31B | 10.6 | 2.2 | 5.9 | 5.9 |
| GPT-OSS 120B | 13.3 | 6.3 | 6.9 | 6.8 |

### By platform

| Model | Platform | P1 | P2 | P3 | P4 |
| --- | --- | ---: | ---: | ---: | ---: |
| Gemini 3.7 Flash | USGS | 8.0 | 5.0 | 11.1 | 14.6 |
|  | GBIF | 2.7 | 2.4 | 11.9 | 11.6 |
|  | NEON | 3.3 | 4.3 | 16.4 | 14.5 |
|  | EPA AQS | 6.1 | 5.4 | 15.5 | 13.6 |
| Gemini 3.1 Pro | USGS | 11.8 | 4.2 | 9.8 | 9.8 |
|  | GBIF | 3.9 | 3.1 | 8.7 | 7.3 |
|  | NEON | 2.5 | 5.2 | 15.7 | 16.3 |
|  | EPA AQS | 9.9 | 11.9 | 20.1 | 11.6 |
| Gemini 3 Flash | USGS | 11.5 | 6.4 | 7.1 | 7.6 |
|  | GBIF | 7.5 | 5.0 | 6.9 | 6.5 |
|  | NEON | 4.6 | 3.3 | 7.8 | 13.3 |
|  | EPA AQS | 13.0 | 7.7 | 9.7 | 7.3 |
| Gemini 2.5 Pro | USGS | 7.0 | 0.7 | 6.5 | 7.3 |
|  | GBIF | 3.7 | 0.5 | 4.3 | 4.8 |
|  | NEON | 5.5 | 1.8 | 12.7 | 18.1 |
|  | EPA AQS | 8.5 | 1.7 | 2.8 | 3.6 |
| Gemini 2.5 Flash | USGS | 1.9 | 1.9 | 6.4 | 5.4 |
|  | GBIF | 0.4 | 1.5 | 3.0 | 3.0 |
|  | NEON | 2.3 | 1.7 | 10.7 | 6.7 |
|  | EPA AQS | 3.5 | 3.3 | 3.3 | 2.8 |
| Qwen 3.6 27B | USGS | 17.3 | 6.3 | 7.5 | 10.4 |
|  | GBIF | 6.8 | 10.4 | 6.1 | 9.8 |
|  | NEON | 14.2 | 4.4 | 16.6 | 20.8 |
|  | EPA AQS | 13.3 | 5.3 | 8.9 | 12.8 |
| Gemma 4 31B | USGS | 13.5 | 1.8 | 6.0 | 6.6 |
|  | GBIF | 3.9 | 3.0 | 3.8 | 2.8 |
|  | NEON | 6.1 | 2.0 | 10.2 | 8.3 |
|  | EPA AQS | 7.3 | 3.8 | 4.9 | 4.7 |
| GPT-OSS 120B | USGS | 15.9 | 7.1 | 6.8 | 6.8 |
|  | GBIF | 5.9 | 3.3 | 5.2 | 6.2 |
|  | NEON | 11.4 | 5.5 | 12.2 | 10.1 |
|  | EPA AQS | 13.8 | 10.4 | 6.5 | 4.5 |

## S6.3 Tokens per scenario (thousands)

Input plus output tokens, averaged over the scenarios for which a record
exists. This is the token use reported in Table 2 of the paper.

| Model | P1 | P2 | P3 | P4 |
| --- | ---: | ---: | ---: | ---: |
| Gemini 3.7 Flash | 73.8 | 24.1 | 153.0 | 202.1 |
| Gemini 3.1 Pro | 84.8 | 33.3 | 180.0 | 202.3 |
| Gemini 3 Flash | 95.4 | 54.1 | 87.5 | 117.5 |
| Gemini 2.5 Pro | 58.3 | 6.3 | 100.9 | 153.6 |
| Gemini 2.5 Flash | 23.1 | 15.2 | 86.5 | 86.9 |
| Qwen 3.6 27B | 177.6 | 59.4 | 125.4 | 193.0 |
| Gemma 4 31B | 88.2 | 10.2 | 69.4 | 89.4 |
| GPT-OSS 120B | 76.3 | 25.7 | 70.4 | 74.3 |

### By platform

| Model | Platform | P1 | P2 | P3 | P4 |
| --- | --- | ---: | ---: | ---: | ---: |
| Gemini 3.7 Flash | USGS | 104.2 | 27.6 | 145.2 | 233.0 |
|  | GBIF | 9.2 | 16.6 | 105.5 | 95.8 |
|  | NEON | 26.1 | 16.8 | 267.8 | 249.3 |
|  | EPA AQS | 30.1 | 24.8 | 246.5 | 146.2 |
| Gemini 3.1 Pro | USGS | 118.8 | 27.7 | 170.8 | 207.1 |
|  | GBIF | 15.2 | 29.5 | 78.5 | 79.8 |
|  | NEON | 11.5 | 28.6 | 347.4 | 396.3 |
|  | EPA AQS | 66.2 | 142.9 | 425.2 | 285.1 |
| Gemini 3 Flash | USGS | 115.4 | 55.9 | 92.4 | 113.4 |
|  | GBIF | 58.5 | 59.1 | 41.7 | 42.9 |
|  | NEON | 43.8 | 14.1 | 125.6 | 324.0 |
|  | EPA AQS | 84.8 | 89.4 | 150.1 | 91.9 |
| Gemini 2.5 Pro | USGS | 68.9 | 6.0 | 92.6 | 126.8 |
|  | GBIF | 22.6 | 5.0 | 28.9 | 39.4 |
|  | NEON | 64.6 | 6.8 | 351.1 | 637.2 |
|  | EPA AQS | 56.9 | 15.3 | 33.4 | 61.0 |
| Gemini 2.5 Flash | USGS | 31.0 | 17.1 | 82.9 | 80.7 |
|  | GBIF | 2.9 | 10.3 | 15.6 | 19.7 |
|  | NEON | 13.4 | 6.3 | 296.3 | 301.8 |
|  | EPA AQS | 21.3 | 29.1 | 28.3 | 38.5 |
| Qwen 3.6 27B | USGS | 220.9 | 51.9 | 110.7 | 178.2 |
|  | GBIF | 49.0 | 101.6 | 38.8 | 91.2 |
|  | NEON | 204.4 | 21.7 | 418.7 | 498.9 |
|  | EPA AQS | 87.3 | 51.8 | 127.1 | 239.9 |
| Gemma 4 31B | USGS | 121.7 | 8.8 | 73.5 | 102.2 |
|  | GBIF | 17.1 | 14.2 | 19.1 | 15.8 |
|  | NEON | 35.7 | 6.1 | 162.2 | 181.7 |
|  | EPA AQS | 40.6 | 19.2 | 49.1 | 51.9 |
| GPT-OSS 120B | USGS | 94.5 | 29.5 | 69.8 | 74.4 |
|  | GBIF | 28.8 | 13.7 | 30.1 | 41.4 |
|  | NEON | 54.8 | 20.9 | 154.8 | 164.2 |
|  | EPA AQS | 77.0 | 36.7 | 89.9 | 44.7 |

## S6.4 Token breakdown per scenario (thousands)

The same averages, split into the three quantities that the cost of S5 is
computed from. Cached input is part of input. Output includes thinking
tokens. No cached input is recorded for the open-weights models, which
were served locally.

| Model | Tokens | P1 | P2 | P3 | P4 |
| --- | --- | ---: | ---: | ---: | ---: |
| Gemini 3.7 Flash | Input | 71.8 | 23.4 | 151.2 | 198.5 |
|  | Cached input | 28.0 | 0.2 | 55.8 | 86.9 |
|  | Output | 2.01 | 0.74 | 1.86 | 3.53 |
| Gemini 3.1 Pro | Input | 80.5 | 30.9 | 174.0 | 194.3 |
|  | Cached input | 34.3 | 6.8 | 116.5 | 136.0 |
|  | Output | 4.28 | 2.40 | 6.08 | 8.00 |
| Gemini 3 Flash | Input | 92.6 | 52.8 | 85.1 | 113.5 |
|  | Cached input | 56.4 | 29.4 | 55.5 | 79.2 |
|  | Output | 2.79 | 1.39 | 2.40 | 4.03 |
| Gemini 2.5 Pro | Input | 54.2 | 5.0 | 97.4 | 145.6 |
|  | Cached input | 24.8 | 0.4 | 62.4 | 100.8 |
|  | Output | 4.17 | 1.31 | 3.54 | 7.99 |
| Gemini 2.5 Flash | Input | 22.1 | 14.0 | 82.2 | 81.0 |
|  | Cached input | 13.7 | 6.7 | 49.2 | 46.4 |
|  | Output | 0.91 | 1.13 | 4.27 | 5.89 |
| Qwen 3.6 27B | Input | 171.9 | 54.8 | 121.1 | 185.3 |
|  | Cached input | 0.0 | 0.0 | 0.0 | 0.0 |
|  | Output | 5.72 | 4.63 | 4.23 | 7.70 |
| Gemma 4 31B | Input | 85.8 | 9.7 | 67.7 | 85.9 |
|  | Cached input | 0.0 | 0.0 | 0.0 | 0.0 |
|  | Output | 2.40 | 0.44 | 1.70 | 3.53 |
| GPT-OSS 120B | Input | 72.3 | 23.7 | 68.2 | 71.4 |
|  | Cached input | 0.0 | 0.0 | 0.0 | 0.0 |
|  | Output | 4.04 | 1.99 | 2.21 | 2.83 |

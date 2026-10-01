# SciDataBench

Can a language agent get the right data out of a real scientific data API?

SciDataBench gives an agent a researcher's request and checks the answer
against a published paper that used the same API. Every scenario walks through
the same four phases:

1. **Find the identifiers** the request needs (a site code, a taxon key, a
   parameter code, …).
2. **Write the API calls** that retrieve the data.
3. **Process the data** into an intermediate number.
4. **Answer the research question** with the paper's headline number.

There are two scenario sets:

- **SciDataBench** — 245 scenarios on NEON, GBIF, USGS and EPA AQS, all four
  phases.
- **SciDataBench-Onboard** — 210 scenarios on eleven more platforms (Argo,
  American Community Survey, CMIP6, Ensembl, iNaturalist, Materials Project,
  NOAA GHCN, OBIS, PANGAEA, USGS Earthquake Catalog, VizieR), phases 1 and 2.

The paper's supplementary material (grading specifications, threshold
sensitivity, pricing and per-model results) is in
[`supplementary/`](supplementary/README.md).

## Install

Python 3.12:

```bash
git clone https://github.com/ixlab/scidatabench.git
cd scidatabench
pip install -r requirements.txt
```

Set an API key for the model you want to test:

```bash
export GOOGLE_API_KEY=...        # Gemini models
```

Any model behind an OpenAI-compatible endpoint (for example a local vLLM
server) works too — see [Other models](#other-models).

## Quick start

Run one scenario through phases 1 and 2:

```bash
python scripts/run_eval.py \
    --model gemini-3-flash-preview \
    --run-id quickstart \
    --scenario usgs/10.1002_hyp.13669_scenario \
    --phases 1,2 --no-sandbox
```

The agent's answer and full trace for each phase land in

```
results/runs/quickstart/per_scenario/usgs/10.1002_hyp.13669_scenario/
    phase_1.json    # "binary_pass": true or false
    phase_2.json    # the API calls the agent wrote
```

Phase 2 is graded on the data the calls actually return, so it takes two more
commands — see [Grading phase 2](#grading-phase-2).

## Running the full benchmark

Phases 3 and 4 work on data that has already been downloaded, so they need the
**gold snapshot** first (see [Gold snapshots](#gold-snapshots)). Then:

```bash
python scripts/run_eval.py --model gemini-3-flash-preview --run-id my_run
```

Useful options:

| Option | What it does |
|---|---|
| `--platform usgs,gbif` | only these platforms |
| `--scenario <platform>/<name>` | only this scenario (repeatable) |
| `--phases 1,2` | only these phases |
| `--workers 8` | run scenarios in parallel |
| `--limit 5` | stop after 5 scenarios |
| `--no-resume` | redo phases that already have a result |

Runs resume by default: rerunning the same `--run-id` skips finished phases.

To try SciDataBench-Onboard instead:

```bash
python scripts/run_eval.py --model gemini-3-flash-preview --run-id my_onboard_run \
    --bench-root data/scidatabench-onboard \
    --gold-root gold/scidatabench-onboard --phases 1,2
```

## Grading phase 2

Execute the calls the agent wrote, then compare what they returned with the
gold snapshot:

```bash
python scripts/execute_calls.py --run-id my_run
python scripts/grade_phase2.py  --run-id my_run
```

`grade_phase2.py` prints a pass rate per platform and writes a
`phase_2.exec.json` next to each `phase_2.json`. For SciDataBench-Onboard, add
`--gold-root gold/scidatabench-onboard` to `grade_phase2.py`.

Executing the calls needs the platforms' credentials:

| Variable | Platform |
|---|---|
| `NEON_TOKEN` | NEON |
| `API_USGS_PAT` | USGS Water Data |
| `AQS_USER`, `AQS_KEY` | EPA AQS |
| `CENSUS_API_KEY` | American Community Survey |
| `MP_API_KEY` | Materials Project |

## Reading the results

Every phase writes one JSON file; `binary_pass` says whether it passed. A quick
pass rate per phase:

```python
import json, glob, collections
passed, total = collections.Counter(), collections.Counter()
for f in glob.glob("results/runs/my_run/per_scenario/*/*/phase_[134].json") + \
         glob.glob("results/runs/my_run/per_scenario/*/*/phase_2.exec.json"):
    phase = f.split("phase_")[1][0]
    total[phase] += 1
    passed[phase] += json.load(open(f)).get("binary_pass") is True
for phase in sorted(total):
    print(f"phase {phase}: {passed[phase]}/{total[phase]}")
```

## Gold snapshots

Phases 3 and 4 read the data the gold API calls returned, and phase 2 is
graded against it. The snapshots go under `gold/scidatabench/` and
`gold/scidatabench-onboard/`.

> **Coming soon.** The snapshots we used are not released yet. They contain
> records from many data providers, each under its own terms, and we will
> publish them once we have finished reviewing those licenses.

In the meantime you can build a snapshot yourself from the live APIs. The
services keep changing, so it will not match ours exactly:

```bash
python scripts/build_gold.py --bench-root data/scidatabench --out gold/scidatabench
```

## Other models

Point the harness at any OpenAI-compatible endpoint:

```bash
python scripts/run_eval.py --model Qwen/Qwen3.6-27B --provider openai \
    --base-url http://localhost:8000/v1 --run-id qwen_run
```

Use `--api-key-env MY_KEY_VAR` if the endpoint needs a key.

## Giving the agent a platform guide

`skills/` holds short guides to each SciDataBench-Onboard platform, written by
an onboarding agent. Pass one to the task agent with `--skill`:

```bash
python scripts/run_eval.py --model gemini-3-flash-preview --run-id with_guide \
    --bench-root data/scidatabench-onboard --gold-root gold/scidatabench-onboard \
    --phases 1,2 --skill skills/gemini-3.7-flash/exec
```

To write your own guides with an onboarding agent:

```bash
python scripts/run_onboarding.py --condition exec \
    --model gemini-3.7-flash --out-dir skills/my-guides/exec
```

`--condition search` lets the onboarding agent read documentation on the web
instead of calling the platform's client (set `TAVILY_API_KEY` or
`SERPER_API_KEY` for search).

## Rephrased requests

`data/perturbations/` holds rewritten versions of the SciDataBench requests —
same task, different wording — to check whether an agent's result depends on
the exact phrasing:

```bash
python scripts/run_eval.py --model gemini-3-flash-preview --run-id reworded \
    --bench-root data/perturbations/phase1-catalogue-synonym --phases 1
```

## Sandbox

By default `run_eval.py` runs the agent inside a
[bubblewrap](https://github.com/containers/bubblewrap) sandbox, so the agent's
code cannot read the answers from the scenario files or the gold snapshot. It
needs `bwrap` installed and an existing, unused directory as the parent of
`SCIDATABENCH_SEALED_ROOT` (default `/srv/scidatabench-sealed`). Use
`--no-sandbox` to skip it, for example when trying things out.

## What's in the repository

```
data/          the scenarios (one JSON file each) and their source papers
skills/        platform guides for SciDataBench-Onboard
harness/       the task agent: prompts, tools, runner
grading/       graders for all four phases
executor/      runs API calls for phase 2 and for the gold snapshot
scripts/       the commands above
supplementary/ supplementary material for the paper
```

## Citation

[to be added]

## License

- **Code** (`harness/`, `grading/`, `executor/`, `scripts/`): [MIT](LICENSE).
- **Benchmark data** (`data/`), **platform guides** (`skills/`) **and
  supplementary material** (`supplementary/`): [CC BY 4.0](data/LICENSE).
  You are free to use, share and adapt them; please cite SciDataBench when
  you do.
- **Gold snapshots** are not covered by these licenses. They hold records
  from the data platforms, which remain under each provider's own terms.

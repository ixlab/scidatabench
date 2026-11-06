---
license: cc-by-4.0
language:
- en
pretty_name: SciDataBench
task_categories:
- question-answering
- text-generation
tags:
- benchmark
- agents
- tool-use
- scientific-data
- data-access
- ecology
- biodiversity
- environmental-science
size_categories:
- n<1K
description: SciDataBench is a benchmark of research requests drawn from published papers for evaluating whether language agents can find, retrieve, and analyze data from live scientific data APIs (NEON, GBIF, USGS, EPA AQS, and eleven further platforms).
---

# Dataset Card for SciDataBench

SciDataBench evaluates whether a language agent can acquire the right data from a live scientific data API on a researcher's behalf. Each scenario is built from a published paper whose analysis uses only one platform's API, so the paper's reported result serves as the answer key.

## Dataset Details

### Dataset Description

- **Curated by:** Hojin Yoo, Eric Sokol, Christine Laney, Hamoud Alhazmi, Tanya Berger-Wolf, Arnab Nandi
- **Language(s) (NLP):** English
- **Repository:** https://github.com/ixlab/scidatabench
- **Paper:** Under review; a link will be added once it is public.

Scientific data platforms are reached through APIs that require identifiers the user usually does not know (site codes, taxon keys, parameter codes) and follow conventions that are rarely fully documented. SciDataBench turns published research into scenarios that test this data acquisition step. Each scenario gives the agent a researcher's request and decomposes the workflow into four phases:

1. **Identifier discovery:** find the platform identifiers the request needs.
2. **Retrieval:** write the API calls that retrieve the data.
3. **Preprocessing:** reduce the returned data to an intermediate quantity.
4. **Research-question answering:** compute the paper's headline number.

The release contains three scenario sets:

| Set | Folder | Platforms | Phases | Scenarios |
|---|---|---|---|---:|
| SciDataBench | `scidatabench/` | NEON, GBIF, USGS Water Data, EPA AQS | 1 to 4 | 245 |
| SciDataBench-Onboard | `scidatabench-onboard/` | Argo, American Community Survey, CMIP6, Ensembl, iNaturalist, Materials Project, NOAA GHCN, OBIS, PANGAEA, USGS Earthquake Catalog, VizieR | 1 and 2 | 210 |
| Perturbations | `perturbations/` | Same as SciDataBench | One phase per set | 391 |

**These files do not contain observational data from the platforms.** A scenario records the request, the gold platform identifiers, the gold API calls, and the gold numeric answers. The observational data itself is downloaded from each platform's live API when the benchmark is run (see [Gold snapshots](https://github.com/ixlab/scidatabench#gold-snapshots)) and remains under that platform's own terms.

### Supported Tasks and Leaderboards

SciDataBench is an evaluation-only benchmark for language agents that use tools to access scientific data. Each phase is graded by a binary pass criterion:

- **Phase 1:** mean per-key F1 between the agent's identifiers and the gold identifiers.
- **Phase 2:** the agent's calls are executed against the live platform, and the returned records are compared with those of the gold calls (record coverage, value agreement, time coverage, and an upper bound on result size).
- **Phases 3 and 4:** the agent's number must fall within a 5% relative tolerance of the gold value.

The evaluation harness and graders are in the [repository](https://github.com/ixlab/scidatabench). There is no public leaderboard at this time; per-model results from the paper are in [`supplementary/`](https://github.com/ixlab/scidatabench/tree/main/supplementary).

## Dataset Structure

```
data/
    scidatabench/
        epa/  gbif/  neon/  usgs/
            <scenario>.json
        papers.csv
        README.md
    scidatabench-onboard/
        argo/  census_acs/  cmip6/  ensembl/  inaturalist/  matproj/
        noaa_ghcn/  obis/  pangaea/  usgs_eq/  vizier/
            <scenario>.json
        papers.csv
        README.md
    perturbations/
        phase1-catalogue-synonym/
        phase2-anchor-duration/
        phase3-alternate-unit/
        phase4-method-paraphrase/
            <platform>/<scenario>.json
        README.md
    LICENSE
```

### Data Instances

Each scenario is one JSON file. An abbreviated example from `scidatabench/usgs/10.1002_hyp.13669_scenario.json`:

```json
{
  "source_doi": "10.1002/hyp.13669",
  "research_question": "Can semiparametric methods like Multivariate Adaptive Regression Splines (MARS) effectively capture non-linear and time-varying relationships between nutrient concentrations and streamflow in the Chesapeake Bay watershed?",
  "phase_1": {
    "user_prompt": "I am conducting a study on riverine nutrient estimation methods. I need to find the USGS streamgage for the Patuxent River near Bowie, Maryland, ...",
    "expected": {"sites": ["01594440"], "parameter_codes": ["00060", "00631"]}
  },
  "phase_2": {
    "user_prompt": "Download the continuous daily discharge data and all available discrete sample records ...",
    "expected": [
      {
        "module": "dataretrieval.waterdata",
        "function": "get_daily",
        "kwargs": {"monitoring_location_id": "USGS-01594440", "parameter_code": "00060", "time": "1985-01-01/2017-12-31"}
      }
    ]
  },
  "phase_3": {"user_prompt": "Clean and merge the two datasets. ...", "expected": 1000, "unit": "observations"},
  "phase_4": {"user_prompt": "...", "expected": "...", "unit": "..."}
}
```

### Data Fields

**Scenario files** (`<platform>/<scenario>.json`):

| Field | Content |
|---|---|
| `source_doi` | DOI of the paper the scenario is built from |
| `research_question` | The paper's research question |
| `phase_1.user_prompt` | Request for the platform identifiers |
| `phase_1.expected` | Gold identifiers, one list per key of the platform's identifier schema |
| `phase_2.user_prompt` | Request for the data |
| `phase_2.expected` | Gold calls, each with `module`, `function`, and `kwargs` |
| `phase_3.user_prompt` | Request for the intermediate quantity |
| `phase_3.expected` | Gold value: a number, or an object or list of numbers |
| `phase_3.unit` | Unit of the gold value |
| `phase_4.user_prompt` | Request for the paper's headline finding |
| `phase_4.expected` | Gold numeric value |
| `phase_4.unit` | Unit of the gold value |
| `phase_4.checkpoint` | The paper's qualitative conclusion and figure reference, where the request also asks for them; recorded but not graded |

SciDataBench-Onboard scenarios contain only `source_doi`, `research_question`, `phase_1`, and `phase_2`. Perturbation scenarios have the same format as SciDataBench; only the request of the perturbed phase differs, and for Phase 3 the gold value and unit are converted accordingly.

**`papers.csv`:** `platform`, `scenario`, `doi`, `title`, `first_author`, `year`, `journal` for the source paper of every scenario. The full list of 455 source papers is also in [PAPERS.md](https://github.com/ixlab/scidatabench/blob/main/PAPERS.md).

### Data Splits

There is no train/test split. All scenarios are intended for evaluation. The three sets above serve as separate configurations: `scidatabench` (main corpus), `scidatabench-onboard` (held-out platforms), and `perturbations` (robustness checks, with one subset per phase).

## Dataset Creation

### Curation Rationale

Existing data agent benchmarks start with the data already in hand, and text-to-SQL benchmarks host the database and declare its schema. Neither measures whether an agent can acquire data from a live scientific platform it does not control. SciDataBench fills this gap and uses published papers as the source of verifiable ground truth: restricting the source set to papers whose analysis uses a single platform's API and no external data means each reported result is recoverable from the API alone.

### Source Data

#### Data Collection and Processing

Candidate papers were drawn from the OpenAlex bibliographic catalog by querying each platform's full name, except for GBIF, where the curated paper list published on the GBIF website was used. Two LLM agents then filtered the candidates: the first retained papers whose analysis consumes data fetched from the platform, and the second applied a seven-point rejection rubric covering document type, data accessibility, external-data dependency, platform centrality, methodological detail, the existence of a reproducible quantitative result, and scope. Of 5,005 candidates for the main corpus, 642 passed the first filter and 362 the second. Each surviving paper yields one scenario. SciDataBench-Onboard was built with the same pipeline on eleven further platforms.

#### Who are the source data producers?

The research questions and target results come from the authors of the 455 source papers listed in `papers.csv` and PAPERS.md. The platform identifiers and API calls refer to data published by the platforms themselves (for example, NEON, operated by Battelle for the U.S. National Science Foundation; GBIF; the U.S. Geological Survey; and the U.S. Environmental Protection Agency). Source papers are not redistributed in this dataset; scenarios reference them by DOI.

### Annotations

#### Annotation process

Scenario requests and gold values were generated from each paper and then validated by an author against three checks: every Phase 1 identifier appears in the source paper, the Phase 2 gold calls execute against the live API, and each Phase 3 and Phase 4 value is either stated in the paper or is the deterministic output of an author-executed computation on the data the gold calls return. Scenarios that failed a check, or that could not be graded on all of their phases, were removed (32% of generated scenarios), leaving 245 in the main corpus. Perturbation sets rewrite one surface feature of the request per phase while holding the task fixed, and the gold value is recomputed wherever a rewrite changes it.

#### Who are the annotators?

The authors, who are graduate-level researchers in computer science experienced with scientific data APIs. Scenarios were not reviewed by domain scientists.

### Personal and Sensitive Information

The scenarios contain no personal information. They describe published research questions and refer to public platform identifiers (for example, station numbers, taxon keys, and data product codes). The American Community Survey scenarios refer to aggregate census statistics, not individual records.

## Considerations for Using the Data

The platforms are live services whose holdings change over time: records are added and, on some platforms such as USGS and EPA AQS, values are revised in place. Running the gold calls today can return more or different data than at validation. The [`snapshots/`](https://github.com/ixlab/scidatabench/tree/main/snapshots) folder records when each gold call was downloaded and how many rows it returned, so results can be aligned with the paper's snapshot.

### Bias, Risks, and Limitations

- **Platform imbalance:** USGS contributes 160 of the 245 main-corpus scenarios.
- **Domain coverage:** the main corpus is centered on ecological and environmental science; SciDataBench-Onboard extends to oceanography, genomics, astronomy, materials science, climate model output, and demographic statistics, but covers only Phases 1 and 2.
- **Request phrasing:** requests and phase boundaries reflect the authors' reading of each paper and may differ from how a domain scientist would phrase them.
- **Ground truth:** gold values follow the published papers and inherit any errors in them.
- **Language:** all requests are in English.

### Recommendations

Report results per phase rather than as a single end-to-end score, since each phase starts from the gold output of the previous one. When comparing with the paper, align the downloaded data with `snapshots/`. Keep the evaluation sandbox enabled so agents cannot read gold answers from the scenario files.

## Licensing Information

The scenario files, `papers.csv`, and the perturbation sets in this folder are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). If you use them, please cite SciDataBench as shown below.

This license covers the benchmark files only. **Data downloaded from the platforms** (for example with `build_gold.py` or by running the benchmark) is not part of this dataset and remains under each platform's own terms. If you publish work that uses that data, attribute it according to the platform's citation guidelines:

| Platform | Citation and use guidelines |
|---|---|
| NEON | https://www.neonscience.org/data-samples/data-policies-citation |
| GBIF | https://www.gbif.org/citation-guidelines |
| USGS Water Data | https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits |
| EPA AQS | https://www.epa.gov/aqs |

The platforms in SciDataBench-Onboard each have their own terms; see each platform's website.

The code in the repository (`harness/`, `grading/`, `executor/`, `scripts/`) is licensed separately under MIT.

## Citation

If you use SciDataBench, please cite:

**BibTeX:**

```bibtex
@software{scidatabench,
  author = {Yoo, Hojin and Sokol, Eric and Laney, Christine and
            Alhazmi, Hamoud and Berger-Wolf, Tanya and Nandi, Arnab},
  title  = {SciDataBench: A Paper-Grounded Benchmark for Language
            Agents on Scientific Data APIs},
  year   = {2026},
  url    = {https://github.com/ixlab/scidatabench}
}
```

A paper citation will be added once the paper is public. Please also cite the source papers of any scenarios you report on individually (see `papers.csv`) and attribute any platform data you publish as described in [Licensing Information](#licensing-information).

## Acknowledgements

This work was supported by the [Imageomics Institute](https://imageomics.org), which is funded by the US National Science Foundation's Harnessing the Data Revolution (HDR) program under [Award #2118240](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2118240) (Imageomics: A New Frontier of Biological Information Powered by Knowledge-Guided Machine Learning), and by the [FAIR4AI-Bio](https://github.com/FAIR4AI-Bio) initiative, funded by the NSF Findable Accessible Interoperable Reusable Open Science (FAIROS) program under [Award #2531922](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2531922) (Collaborative Research: Disciplinary Improvements: AI-ready Ecology and Biodiversity Data Infrastructure for Open Science).

This material is based in part upon work supported by the National Ecological Observatory Network (NEON), a program sponsored by the U.S. National Science Foundation (NSF) and operated under cooperative agreement by Battelle.

Any opinions, findings and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the National Science Foundation.

## Glossary

- **Scenario:** one research request built from one published paper, with gold outputs for each phase.
- **Platform:** a scientific data service reached through a live API (for example, NEON or GBIF).
- **Gold call:** the reference API call whose returned records define the correct Phase 2 result.
- **Onboarding:** preparing an agent to work on an unfamiliar platform by supplying a written guide (a "skill"); the guides used in the paper are in [`skills/`](https://github.com/ixlab/scidatabench/tree/main/skills).

## Dataset Card Authors

Hojin Yoo

## Dataset Card Contact

Hojin Yoo (yoo.515@osu.edu)

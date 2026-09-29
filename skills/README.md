# Onboarding skills

Platform guides written by the onboarding agent (`scripts/run_onboarding.py`)
for the eleven SciDataBench-Onboard platforms.

```
<author model>/<acquisition method>/
    SKILL_phase1_<platform>.md   how to find the platform's identifiers
    SKILL_phase2_<platform>.md   how to construct calls to its API
    run_<platform>.json          model, tokens, tool-call turns and elapsed
                                 time of the onboarding run; for `search`, the
                                 searches and pages it read
```

| Folder | Written by | Acquisition method |
|---|---|---|
| `gemini-3-flash/search/` | Gemini 3 Flash | web search and page fetches |
| `gemini-3-flash/exec/` | Gemini 3 Flash | importing and calling the platform client |
| `gemini-3.7-flash/search/` | Gemini 3.7 Flash | web search and page fetches |
| `gemini-3.7-flash/exec/` | Gemini 3.7 Flash | importing and calling the platform client |

A task agent reads one folder with `scripts/run_eval.py --skill <folder>`: the
document for the active phase and platform is prepended to that phase's
request.

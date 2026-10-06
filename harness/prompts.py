"""Per-phase prompt builders.

The prompts are split by what the agent is supposed to do:
    Phases 1 & 2 — IDENTIFICATION: the data is NOT yet downloaded.
        The agent must work out what to fetch (data products / sites /
        taxon keys / parameter codes / ...) and which calls to issue,
        using only the platform Python package as a reference. The only
        tool exposed is `run_python` (so the agent can `import` the
        package and read its docstrings / signatures).
    Phases 3 & 4 — COMPUTATION: a CACHE_ROOT directory contains the
        files produced by phase-2's calls. The agent gets `run_bash` for
        filesystem exploration and `run_python` for the actual data work.

The system content is inlined into the first user message of a phase (see
history.py) rather than sent as a SystemMessage: with tools bound, Gemini 2.5
Flash sometimes returned an empty AIMessage when given a system prompt.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import schemas


# ---------------------------------------------------------------------------
# Onboarding skills (paper, Section 4)
#
# A skill directory holds one document per phase and platform, written by the
# onboarding agent (scripts/run_onboarding.py):
#     <skill_dir>/SKILL_phase1_<platform>.md   how to find identifiers
#     <skill_dir>/SKILL_phase2_<platform>.md   how to construct calls
# The document for the active phase is prepended to that phase's request.
# ---------------------------------------------------------------------------

def load_skill(skill_dir: str | Path | None, phase: int, platform: str) -> str:
    """The skill text for (phase, platform), or "" when there is none."""
    if not skill_dir:
        return ""
    p = Path(skill_dir) / f"SKILL_phase{int(phase)}_{platform}.md"
    return p.read_text().strip() if p.exists() else ""


def _inject_skill(body: str, skill_text: str) -> str:
    """Prepend a `## Reference knowledge` section to `body`. The skill
    files already start with their own H1/H2 headings, so we just wrap
    the whole block in section separators rather than mutating it."""
    if not skill_text:
        return body
    return (
        "## Reference knowledge\n"
        "Use the platform-specific guidance below to inform your "
        "decisions in this phase.\n\n"
        + skill_text.strip()
        + "\n\n---\n\n"
        + body
    )


# ---------------------------------------------------------------------------
# Prologues. PROLOGUE_IDENT opens phases 1 and 2, PROLOGUE_COMPUTE phases 3
# and 4. The two phase-1 variants are the tool ablation of Section 4.2:
# `notools` binds no tool at all, `offline` keeps run_python but cuts the
# network.
# ---------------------------------------------------------------------------

# Appended to every prologue. The REPL has no stdin and a read-only
# filesystem outside `results/` + /tmp; commands that try to install
# packages or wait for keyboard input will hang or fail.
_GLOBAL_GUARDRAILS = """\
Environment constraints:
- Do NOT install or upgrade packages (no `pip install`, `!pip`, `subprocess`
  invocations of pip / conda / apt / R `install.packages`). All required
  packages are already available. The filesystem is read-only outside the
  scenario output directory, so writes elsewhere fail with EROFS.
- The `run_python` REPL has NO stdin. Never run code that waits for
  interactive input — no `input()`, no `getpass`, no shell commands that
  pause for `y/n` confirmation. If a tool you must invoke would prompt,
  pass its non-interactive flag up front (e.g. `-y`, `--yes`, `--quiet`,
  `--non-interactive`) so the call cannot block. A blocked call wastes the
  entire scenario budget.
"""


PROLOGUE_IDENT = """\
You are a scientific-data agent. The dataset has NOT yet been downloaded —
your job is to identify (a) which data items the user wants and (b) which
package functions to call to fetch them. Available tool: `run_python` (a
persistent Python REPL with `pd`, `np`, `Path`, `glob`, `zipfile`, `os`, `io`
pre-loaded). You may `import` the platform package and inspect its
docstrings / signatures (e.g. `help(...)`, `dir(...)`) but DO NOT actually
fetch data — phase 2 only enumerates the calls. End every reply with EXACTLY
ONE fenced ```json``` block matching the output structure. Do not invent
fields.
""" + "\n" + _GLOBAL_GUARDRAILS


PROLOGUE_IDENT_NOTOOLS = """\
You are a scientific-data agent. The dataset has NOT yet been downloaded —
your job is to identify (a) which data items the user wants and (b) which
package functions to call to fetch them. NO tools are available in this
session: there is no Python REPL, no shell and no network, so you cannot
import the platform package, read its documentation, or query the service.
Answer from what you already know. End every reply with EXACTLY ONE fenced
```json``` block matching the output structure. Do not invent fields.
"""


PROLOGUE_IDENT_OFFLINE = """\
You are a scientific-data agent. The dataset has NOT yet been downloaded —
your job is to identify (a) which data items the user wants and (b) which
package functions to call to fetch them. Available tool: `run_python` (a
persistent Python REPL with `pd`, `np`, `Path`, `glob`, `zipfile`, `os`, `io`
pre-loaded). This session has NO NETWORK ACCESS: you may `import` the platform
package and inspect its docstrings / signatures (e.g. `help(...)`,
`dir(...)`), but every request that contacts a server will fail, so identifier
values must come from your own knowledge. End every reply with EXACTLY ONE
fenced ```json``` block matching the output structure. Do not invent fields.
""" + "\n" + _GLOBAL_GUARDRAILS


PROLOGUE_IDENT_BY_MODE = {
    "notools": PROLOGUE_IDENT_NOTOOLS,
    "offline": PROLOGUE_IDENT_OFFLINE,
}


PROLOGUE_COMPUTE = """\
You are a scientific-data agent with access to these tools:
run_bash (shell — stdin is closed, so commands waiting for input will
fail; use `find`, `du`, `unzip -l`, `head`, `grep`, `wc` for cheap
filesystem exploration), run_python (persistent REPL — pd, np, Path,
glob, zipfile, os, io are pre-loaded; use it to load and analyse the
data). The data has already been downloaded into CACHE_ROOT — inspect
it before answering. End every reply with EXACTLY ONE fenced ```json```
block matching the output structure. Do not invent fields.
""" + "\n" + _GLOBAL_GUARDRAILS


# ---------------------------------------------------------------------------
# Phase 1 — IDENTIFICATION (no CACHE_ROOT, run_python only)
# ---------------------------------------------------------------------------

def build_phase1_user(*, scenario: dict, platform: str,
                      include_system: bool = False,
                      phase1_mode: str = "default") -> str:
    """`phase1_mode` only changes the note about what the agent may use.

    The two ablation modes MUST be reflected here, not just in the tool list.
    The default note instructs the agent to use `run_python`; leaving it in
    place while the tool is gone makes the agent spend turns reaching for
    something that does not exist, which would be measured as a difficulty
    effect when it is really a prompt bug.
    """
    p1 = scenario.get("phase_1") or {}
    body = p1.get("user_prompt") or ""
    pkg = schemas.PHASE2_PACKAGE[platform]
    template = schemas.phase1_envelope_template(platform)
    if phase1_mode == "notools":
        extra_note = (
            "NO data has been downloaded yet, and NO tools are available in "
            "this session — there is no Python REPL and no network. Answer "
            "from your own knowledge of the platform and the domain. If you "
            "are not sure of an identifier, give your best estimate rather "
            "than describing how you would look it up."
        )
    elif phase1_mode == "offline":
        extra_note = (
            f"NO data has been downloaded yet. You have the `run_python` tool "
            f"and the installed packages, but this session has NO NETWORK "
            f"ACCESS: any HTTP request or client call that contacts a server "
            f"will fail. You may still `import {pkg}` and inspect it locally "
            f"(e.g. `help({pkg})`, `dir(...)`) to work out the API. Identifier "
            f"values must come from your own knowledge."
        )
    elif schemas.phase2_interface(platform) == "rest":
        # This benchmark reaches the platform over HTTP, so there is no one
        # package to point the agent at. Say that plainly — claiming no
        # client exists would be false for all four of these platforms.
        extra_note = (
            f"NO data has been downloaded yet. This benchmark reaches the "
            f"platform through its HTTP API ({pkg}). Use the `run_python` "
            f"tool with `requests` to consult the service's own metadata / "
            f"lookup endpoints if you need to confirm identifiers. Do not "
            f"retrieve the actual dataset — phase 2 will enumerate those "
            f"requests."
        )
    else:
        extra_note = (
            f"NO data has been downloaded yet. Use the `run_python` tool to "
            f"`import {pkg}` and inspect its API (e.g. `help({pkg})`, "
            f"`dir(...)`, `help({pkg}.<submodule>.<function>)`) if you need "
            f"to confirm identifiers. Do not call any data-fetching function "
            f"— phase 2 will enumerate those calls."
        )
    text = _wrap_envelope(
        task_text=body,
        envelope_template=template,
        phase_label="Phase 1 — identify the desired data",
        extra_note=extra_note,
    )
    if include_system:
        prologue = PROLOGUE_IDENT_BY_MODE.get(phase1_mode, PROLOGUE_IDENT)
        text = prologue.rstrip() + "\n\n---\n\n" + text
    return text


# ---------------------------------------------------------------------------
# Phase 2 — IDENTIFICATION (no CACHE_ROOT, run_python only)
# ---------------------------------------------------------------------------

_GBIF_PAGINATION_NOTE = (
    "For each GBIF call, also include a top-level boolean "
    "`requires_pagination`: true if you expect the query to need "
    "pagination to retrieve all results, false otherwise. List one "
    "entry per logical query — do not enumerate paginated calls."
)


def _phase2_extra_note(*, platform: str, pkg: str) -> str:
    """The Phase-2 user-message tail: everything after the scenario text
    and before the envelope template."""
    if schemas.phase2_interface(platform) == "rest":
        # There is no single package to introspect here, so the request
        # namespace has to be stated — the equivalent of what `dir()` /
        # `help()` gives the client-library platforms for free. The spec
        # describes the format only; which endpoint and which parameters this
        # scenario needs is still the agent's job.
        #
        # The task text above may name a Python client (`mp_api`, `census`,
        # `meteostat`); the note below says how to write the call down, and
        # is explicit that the two are not in conflict.
        return (
            f"This benchmark reaches the platform through its HTTP API "
            f"({pkg}), and grades the data those requests return. NO data "
            f"has been downloaded yet — you should not actually fetch data. "
            f"List EVERY request you would issue, in order, as elements of "
            f"the JSON list, using the module / function namespace and the "
            f"parameter names given below verbatim. If the task above "
            f"mentions a Python client for this platform, declare the "
            f"equivalent HTTP request in that namespace instead — the "
            f"underlying service, and the data you must retrieve, are the "
            f"same.\n\n"
            + schemas.REST_INTERFACE_SPEC[platform]
        )

    return (
        f"Use the `{pkg}` package (any of its submodules). NO data has "
        f"been downloaded yet — you should not actually fetch data. "
        f"Use `run_python` to `import {pkg}` and inspect its functions "
        f"(`help(...)`, `dir(...)`) if you need to confirm function "
        f"names or argument names. List EVERY function call you would "
        f"issue, in order, as elements of the JSON list. Use the EXACT "
        f"Python function name and argument names exposed by the "
        f"package."
    )


def build_phase2_user(*, scenario: dict, platform: str) -> str:
    p2 = scenario.get("phase_2") or {}
    body = p2.get("user_prompt") or ""
    pkg = schemas.PHASE2_PACKAGE[platform]
    template = schemas.phase2_envelope_template(platform)

    extra_note = _phase2_extra_note(platform=platform, pkg=pkg)

    if platform == "gbif":
        extra_note += "\n\n" + _GBIF_PAGINATION_NOTE

    return _wrap_envelope(
        task_text=body,
        envelope_template=template,
        phase_label="Phase 2 — function calls to fetch the data",
        extra_note=extra_note,
    )


# ---------------------------------------------------------------------------
# Phase 3 — COMPUTATION (CACHE_ROOT + full toolset)
# ---------------------------------------------------------------------------

def build_phase3_user(*, scenario: dict, platform: str,
                      cache_root: str) -> str:
    p3 = scenario.get("phase_3") or {}
    body = p3.get("user_prompt") or ""
    expected = p3.get("expected")
    declared_unit = p3.get("unit")
    template = schemas.phase3_envelope_template(expected, declared_unit)
    extra = (
        "You MUST inspect the data files under CACHE_ROOT using the "
        "available tools (run_bash for filesystem exploration / "
        "run_python for loading and computing on the data) and compute "
        "the answer from them. Do not answer from memory.\n"
        "Replace each `<FILL>` in the `value` template with the "
        "computed number. Preserve the exact keys / list length shown."
    )
    return _wrap_envelope(
        task_text=body,
        envelope_template=template,
        phase_label="Phase 3 — compute the requested value(s)",
        cache_root=cache_root,
        extra_note=extra,
    )


# ---------------------------------------------------------------------------
# Phase 4 — COMPUTATION + VISUALIZATION (CACHE_ROOT + full toolset)
# ---------------------------------------------------------------------------

def build_phase4_user(*, scenario: dict, platform: str,
                      cache_root: str, output_dir: str) -> str:
    p4 = scenario.get("phase_4") or {}
    body = p4.get("user_prompt") or ""
    # Every published scenario asks for a numeric answer (`expected`);
    # `checkpoint.enabled` says whether it also asks for a qualitative one.
    n_enabled = "expected" in p4
    q_enabled = bool((p4.get("checkpoint") or {}).get("enabled", False))
    template = schemas.phase4_envelope_template(n_enabled, q_enabled)
    extra = (
        "You MUST inspect the data files under CACHE_ROOT using the "
        "available tools (run_bash for filesystem exploration / "
        "run_python for loading, computing, and plotting) and compute "
        "the answer from them. Do not answer from memory.\n"
        f"Write any visualization output (PNG, etc.) to absolute paths "
        f"under: {output_dir}\n"
        "Then list those paths in `files_produced`."
    )
    if n_enabled:
        unit = p4.get("unit")
        unit_clause = f" (unit: {unit})" if unit else ""
        extra += (
            "\n`numeric_answer` must be the computed scalar"
            f"{unit_clause}."
        )
    if q_enabled:
        extra += (
            "\n`qualitative_answer` is a short paragraph (2–4 sentences) "
            "describing what the visualization shows."
        )
    return _wrap_envelope(
        task_text=body,
        envelope_template=template,
        phase_label="Phase 4 — analysis & visualization",
        cache_root=cache_root,
        extra_note=extra,
    )


# ---------------------------------------------------------------------------
# Common formatter
# ---------------------------------------------------------------------------

def _wrap_envelope(*, task_text: str, envelope_template: Any,
                   phase_label: str, cache_root: str | None = None,
                   extra_note: str | None = None) -> str:
    parts = [f"## {phase_label}", ""]
    if cache_root:
        parts += [
            f"CACHE_ROOT (local data already downloaded for this scenario): "
            f"{cache_root}",
            "",
        ]
    parts += [
        "### Task",
        task_text.strip(),
    ]
    if extra_note:
        parts += ["", extra_note.strip()]
    parts += [
        "",
        "### Output structure",
        "Return your answer inside a fenced ```json``` block matching exactly:",
        "```json",
        json.dumps(envelope_template, indent=2, ensure_ascii=False),
        "```",
    ]
    return "\n".join(parts)

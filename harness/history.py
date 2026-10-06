"""Build a chat-style message list seeded with prior-phase ground truth.

When evaluating phase N, the agent sees:
    for each prior phase k < N:
        HumanMessage(prompt for phase k, with envelope template)
        AIMessage(json envelope filled with the gold values)
    HumanMessage(prompt for phase N)

The agent treats the previous phases' gold as its own past output, so every
phase starts from a correct checkpoint and a failure does not propagate.

The system content is INLINED into the first user message. It is not sent
as a SystemMessage and not passed via `create_agent(system_prompt=...)`:
with tools bound, both pathways made Gemini 2.5 Flash sometimes return an
empty AIMessage on later phases.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from . import prompts, schemas


def _gold_phase1(scenario: dict, platform: str) -> dict[str, list]:
    e1 = scenario.get("phase_1", {}).get("expected") or {}
    return {k: e1.get(k, []) for k in schemas.PHASE1_KEYS[platform]}


def _gold_phase2(scenario: dict) -> list[dict]:
    return scenario.get("phase_2", {}).get("expected") or []


def _gold_phase3(scenario: dict) -> dict:
    p3 = scenario.get("phase_3") or {}
    return {"value": p3.get("expected"), "unit": p3.get("unit")}


def _wrap_ai_envelope(payload: Any) -> str:
    """Format a gold payload exactly as we ask the agent to format theirs:
    a fenced ```json``` block."""
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    return f"```json\n{body}\n```"


def build_history(*, scenario: dict, platform: str, target_phase: int,
                  cache_root: str, output_dir: str,
                  phase1_mode: str = "default",
                  skill_dir: str | None = None) -> list:
    """Return the LangChain message list for the agent on `target_phase`."""
    msgs: list = []

    if target_phase > 1:
        msgs.append(HumanMessage(content=prompts.build_phase1_user(
            scenario=scenario, platform=platform, include_system=True,
        )))
        msgs.append(AIMessage(content=_wrap_ai_envelope(
            _gold_phase1(scenario, platform)
        )))

    if target_phase > 2:
        msgs.append(HumanMessage(content=prompts.build_phase2_user(
            scenario=scenario, platform=platform,
        )))
        msgs.append(AIMessage(content=_wrap_ai_envelope(
            _gold_phase2(scenario)
        )))

    if target_phase > 3:
        msgs.append(HumanMessage(content=prompts.build_phase3_user(
            scenario=scenario, platform=platform, cache_root=cache_root,
        )))
        msgs.append(AIMessage(content=_wrap_ai_envelope(
            _gold_phase3(scenario)
        )))

    # The active phase's prompt. The prologue describing the tools is
    # attached only ONCE, to the very first user message: duplicating it
    # across turns confused Gemini Flash and triggered empty AIMessages.
    is_first_user = len(msgs) == 0  # True only when target_phase == 1

    if target_phase == 1:
        # `phase1_mode` changes the ACTIVE phase-1 prompt only, never the
        # copy replayed as history for later phases, whose agent does hold
        # run_python.
        body = prompts.build_phase1_user(
            scenario=scenario, platform=platform,
            include_system=is_first_user, phase1_mode=phase1_mode,
        )
    elif target_phase == 2:
        body = prompts.build_phase2_user(scenario=scenario, platform=platform)
        if is_first_user:
            body = prompts.PROLOGUE_IDENT.rstrip() + "\n\n---\n\n" + body
    elif target_phase == 3:
        body = prompts.build_phase3_user(
            scenario=scenario, platform=platform, cache_root=cache_root,
        )
        if is_first_user:
            body = prompts.PROLOGUE_COMPUTE.rstrip() + "\n\n---\n\n" + body
        else:
            # Mid-conversation tool-set switch (IDENT → COMPUTE) — remind
            # the agent it now has the full file-reading toolkit.
            body = (
                "Note: from this phase onward you also have run_bash "
                "(shell — stdin is closed; use `find`, `du`, `unzip -l`, "
                "`head`, `grep` for filesystem exploration). The data is "
                "downloaded under CACHE_ROOT.\n\n"
            ) + body
    elif target_phase == 4:
        body = prompts.build_phase4_user(
            scenario=scenario, platform=platform,
            cache_root=cache_root, output_dir=output_dir,
        )
        if is_first_user:
            body = prompts.PROLOGUE_COMPUTE.rstrip() + "\n\n---\n\n" + body
    else:
        raise ValueError(f"target_phase out of range: {target_phase}")

    # Onboarding skill, prepended to the active user message only; replayed
    # prior-phase messages keep their original form.
    skill_text = prompts.load_skill(skill_dir, target_phase, platform)
    if skill_text:
        body = prompts._inject_skill(body, skill_text)

    msgs.append(HumanMessage(content=body))
    return msgs

"""Per-scenario driver: runs the requested phases and writes one JSON record
per phase.

    <output_dir>/<platform>/<scenario_stem>/phase_<N>.json

Each phase is its own episode, started from the gold output of the phases
before it (see history.py), so a failure in one phase does not propagate.
Phases 1, 3 and 4 are graded as they finish. Phase 2 records the calls the
agent declared; they are executed and graded afterwards on the data they
return (scripts/execute_calls.py, scripts/grade_phase2.py).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

from grading import compare

from . import agent as eagent, history, records, tools as etools


def _invoke_agent(agent_runnable, messages: list, recursion_limit: int):
    """Invoke the agent and return the final state's messages list."""
    state = agent_runnable.invoke(
        {"messages": messages},
        {"recursion_limit": recursion_limit},
    )
    return state.get("messages", []) or []


def run_one_phase(*, scenario: dict, platform: str, scenario_stem: str,
                  phase: int, model_id: str,
                  cache_root: Path, output_dir: Path,
                  provider: str = "google-genai",
                  base_url: str | None = None,
                  api_key_env: str | None = None,
                  thinking_budget: int | None = 2048,
                  recursion_limit: int = 80,
                  phase1_mode: str = "default",
                  skill_dir: str | None = None) -> records.PhaseRecord:
    """Run a single phase with a freshly built agent and a clean REPL."""
    etools.reset_python_namespace(cache_root)

    model = eagent.build_model(
        model_id=model_id,
        provider=provider,
        base_url=base_url,
        api_key_env=api_key_env,
        thinking_budget=thinking_budget,
    )
    agent_runnable = eagent.build_agent(
        model, tools=etools.tools_for_run(phase, phase1_mode))
    # Arm the network block for `offline`, and disarm it otherwise, so a
    # process that runs several phases cannot leak the flag between them.
    etools.set_offline(phase == 1 and phase1_mode == "offline")

    msgs = history.build_history(
        scenario=scenario,
        platform=platform,
        target_phase=phase,
        cache_root=str(cache_root),
        output_dir=str(output_dir),
        phase1_mode=phase1_mode,
        skill_dir=skill_dir,
    )

    record = records.make_phase_record(
        scenario_id=f"{platform}/{scenario_stem}",
        platform=platform, phase=phase, model_id=model_id,
    )

    t_start = time.time()
    err: str | None = None
    out_messages: list = []
    try:
        out_messages = _invoke_agent(agent_runnable, msgs, recursion_limit)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        # Recover the partial trace (langgraph may have thrown before the
        # final message; streaming captures every step that ran).
        try:
            partial: list = list(msgs)
            for chunk in agent_runnable.stream(
                {"messages": msgs},
                {"recursion_limit": recursion_limit},
                stream_mode="updates",
            ):
                for node_state in chunk.values():
                    for m in (node_state.get("messages") or []):
                        partial.append(m)
            if len(partial) > len(msgs):
                out_messages = partial
        except Exception:
            pass
    t_end = time.time()

    records.fill_record_from_run(
        record,
        input_messages=msgs,
        output_messages=out_messages,
        t_start=t_start, t_end=t_end,
        error=err,
    )

    if err is not None or record.envelope is None:
        # A runtime error or a missing answer counts as a failure.
        record.verdict = "error"
        record.binary_pass = False
        record.score = 0.0
        record.comparison = {
            "verdict": "error",
            "binary_pass": False,
            "score": 0.0,
            "details": {
                "reason": err or "no envelope extracted from agent output",
            },
        }
        return record

    comp = compare.compare_phase(phase, agent=record.envelope,
                                 scenario=scenario, platform=platform)
    if comp is not None:
        record.comparison = comp
        record.verdict = comp.get("verdict")
        record.binary_pass = comp.get("binary_pass")
        record.score = comp.get("score")
    return record


def run_scenario(*, scenario_path: Path, platform: str,
                 cache_root: Path, output_dir: Path,
                 phases: Iterable[int],
                 model_id: str,
                 provider: str = "google-genai",
                 base_url: str | None = None,
                 api_key_env: str | None = None,
                 thinking_budget: int | None = 2048,
                 recursion_limit: int = 80,
                 phase1_mode: str = "default",
                 skill_dir: str | None = None,
                 resume: bool = True) -> dict:
    """Run the requested phases for one scenario; returns a small summary."""
    scenario = json.loads(scenario_path.read_text())

    scen_out_dir = output_dir / platform / scenario_path.stem
    scen_out_dir.mkdir(parents=True, exist_ok=True)

    summary = {"scenario": scenario_path.stem, "platform": platform,
               "phases": {}}

    for ph in phases:
        out_path = scen_out_dir / f"phase_{ph}.json"
        if resume and out_path.exists():
            try:
                prev = json.loads(out_path.read_text())
                summary["phases"][ph] = {
                    "status": "skipped (resume)",
                    "verdict": (prev.get("comparison") or {}).get("verdict"),
                }
                continue
            except Exception:
                pass

        record = run_one_phase(
            scenario=scenario, platform=platform,
            scenario_stem=scenario_path.stem,
            phase=ph, model_id=model_id,
            cache_root=cache_root, output_dir=scen_out_dir,
            provider=provider, base_url=base_url, api_key_env=api_key_env,
            thinking_budget=thinking_budget,
            recursion_limit=recursion_limit,
            phase1_mode=phase1_mode,
            skill_dir=skill_dir,
        )
        # The seal's "agent code is running" flag must be down before the
        # runner writes: out_path lives under the sealed root, so a flag left
        # set would turn the runner's own write into a SealedPathError. The
        # runner is definitionally not agent code here, so clearing is safe.
        etools.reset_agent_flag()
        out_path.write_text(json.dumps(record.to_dict(),
                                       indent=2, ensure_ascii=False))
        summary["phases"][ph] = {
            "status": "ok" if record.error is None else "error",
            "wall_time_s": record.wall_time_s,
            "tokens_total": (record.tokens or {}).get("total"),
            "verdict": record.verdict,
            "binary_pass": record.binary_pass,
            "score": record.score,
            "error": record.error,
        }

    return summary

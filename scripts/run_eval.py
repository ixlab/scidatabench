"""Run the task agent on SciDataBench or SciDataBench-Onboard.

Examples
--------
# One model on the whole benchmark, all four phases
python scripts/run_eval.py --model gemini-3.7-flash --run-id g37_base

# An open-weights model behind a vLLM server
python scripts/run_eval.py --model Qwen/Qwen3.6-27B --provider openai \
    --base-url http://localhost:8000/v1 --run-id qwen_base

# A perturbation set (paper, Table 3)
python scripts/run_eval.py --model gemini-3.7-flash --run-id g37_p1 \
    --bench-root data/perturbations/phase1-catalogue-synonym --phases 1

# SciDataBench-Onboard with an onboarding skill (paper, Section 4)
python scripts/run_eval.py --model gemini-3-flash-preview --run-id g3_skill \
    --bench-root data/scidatabench-onboard --phases 1,2 \
    --skill skills/gemini-3.7-flash/exec

# Tool ablation on Phase 1 (paper, Table 4)
python scripts/run_eval.py ... --phases 1 --phase1-mode offline
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import signal
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

BENCH_ROOT = REPO_ROOT / "data" / "scidatabench"
GOLD_ROOT = REPO_ROOT / "gold" / "scidatabench"
RESULTS_ROOT = REPO_ROOT / "results"

_SANDBOX_ENV_FLAG = "SCIDATABENCH_SANDBOXED"

# Where the sandbox relocates everything that carries an answer. bwrap mounts
# a tmpfs on the PARENT and creates the bind destinations inside it, so the
# parent must be an existing, otherwise unused directory on the host (`/` is
# bound read-only, so bwrap cannot create a new top-level name).
SEALED = Path(os.environ.get("SCIDATABENCH_SEALED_ROOT",
                             "/srv/scidatabench-sealed"))

# Repository directories that hold answers, grades or other runs' output.
_MASK_DIRS = ("data", "gold", "results", "skills", "supplementary", "logs",
              ".git")


def _set_arg(argv: list[str], name: str, value: str) -> list[str]:
    """Drop any existing `--name V` / `--name=V` and append `--name value`."""
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a == name:
            skip = True
            continue
        if a.startswith(name + "="):
            continue
        out.append(a)
    return out + [name, value]


def _argval(name: str, default: str | None) -> str | None:
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def _maybe_reexec_in_sandbox() -> None:
    """Re-execute this script inside a bwrap sandbox that restricts writes
    AND hides the answers.

    The agent gets `run_python`, and Phase 1 asks for identifiers whose only
    copy on the machine is the scenario file itself, so a capable model will
    eventually go and read it. Everything that carries an answer — scenario
    files, gold snapshots, other runs' records, skills of other conditions —
    is therefore relocated under SEALED and masked at its original path. The
    runner is pointed at the sealed copies by rewriting its own arguments;
    the agent, which only knows the original paths, finds empty directories.
    `harness/tools.py` adds an audit hook that refuses the sealed root, and
    the harness source, to agent code.

    HOME is blanked except for the Python environment and this repository,
    since other copies of a benchmark are easy to leave lying around there.

    Bypass with --no-sandbox; skipped when already inside, or when bwrap is
    not installed.
    """
    if "--no-sandbox" in sys.argv:
        return
    if os.environ.get(_SANDBOX_ENV_FLAG) == "1":
        return
    if not shutil.which("bwrap"):
        print("[sandbox] bwrap not found on PATH; running unsandboxed. "
              "Install bubblewrap or pass --no-sandbox to silence.",
              file=sys.stderr, flush=True)
        return
    if not SEALED.parent.is_dir():
        raise SystemExit(
            f"[sandbox] {SEALED.parent} does not exist. Set "
            f"SCIDATABENCH_SEALED_ROOT to a path whose parent is an existing, "
            f"unused directory, or pass --no-sandbox.")

    home = Path.home()
    tmp_dirs = [home / ".cache", home / ".config", home / ".local" / "state"]
    for d in tmp_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Resolve what this invocation will read before anything is masked.
    bench_src = Path(_argval("--bench-root", str(BENCH_ROOT))).resolve()
    gold_src = Path(_argval("--gold-root", str(GOLD_ROOT))).resolve()
    out_src = Path(_argval("--output-root", str(RESULTS_ROOT / "runs"))).resolve()
    skill_arg = _argval("--skill", None)
    skill_src = Path(skill_arg).resolve() if skill_arg else None
    out_src.mkdir(parents=True, exist_ok=True)

    masks = {str(bench_src)} | {str(REPO_ROOT / d) for d in _MASK_DIRS
                                if (REPO_ROOT / d).is_dir()}
    if gold_src.exists():
        masks.add(str(gold_src))
    if skill_src is not None:
        masks.add(str(skill_src))
    # Loose files at the repository root (README, notes) are blanked as well:
    # the runner reads none of them.
    root_files = sorted(str(f) for f in REPO_ROOT.iterdir()
                        if f.is_file() and not f.name.startswith("."))

    # The Python environment must stay readable. Hand it back explicitly when
    # it lives under HOME (conda, venv), since HOME itself is blanked.
    env_binds = {Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()}
    if (home / ".conda").is_dir():
        env_binds.add(home / ".conda")
    env_binds = sorted(str(p) for p in env_binds if str(p).startswith(str(home)))

    bwrap_args: list[str] = [
        "bwrap",
        "--ro-bind", "/", "/",
        "--dev", "/dev",
        "--proc", "/proc",
        "--tmpfs", "/tmp",
        "--tmpfs", str(SEALED.parent),
        "--tmpfs", str(home),
    ]
    for p in env_binds:
        bwrap_args += ["--ro-bind", p, p]
    for d in tmp_dirs:
        bwrap_args += ["--tmpfs", str(d)]
    bwrap_args += [
        "--ro-bind", str(REPO_ROOT), str(REPO_ROOT),
        # Sealed copies first: bind sources resolve in the host namespace, so
        # they survive the masks applied to their original paths below.
        "--ro-bind", str(bench_src), str(SEALED / "bench"),
        "--bind", str(out_src), str(SEALED / "results"),
        "--setenv", _SANDBOX_ENV_FLAG, "1",
        "--setenv", "SCIDATABENCH_SEALED_ROOT", str(SEALED),
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        # libhdf5 segfaults inside the sandbox when its file-locking probe
        # hits a read-only mount; disabling locks is the upstream fix.
        "--setenv", "HDF5_USE_FILE_LOCKING", "FALSE",
        "--share-net",
        "--die-with-parent",
        "--unshare-pid",
    ]
    if gold_src.exists():
        bwrap_args += ["--ro-bind", str(gold_src), str(SEALED / "gold")]
    if skill_src is not None:
        bwrap_args += ["--ro-bind", str(skill_src), str(SEALED / "skill")]

    # Masks go last so they cannot shadow the bind sources above.
    for m in sorted(masks):
        bwrap_args += ["--tmpfs", m]
    for f in root_files:
        bwrap_args += ["--ro-bind", "/dev/null", f]

    inner = list(sys.argv[1:])
    inner = _set_arg(inner, "--bench-root", str(SEALED / "bench"))
    inner = _set_arg(inner, "--output-root", str(SEALED / "results"))
    if gold_src.exists():
        inner = _set_arg(inner, "--gold-root", str(SEALED / "gold"))
    if skill_src is not None:
        inner = _set_arg(inner, "--skill", str(SEALED / "skill"))

    bwrap_args += [sys.executable, str(Path(__file__).resolve()), *inner]
    print(f"[sandbox] entering bwrap — scenarios, gold, results and skills are "
          f"relocated to {SEALED} and masked at their real paths. Pass "
          f"--no-sandbox to disable.", flush=True)
    os.execvp("bwrap", bwrap_args)


if __name__ == "__main__":
    _maybe_reexec_in_sandbox()


from harness import runner, tools as etools  # noqa: E402


class _ScenarioTimeout(Exception):
    """Raised when a single scenario exceeds the configured wall budget.

    An Exception rather than a BaseException on purpose: the runner's own
    `except Exception` turns it into a phase record, which lets resume skip
    the scenario instead of retrying the hang forever.
    """


# The re-arm below must stop the moment a scenario is abandoned, or it keeps
# firing through the cleanup path.
_alarm_armed = False


def _alarm_handler(_signum, _frame):
    if not _alarm_armed:
        return
    # Re-arm before raising: tool bodies catch broad exceptions so the model
    # gets a readable error, which also swallows this one; a single-shot
    # alarm would then silently stop enforcing the budget.
    signal.alarm(5)
    raise _ScenarioTimeout("scenario timeout reached")


def _disarm_alarm() -> None:
    """Stop the budget alarm and unstick the seal flag. Call this FIRST in
    every handler that runs after a scenario ends."""
    global _alarm_armed
    _alarm_armed = False
    signal.alarm(0)
    etools.reset_agent_flag()


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bench-root", default=str(BENCH_ROOT),
                   help="Directory of scenario files, one sub-directory per "
                        "platform (default: data/scidatabench).")
    p.add_argument("--gold-root", default=str(GOLD_ROOT),
                   help="Gold snapshot of the benchmark, one directory per "
                        "scenario; phases 3 and 4 read it as CACHE_ROOT.")
    p.add_argument("--platform", default=None,
                   help="Comma-separated platforms to run (default: all "
                        "platforms under --bench-root).")
    p.add_argument("--scenario", action="append", default=[],
                   help="A single scenario, '<platform>/<stem>'. Repeatable.")
    p.add_argument("--phases", default="1,2,3,4",
                   help="Comma-separated phase numbers (default: 1,2,3,4).")
    p.add_argument("--model", required=True,
                   help="Chat model id, e.g. gemini-3.7-flash, or the model "
                        "name a vLLM server exposes (e.g. Qwen/Qwen3.6-27B).")
    p.add_argument("--provider", choices=["google-genai", "openai"],
                   default="google-genai",
                   help="'openai' targets any OpenAI-compatible endpoint, "
                        "including vLLM (requires --base-url).")
    p.add_argument("--base-url", default=None,
                   help="Endpoint for --provider openai, e.g. "
                        "http://localhost:8000/v1.")
    p.add_argument("--api-key-env", default=None,
                   help="Env var holding the API key for --provider openai.")
    p.add_argument("--phase1-mode", choices=list(etools.PHASE1_MODE_CHOICES),
                   default="default",
                   help="Phase-1 tools (paper, Table 4): 'default' = "
                        "run_python; 'offline' = run_python without network; "
                        "'notools' = no tool.")
    p.add_argument("--skill", default=None,
                   help="Onboarding skill directory to inject into phases 1 "
                        "and 2, e.g. skills/gemini-3.7-flash/exec.")
    p.add_argument("--thinking-budget", type=int, default=2048,
                   help="Gemini thinking-token cap (ignored for --provider "
                        "openai).")
    p.add_argument("--recursion-limit", type=int, default=80,
                   help="Agent step limit per phase.")
    p.add_argument("--scenario-timeout", type=int, default=0,
                   help="Max wall-clock seconds for one scenario across its "
                        "phases; 0 disables. Ignored with --workers > 1.")
    p.add_argument("--run-id", required=True,
                   help="Name of the run directory under --output-root.")
    p.add_argument("--output-root", default=str(RESULTS_ROOT / "runs"),
                   help="Where run directories are written.")
    p.add_argument("--no-resume", action="store_true",
                   help="Re-run phases whose record already exists.")
    p.add_argument("--limit", type=int, default=None,
                   help="Run at most this many scenarios.")
    p.add_argument("--workers", type=int, default=1,
                   help="Parallel scenario workers (separate processes, each "
                        "with its own REPL).")
    p.add_argument("--no-sandbox", action="store_true",
                   help="Do not re-execute inside the bwrap sandbox.")
    return p.parse_args()


def _platforms_in(bench_root: Path) -> list[str]:
    return sorted(d.name for d in bench_root.iterdir()
                  if d.is_dir() and any(d.glob("*.json")))


def collect_scenarios(args) -> list[tuple[str, Path]]:
    """(platform, scenario path) for every scenario selected."""
    bench_root = Path(args.bench_root)
    out: list[tuple[str, Path]] = []
    if args.scenario:
        for sid in args.scenario:
            if "/" not in sid:
                raise SystemExit(f"--scenario requires platform/stem, got: {sid}")
            plat, stem = sid.split("/", 1)
            fp = bench_root / plat / (stem if stem.endswith(".json")
                                      else stem + ".json")
            if not fp.exists():
                raise SystemExit(f"scenario not found: {fp}")
            out.append((plat, fp))
    else:
        known = _platforms_in(bench_root)
        wanted = ([p.strip() for p in args.platform.split(",") if p.strip()]
                  if args.platform else known)
        for plat in wanted:
            if plat not in known:
                raise SystemExit(f"unknown platform: {plat} "
                                 f"(under {bench_root}: {', '.join(known)})")
            out += [(plat, fp) for fp in sorted((bench_root / plat).glob("*.json"))]
    return out[: args.limit] if args.limit else out


def _run_kwargs(args, plat: str, fp: Path, phases: list[int],
                per_scen: Path) -> dict:
    return dict(
        scenario_path=fp, platform=plat,
        cache_root=Path(args.gold_root) / plat / fp.stem,
        output_dir=per_scen, phases=phases,
        model_id=args.model, provider=args.provider,
        base_url=args.base_url, api_key_env=args.api_key_env,
        thinking_budget=args.thinking_budget,
        recursion_limit=args.recursion_limit,
        phase1_mode=args.phase1_mode, skill_dir=args.skill,
        resume=not args.no_resume,
    )


def _needs_gold(phases: list[int]) -> bool:
    """Only phases 3 and 4 read the gold snapshot."""
    return any(p in (3, 4) for p in phases)


def _process_scenario(args, plat: str, fp_str: str, phases: list[int],
                      per_scen_str: str) -> dict:
    """Worker entry point for --workers > 1 (picklable arguments)."""
    fp = Path(fp_str)
    try:
        return runner.run_scenario(**_run_kwargs(args, plat, fp, phases,
                                                 Path(per_scen_str)))
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return {"scenario": fp.stem, "platform": plat, "status": "error",
                "error": f"{type(e).__name__}: {e}",
                "traceback_tail": traceback.format_exc().splitlines()[-10:]}


def main():
    global _alarm_armed
    args = parse_args()
    phases = [int(p) for p in args.phases.split(",") if p.strip()]
    if not phases:
        raise SystemExit("no phases requested")

    # Absolute paths: workers and the sandbox may run from another directory.
    args.bench_root = str(Path(args.bench_root).resolve())
    args.output_root = str(Path(args.output_root).resolve())
    args.gold_root = str(Path(args.gold_root).resolve())
    if args.skill:
        args.skill = str(Path(args.skill).resolve())

    out_root = Path(args.output_root) / args.run_id
    per_scen = out_root / "per_scenario"
    per_scen.mkdir(parents=True, exist_ok=True)

    # Per-launch config and summary, so several launches (e.g. one per
    # platform) can write into the same run directory.
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out_root / f"config.{stamp}.json").write_text(json.dumps({
        "run_id": args.run_id,
        "started_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": args.model,
        "provider": args.provider,
        "base_url": args.base_url,
        "phases": phases,
        "phase1_mode": args.phase1_mode,
        "skill": args.skill,
        "thinking_budget": args.thinking_budget,
        "recursion_limit": args.recursion_limit,
        "bench_root": args.bench_root,
        "platforms": args.platform,
        "scenarios": args.scenario or None,
    }, indent=2))
    summary_path = out_root / f"summary.{stamp}.json"

    scenarios = collect_scenarios(args)
    if _needs_gold(phases):
        missing = [(p, f) for p, f in scenarios
                   if not (Path(args.gold_root) / p / f.stem).exists()]
        if missing:
            print(f"[scidatabench] {len(missing)} scenario(s) have no gold "
                  f"snapshot under {args.gold_root} and are skipped.",
                  flush=True)
            scenarios = [s for s in scenarios if s not in missing]
    print(f"[scidatabench] {len(scenarios)} scenario(s); phases={phases}; "
          f"model={args.model}; run_id={args.run_id}", flush=True)

    summaries: list[dict] = []

    def _persist_summary():
        summary_path.write_text(json.dumps({"summaries": summaries},
                                           indent=2, ensure_ascii=False))

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(_process_scenario, args, plat, str(fp),
                                 phases, str(per_scen)): (plat, fp)
                       for plat, fp in scenarios}
            try:
                for i, fut in enumerate(as_completed(futures), 1):
                    plat, fp = futures[fut]
                    try:
                        summary = fut.result()
                    except Exception as e:
                        summary = {"scenario": fp.stem, "platform": plat,
                                   "status": "error",
                                   "error": f"{type(e).__name__}: {e}"}
                    summaries.append(summary)
                    _persist_summary()
                    print(f"  [{i:>3}/{len(scenarios)}] {plat}/{fp.stem}: "
                          f"{summary.get('status') or 'done'}", flush=True)
            except KeyboardInterrupt:
                ex.shutdown(wait=False, cancel_futures=True)
                _persist_summary()
                raise
    else:
        if args.scenario_timeout > 0:
            signal.signal(signal.SIGALRM, _alarm_handler)
        for i, (plat, fp) in enumerate(scenarios, 1):
            print(f"  [{i:>3}/{len(scenarios)}] {plat}/{fp.stem} ...", flush=True)
            if args.scenario_timeout > 0:
                _alarm_armed = True
                signal.alarm(args.scenario_timeout)
            try:
                summary = runner.run_scenario(**_run_kwargs(args, plat, fp,
                                                            phases, per_scen))
            except _ScenarioTimeout:
                _disarm_alarm()
                summary = {"scenario": fp.stem, "platform": plat,
                           "status": "timeout",
                           "scenario_timeout_s": args.scenario_timeout}
            except KeyboardInterrupt:
                _disarm_alarm()
                _persist_summary()
                raise
            except Exception as e:
                _disarm_alarm()
                tb = traceback.format_exc()
                print(tb, file=sys.stderr, flush=True)
                summary = {"scenario": fp.stem, "platform": plat,
                           "status": "error",
                           "error": f"{type(e).__name__}: {e}",
                           "traceback_tail": tb.splitlines()[-10:]}
            finally:
                _disarm_alarm()
            summaries.append(summary)
            _persist_summary()
    _persist_summary()
    print(f"[scidatabench] done. Output under: {out_root}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Execute the calls an agent declared in Phase 2, so that Phase 2 can be
graded on the data they return (scripts/grade_phase2.py).

Reads `phase_2.json` from every scenario of a run, executes each declared
call through executor/calls.py, and writes an index of what each scenario's
calls returned:

    <exec-root>/exec_runs/<tag>/index.json     scenario -> [{call, sha, status, rows}]
    <exec-root>/exec_runs/<tag>/summary.json   status counts, not-callable reasons
    <exec-root>/exec_cache/<sha[:2]>/<sha>/    the payloads, shared across runs

Usage
    python scripts/execute_calls.py --run-id g37_base
    python scripts/execute_calls.py --run-id g37_base --platform usgs
    python scripts/execute_calls.py --run-id g37_base --dry-run
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from executor import calls, handlers as dh  # noqa: E402


def _envelopes(run_dir: pathlib.Path, platforms: set[str] | None) -> dict:
    """(platform, stem) -> declared calls, or None when the record has none."""
    out: dict[tuple[str, str], list | None] = {}
    per_scen = run_dir / "per_scenario"
    if not per_scen.is_dir():
        raise SystemExit(f"per_scenario/ missing under {run_dir}")
    for plat_dir in sorted(p for p in per_scen.iterdir() if p.is_dir()):
        if platforms and plat_dir.name not in platforms:
            continue
        for scen_dir in sorted(p for p in plat_dir.iterdir() if p.is_dir()):
            fp = scen_dir / "phase_2.json"
            if not fp.exists():
                continue
            try:
                env = json.loads(fp.read_text()).get("envelope")
            except Exception:
                continue
            if isinstance(env, dict):
                env = [env]                       # unwrapped single call
            out[(plat_dir.name, scen_dir.name)] = (
                [c for c in env if isinstance(c, dict)]
                if isinstance(env, list) else None)
    return out


def calls_from_run(run_dir: pathlib.Path, platforms: set[str] | None):
    """Yield (platform, scenario_stem, [call, ...] or None) from a run."""
    for (plat, stem), declared in sorted(_envelopes(run_dir, platforms).items()):
        yield plat, stem, declared


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--run-id", help="run directory name under --runs-root")
    src.add_argument("--run-dir", help="path to a run directory")
    ap.add_argument("--runs-root", default=str(REPO / "results" / "runs"))
    ap.add_argument("--exec-root", default=str(REPO / "exec"),
                    help="parent of exec_cache/ and exec_runs/")
    ap.add_argument("--platform", default="all",
                    help="comma-separated platform subset, or 'all'")
    ap.add_argument("--max-calls", type=int, default=None,
                    help="at most N calls per scenario (smoke testing)")
    ap.add_argument("--call-timeout", type=int, default=0,
                    help="abort any single call that exceeds N seconds "
                         "(0 = no limit). Timed-out calls are recorded as "
                         "`timeout` and cached.")
    ap.add_argument("--force", action="store_true",
                    help="ignore cached results and re-execute")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve and hash calls without executing them")
    ap.add_argument("--tag", default=None,
                    help="name for the exec_runs/ index (default: run name)")
    args = ap.parse_args()

    exec_root = pathlib.Path(args.exec_root)
    platforms = (None if args.platform == "all"
                 else {p.strip() for p in args.platform.split(",") if p.strip()})
    versions = dh._package_versions()
    opts = dict(calls.DEFAULT_OPTS)
    opts["call_timeout"] = args.call_timeout

    run_dir = (pathlib.Path(args.run_dir).resolve() if args.run_dir
               else pathlib.Path(args.runs_root) / args.run_id)
    if not run_dir.is_dir():
        raise SystemExit(f"run directory not found: {run_dir}")
    source = calls_from_run(run_dir, platforms)
    tag = args.tag or run_dir.name

    dh.log(f"source    : {run_dir}")
    dh.log(f"exec root : {exec_root}")
    dh.log(f"tag       : {tag}" + ("   [DRY RUN]" if args.dry_run else ""))
    dh.log(f"call cap  : "
           + (f"{args.call_timeout}s" if args.call_timeout else "none"))

    index: dict[str, list] = {}
    status_counts: collections.Counter = collections.Counter()
    by_platform: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    reasons: collections.Counter = collections.Counter()
    n_scen = 0
    t_start = time.time()

    for platform, stem, declared in source:
        n_scen += 1
        if declared is None:
            status_counts["no_envelope"] += 1
            by_platform[platform]["no_envelope"] += 1
            index[f"{platform}/{stem}"] = []
            continue
        if args.max_calls:
            declared = declared[: args.max_calls]
        rows = []
        for c in declared:
            module = str(c.get("module") or "")
            function = str(c.get("function") or "")
            meta = calls.execute_call(
                platform, module, function, c.get("kwargs") or {},
                cache_root=exec_root, versions=versions, opts=opts,
                force=args.force, dry_run=args.dry_run)
            st = meta.get("status", "?")
            status_counts[st] += 1
            by_platform[platform][st] += 1
            if st == "not_callable":
                reasons[(platform, meta.get("reason", "?"),
                         f"{module}.{function}")] += 1
            rows.append({"module": module, "function": function,
                         "sha": meta["sha"], "status": st,
                         "rows": meta.get("rows"),
                         "cached": meta.get("cached", False),
                         "elapsed_s": meta.get("elapsed_s")})
            mark = {"success": "ok", "error": "ERR",
                    "not_callable": "NC", "setup_call": "cfg",
                    "skipped_too_large": "skip", "dry_run": "-",
                    "transient_error": "RETRY", "timeout": "TMO",
                    "chained": "chain", "not_data": "NODATA"}.get(st, "?")
            if not meta.get("cached"):
                dh.log(f"  {platform}/{stem[:40]:<40} {function[:26]:<26} "
                       f"{mark:<4} {str(meta.get('rows', '-')):>9} rows"
                       + (f"  {str(meta.get('error'))[:80]}"
                          if st in ("error", "not_callable") else ""))
        index[f"{platform}/{stem}"] = rows

    out_dir = exec_root / "exec_runs" / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    # MERGE, don't overwrite, so that one platform can be executed at a time
    # (e.g. several processes in parallel, one per platform) without one
    # invocation deleting another's entries.
    index_path = out_dir / "index.json"
    merged: dict = {}
    if index_path.exists():
        try:
            merged = json.loads(index_path.read_text())
        except Exception:
            merged = {}
    replaced = sum(1 for k in index if k in merged)
    merged.update(index)
    index_path.write_text(json.dumps(merged, indent=2, default=str))
    if replaced or len(merged) > len(index):
        dh.log(f"index merged: {len(index)} scenarios written "
               f"({replaced} replaced), {len(merged)} total on disk")

    # Status counts are recomputed from the MERGED index so the summary
    # describes the run as a whole, not just this invocation's slice.
    m_status: collections.Counter = collections.Counter()
    m_by_plat: dict = collections.defaultdict(collections.Counter)
    for sid, rows_ in merged.items():
        plat_ = sid.split("/", 1)[0]
        for r_ in rows_:
            st_ = str(r_.get("status"))
            m_status[st_] += 1
            m_by_plat[plat_][st_] += 1

    summary = {
        "tag": tag,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "scenarios": len(merged),
        "scenarios_this_invocation": n_scen,
        "platforms_this_invocation": sorted(by_platform),
        "calls": sum(len(v) for v in merged.values()),
        "status": dict(m_status),
        "by_platform": {p: dict(c) for p, c in m_by_plat.items()},
        "not_callable": [{"platform": p, "reason": r, "call": c, "n": n}
                         for (p, r, c), n in reasons.most_common()],
        "package_versions": versions,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    dh.log("=" * 72)
    dh.log(f"DONE in {(time.time()-t_start)/60:.1f} min — "
           f"{n_scen} scenarios, {summary['calls']} calls")
    dh.log(f"{'platform':<14}" + "".join(f"{k:>10}" for k in
                                         ("success", "error", "not_call",
                                          "not_data", "timeout", "chained",
                                          "skipped", "transient")))
    for p in sorted(by_platform):
        c = by_platform[p]
        dh.log(f"{p:<14}{c['success']:>10}{c['error']:>10}"
               f"{c['not_callable']:>10}{c['not_data']:>10}"
               f"{c['timeout']:>10}{c['chained']:>10}"
               f"{c['skipped_too_large']:>10}{c['transient_error']:>10}")
    if status_counts.get("transient_error"):
        dh.log("")
        dh.log(f"  {status_counts['transient_error']} call(s) still failing "
               f"transiently after 3 retries — NOT cached, so re-running this "
               f"command retries only those.")
    if reasons:
        dh.log("")
        dh.log("not-callable:")
        for (p, r, c), n in reasons.most_common(15):
            dh.log(f"  {n:>4}  {p:<12} {r:<18} {c}")
    dh.log(f"index -> {out_dir}")


if __name__ == "__main__":
    main()

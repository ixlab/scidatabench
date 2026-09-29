#!/usr/bin/env python
"""Grade Phase 2 on the data its calls return (paper, Section 2.2;
supplementary S3).

Compares two already-materialised sets of results:

    gold   <gold-root>/<platform>/<scenario>/manifest.json + payloads
           (scripts/build_gold.py)
    agent  <exec-root>/exec_runs/<tag>/index.json -> exec_cache/<sha>/
           (scripts/execute_calls.py)

Neither side is executed here, so grading is cheap and can be re-run freely.
Writes `phase_2.exec.json` next to each `phase_2.json` of the run and prints a
per-platform summary.

Usage
    python scripts/grade_phase2.py --run-id g37_base
    python scripts/grade_phase2.py --run-id g3_skill \
        --gold-root gold/scidatabench-onboard --platform argo --verbose
    python scripts/grade_phase2.py --run-id ... --no-write
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import warnings

# Concatenating the sparse, heterogeneous frames these APIs return trips
# pandas' all-NA-column FutureWarning thousands of times; it says nothing
# about the comparison.
warnings.filterwarnings("ignore")

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from grading.phase2 import grade_scenario, load_call          # noqa: E402
from grading.phase2.registry import spec_for                  # noqa: E402

DEFAULT_EXEC = REPO / "exec"
DEFAULT_GOLD = REPO / "gold" / "scidatabench"




def load_gold(gold_root: pathlib.Path, platform: str, stem: str,
              want=None):
    """Gold frames, per-call statuses, and when the snapshot was taken.

    The gold cache is a frozen snapshot, not a contemporaneous fetch: the
    manifest records when each call's data was retrieved (`downloaded_at`, per
    call and for the scenario). Agent calls are executed later, so the two
    sides can differ by months. That is by design — key-based coverage is
    drift-robust for an append-only archive, since later records inflate
    `over` without reducing `record_cov` — but it is NOT free for USGS and EPA,
    which revise values in place. So the gap is measured and reported rather
    than assumed away.
    """
    d = gold_root / platform / stem
    mf = d / "manifest.json"
    if not mf.exists():
        return [], [], None
    try:
        manifest = json.loads(mf.read_text())
    except Exception:
        return [], [], None
    calls = manifest.get("calls", [])
    frames, statuses = [], []
    for c in calls:
        statuses.append(str(c.get("status")))
        frames.extend(load_call(c, d, platform, want))
    snap = manifest.get("downloaded_at")
    return frames, statuses, snap


def load_agent(exec_root: pathlib.Path, rows: list[dict], platform: str):
    frames, statuses, snaps = [], [], []
    for r in rows:
        statuses.append(str(r.get("status")))
        sha = str(r.get("sha") or "")
        if not sha or r.get("status") != "success":
            continue
        d = exec_root / "exec_cache" / sha[:2] / sha
        mp = d / "meta.json"
        if not mp.exists():
            continue
        try:
            meta = json.loads(mp.read_text())
        except Exception:
            continue
        if meta.get("downloaded_at"):
            snaps.append(str(meta["downloaded_at"]))
        frames.extend(load_call(meta, d, platform))
    return frames, statuses, (max(snaps) if snaps else None)


def _drift_days(gold_iso, agent_iso) -> float | None:
    """Days between the gold snapshot and the agent's execution."""
    if not gold_iso or not agent_iso:
        return None
    import datetime as _dt

    def _p(s):
        s = str(s).replace("Z", "+00:00")
        try:
            d = _dt.datetime.fromisoformat(s)
        except ValueError:
            return None
        return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)

    g, a = _p(gold_iso), _p(agent_iso)
    return None if (g is None or a is None) else round((a - g).total_seconds() / 86400, 1)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--tag", default=None,
                    help="exec_runs/ tag (default: same as --run-id)")
    ap.add_argument("--runs-root", default=str(REPO / "results" / "runs"))
    ap.add_argument("--exec-root", default=str(DEFAULT_EXEC),
                    help="parent of exec_cache/ and exec_runs/")
    ap.add_argument("--gold-root", default=str(DEFAULT_GOLD),
                    help="gold snapshot of the benchmark the run used")
    ap.add_argument("--platform", default="all")
    ap.add_argument("--no-write", action="store_true",
                    help="print only; do not write phase_2.exec.json")
    ap.add_argument("--only", default=None,
                    help="file with one scenario id per line; grade and write "
                         "ONLY those. For re-grading the scenarios a grader "
                         "fix actually touches, leaving every other record "
                         "exactly as it was")
    ap.add_argument("--verbose", action="store_true",
                    help="one line per scenario")
    args = ap.parse_args()

    exec_root = pathlib.Path(args.exec_root)
    gold_root = pathlib.Path(args.gold_root)
    run_dir = pathlib.Path(args.runs_root) / args.run_id
    tag = args.tag or args.run_id
    index_path = exec_root / "exec_runs" / tag / "index.json"
    if not index_path.exists():
        raise SystemExit(f"agent execution index not found: {index_path}\n"
                         f"run scripts/execute_calls.py first")
    index = json.loads(index_path.read_text())

    plats = (None if args.platform == "all"
             else {p.strip() for p in args.platform.split(",") if p.strip()})

    by_plat: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    drifts: dict[str, list[float]] = collections.defaultdict(list)
    scores: dict[str, list[float]] = collections.defaultdict(list)
    comps: dict[str, list[float]] = collections.defaultdict(list)
    n_written = 0

    only = None
    if args.only:
        only = {l.strip() for l in pathlib.Path(args.only).read_text().splitlines()
                if l.strip()}

    for sid, rows in sorted(index.items()):
        platform, stem = sid.split("/", 1)
        if plats and platform not in plats:
            continue
        if only is not None and sid not in only:
            continue
        # Agent first, then gold through the agent's columns. `value_fid`
        # compares the columns both sides carry, so a gold column the agent
        # never returned contributes nothing — but on NEON it costs real
        # memory: one scenario's gold is 1.86M rows x 77 columns (4.8 GB) while
        # its agent side has two tables. Reading gold whole is what pushed the
        # usgs sweep to 64 GB and an OOM kill.
        agent_frames, agent_status, agent_snap = load_agent(exec_root, rows, platform)
        want = None
        if platform == "neon" and agent_frames:
            spec = spec_for(platform)
            want = {str(c).strip().lower()
                    for _, df in agent_frames for c in df.columns}
            want |= {c.strip().lower() for opt in spec.key for c in opt}
            want |= {c.strip().lower() for c in spec.time_col}
        gold_frames, gold_status, gold_snap = load_gold(gold_root, platform,
                                                        stem, want)
        res = grade_scenario(platform, gold_frames, agent_frames, agent_status)
        res["details"]["gold_call_status"] = dict(collections.Counter(gold_status))
        drift = _drift_days(gold_snap, agent_snap)
        res["details"]["snapshot"] = {"gold": gold_snap, "agent": agent_snap,
                                      "drift_days": drift}
        if drift is not None:
            drifts[platform].append(drift)

        by_plat[platform][res["verdict"]] += 1
        if res["score"] is not None:
            scores[platform].append(res["score"])
            m = res["details"].get("metrics", {})
            for k in ("record_cov", "value_fid", "time_cov"):
                if m.get(k) is not None:
                    comps[k].append(m[k])

        if args.verbose:
            m = res["details"].get("metrics", {})
            print(f"  {platform:<12} {stem[:44]:<46} {res['verdict']:<13} "
                  f"score={res['score']}  "
                  f"rec={m.get('record_cov')} val={m.get('value_fid')} "
                  f"time={m.get('time_cov')} over={m.get('over')}")

        if not args.no_write:
            out = run_dir / "per_scenario" / platform / stem / "phase_2.exec.json"
            if out.parent.exists():
                out.write_text(json.dumps(
                    {"scenario_id": sid, "platform": platform, "phase": 2,
                     "metric": "result_equivalence", **res},
                    indent=2, default=str))
                n_written += 1

    # ---- report ----
    order = ["PASS", "OVER-BROAD", "WRONG-SLICE", "EMPTY",
             "NOT-CALLABLE", "NO-ANSWER", "UNGRADABLE"]
    print()
    print(f"{'platform':<13}{'n':>4}{'grad':>6}" +
          "".join(f"{v[:11]:>13}" for v in order) + f"{'pass_rate':>11}{'score':>8}")
    print("-" * (13 + 4 + 6 + 13 * len(order) + 19))
    tot = collections.Counter()
    for p in sorted(by_plat):
        c = by_plat[p]
        n = sum(c.values())
        gradable = n - c["UNGRADABLE"]
        pr = (c["PASS"] + c["OVER-BROAD"]) / gradable if gradable else 0.0
        sc = sum(scores[p]) / len(scores[p]) if scores[p] else 0.0
        print(f"{p:<13}{n:>4}{gradable:>6}" +
              "".join(f"{c[v]:>13}" for v in order) +
              f"{pr:>10.1%}{sc:>8.3f}")
        tot.update(c)
    n = sum(tot.values())
    gradable = n - tot["UNGRADABLE"]
    allsc = [s for v in scores.values() for s in v]
    pr = (tot["PASS"] + tot["OVER-BROAD"]) / gradable if gradable else 0.0
    print("-" * (13 + 4 + 6 + 13 * len(order) + 19))
    print(f"{'OVERALL':<13}{n:>4}{gradable:>6}" +
          "".join(f"{tot[v]:>13}" for v in order) +
          f"{pr:>10.1%}{(sum(allsc)/len(allsc) if allsc else 0):>8.3f}")

    # Drift between the frozen gold and the agent execution. Reported, not
    # corrected: the right response differs by platform (GBIF appends, USGS
    # and EPA revise), and the reader needs the number to judge which.
    if any(drifts.values()):
        print("\n# gold-to-agent snapshot drift (days)")
        for p in sorted(drifts):
            v = sorted(drifts[p])
            if v:
                print(f"  {p:<12} n={len(v):>4}  median={v[len(v)//2]:>6.0f}"
                      f"  min={v[0]:.0f}  max={v[-1]:.0f}")

    print("\n# component means (over scenarios where the component applies)")
    for k in ("record_cov", "value_fid", "time_cov"):
        v = comps[k]
        print(f"  {k:<12} n={len(v):>4}  mean={sum(v)/len(v):.4f}" if v
              else f"  {k:<12} n=   0")
    if not args.no_write:
        print(f"\nwrote {n_written} phase_2.exec.json records under {run_dir}")


if __name__ == "__main__":
    main()

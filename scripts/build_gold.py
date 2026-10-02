#!/usr/bin/env python
"""Build the gold snapshot of a benchmark: execute every scenario's gold
Phase-2 calls and save what they return.

The snapshot is what Phase 2 is graded against (scripts/grade_phase2.py) and
what Phases 3 and 4 read as CACHE_ROOT (scripts/run_eval.py). It is "what the
API returned at download time": the services behind SciDataBench are live and
are revised and extended, so a snapshot rebuilt today will differ from the
one the paper used. snapshots/ records when each of its calls was downloaded
and how many rows it returned.

    <out>/<platform>/<scenario_stem>/manifest.json   one entry per call
    <out>/<platform>/<scenario_stem>/call_NN.*       the payloads

A call whose manifest entry is already `success` is skipped, so the script
can be stopped and restarted freely.

Usage
    python scripts/build_gold.py --bench-root data/scidatabench \
        --out gold/scidatabench
    python scripts/build_gold.py --bench-root data/scidatabench-onboard \
        --out gold/scidatabench-onboard --platform obis,pangaea
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys
import time
import traceback

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from executor import handlers as dh  # noqa: E402


def process_scenario(platform: str, fp: pathlib.Path, out_root: pathlib.Path,
                     opts: dict) -> dict:
    stem = fp.stem

    scen = json.loads(fp.read_text())
    calls = scen.get("phase_2", {}).get("expected") or []
    if not calls:
        return {"scenario": stem, "status": "no_calls"}

    d = out_root / platform / stem
    if opts["dry_run"]:
        # Touch nothing on disk — a dry run that leaves empty scenario dirs
        # behind makes the cache look half-populated.
        dh.log(f"  [dry-run] {len(calls)} calls: "
            + ", ".join(sorted({str(c.get('function')) for c in calls if isinstance(c, dict)}))[:100])
        return {"scenario": stem, "status": "dry_run", "calls": len(calls)}

    d.mkdir(parents=True, exist_ok=True)
    mpath = d / "manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {}
    prev = {c["idx"]: c for c in manifest.get("calls", []) if "idx" in c}

    manifest.update({
        "scenario_file": fp.name,
        "platform": platform,
        "package_versions": dh._package_versions(),
    })

    entries, n_ok, n_err, n_skip = [], 0, 0, 0
    for idx, call in enumerate(calls):
        if not isinstance(call, dict):
            continue
        old = prev.get(idx)
        stale_empty = (opts["redo_empty"] and old
                       and old.get("status") == "success"
                       and not (old.get("rows") or 0))
        if (old and old.get("status") in ("success", "skipped_too_large")
                and not opts["force"] and not stale_empty):
            entries.append(old)
            n_ok += old.get("status") == "success"
            n_skip += old.get("status") == "skipped_too_large"
            continue

        fn = str(call.get("function") or "")
        kw = call.get("kwargs") or {}
        entry = {"idx": idx, "module": call.get("module"), "function": fn, "kwargs": kw}
        t0 = time.time()
        try:
            res = dh.HANDLERS[platform](kw, fn, d, idx, opts)
            entry["status"] = res.pop("status_override", "success")
            entry.update(res)
            entry["downloaded_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
            if entry["status"] == "success":
                n_ok += 1
            else:
                n_skip += 1
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = f"{type(e).__name__}: {e}"
            entry["traceback_tail"] = traceback.format_exc().splitlines()[-4:]
            n_err += 1
        entry["elapsed_seconds"] = round(time.time() - t0, 2)
        entries.append(entry)
        mark = {"success": "ok", "error": "ERR", "skipped_too_large": "skip"}.get(entry["status"], "?")
        dh.log(f"    call_{idx:02d} {fn:<28} {mark:<5} "
            f"{entry.get('rows', '-'):>9} rows  {entry['elapsed_seconds']:>7.1f}s"
            + (f"  {entry.get('error', '')[:90]}" if entry["status"] == "error" else ""))
        manifest["calls"] = entries
        mpath.write_text(json.dumps(manifest, indent=2, default=str))

    manifest["calls"] = entries
    # The snapshot's time is that of its latest call, so a resumed build
    # still records when the data it holds was retrieved.
    times = [e["downloaded_at"] for e in entries if e.get("downloaded_at")]
    if times:
        manifest["downloaded_at"] = max(times)
    mpath.write_text(json.dumps(manifest, indent=2, default=str))
    return {"scenario": stem, "status": "done", "ok": n_ok,
            "error": n_err, "skipped": n_skip, "calls": len(calls)}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bench-root", required=True,
                    help="scenario directory, e.g. data/scidatabench")
    ap.add_argument("--out", required=True,
                    help="snapshot directory, e.g. gold/scidatabench")
    ap.add_argument("--platform", default="all",
                    help="comma-separated platform list, or 'all'")
    ap.add_argument("--scenario", action="append",
                    help="<platform>/<stem>, repeatable")
    ap.add_argument("--limit", type=int,
                    help="first N scenarios per platform (smoke test)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list work, make no API calls")
    ap.add_argument("--force", action="store_true",
                    help="re-download successful calls")
    ap.add_argument("--redo-empty", action="store_true",
                    help="also re-run calls recorded as success with 0 rows")
    ap.add_argument("--obis-max-rows", type=int,
                    default=dh.OBIS_MAX_ROWS_DEFAULT)
    ap.add_argument("--inat-max-rows", type=int,
                    default=dh.INAT_MAX_ROWS_DEFAULT)
    ap.add_argument("--pangaea-max-rows", type=int,
                    default=dh.PANGAEA_MAX_ROWS_DEFAULT)
    args = ap.parse_args()

    bench = pathlib.Path(args.bench_root).resolve()
    out_root = pathlib.Path(args.out).resolve()
    opts = {"dry_run": args.dry_run, "force": args.force,
            "redo_empty": args.redo_empty,
            "obis_max_rows": args.obis_max_rows,
            "inat_max_rows": args.inat_max_rows,
            "pangaea_max_rows": args.pangaea_max_rows}

    known = sorted(p.name for p in bench.iterdir() if p.is_dir())
    if args.scenario:
        jobs = []
        for sid in args.scenario:
            plat, stem = sid.split("/", 1)
            fp = bench / plat / (stem if stem.endswith(".json") else stem + ".json")
            if not fp.exists():
                sys.exit(f"scenario not found: {fp}")
            jobs.append((plat, fp))
    else:
        plats = known if args.platform == "all" else \
            [p.strip() for p in args.platform.split(",") if p.strip()]
        jobs = []
        for p in plats:
            if p not in known or p not in dh.HANDLERS:
                sys.exit(f"unknown platform: {p} (under {bench}: {', '.join(known)})")
            fps = sorted((bench / p).glob("*.json"))
            if args.limit:
                fps = fps[: args.limit]
            jobs.extend((p, fp) for fp in fps)

    dh.log(f"benchmark : {bench}")
    dh.log(f"output    : {out_root}")
    dh.log(f"scenarios : {len(jobs)}")
    if args.dry_run:
        dh.log("DRY RUN — no API calls")

    t_start = time.time()
    summary: dict[str, dict] = {}
    for i, (plat, fp) in enumerate(jobs, 1):
        dh.log(f"[{i}/{len(jobs)}] {plat}/{fp.stem}")
        try:
            r = process_scenario(plat, fp, out_root, opts)
        except KeyboardInterrupt:
            dh.log("interrupted by user")
            break
        except Exception as e:
            dh.log(f"  SCENARIO FAILED: {type(e).__name__}: {e}")
            r = {"scenario": fp.stem, "status": "scenario_error"}
        s = summary.setdefault(plat, {"scen": 0, "ok": 0, "error": 0,
                                      "skipped": 0})
        s["scen"] += 1
        for k in ("ok", "error", "skipped"):
            s[k] += r.get(k, 0)

    dh.log("=" * 60)
    dh.log(f"DONE in {(time.time()-t_start)/60:.1f} min")
    dh.log(f"{'platform':<14}{'scen':>6}{'ok':>8}{'error':>8}{'skipped':>9}")
    for p in sorted(summary):
        s = summary[p]
        dh.log(f"{p:<14}{s['scen']:>6}{s['ok']:>8}{s['error']:>8}{s['skipped']:>9}")


if __name__ == "__main__":
    main()

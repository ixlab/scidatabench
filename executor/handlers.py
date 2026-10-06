"""Platform handlers: execute one declared call and save what it returns.

Used twice, so that gold and agent calls are executed the same way:
    scripts/build_gold.py     materialises the gold snapshot of a benchmark
    scripts/execute_calls.py  executes the calls an agent declared in Phase 2

A handler takes `(kwargs, function, out_dir, call_index, opts)`, writes the
payload under `out_dir` and returns a small dict describing it. Output layout
of one scenario's gold snapshot:

    <gold-root>/<platform>/<scenario_stem>/
        manifest.json
        call_00.parquet             relation  (most platforms)
        call_00.json                record    (ensembl)
        call_00.nc                  array     (argo, alongside the parquet)
        call_00.quakeml             (usgs_eq, alongside the parquet)
        call_00__<table>.parquet    (vizier returns a TableList)
        call_00.meta.json           (pangaea dataset metadata)
        <neon zips>                 (neon: one zip per product, site, month)

The snapshot is "what the API returned at download time": live services grow
and revise, so the UTC timestamp and the installed package versions are
written into every manifest. A query whose advertised total exceeds the
per-platform row cap is recorded as `skipped_too_large` rather than silently
truncated.

Credentials are read from the environment: NEON_TOKEN, API_USGS_PAT (or
API_USGS_PAT1..4, rotated), AQS_USER and AQS_KEY, CENSUS_API_KEY, MP_API_KEY.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import pathlib
import re
import time
import warnings

warnings.filterwarnings("ignore")

# pyinaturalist logs every HTTP request at INFO and pyobis prints a progress
# bar per page; across a multi-hour run that buries our own progress lines.
for _noisy in ("pyinaturalist", "pyobis", "urllib3", "intake_esgf", "argopy"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

import pandas as pd
from datetime import date as _dtdate
import requests


OBIS_MAX_ROWS_DEFAULT = 1_000_000
INAT_MAX_ROWS_DEFAULT = 200_000
PANGAEA_MAX_ROWS_DEFAULT = 2_000_000


def log(msg: str) -> None:
    ts = _dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# Transient upstream failures, all observed in the first full run: NCBI answers
# 502 under load (pysradb then trips over the NA-filled frame and raises
# "boolean value of NA is ambiguous"), the USGS FDSN endpoint returns 503, and
# VizieR times out.  Retrying with backoff cleared every one of them.
_TRANSIENT = ("boolean value of na is ambiguous", "502", "503", "504",
              "timed out", "timeout", "connection", "temporarily unavailable",
              "service unavailable", "remote end closed", "reset by peer")


def retry(fn, tries: int = 4, waits=(5, 20, 60), what: str = ""):
    """Run `fn`, retrying only on transient upstream failures."""
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:
            msg = f"{type(e).__name__}: {e}".lower()
            if attempt == tries - 1 or not any(t in msg for t in _TRANSIENT):
                raise
            w = waits[min(attempt, len(waits) - 1)]
            log(f"      transient ({what or type(e).__name__}), retry in {w}s: {str(e)[:80]}")
            time.sleep(w)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _is_null(v) -> bool:
    """None / NaN / pd.NA / NaT, without ever evaluating a value's truthiness.

    `v != v` is the usual NaN idiom but it raises TypeError on pandas' NA
    singleton, and pysradb hands back frames full of it.
    """
    if v is None:
        return True
    try:
        r = pd.isna(v)
    except (TypeError, ValueError):
        return False
    return bool(r) if isinstance(r, bool) or getattr(r, "ndim", 0) == 0 else False


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Make a DataFrame parquet-serialisable.

    astropy Tables, ESGF catalogues and json_normalize output carry byte
    strings, masked values, list-valued cells, and — the case that actually
    bit us — object columns holding two different python types across rows
    (e.g. str in some records, float in others).  Parquet infers one arrow
    type per column and fails on all of those, so containers become JSON text
    and any column left with mixed non-null types is stringified.
    """
    df = df.copy()
    # Address columns positionally: a duplicated label (the Census `group()`
    # expansion repeats NAME) makes df[label] return a DataFrame, not a Series.
    for i in range(df.shape[1]):
        s = df.iloc[:, i]
        if s.dtype != object:
            continue
        if s.map(lambda v: isinstance(v, (list, dict, set, tuple))).any():
            s = s.map(lambda v: json.dumps(v, default=str)
                      if isinstance(v, (list, dict, set, tuple)) else v)
        else:
            s = s.map(lambda v: v.decode("utf-8", "replace")
                      if isinstance(v, bytes) else v)
        # Normalise every flavour of null to None so parquet gets one type.
        if s.map(lambda v: v is not None and _is_null(v)).any():
            s = s.map(lambda v: None if _is_null(v) else v)
        kinds = {type(v).__name__ for v in s if not _is_null(v)}
        if len(kinds) > 1:
            s = s.map(lambda v: None if _is_null(v) else str(v))
        df.isetitem(i, s)
    df.columns = _dedupe_columns(df.columns)
    return df


def _dedupe_columns(cols) -> list[str]:
    """Parquet needs unique column names; suffix repeats as name, name_1, ..."""
    seen: dict[str, int] = {}
    out = []
    for c in cols:
        c = str(c)
        if c in seen:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            out.append(c)
    return out


def save_df(df: pd.DataFrame, path: pathlib.Path) -> tuple[str, str]:
    """Write a DataFrame, preferring parquet. Returns (filename, format)."""
    df = _clean_df(df)
    try:
        df.to_parquet(path, index=False)
        return path.name, "parquet"
    except Exception:
        csv = path.with_suffix(".csv")
        df.to_csv(csv, index=False)
        return csv.name, "csv"


def _result(output: str, fmt: str, df: pd.DataFrame | None = None, **extra) -> dict:
    out = {"output": output, "format": fmt}
    if df is not None:
        out["rows"] = int(len(df))
        out["columns"] = [str(c) for c in df.columns]
    out.update(extra)
    return out


# ---------------------------------------------------------------------------
# Per-platform handlers
# Each takes (kwargs, function, call_dir, idx, opts) and returns a dict that is
# merged into the manifest entry.  Raising is fine — the caller records it.
# ---------------------------------------------------------------------------

def _argo_wmo(v):
    """argopy's `.float()` takes a single WMO or a list of them.

    The gold only ever names one, so this used to be a bare `int(...)`, which
    raises TypeError on a list — scoring a perfectly valid multi-float request
    as a failed call. Accept both; anything non-numeric still raises.
    """
    if isinstance(v, (list, tuple, set)):
        return [int(x) for x in v]
    return int(v)


# `DataFetcher(mode=, src=, ds=)` settings and the access point's own
# arguments arrive in one flat kwargs dict, because the envelope has no way
# to express a fluent chain. Split them back apart here — silently dropping
# `ds="bgc"` would return physical data for a biogeochemical request, which
# is the worst kind of failure: a full result set that answers the wrong
# question.
_ARGO_CTOR_KEYS = ("mode", "src", "ds", "params", "measured", "cache",
                   "parallel", "chunks", "chunks_maxsize", "api_timeout")


def _argo_fetcher(kw):
    from argopy import DataFetcher
    ctor = {k: v for k, v in kw.items() if k in _ARGO_CTOR_KEYS}
    return DataFetcher(**ctor) if ctor else DataFetcher()


def h_argo(kw, fn, d, idx, opts):
    if fn.endswith("float"):
        wmo = _argo_wmo(kw["wmo"])
        ds = retry(lambda: _argo_fetcher(kw).float(wmo).to_xarray(),
                   what="argo.float")
        detail = {"wmo": kw["wmo"]}
    elif fn.endswith("profile"):
        wmo = _argo_wmo(kw["wmo"])
        cyc = kw["cyc"]
        cyc = [int(c) for c in cyc] if isinstance(cyc, (list, tuple)) else int(cyc)
        ds = retry(lambda: _argo_fetcher(kw).profile(wmo, cyc).to_xarray(),
                   what="argo.profile")
        detail = {"wmo": kw["wmo"], "cyc": kw["cyc"]}
    elif fn.endswith("region"):
        box = list(kw["box"])
        # Some gold boxes use the 0-360 longitude convention (e.g. 290);
        # argopy requires [-180, 180].
        box[:2] = [(float(x) - 360.0 if float(x) > 180 else float(x)) for x in box[:2]]
        if box[0] > box[1]:                    # wrapped across the antimeridian
            raise ValueError(f"box crosses the antimeridian after normalisation: {box[:2]}")
        ds = retry(lambda: _argo_fetcher(kw).region(box).to_xarray(),
                   what="argo.region")
        detail = {"box": kw["box"], "box_normalised": box}
    else:
        raise ValueError(f"unsupported argo function: {fn}")

    nc = d / f"call_{idx:02d}.nc"
    try:
        ds.to_netcdf(nc)
    except Exception:
        nc = None
    df = ds.to_dataframe().reset_index()
    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(name, fmt, df,
                   xr_dims={k: int(v) for k, v in ds.sizes.items()},
                   xr_vars=[str(v) for v in ds.data_vars],
                   netcdf=(nc.name if nc else None), **detail)


def h_cmip6(kw, fn, d, idx, opts):
    from intake_esgf import ESGFCatalog
    cat = ESGFCatalog().search(**kw)
    df = cat.df.copy()
    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    # The result is a dataset listing (id_set), not the netCDF payload.
    return _result(name, fmt, df, result_kind="dataset_listing")


_ENSEMBL_SERVER = "https://rest.ensembl.org"
_ensembl_release_cache: list = []


def _ensembl_release() -> str | None:
    if _ensembl_release_cache:
        return _ensembl_release_cache[0]
    try:
        r = requests.get(f"{_ENSEMBL_SERVER}/info/data",
                         headers={"Content-Type": "application/json"}, timeout=30)
        rel = ",".join(str(x) for x in (r.json() or {}).get("releases", []))
    except Exception:
        rel = None
    _ensembl_release_cache.append(rel)
    return rel


def h_ensembl(kw, fn, d, idx, opts):
    kw = dict(kw)
    h = {"Content-Type": "application/json"}
    if fn == "lookup_symbol":
        sp = kw.pop("species", "homo_sapiens"); sym = kw.pop("symbol")
        path = f"/lookup/symbol/{sp}/{sym}"
    elif fn == "lookup_id":
        path = f"/lookup/id/{kw.pop('id')}"
    elif fn == "sequence_id":
        path = f"/sequence/id/{kw.pop('id')}"
    elif fn == "overlap_region":
        sp = kw.pop("species", "homo_sapiens"); reg = kw.pop("region")
        path = f"/overlap/region/{sp}/{reg}"
    elif fn == "homology_id":
        sp = kw.pop("species", None); gid = kw.pop("id")
        path = f"/homology/id/{sp}/{gid}" if sp else f"/homology/id/{gid}"
    elif fn == "variation_id":
        # Not used by any gold call, so it was missing here and every agent
        # that reached for it was scored NOT-CALLABLE. It is a real endpoint
        # under the same naming convention as the five above
        # (`/variation/:species/:id`, verified 200 with `pops=1` returning a
        # `populations` block), so the gap was the executor's, not the call's.
        sp = kw.pop("species", "homo_sapiens"); vid = kw.pop("id")
        path = f"/variation/{sp}/{vid}"
    else:
        raise ValueError(f"unsupported ensembl function: {fn}")

    r = requests.get(_ENSEMBL_SERVER + path, params=kw, headers=h, timeout=120)
    if fn == "homology_id" and r.status_code == 400 and "/homology/id/" in path:
        # Older REST deployments expose /homology/id/:id without the species.
        gid = path.rsplit("/", 1)[-1]
        r = requests.get(f"{_ENSEMBL_SERVER}/homology/id/{gid}",
                         params=kw, headers=h, timeout=120)
    r.raise_for_status()
    payload = r.json()
    out = d / f"call_{idx:02d}.json"
    out.write_text(json.dumps(payload, indent=2))
    n = len(payload) if isinstance(payload, list) else 1
    time.sleep(0.1)  # Ensembl asks for <= 15 req/s
    return _result(out.name, "json", None, rows=n,
                   ensembl_release=_ensembl_release(), endpoint=path)


# iNaturalist embeds the full identification / comment thread inside every
# observation record. Those columns are ~96% of the payload (125 KB -> 5.5 KB
# per observation once dropped) AND they are volatile by construction — people
# keep adding identifications to old observations — so keeping them would
# corrupt any value comparison as surely as it blows up the cache.
INAT_DROP_COLS = ("identifications", "non_owner_ids", "comments", "faves",
                  "votes", "reviewed_by", "project_observations")


# Pagination is this handler's business, not the caller's: the loop below
# walks every page and then falls back to id_below paging. An agent that
# declares `per_page=200, page=1` is describing the same retrieval, but
# forwarding those verbatim collides with the loop's own arguments
# ("got multiple values for keyword argument 'per_page'") and the call is
# recorded as not_callable — a defect in the executor, not in the call.
# Dropping them also collapses `page=1,2,3…` declarations onto one cache
# entry, since the handler already returns the full result set either way.
_INAT_PAGING_KEYS = ("per_page", "page", "id_below", "id_above")


def h_inaturalist(kw, fn, d, idx, opts):
    from pyinaturalist import get_observations
    cap = opts["inat_max_rows"]
    kw = {k: v for k, v in kw.items() if k not in _INAT_PAGING_KEYS}
    probe = get_observations(per_page=1, **kw)
    total = int(probe.get("total_results") or 0)
    if total > cap:
        return _result("", "none", None, rows=0, total_available=total,
                       status_override="skipped_too_large",
                       note=f"{total:,} > --inat-max-rows {cap:,}")
    results, page = [], 1
    while len(results) < total and page <= 50:          # API caps page*per_page at 10k
        r = get_observations(per_page=200, page=page, **kw)
        got = r.get("results") or []
        if not got:
            break
        results.extend(got)
        page += 1
        time.sleep(0.5)
    if len(results) < total:                            # deep paging via id_below
        while len(results) < total and results:
            r = get_observations(per_page=200, id_below=results[-1]["id"], **kw)
            got = r.get("results") or []
            if not got:
                break
            results.extend(got)
            time.sleep(0.5)
    for r in results:
        for c in INAT_DROP_COLS:
            r.pop(c, None)
    df = pd.json_normalize(results) if results else pd.DataFrame()
    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(name, fmt, df, total_available=total,
                   dropped_columns=list(INAT_DROP_COLS))


_sraweb = []


def h_noaa_ghcn(kw, fn, d, idx, opts):
    """NOAA NCEI Access API — GHCN-Daily station observations.

    The gold was rewritten from meteostat to this endpoint because meteostat
    keeps its own station registry and cannot resolve GHCN ids (see
    scripts/rewrite_noaa_ghcn_gold.py). No token is required.
    """
    p = {"dataset": "daily-summaries", "format": "json",
         **{k: v for k, v in kw.items() if v is not None}}
    r = retry(lambda: requests.get(
        "https://www.ncei.noaa.gov/access/services/data/v1",
        params=p, timeout=300), what="ncei")
    r.raise_for_status()
    try:
        recs = r.json()
    except Exception:
        # NCEI answers 200 with an HTML notice when a query is malformed.
        raise RuntimeError(f"non-JSON response: {r.text[:150]}")
    df = pd.json_normalize(recs) if recs else pd.DataFrame()
    # Values arrive as space-padded strings ("  -11"); make the measurements
    # numeric so the cache is directly comparable.
    for c in df.columns:
        if c not in ("STATION", "DATE") and df[c].dtype == object:
            conv = pd.to_numeric(df[c].astype(str).str.strip(), errors="coerce")
            if conv.notna().any():
                df[c] = conv
    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(name, fmt, df, station=p.get("stations"))


def h_census_acs(kw, fn, d, idx, opts):
    """US Census Data API.

    Without a key the service answers HTTP 200 with a "Missing Key" HTML page
    rather than an error status, so a non-JSON body is treated as a failure
    instead of being written out as an empty table.
    """
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise RuntimeError("CENSUS_API_KEY 미설정")
    p = {"get": kw["get"], "for": kw["for"], "key": key}
    if kw.get("in"):
        p["in"] = kw["in"]
    url = f"https://api.census.gov/data/{kw['year']}/{kw['dataset']}"
    r = retry(lambda: requests.get(url, params=p, timeout=600), what="census")
    if "json" not in r.headers.get("content-type", ""):
        raise RuntimeError(f"non-JSON (키/문법 문제?): {r.text[:130]}")
    j = r.json()
    df = pd.DataFrame(j[1:], columns=j[0]) if len(j) > 1 else pd.DataFrame(columns=j[0])
    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(name, fmt, df, year=kw["year"], dataset=kw["dataset"])


def h_matproj(kw, fn, d, idx, opts):
    """Materials Project REST API, paginated.

    `fn` carries the endpoint path (materials/summary, materials/elasticity...).
    mp_api itself is unimportable in this env, so this talks to REST directly.
    """
    key = os.environ.get("MP_API_KEY")
    if not key:
        raise RuntimeError("MP_API_KEY 미설정")
    rows, page, per = [], 0, 1000
    while True:
        p = {**kw, "_limit": per, "_skip": page * per}
        r = retry(lambda p=p: requests.get(f"https://api.materialsproject.org/{fn}/",
                                           headers={"X-API-KEY": key}, params=p,
                                           timeout=600), what="matproj")
        r.raise_for_status()
        j = r.json()
        got = j.get("data") or []
        rows.extend(got)
        total = (j.get("meta") or {}).get("total_doc") or 0
        page += 1
        if len(got) < per or len(rows) >= total or page > 200:
            break
    df = pd.json_normalize(rows) if rows else pd.DataFrame()
    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(name, fmt, df, endpoint=fn)


_OBIS_KEYS = {"scientificname", "taxonid", "startdate", "enddate", "geometry",
              "startdepth", "enddepth", "hasextensions", "mof", "areaid",
              "nodeid", "instituteid", "datasetid", "flags", "exclude"}


def h_obis(kw, fn, d, idx, opts):
    base = "https://api.obis.org/v3/occurrence"
    params = {k: v for k, v in kw.items() if k in _OBIS_KEYS}
    cap = opts["obis_max_rows"]

    probe = retry(lambda: requests.get(base, params={**params, "size": 0},
                                       timeout=180).json(), what="obis probe")
    total = int(probe.get("total") or 0)
    if total > cap:
        return _result("", "none", None, rows=0, total_available=total,
                       status_override="skipped_too_large",
                       note=f"{total:,} > --obis-max-rows {cap:,}")

    rows, after = [], None
    while len(rows) < total:
        p = {**params, "size": 10000}
        if after:
            p["after"] = after
        j = retry(lambda p=p: requests.get(base, params=p, timeout=300).json(),
                  what="obis page")
        got = j.get("results") or []
        if not got:
            break
        rows.extend(got)
        after = got[-1].get("id")
        log(f"      obis call_{idx:02d}: {len(rows):,}/{total:,}")
    df = pd.json_normalize(rows) if rows else pd.DataFrame()
    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(name, fmt, df, total_available=total)


def h_pangaea(kw, fn, d, idx, opts):
    from pangaeapy.pandataset import PanDataSet
    ds = retry(lambda: PanDataSet(str(kw["id"])), what="pangaea")
    meta = {
        "title": str(getattr(ds, "title", None)),
        "doi": str(getattr(ds, "doi", None)),
        "citation": str(getattr(ds, "citation", None)),
        "params": [str(p) for p in (getattr(ds, "params", {}) or {})],
        "is_collection": bool(getattr(ds, "isCollection", False)),
    }

    members, extra = [], {}
    if meta["is_collection"]:
        # A collection carries no data of its own — its rows live in the child
        # datasets, so an un-expanded collection silently yields 0 rows.
        members = [str(m).replace("doi:", "") for m in
                   (getattr(ds, "collection_members", None) or [])]
        meta["collection_members"] = members
        frames, total, truncated = [], 0, False
        for mid in members:
            child = retry(lambda mid=mid: PanDataSet(mid), what=f"pangaea child {mid}")
            cdf = getattr(child, "data", None)
            if cdf is None or not len(cdf):
                continue
            cdf = cdf.copy()
            cdf["__pangaea_member"] = mid
            frames.append(cdf)
            total += len(cdf)
            if total > opts["pangaea_max_rows"]:
                truncated = True
                break
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        extra = {"n_members": len(members), "members_fetched": len(frames),
                 "truncated": truncated}
    else:
        df = ds.data if getattr(ds, "data", None) is not None else pd.DataFrame()

    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    (d / f"call_{idx:02d}.meta.json").write_text(json.dumps(meta, indent=2))
    return _result(name, fmt, df, meta=f"call_{idx:02d}.meta.json",
                   dataset_title=meta["title"][:120],
                   is_collection=meta["is_collection"], **extra)


# `Client.get_events` is a method on a constructed client, but a declared call
# is a single flat kwargs dict with nowhere to put the constructor's arguments.
# Route them instead of rejecting the call — the same split `_ARGO_CTOR_KEYS`
# already performs for argopy. Values are honoured, not overridden: base_url
# selects the FDSN service, so an agent naming IRIS gets IRIS. USGS is only the
# fallback when the call names no service.
_OBSPY_CTOR_KEYS = ("base_url", "user", "password", "debug", "eida_token",
                    "force_redirect", "user_agent", "_discover_services")


def h_usgs_eq(kw, fn, d, idx, opts):
    from obspy import UTCDateTime
    from obspy.clients.fdsn import Client
    ctor = {k: v for k, v in kw.items() if k in _OBSPY_CTOR_KEYS}
    base_url = ctor.pop("base_url", None) or "USGS"
    p = {k: v for k, v in kw.items() if k not in _OBSPY_CTOR_KEYS}
    for t in ("starttime", "endtime"):
        if p.get(t):
            p[t] = UTCDateTime(str(p[t]))
    from obspy.clients.fdsn.header import FDSNNoDataException
    try:
        cat = retry(lambda: Client(base_url, timeout=300,
                                   **ctor).get_events(**p), what="fdsn")
    except FDSNNoDataException:
        # HTTP 204: the query is well-formed, the catalogue simply holds no
        # matching event.  That is an empty result, not a failure.
        df = pd.DataFrame(columns=["event_id", "time", "latitude", "longitude",
                                   "depth_m", "magnitude", "magnitude_type",
                                   "description"])
        name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
        return _result(name, fmt, df, empty_reason="FDSN 204 no data")

    qml = d / f"call_{idx:02d}.quakeml"
    try:
        cat.write(str(qml), format="QUAKEML")
    except Exception:
        qml = None

    recs = []
    for ev in cat:
        o = ev.preferred_origin() or (ev.origins[0] if ev.origins else None)
        m = ev.preferred_magnitude() or (ev.magnitudes[0] if ev.magnitudes else None)
        recs.append({
            "event_id": str(ev.resource_id).rsplit("/", 1)[-1],
            "time": str(o.time) if o else None,
            "latitude": float(o.latitude) if o and o.latitude is not None else None,
            "longitude": float(o.longitude) if o and o.longitude is not None else None,
            "depth_m": float(o.depth) if o and o.depth is not None else None,
            "magnitude": float(m.mag) if m and m.mag is not None else None,
            "magnitude_type": str(m.magnitude_type) if m else None,
            "description": str(ev.event_descriptions[0].text) if ev.event_descriptions else None,
        })
    df = pd.DataFrame(recs)
    name, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(name, fmt, df, quakeml=(qml.name if qml else None))


# The gold spells VizieR's region query `center` / `radius_arcmin`. Those are
# this benchmark's names, not astroquery's — the real signature is
# `query_region(coordinates, radius=...)`. Phase 2 tells the agent to use the
# package's own argument names, so an agent writing `coordinates` / `radius`
# is following the instruction and must not be failed for it.
#
# Gold's spellings are checked FIRST in both helpers, so the gold execution
# path is unchanged and the cached vizier gold stays valid.
#
# JSON cannot carry a SkyCoord or a Quantity, so agents serialise the
# constructor call. Those expressions are PARSED (never eval'd); a string that
# carries no actual value ("SkyCoord object") still raises.
_SKYCOORD_RA_DEC = re.compile(
    r"ra\s*=\s*['\"]?\s*([^,'\"]+?)\s*['\"]?\s*,\s*"
    r"dec\s*=\s*['\"]?\s*([^,'\")]+?)\s*['\"]?\s*[,)]", re.I)


def _vizier_center(kw):
    """Resolve the search centre from either spelling into a SkyCoord."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    raw = kw.get("center", kw.get("coordinates", kw.get("coord")))
    if raw is None:
        raise ValueError("no search centre given (center / coordinates)")
    if not isinstance(raw, str):
        raise ValueError(f"unsupported centre value: {raw!r}")
    s = raw.strip()

    parts = s.split()
    if len(parts) == 2:                         # gold form: "40.67 18.93"
        try:
            return SkyCoord(float(parts[0]), float(parts[1]), unit=(u.deg, u.deg))
        except ValueError:
            pass

    m = _SKYCOORD_RA_DEC.search(s)
    if m:
        ra_s, dec_s = m.group(1).strip(), m.group(2).strip()
        try:                                    # plain degrees
            return SkyCoord(float(ra_s), float(dec_s), unit=(u.deg, u.deg))
        except ValueError:                      # sexagesimal
            unit = ((u.hourangle, u.deg)
                    if any(c in ra_s.lower() for c in "hd:")
                    else (u.deg, u.deg))
            return SkyCoord(ra_s, dec_s, unit=unit)
    if s.lower().startswith("skycoord"):
        raise ValueError(f"centre carries no coordinate value: {s[:60]!r}")
    return SkyCoord.from_name(s)                # a resolvable object name


def _vizier_radius(kw):
    """Resolve the search radius from either spelling into an angle.

    Parsed as an `Angle`, not a bare `Quantity`: in an angular context astropy
    reads "14d" as 14 degrees and "3s" as 3 arcsec, whereas `Quantity` reads
    them as 14 days and 3 seconds and the query then fails on a unit error.
    `Angle` also accepts "3 degrees", which `Quantity` rejects outright.
    """
    import astropy.units as u
    from astropy.coordinates import Angle
    if kw.get("radius_arcmin") is not None:     # gold form
        return float(kw["radius_arcmin"]) * u.arcmin
    r = kw.get("radius")
    if r is None:
        return 5 * u.arcmin
    if isinstance(r, (int, float)):
        return float(r) * u.arcmin              # gold's unit convention
    s = str(r).strip()
    try:
        return Angle(s)
    except Exception:
        pass
    try:                                        # a bare number in a string
        return float(s) * u.arcmin
    except ValueError as e:
        raise ValueError(f"unparseable radius {r!r}") from e


# Constructor-only arguments of VizierClass. A declared call is one flat
# kwargs dict, so an agent asking for `row_limit=-1` has nowhere to put it but
# alongside the query arguments, where astroquery rejects it as an unexpected
# keyword. Drop them here rather than reject the call: the handler already
# constructs `Vizier(row_limit=-1)`, which is exactly what such a call asks
# for. Same routing `_OBSPY_CTOR_KEYS` performs for obspy.
_VIZIER_CTOR_KEYS = ("row_limit", "timeout", "columns", "keywords",
                     "ucd", "vizier_server")


def h_vizier(kw, fn, d, idx, opts):
    from astroquery.vizier import Vizier
    kw = {k: v for k, v in kw.items() if k not in _VIZIER_CTOR_KEYS}
    v = Vizier(row_limit=-1)          # default is 50 rows — always override
    v.TIMEOUT = 300                   # astroquery's default can hang forever
    cat = kw.get("catalog")
    if fn.endswith("query_constraints"):
        if "column_filters" in kw:
            # Present but empty means "no constraint — return the catalogue",
            # which is what several gold calls do. Treating that as a missing
            # key would forward `column_filters={}` as a column constraint and
            # match nothing.
            filters = kw.get("column_filters") or {}
        else:
            # Constraints passed as plain kwargs instead of nested.
            filters = {k: val for k, val in kw.items() if k != "catalog"}
        tl = retry(lambda: v.query_constraints(catalog=cat, **filters),
                   what="vizier")
    elif fn.endswith("query_region"):
        coord = _vizier_center(kw)
        rad = _vizier_radius(kw)
        tl = retry(lambda: v.query_region(coord, radius=rad, catalog=cat),
                   what="vizier")
    elif fn.endswith("query_object"):
        obj = kw.get("object_name") or kw.get("object")
        if not obj:
            raise ValueError("query_object needs object_name")
        tl = retry(lambda: v.query_object(str(obj), catalog=cat), what="vizier")
    elif fn.endswith("get_catalogs"):
        # Fetches whole catalogues by name — a legitimate way to express
        # "give me all of VII/202" that no gold call happens to use, so it
        # was falling through to generic dispatch and failing there.
        tl = retry(lambda: v.get_catalogs(cat), what="vizier")
    else:
        raise ValueError(f"unsupported vizier function: {fn}")

    outs, total, cols = [], 0, []
    for tname in (tl.keys() if len(tl) else []):
        tb = tl[tname]
        df = tb.to_pandas() if len(tb) else pd.DataFrame()
        safe = str(tname).replace("/", "_")
        name, fmt = save_df(df, d / f"call_{idx:02d}__{safe}.parquet")
        outs.append({"table": str(tname), "output": name, "rows": int(len(df)),
                     "columns": [str(c) for c in df.columns]})
        total += len(df)
        cols = cols or [str(c) for c in df.columns]
    return _result(outs[0]["output"] if outs else "", "parquet_multi", None,
                   rows=total, columns=cols, tables=outs, n_tables=len(outs))


# ---------------------------------------------------------------------------
# The four original platforms (benchmark.combined)
#
# These were downloaded by a separate pipeline when the benchmark was built,
# so the exec path never had handlers for them and every declared call fell
# through to generic dispatch — where all four fail for their own reason:
#
#   usgs  dataretrieval returns (frame, metadata); a tuple is not a frame
#   gbif  occurrences.search returns {count, results}; json_normalize of the
#         dict yields ONE row, and nothing pages past the first 300 records
#   epa   bdate/edate are typed datetime.date, and the client needs
#         credentials installed before any query
#   neon  the fetchers write zips to disk and return None (or a dict of
#         frames), and prompt interactively unless check_size=False
#
# All four are executor gaps, not call-construction errors, so they are fixed
# here rather than by rewriting what the agent declared.
# ---------------------------------------------------------------------------

def _unwrap_frame(res):
    """dataretrieval returns (frame, metadata); everything else is itself."""
    if isinstance(res, tuple):
        res = res[0] if res else None
    if res is None:
        return pd.DataFrame()
    return res


def _degeo(df):
    """Rewrite geometry columns as WKT text so the frame can go to parquet.

    dataretrieval returns a GeoDataFrame whose geometry column carries
    geopandas' own extension dtype, not `object`, so a dtype==object test
    misses it and `to_parquet` then dies with "Conversion failed for column
    geometry". The fallback wrote CSV instead, and the CSV round-trip stripped
    the leading zeros off `parameter_code` ("00060" -> 60) and `statistic_id`,
    which made every row key differ from gold: a scenario that had fetched
    byte-identical data scored record_cov 0.0. Both cases are handled here.
    """
    try:
        from shapely.geometry.base import BaseGeometry
    except Exception:
        BaseGeometry = ()                       # shapely absent: dtype test only
    df = df.copy()
    for c in df.columns:
        col = df[c]
        is_geo_dtype = "geometry" in str(col.dtype).lower()
        holds_geom = (col.dtype == object and col.notna().any()
                      and BaseGeometry
                      and isinstance(col.dropna().iloc[0], BaseGeometry))
        if is_geo_dtype or holds_geom:
            df[c] = col.map(lambda g: None if g is None else
                            (g.wkt if hasattr(g, "wkt") else str(g)))
    if type(df).__name__ == "GeoDataFrame":
        df = pd.DataFrame(df)
    return df


# ---------------------------------------------------------------------------
# USGS token rotation
#
# The waterdata API rate-limits per token, and the agent runs declare ~1,400
# distinct USGS calls, so one token stalls the sweep. `.bashrc` carries four
# (API_USGS_PAT1..4); rotate through them on 429 and cool the exhausted one
# down. This mirrors `generate_phase2_gt.USGSTokenPool`, reimplemented here so
# the exec path does not depend on the neon-bench tree.
#
# `dataretrieval` reads the token from os.environ["API_USGS_PAT"] on every
# call, so activating a token means setting that variable.
# ---------------------------------------------------------------------------

_USGS_PROBE = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items"


class USGSTokenPool:
    def __init__(self, fallback_cooldown: float = 600.0):
        self.tokens = [os.environ[f"API_USGS_PAT{i}"]
                       for i in range(1, 5) if os.environ.get(f"API_USGS_PAT{i}")]
        if not self.tokens and os.environ.get("API_USGS_PAT"):
            self.tokens = [os.environ["API_USGS_PAT"]]
        self.cooldowns = {t: 0.0 for t in self.tokens}
        self.idx = 0
        self.fallback_cooldown = fallback_cooldown
        if self.tokens:
            self._activate()
            log(f"[USGS] token pool: {len(self.tokens)} token(s)")
        else:
            log("[USGS] WARNING: no API_USGS_PAT* in env — rate limits will bite")

    def _activate(self):
        os.environ["API_USGS_PAT"] = self.tokens[self.idx]

    def label(self) -> str:
        return f"#{self.idx+1}/{self.tokens[self.idx][:8]}..." if self.tokens else "(none)"

    def _retry_after(self) -> float:
        """Ask the service how long this token is out for. Costs one request."""
        try:
            r = requests.get(_USGS_PROBE, params={"limit": 1},
                             headers={"X-Api-Key": self.tokens[self.idx]}, timeout=15)
            ra = r.headers.get("Retry-After")
            if ra is not None:
                try:
                    return float(ra)
                except ValueError:
                    pass
            rem = r.headers.get("X-RateLimit-Remaining")
            if rem is not None and r.status_code == 200 and int(rem) > 0:
                return 0.0
        except Exception:
            pass
        return self.fallback_cooldown

    def mark_cooldown(self):
        if not self.tokens:
            return
        secs = self._retry_after()
        self.cooldowns[self.tokens[self.idx]] = time.time() + secs
        log(f"    [USGS] token {self.label()} cooling {secs:.0f}s")

    def rotate(self):
        if not self.tokens:
            return
        now = time.time()
        n = len(self.tokens)
        for step in range(1, n + 1):
            cand = (self.idx + step) % n
            if self.cooldowns[self.tokens[cand]] <= now:
                self.idx = cand
                self._activate()
                log(f"    [USGS] rotated -> {self.label()}")
                return
        earliest = min(range(n), key=lambda i: self.cooldowns[self.tokens[i]])
        wait = max(0.0, self.cooldowns[self.tokens[earliest]] - now) + 5.0
        log(f"    [USGS] all {n} tokens cooling — sleeping {wait:.0f}s")
        time.sleep(wait)
        self.idx = earliest
        self._activate()
        self.cooldowns[self.tokens[earliest]] = 0.0


_USGS_POOL: "USGSTokenPool | None" = None


def usgs_pool() -> USGSTokenPool:
    global _USGS_POOL
    if _USGS_POOL is None:
        _USGS_POOL = USGSTokenPool()
    return _USGS_POOL


def _is_429(e: Exception) -> bool:
    s = str(e)
    return "429" in s or "Too Many Requests" in s or "rate limit" in s.lower()


def _usgs_with_rotation(fn, kw: dict):
    """One USGS call, rotating tokens on 429."""
    pool = usgs_pool()
    attempts = (len(pool.tokens) * 3 + 2) if pool.tokens else 1
    last = None
    for i in range(attempts):
        try:
            return fn(**kw)
        except Exception as e:
            if pool.tokens and _is_429(e):
                last = e
                log(f"      [USGS] 429 {i+1}/{attempts} ({pool.label()})")
                pool.mark_cooldown()
                pool.rotate()
                continue
            raise
    raise last


# `get_continuous` rejects windows longer than ~1100 days. An agent asking for
# a decade is asking for something the service will serve — in pieces — so the
# window is split here rather than the call being failed.
_USGS_CONTINUOUS_MAX_DAYS = 1090


def _split_window(time_str, max_days: int) -> list:
    if not isinstance(time_str, str) or "/" not in time_str:
        return [time_str]
    a, b = (s.strip() for s in time_str.split("/", 1))
    try:
        start = _dtdate.fromisoformat(a)
        end = _dtdate.fromisoformat(b)
    except ValueError:
        return [time_str]
    if (end - start).days <= max_days:
        return [time_str]
    out, cur = [], start
    step = _dt.timedelta(days=max_days)
    while cur <= end:
        seg = min(cur + step, end)
        out.append(f"{cur.isoformat()}/{seg.isoformat()}")
        cur = seg + _dt.timedelta(days=1)
    return out


def _keep_index(df):
    """Move a meaningful index into a column before the frame is saved.

    `save_df` writes parquet with `index=False`, and `dataretrieval.nwis`
    returns the OBSERVATION DATE as the index (named `datetime`) rather than
    as a column. So every NWIS time-series result was cached with its dates
    silently discarded: 12,053 values and no way to tell which day any of them
    belonged to, which no amount of column mapping can repair downstream. The
    Water Data endpoints put the date in a `time` column and are unaffected.
    """
    if df is None or not hasattr(df, "index"):
        return df
    idx = df.index
    named = idx.name is not None and str(idx.name) not in ("", "None")
    if named or isinstance(idx, pd.DatetimeIndex):
        name = idx.name or "datetime"
        if name not in df.columns:
            df = df.reset_index()
            if "index" in df.columns and name != "index":
                df = df.rename(columns={"index": name})
    return df


def h_usgs(kw, fn, d, idx, opts):
    """`dataretrieval`, any of its query functions.

    The package exposes the same function from several modules
    (`dataretrieval.get_daily`, `dataretrieval.waterdata.get_daily`) and the
    agents used every spelling. Resolution is by attribute lookup on the
    declared module, so a name that does not exist still raises AttributeError
    and is recorded as not-callable.
    """
    import importlib
    mod_name = opts.get("_module") or "dataretrieval"
    try:
        mod = importlib.import_module(mod_name)
    except ImportError:
        mod = importlib.import_module("dataretrieval")
    name = fn.split(".")[-1]
    if not hasattr(mod, name):
        raise AttributeError(f"{mod_name} has no attribute {name!r}")
    call = getattr(mod, name)

    windows = _split_window(kw.get("time"), _USGS_CONTINUOUS_MAX_DAYS) \
        if name == "get_continuous" else [None]
    if len(windows) > 1:
        log(f"      [USGS] splitting {kw.get('time')} into {len(windows)} "
            f"sub-windows (1100-day cap)")
        frames = []
        for w in windows:
            frames.append(_keep_index(_unwrap_frame(
                _usgs_with_rotation(call, {**kw, "time": w}))))
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    else:
        df = _unwrap_frame(_usgs_with_rotation(call, kw))
    df = _degeo(_keep_index(df))
    name_out, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(name_out, fmt, df, usgs_function=name,
                   sub_windows=len(windows) if len(windows) > 1 else None)


# Occurrence search pages at 300; the API refuses offsets past 100,000.
GBIF_PAGE = 300
GBIF_MAX_ROWS_DEFAULT = 100_000


def h_gbif(kw, fn, d, idx, opts):
    """`pygbif`. `occurrences.search` is paged; lookups return their payload.

    Paging is the handler's business, not the caller's: an agent that declares
    `limit=300, offset=0` is describing the same retrieval as one that
    declares nothing, and forwarding those verbatim would truncate the result
    to a single page. Both collapse onto the full record set.
    """
    from pygbif import occurrences, species, registry
    name = fn.split(".")[-1]
    cap = int(opts.get("gbif_max_rows") or GBIF_MAX_ROWS_DEFAULT)

    if name in ("search", "occ_search"):
        q = {k: v for k, v in kw.items()
             if k not in ("limit", "offset", "page", "per_page")}
        probe = retry(lambda: occurrences.search(limit=1, **q), what="gbif probe")
        total = int(probe.get("count") or 0)
        if total > cap:
            return _result("", "none", None, rows=0, total_available=total,
                           status_override="skipped_too_large",
                           note=f"{total:,} > --gbif-max-rows {cap:,}")
        rows, offset = [], 0
        while offset < min(total, 100_000):
            r = retry(lambda o=offset: occurrences.search(limit=GBIF_PAGE,
                                                          offset=o, **q),
                      what="gbif page")
            got = r.get("results") or []
            if not got:
                break
            rows.extend(got)
            offset += GBIF_PAGE
            if r.get("endOfRecords"):
                break
        df = pd.json_normalize(rows) if rows else pd.DataFrame()
        out, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
        return _result(out, fmt, df, gbif_count=total)

    # Metadata / lookup endpoints — one payload, no paging.
    src = {"name_backbone": species, "name_suggest": species,
           "name_lookup": species, "dataset_search": registry,
           "datasets": registry}.get(name, occurrences)
    if not hasattr(src, name):
        raise AttributeError(f"pygbif has no {name!r}")
    payload = retry(lambda: getattr(src, name)(**kw), what=f"gbif {name}")
    if isinstance(payload, pd.DataFrame):
        df = payload
    elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
        df = pd.json_normalize(payload["results"])
    elif isinstance(payload, list):
        df = pd.json_normalize(payload)
    else:
        df = pd.json_normalize([payload])
    out, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(out, fmt, df, gbif_endpoint=name)


_AQS_READY = []


def _aqs_date(v):
    """pyaqsapi types bdate/edate as datetime.date; gold writes them as text."""
    import datetime as _d
    if isinstance(v, _d.date):
        return v
    s = str(v).strip()
    if "T" in s:                       # ISO datetime -> keep the date part
        s = s.split("T", 1)[0]
    for f in ("%Y-%m-%d", "%Y%m%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return _d.datetime.strptime(s, f).date()
        except ValueError:
            continue
    raise ValueError(f"unparseable AQS date {v!r}")


def h_epa(kw, fn, d, idx, opts):
    """`pyaqsapi`, any aggregation level.

    Credentials are installed once per process; the declared call never
    carries them (`aqs_credentials` is classified as a setup call).
    """
    import importlib
    if not _AQS_READY:
        import pyaqsapi
        user, key = os.environ.get("AQS_USER"), os.environ.get("AQS_KEY")
        if not user or not key:
            raise RuntimeError("AQS_USER / AQS_KEY not set")
        pyaqsapi.aqs_credentials(username=user, key=key)
        _AQS_READY.append(True)

    mod_name = opts.get("_module") or "pyaqsapi"
    try:
        mod = importlib.import_module(mod_name)
    except ImportError:
        raise AttributeError(f"no module {mod_name!r} in pyaqsapi")
    name = fn.split(".")[-1]
    if not hasattr(mod, name):
        raise AttributeError(f"{mod_name} has no attribute {name!r}")

    kw = dict(kw)
    for k in ("bdate", "edate", "cbdate", "cedate"):
        if kw.get(k) is not None:
            kw[k] = _aqs_date(kw[k])
    df = _unwrap_frame(retry(lambda: getattr(mod, name)(**kw),
                             what=f"epa {name}"))
    if not isinstance(df, pd.DataFrame):
        df = pd.json_normalize(getattr(df, "data", df))
    out, fmt = save_df(df, d / f"call_{idx:02d}.parquet")
    return _result(out, fmt, df, aqs_function=f"{mod_name}.{name}")


# Metadata shipped inside every NEON zip. They describe the product rather
# than measure anything, are identical across sites and months, and would
# dominate a table-level comparison, so they are never a merge unit.
NEON_META_TABLES = frozenset({
    "validation", "categoricalCodes", "variables", "readme", "sensor_positions",
    "science_review_flags", "issueLog", "citation",
})


def _neon_sites(dpid: str, startdate=None, enddate=None) -> list:
    """Sites publishing `dpid` inside the requested window."""
    r = requests.get(f"https://data.neonscience.org/api/v0/products/{dpid}",
                     headers={"X-API-Token": os.environ.get("NEON_TOKEN", "")},
                     timeout=60)
    r.raise_for_status()
    out = []
    for sc in r.json()["data"]["siteCodes"]:
        months = sc.get("availableMonths") or []
        if startdate:
            months = [m for m in months if m >= str(startdate)[:7]]
        if enddate:
            months = [m for m in months if m <= str(enddate)[:7]]
        if months:
            out.append(sc["siteCode"])
    return sorted(out)


def h_neon(kw, fn, d, idx, opts):
    """`neonutilities`, the zip fetchers.

    Both `zips_by_product` and `load_by_product` are answered by downloading
    the month/site zips: that is what gold holds (`format: neon_zips`), and
    the grader stacks the per-table CSVs out of them for both sides. Writing
    the zips also avoids `load_by_product`'s in-memory stack, which spikes to
    tens of GB on the larger products.
    """
    import neonutilities as nu
    name = fn.split(".")[-1]
    if name not in ("zips_by_product", "load_by_product"):
        raise ValueError(f"unsupported neon function: {fn}")

    out_dir = d / f"call_{idx:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    q = {k: v for k, v in kw.items()
         if k not in ("savepath", "check_size", "token", "progress")}
    q.setdefault("package", "basic")

    # `site="all"` makes neonutilities scan every publishing site-month before
    # it downloads anything — 258 requests for DP1.10081.001 over three years —
    # and the scan is atomic: one dropped connection loses all of it and starts
    # over. Measured against the live API with a token the limit is 2000 and a
    # 36-request burst consumed 5 of it, so this was never a quota problem;
    # it was a connection drop retried by restarting the whole scan.
    #
    # Issuing one call per publishing site retrieves the same data — "all"
    # means the sites publishing the product — while capping a lost scan at a
    # dozen requests. Zips already on disk are skipped, so progress survives.
    site = q.get("site", "all")
    if isinstance(site, str) and site.lower() == "all":
        try:
            sites = _neon_sites(q["dpid"], q.get("startdate"), q.get("enddate"))
            log(f"      [NEON] site='all' -> {len(sites)} publishing sites")
        except Exception as e:
            log(f"      [NEON] site expansion failed ({type(e).__name__}); using 'all'")
            sites = ["all"]
    elif isinstance(site, (list, tuple)):
        sites = list(site)
    else:
        sites = [site]

    failed = []
    for s in sites:
        try:
            retry(lambda s=s: nu.zips_by_product(
                      savepath=str(out_dir), check_size=False, progress=False,
                      token=os.environ.get("NEON_TOKEN"), **{**q, "site": s}),
                  what=f"neon {q.get('dpid')} {s}")
        except Exception as e:
            failed.append(f"{s}: {type(e).__name__}")
            log(f"      [NEON] {s} failed: {type(e).__name__}: {str(e)[:120]}")
    if failed and len(failed) == len(sites):
        raise RuntimeError("every NEON site failed: " + "; ".join(failed[:5]))

    files = sorted(str(f.relative_to(out_dir))
                   for f in out_dir.rglob("*") if f.is_file())
    total = sum((out_dir / f).stat().st_size for f in files)
    return _result(f"call_{idx:02d}/", "neon_zips", None,
                   num_zip_files=sum(1 for f in files if f.endswith(".zip")),
                   total_bytes=int(total),
                   files=[{"file": f} for f in files],
                   declared_function=name)


HANDLERS = {
    "neon": h_neon, "gbif": h_gbif, "usgs": h_usgs, "epa": h_epa,
    "argo": h_argo, "cmip6": h_cmip6, "ensembl": h_ensembl,
    "census_acs": h_census_acs, "inaturalist": h_inaturalist,
    "matproj": h_matproj, "noaa_ghcn": h_noaa_ghcn,
    "obis": h_obis, "pangaea": h_pangaea, "usgs_eq": h_usgs_eq,
    "vizier": h_vizier,
}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def _package_versions() -> dict:
    import importlib
    out = {}
    for m in ("argopy", "intake_esgf", "pyinaturalist", "astroquery",
              "pyobis", "pangaeapy", "obspy", "pandas", "requests"):
        try:
            out[m] = str(getattr(importlib.import_module(m), "__version__", "?"))
        except Exception:
            out[m] = None
    return out

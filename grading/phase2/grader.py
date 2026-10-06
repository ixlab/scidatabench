"""Grade Phase 2 on the data retrieved, not on the calls declared.

The reference plan and the agent's plan are both executed; their results are
merged per the platform registry and compared. Three numbers per scenario:

    record_cov   |K_gold ∩ K_agent| / |K_gold|     did the rows arrive
    value_fid    agreement on the columns both sides carry, over matched rows
    time_cov     |T_gold ∩ T_agent| / |T_gold|     was the whole period covered

`over = |K_agent| / |K_gold|` is reported but does not gate the primary
verdict.

Relation to prior work
----------------------
Execution-based text-to-SQL grading compares the result *table* rather than
the query. Spider and Spider 2.0 use Execution Accuracy — the returned
multiset of rows must equal the reference — and Spider 2.0-lite relaxes this
to column containment: every gold column must appear in the prediction. BIRD's
Soft-F1 relaxes it further, giving partial credit from row-level and
element-level overlap so that returning 99 of 100 correct rows is not scored
identically to returning none.

Two things make a straight port of those metrics wrong here:

  * Their result tables are small and unkeyed, so rows are compared as a set
    of value tuples. Ours are scientific records with a natural identity —
    a float cycle at a depth, a station-day, an event id — and that identity
    is stable across retrieval paths while the accompanying columns are not.
    Keying on identity separates "the row is missing" from "the row is there
    with a different value", which set overlap conflates.
  * A single number hides skew. If one station holds 99% of the rows, an
    agent that fetched only that station scores 0.99 on row overlap. The time
    axis is reported separately for that reason.

So `record_cov` is Soft-F1's recall computed on the record key instead of on
whole rows, `value_fid` is its element-level term restricted to rows that
matched, and containment (rather than equality) follows Spider 2.0-lite.
"""
from __future__ import annotations

import io
import json
import math
import os
import pathlib
import re
import zipfile
from typing import Any

import pandas as pd

from .registry import spec_for, is_volatile

# One tolerance across the benchmark, matching phases 3 and 4.
REL_TOL = 0.05
# Coverage/fidelity thresholds of the pass criterion (paper, Section 2.2).
EPS_RECORD = 0.02
EPS_VALUE = 0.01
EPS_TIME = 0.02
EPS_OVER = 0.05
OVER_CEILING = 100.0        # a whole-archive download can never pass


# ---------------------------------------------------------------------------
# Loading a call's payload
# ---------------------------------------------------------------------------

def needed_columns(spec) -> set[str] | None:
    """Lowercased columns the metrics actually read, or None to keep them all.

    Everything else in a payload is dead weight here, and the weight is not
    small: `dataretrieval.get_samples` returns 176 WQX columns and a single
    USGS scenario can declare 286 calls. Concatenating those whole made the
    grader allocate 64 GB on the usgs sweep and get OOM-killed, taking the
    entire eight-baseline run with it — silently, since a killed process
    writes no traceback.

    Projection is only safe where the platform names its value columns. When
    `value_cols` is empty the comparison is "whatever gold and agent share",
    which is not knowable from one side, so those platforms are read whole.
    """
    if not spec.value_cols:
        return None
    want = {c.strip().lower() for opt in spec.key for c in opt}
    want |= {c.strip().lower() for c in spec.value_cols}
    want |= {c.strip().lower() for c in spec.time_col}
    return want


def _read_frame(path: pathlib.Path,
                want: set[str] | None = None) -> pd.DataFrame | None:
    try:
        if path.suffix == ".parquet":
            if want:
                # Ask the reader for the subset: parquet is columnar, so the
                # rest is never materialised at all.
                import pyarrow.parquet as pq
                have = [c for c in pq.ParquetFile(path).schema.names
                        if str(c).strip().lower() in want]
                if have:
                    return pd.read_parquet(path, columns=have)
            return pd.read_parquet(path)
        if path.suffix == ".json":
            payload = json.loads(path.read_text())
            if isinstance(payload, list):
                df = pd.json_normalize(payload) if payload else pd.DataFrame()
            else:
                df = pd.json_normalize([payload])
            return _project(df, want)
        if path.suffix == ".csv":
            return _project(pd.read_csv(path, low_memory=False), want)
    except Exception:
        return None
    return None


def _project(df: pd.DataFrame, want: set[str] | None) -> pd.DataFrame:
    if not want or df is None or df.empty:
        return df
    keep = [c for c in df.columns if str(c).strip().lower() in want]
    return df[keep] if keep else df


# NEON ships one zip per site-month, and each zip holds several unrelated
# tables plus the product's metadata. Gold stores those zips verbatim
# (`format: neon_zips`, no parquet), so both sides are stacked here rather
# than at download time — the gold cache stays exactly as it was built.
#
# The table name is the merge unit. NEON file names are
#     NEON.<domain>.<site>.<DPID>.<table>.<month>.<package>.<timestamp>.csv
# and the token before the month is the table.
NEON_META_TABLES = frozenset({
    "validation", "categoricalCodes", "variables", "readme",
    "sensor_positions", "science_review_flags", "issueLog", "citation",
})


def _neon_parse(member: str) -> tuple[str, dict] | None:
    """(table, columns-to-inject) for a NEON csv member, or None if metadata.

    NEON writes two filename layouts, and the parser used to know only one:

      observational (OS)  NEON.D14.SRER.DP1.10022.001.bet_sorting.2016-10.basic.<ts>
                           0   1   2    3    4    5       6          7
      instrumented  (IS)  NEON.D17.SJER.DP1.00002.001.000.040.030.SAAT_30min.2020-08.basic.<ts>
                           0   1   2    3    4    5   6   7   8       9        10

    An IS file carries HOR.VER.TMI — horizontal position, vertical position,
    averaging interval — between the product id and the table name. Reading
    parts[6] as the table gave "000", and parts[7] ("040") then failed the
    YYYY-MM check, so EVERY sensor data file was classified as metadata and
    dropped. Seven phase-2 scenarios were graded UNGRADABLE ("gold retrieved
    no rows") on gold directories holding 5 MB to 6.4 GB of data — every one
    of them an IS product (air temperature, wind, pressure, humidity,
    precipitation, soil water).

    For IS files the position has to be kept as COLUMNS, because the same
    table (SAAT_30min) is published once per sensor height and those rows are
    different measurements at the same timestamp. NEON's own stackByTable does
    exactly this — it adds siteID, horizontalPosition and verticalPosition —
    so the injected names match what a stacked agent result would carry.
    """
    stem = member.rsplit("/", 1)[-1]
    if not stem.endswith(".csv"):
        return None
    parts = stem[:-4].split(".")
    if len(parts) < 7 or parts[0] != "NEON":
        return None
    site = parts[2]
    if (len(parts) >= 11 and parts[6].isdigit() and parts[7].isdigit()
            and parts[8].isdigit()):
        name, month = parts[9], parts[10]
        inject = {"siteID": site, "horizontalPosition": parts[6],
                  "verticalPosition": parts[7]}
    else:
        name = parts[6]
        month = parts[7] if len(parts) > 7 else None
        inject = {"siteID": site}
    if name in NEON_META_TABLES:
        return None
    # Metadata files carry the table slot but no month: NEON.D14.SRER.DP0.
    # 10022.001.validation.<ts>.csv is caught above; anything left whose next
    # token is not YYYY-MM is a product-level file, not an observation table.
    if month is not None and not _MONTHISH.match(month):
        return None
    return name, inject


def _neon_table_name(member: str) -> str | None:
    """Table name from a NEON csv member path, or None if it is metadata."""
    got = _neon_parse(member)
    return got[0] if got else None


_MONTHISH = re.compile(r"^\d{4}-\d{2}$")


def _neon_cache_dir(root: pathlib.Path) -> pathlib.Path:
    """Where the stacked tables for one NEON call directory are kept.

    Stacking means opening every month zip and parsing the CSVs inside, which
    for a large product is minutes of work — and the same gold directory is
    stacked once per baseline, eight times over. The result is deterministic,
    so it is written out once and read back as parquet afterwards.
    """
    import hashlib
    key = f"{_NEON_STACK_VERSION}|{root.resolve()}"
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return _NEON_STACK_ROOT / h[:2] / h


# Bumped whenever stacking changes what it produces. v1 stacks were written by
# a parser that dropped every IS (sensor) file, so they record `[]` for every
# sensor product; v2 kept every averaging interval; v3 keeps only the coarsest
# (see _neon_keep_members). A new version makes older stacks unreachable
# without deleting them.
_NEON_STACK_VERSION = "3-coarsest-tmi"


# Stacked NEON tables are cached here (default: `cache/neon_stack` in the
# repository). Point SCIDATABENCH_NEON_STACK_CACHE at a larger disk when the
# repository's is small: a full NEON sweep stacks tens of GB.
_NEON_STACK_ROOT = pathlib.Path(
    os.environ.get("SCIDATABENCH_NEON_STACK_CACHE")
    or pathlib.Path(__file__).resolve().parents[2] / "cache" / "neon_stack")


def _neon_keep_members(names: list[str]) -> set[str]:
    """The IS members to stack: the COARSEST averaging interval per sensor.

    A NEON sensor product publishes the same measurement at several averaging
    intervals — SAAT_1min and SAAT_30min, EOS_1_min / EOS_5_min / EOS_30_min —
    and the interval is the TMI field of the filename. Checked across every
    gold zip: each finer-interval table is an interval variant of the coarser
    one kept for that product, never a different quantity.

    Keeping only the coarsest interval is not an approximation of the grade.
    NEON ships one zip per product/site/month holding EVERY interval, so an
    agent cannot retrieve the 30-minute table without the 1-minute one; the
    two are the same evidence about whether it fetched the right product,
    site and window, which is what phase 2 grades. The finer tables are,
    however, almost all of the volume — 36.0 of the 37.5 GB in
    hess-23-1179-2019 — and stacking them whole on both sides exceeds the
    64 GB cgroup, which ends in SIGSEGV rather than MemoryError.

    It also stops penalising a legitimate choice: neonutilities'
    `timeindex=30` fetches only the 30-minute files. Graded on every interval,
    that agent would have lost record coverage for skipping 1-minute data the
    task never needed.

    Grouped by (product, horizontal, vertical) so each sensor position keeps
    its own coarsest table. OS members are all kept.

    Known edge, checked rather than assumed: an agent that fetched ONLY a finer
    published interval (`timeindex=1` on SAAT) keeps SAAT_1min while gold keeps
    SAAT_30min, so the two never meet and correct data scores zero. Across all
    nine graded runs (2026-09-10) no agent call did that — 85 asked for the
    coarsest interval, 50 for one the product does not publish (which returns
    no data from neonutilities itself), 401 set no interval. Re-check before
    relying on this rule for a new run.
    """
    best: dict[tuple, str] = {}
    info: dict[str, tuple] = {}
    for m in names:
        if not m.endswith(".csv"):
            continue
        p = m.rsplit("/", 1)[-1][:-4].split(".")
        if (len(p) >= 11 and p[0] == "NEON" and p[6].isdigit()
                and p[7].isdigit() and p[8].isdigit()):
            grp = (p[3], p[4], p[5], p[6], p[7])
            info[m] = (grp, p[8])
            if p[8] > best.get(grp, ""):
                best[grp] = p[8]
    return {m for m in names if m not in info or info[m][1] == best[info[m][0]]}


def _neon_frames(d: pathlib.Path, output: str,
                 want: set[str] | None = None) -> list[tuple[str, pd.DataFrame]]:
    """Stack every zip under the call directory into one frame per table."""
    root = d / str(output).rstrip("/")
    if not root.is_dir():
        return []

    cache = _neon_cache_dir(root)
    manifest = cache / "tables.json"
    if manifest.is_file():
        try:
            names = json.loads(manifest.read_text())
            out = []
            for tab in names:
                f = cache / f"{tab}.parquet"
                if f.is_file():
                    df = _read_frame(f, want)
                    if df is not None and len(df):
                        out.append((tab, df))
            return out
        except Exception:
            pass                                  # corrupt cache -> restack

    by_table: dict[str, list[pd.DataFrame]] = {}
    zips = sorted(root.rglob("*.zip"))
    # First pass reads only the zip DIRECTORIES, to find each sensor's coarsest
    # interval across the whole call before any data is decompressed.
    all_names: list[str] = []
    for z in zips:
        try:
            with zipfile.ZipFile(z) as zf:
                all_names.extend(zf.namelist())
        except Exception:
            continue
    keep = _neon_keep_members(all_names)
    for z in zips:
        try:
            zf = zipfile.ZipFile(z)
        except Exception:
            continue
        with zf:
            for member in zf.namelist():
                if member not in keep:
                    continue
                got = _neon_parse(member)
                if got is None:
                    continue
                table, inject = got
                try:
                    df = pd.read_csv(io.BytesIO(zf.read(member)),
                                     low_memory=False)
                except Exception:
                    continue
                if len(df):
                    for col, val in inject.items():
                        if col not in df.columns:
                            df[col] = val
                    by_table.setdefault(table, []).append(df)
    # Loose csvs, for a call that was unzipped on disk rather than left zipped.
    loose = sorted(root.rglob("*.csv"))
    keep_loose = _neon_keep_members([c.name for c in loose])
    for c in loose:
        if c.name not in keep_loose:
            continue
        got = _neon_parse(c.name)
        if got is None:
            continue
        table, inject = got
        try:
            df = pd.read_csv(c, low_memory=False)
        except Exception:
            continue
        for col, val in inject.items():
            if col not in df.columns:
                df[col] = val
        if len(df):
            by_table.setdefault(table, []).append(df)
    out = []
    for table, frames in sorted(by_table.items()):
        try:
            out.append((table, pd.concat(frames, ignore_index=True)))
        except Exception:
            continue
    try:
        cache.mkdir(parents=True, exist_ok=True)
        for table, df in out:
            df.to_parquet(cache / f"{table}.parquet", index=False)
        (cache / "tables.json").write_text(json.dumps([t for t, _ in out]))
    except Exception:
        pass                                      # cache is an optimisation
    return [(tab, _project(df, want)) for tab, df in out]


# ---------------------------------------------------------------------------
# USGS: one set of observations, two API generations
# ---------------------------------------------------------------------------

# NWIS returns a WIDE frame: the parameter and the statistic are encoded in
# the column NAME (`00060_Mean`), the date is the index, the site has no
# `USGS-` prefix, and the approval flag is a letter code. Water Data returns
# the same observations LONG: one `value` column with `parameter_code`,
# `statistic_id`, `time` and `monitoring_location_id` beside it.
#
# Verified against the live services (site 01594440, 00060, 1985-2017):
# 12,053 rows on both sides, every date shared, all 12,053 values identical.
# The difference is presentation, so it is undone here rather than being
# scored as missing data.
#
# NWIS statistic suffixes -> USGS statistic codes.
_NWIS_STAT = {"mean": "00003", "max": "00001", "min": "00002",
              "sum": "00006", "median": "00008", "": "00003"}
_NWIS_APPROVAL = {"A": "Approved", "P": "Provisional", "e": "Estimated"}
_NWIS_VALUE_COL = re.compile(r"^(\d{5})(?:_(\w+?))?(_cd)?$")


def _nwis_approval(code) -> str:
    """'A' -> Approved, 'A, e' -> Approved (the estimate flag is kept apart)."""
    s = str(code or "").strip()
    if not s:
        return ""
    first = s.split(",")[0].strip()
    return _NWIS_APPROVAL.get(first, first)


def _normalise_usgs(df: "pd.DataFrame", function: str) -> "pd.DataFrame":
    """Rewrite an NWIS time-series frame into the Water Data column vocabulary."""
    if df is None or df.empty:
        return df
    cols = {str(c) for c in df.columns}
    # Already long (Water Data), or a schema this does not apply to.
    if "monitoring_location_id" in cols or "Result_MeasureIdentifier" in cols:
        return df
    value_cols = [c for c in df.columns if _NWIS_VALUE_COL.match(str(c))
                  and not str(c).endswith("_cd")]
    if not value_cols:
        return df

    df = df.reset_index()
    time_col = next((c for c in ("datetime", "date", "time")
                     if c in df.columns), None)
    site_col = next((c for c in ("site_no", "site", "monitoring_location_id")
                     if c in df.columns), None)
    if time_col is None or site_col is None:
        return df

    times = pd.to_datetime(df[time_col], errors="coerce", utc=True)
    times = times.dt.tz_localize(None).dt.normalize()
    sites = df[site_col].astype(str).str.strip()
    sites = sites.where(sites.str.startswith("USGS-"), "USGS-" + sites)

    out = []
    for vc in value_cols:
        m = _NWIS_VALUE_COL.match(str(vc))
        pcode = m.group(1)
        stat = _NWIS_STAT.get((m.group(2) or "").lower(), "00003")
        cd = f"{vc}_cd"
        out.append(pd.DataFrame({
            "monitoring_location_id": sites,
            "parameter_code": pcode,
            "statistic_id": stat,
            "time": times,
            "value": pd.to_numeric(df[vc], errors="coerce"),
            "approval_status": (df[cd].map(_nwis_approval)
                                if cd in df.columns else ""),
        }))
    return pd.concat(out, ignore_index=True).dropna(subset=["value"])


def load_call(meta: dict, d: pathlib.Path, platform: str,
              want: set[str] | None = None) -> list[tuple[str, pd.DataFrame]]:
    """Return [(unit, frame), ...] for one executed call.

    A call usually yields one frame. VizieR is the exception: one query
    returns a TableList, and each catalogue table is its own merge unit.
    """
    if meta.get("status") != "success":
        return []
    spec = spec_for(platform)
    out: list[tuple[str, pd.DataFrame]] = []

    # An explicit projection from the caller wins: for NEON the columns worth
    # keeping are the ones the OTHER side actually carries, which the registry
    # cannot know (`value_cols` is empty because a NEON product's schema is
    # per-table). See grade_phase2_exec, which loads the agent first and then
    # reads gold through the agent's column set — `value_fid` compares the
    # intersection, so dropping what the other side lacks changes nothing.
    if want is None:
        want = needed_columns(spec)
    tables = meta.get("tables")
    if tables:                                   # parquet_multi (vizier)
        for t in tables:
            df = _read_frame(d / str(t.get("output") or ""), want)
            if df is not None:
                out.append((str(t.get("table") or ""), df))
        return out

    name = meta.get("output")
    if not name:
        return []

    if meta.get("format") == "neon_zips" or str(name).endswith("/"):
        # One frame per table, each its own merge unit.
        return _neon_frames(d, str(name), want)

    # NWIS frames are normalised into the Water Data vocabulary AFTER being
    # read, so their own column names must survive the projection.
    df = _read_frame(d / str(name), None if platform == "usgs" else want)
    if df is None:
        return []
    if platform == "usgs":
        df = _project(_normalise_usgs(df, str(meta.get("function") or "")), want)
    return [(_unit_of(meta, spec), df)]


_DOI_PREFIXES = ("doi:", "https://doi.org/", "http://doi.org/",
                 "https://dx.doi.org/", "http://dx.doi.org/")


def _norm_unit_value(v) -> str:
    """Canonicalise one kwarg value used as a merge-unit key.

    The unit key decides which gold table an agent table is compared against,
    so a purely cosmetic difference in how an identifier is written silently
    becomes "missing from agent result" — the agent's rows are never even
    looked at. That is a false negative, not a wrong answer: a PANGAEA call
    with `id="doi:10.1594/PANGAEA.905471"` returned the identical 26,750 rows
    as gold's `id="10.1594/PANGAEA.905471"`, and pangaeapy accepts both, yet
    the scenario scored 0.0 and all 16 pangaea scenarios in one run went the
    same way.

    Only two platforms key on kwargs (pangaea on `id`, census_acs on
    `dataset`+`year`), so the normalisation stays deliberately narrow:
    resolve DOI spellings and fold case. It never merges two identifiers that
    name different resources.
    """
    s = str(v if v is not None else "").strip()
    low = s.lower()
    for p in _DOI_PREFIXES:
        if low.startswith(p):
            s = s[len(p):]
            break
    return s.casefold()


def _unit_of(meta: dict, spec) -> str:
    src = spec.unit_from
    if not src:
        return ""
    if src == "function":
        fn = str(meta.get("function") or "").split(".")[-1]
        # Fold the endpoint onto the kind of data it returns, when the
        # platform declares a mapping. Unmapped endpoints keep their own name.
        return spec.unit_map.get(fn, fn) if spec.unit_map else fn
    if src.startswith("call_kwarg:"):
        kw = meta.get("kwargs") or {}
        parts = src.split(":", 1)[1].split("+")
        return "|".join(_norm_unit_value(kw.get(p, "")) for p in parts)
    return ""


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _col_lookup(df: pd.DataFrame) -> dict[str, str]:
    """lowercased name -> actual column name."""
    return {str(c).strip().lower(): c for c in df.columns}


def _pick_key(df: pd.DataFrame, spec, platform: str
              ) -> tuple[tuple[str, ...] | None, bool]:
    """Choose the row key. Returns (columns, row_keyed).

    Named keys are tried in order. Published catalogues that carry none of
    them — VizieR serves hundreds of tables, each with its own column names —
    fall back to the whole row as the identity. That is precisely Spider's
    execution-accuracy semantics: the row either appears in the result or it
    does not. `row_keyed` is returned so the caller can suppress value
    fidelity, which would otherwise be trivially 1.0 because the key already
    contains every value.
    """
    look = _col_lookup(df)
    for option in spec.key:
        cols = [look.get(c.strip().lower()) for c in option]
        if all(c is not None for c in cols):
            return tuple(cols), False          # type: ignore[arg-type]
    usable = [c for c in df.columns
              if str(c) not in ("__key", "__unit")
              and not is_volatile(platform, str(c))]
    if usable:
        return tuple(usable), True
    return None, False


def _norm_scalar(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none", "nat", "<na>"):
        return ""
    # 5901172.0 and 5901172 are the same float id.
    try:
        f = float(s)
        # inf / -inf / nan have no integer form; `int(inf)` raises
        # OverflowError, which crashed the whole run when one USGS value came
        # back as infinity. They are still legitimate cell values, so they
        # canonicalise to their own text rather than blowing up the key.
        if not math.isfinite(f):
            return s.lower()
        if f == int(f):
            return str(int(f))
        return repr(round(f, 6))
    except (TypeError, ValueError, OverflowError):
        return s


def key_series(df: pd.DataFrame, cols: tuple[str, ...], unit: str) -> pd.Series:
    parts = [df[c].map(_norm_scalar) for c in cols]
    s = parts[0]
    for p in parts[1:]:
        s = s + "|" + p
    return (unit + "||" if unit else "") + s


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------

def merge(frames: list[tuple[str, pd.DataFrame]], platform: str
          ) -> tuple[pd.DataFrame | None, list[str], bool]:
    """Fold a scenario's call outputs into one keyed table.

    Returns (table indexed by row identity, notes, row_keyed). The table is
    None when no frame carried any usable column at all.
    """
    spec = spec_for(platform)
    notes: list[str] = []
    keyed: list[pd.DataFrame] = []
    row_keyed = False
    for unit, df in frames:
        if df is None or df.empty:
            continue
        df = df.copy()
        df.columns = [str(c) for c in df.columns]
        # A duplicated label makes `df[label]` return a DataFrame rather than a
        # Series, which blows up key construction. GBIF occurrence payloads
        # carry `key` three times — json_normalize emits one per nesting depth
        # that happens to expose it — and that alone aborted the whole sweep.
        # A repeated label cannot be addressed unambiguously anyway, so the
        # first occurrence wins.
        if df.columns.duplicated().any():
            df = df.loc[:, ~df.columns.duplicated()]
        cols, rk = _pick_key(df, spec, platform)
        if cols is None:
            notes.append(f"no usable column in a {len(df)}-row frame "
                         f"(unit={unit or '-'})")
            continue
        if rk:
            row_keyed = True
            notes.append(f"no named key in a {len(df)}-row frame "
                         f"(unit={unit or '-'}) — keyed on the whole row")
        df["__key"] = key_series(df, cols, unit)
        df["__unit"] = unit
        keyed.append(df)
    if not keyed:
        return None, notes, row_keyed
    out = pd.concat(keyed, ignore_index=True, sort=False)
    # Same record fetched by two calls -> keep one.
    out = out.drop_duplicates(subset="__key", keep="first")
    return out, notes, row_keyed


# ---------------------------------------------------------------------------
# The three metrics
# ---------------------------------------------------------------------------

def _values_agree(a: Any, b: Any) -> bool:
    sa, sb = _norm_scalar(a), _norm_scalar(b)
    if sa == sb:
        return True
    if sa == "" or sb == "":
        return False
    try:
        fa, fb = float(sa), float(sb)
    except (TypeError, ValueError):
        return False
    if math.isnan(fa) or math.isnan(fb):
        return False
    denom = max(abs(fb), 1e-9)
    return abs(fa - fb) / denom <= REL_TOL


def value_fidelity(g: pd.DataFrame, a: pd.DataFrame, platform: str,
                   shared_keys: list[str]) -> tuple[float | None, dict]:
    """Agreement on the columns both sides carry, over matched rows."""
    spec = spec_for(platform)
    if spec.result_type == "id_set" or not shared_keys:
        return None, {"reason": "id_set — membership only, no values"}

    gl, al = _col_lookup(g), _col_lookup(a)
    if spec.value_cols:
        wanted = [c.strip().lower() for c in spec.value_cols]
    else:
        wanted = sorted(set(gl) & set(al))
    cols = [(gl[c], al[c]) for c in wanted
            if c in gl and c in al and not is_volatile(platform, c)
            and c not in ("__key", "__unit")]
    if not cols:
        return None, {"reason": "no comparable column shared by both results"}

    gi = g.set_index("__key")
    ai = a.set_index("__key")
    agree = total = 0
    per_col: dict[str, list[int]] = {}
    for gc, ac in cols:
        gv = gi.loc[shared_keys, gc]
        av = ai.loc[shared_keys, ac]
        ok = sum(1 for x, y in zip(av.tolist(), gv.tolist())
                 if _values_agree(x, y))
        per_col[str(gc)] = [ok, len(shared_keys)]
        agree += ok
        total += len(shared_keys)
    return (agree / total if total else None), {
        "columns_compared": [str(c) for c, _ in cols],
        "per_column": per_col,
    }


def _to_datetime(s: "pd.Series") -> "pd.Series":
    """Parse a timestamp column whose rows may not share one format.

    Since pandas 2.0 `to_datetime` infers a SINGLE format from the first
    non-null value and coerces everything that does not match it to NaT. Real
    columns are not that tidy: one GBIF `eventDate` column holds
    `2025-10-05T13:33` next to `2025-10-16T19:06:55` and `2024-10-06`, and the
    inferred-format path silently discarded 56 of its 59 values — dropping
    `time_cov` to 0.33 on a scenario whose records matched gold exactly.
    ISO8601 handles varying precision; `mixed` covers the rest.
    """
    for fmt in ("ISO8601", "mixed"):
        try:
            return pd.to_datetime(s, errors="coerce", utc=True, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.to_datetime(s, errors="coerce", utc=True)


def time_coverage(g: pd.DataFrame, a: pd.DataFrame, platform: str
                  ) -> tuple[float | None, dict]:
    spec = spec_for(platform)
    if not spec.time_col:
        return None, {"reason": "platform has no time axis"}
    gl, al = _col_lookup(g), _col_lookup(a)
    col = next((c.strip().lower() for c in spec.time_col
                if c.strip().lower() in gl and c.strip().lower() in al), None)
    if col is None:
        return None, {"reason": "time column absent from one side"}

    def buckets(df, actual):
        t = _to_datetime(df[actual]).dropna()
        if t.empty:
            return set()
        # Everything is already normalised to UTC; drop the tzinfo so
        # `to_period` does not warn about discarding it.
        return set(t.dt.tz_localize(None).dt.to_period(spec.time_bucket)
                   .astype(str))

    gb = buckets(g, gl[col])
    if not gb:
        return None, {"reason": "gold time column unparseable"}
    ab = buckets(a, al[col])
    return len(gb & ab) / len(gb), {
        "bucket": spec.time_bucket,
        "gold_buckets": len(gb), "agent_buckets": len(ab),
        "missing": sorted(gb - ab)[:8],
    }


def table_stats_score(gf: list[tuple[str, pd.DataFrame]],
                      af: list[tuple[str, pd.DataFrame]]) -> tuple[dict, dict]:
    """PANGAEA: no row key exists, so compare shape and per-column summaries.

    Justified in the registry: DOIs pin the dataset version, so there is no
    drift to catch, and 72% of the columns are float — a full-table hash would
    break on parquet round-trip representation alone.
    """
    gmap = {u: d for u, d in gf}
    amap = {u: d for u, d in af}
    row_scores, col_scores, stat_scores = [], [], []
    detail = {}
    for unit, gd in gmap.items():
        if gd is None or (len(gd) == 0 and len(gd.columns) == 0):
            # The DOI resolved but carries no table. There is nothing to
            # retrieve and nothing to compare, so it neither credits nor
            # penalises — scoring it 0 would have made an empty reference
            # unreachable.
            detail[unit] = {"status": "gold table is empty — not scored"}
            continue
        ad = amap.get(unit)
        if ad is None:
            row_scores.append(0.0); col_scores.append(0.0); stat_scores.append(0.0)
            detail[unit] = {"status": "missing from agent result"}
            continue
        rs = 1.0 if len(gd) == len(ad) else max(
            0.0, 1 - abs(len(ad) - len(gd)) / max(len(gd), 1))
        gc = {str(c) for c in gd.columns}
        ac = {str(c) for c in ad.columns}
        # Containment: every gold column must appear. Vacuously satisfied
        # when gold has none, matching the empty-set convention used by the
        # phase-1/2 comparators.
        cs = len(gc & ac) / len(gc) if gc else 1.0
        ok = tot = 0
        for c in sorted(gc & ac):
            try:
                gs, as_ = gd[c], ad[c]
                if pd.api.types.is_numeric_dtype(gs) and pd.api.types.is_numeric_dtype(as_):
                    for fn in ("sum", "mean", "min", "max"):
                        tot += 1
                        ok += _values_agree(getattr(as_, fn)(), getattr(gs, fn)())
                else:
                    tot += 1
                    ok += set(gs.dropna().astype(str)) == set(as_.dropna().astype(str))
            except Exception:
                tot += 1
        ss = ok / tot if tot else 1.0
        row_scores.append(rs); col_scores.append(cs); stat_scores.append(ss)
        detail[unit] = {"gold_rows": len(gd), "agent_rows": len(ad),
                        "row_score": round(rs, 4), "col_score": round(cs, 4),
                        "stat_score": round(ss, 4)}
    m = lambda xs: (sum(xs) / len(xs)) if xs else 0.0     # noqa: E731
    return ({"record_cov": m(row_scores),
             "value_fid": m(stat_scores),
             "time_cov": None,
             "over": (len(amap) / len(gmap)) if gmap else 0.0,
             "col_cov": m(col_scores)},
            {"units": detail})


# ---------------------------------------------------------------------------
# Scenario-level grading
# ---------------------------------------------------------------------------

def grade_scenario(platform: str,
                   gold_frames: list[tuple[str, pd.DataFrame]],
                   agent_frames: list[tuple[str, pd.DataFrame]],
                   agent_statuses: list[str]) -> dict:
    spec = spec_for(platform)
    detail: dict = {"agent_call_status": _tally(agent_statuses)}

    gold_rows = sum(len(d) for _, d in gold_frames)
    if not gold_frames or gold_rows == 0:
        return {"verdict": "UNGRADABLE", "binary_pass": None, "score": None,
                "details": {**detail, "reason": "gold retrieved no rows"}}

    if not agent_statuses:
        return {"verdict": "NO-ANSWER", "binary_pass": False, "score": 0.0,
                "details": {**detail, "reason": "agent declared no call"}}
    if not any(s == "success" for s in agent_statuses):
        graded = [s for s in agent_statuses if s not in ("chained", "setup_call")]
        v = "NOT-CALLABLE" if graded else "NO-ANSWER"
        return {"verdict": v, "binary_pass": False, "score": 0.0,
                "details": {**detail,
                            "reason": "no agent call returned data"}}

    # --- PANGAEA: statistics rather than rows --------------------------
    if spec.result_type == "table_stats":
        m, d2 = table_stats_score(gold_frames, agent_frames)
        detail.update(d2)
        return _finalise(m, detail, platform)

    g, gnotes, g_rk = merge(gold_frames, platform)
    a, anotes, a_rk = merge(agent_frames, platform)
    detail["merge_notes"] = gnotes + anotes
    row_keyed = g_rk or a_rk
    if g is None:
        return {"verdict": "UNGRADABLE", "binary_pass": None, "score": None,
                "details": {**detail, "reason": "no key column in gold result"}}
    if a is None:
        return {"verdict": "WRONG-SLICE", "binary_pass": False, "score": 0.0,
                "details": {**detail,
                            "reason": "no key column in agent result"}}
    if a.empty:
        return {"verdict": "EMPTY", "binary_pass": False, "score": 0.0,
                "details": {**detail, "gold_rows": len(g)}}

    gk = list(dict.fromkeys(g["__key"].tolist()))
    ak = set(a["__key"].tolist())
    shared = [k for k in gk if k in ak]
    record_cov = len(shared) / len(gk)
    over = len(ak) / len(gk) if gk else 0.0

    if row_keyed:
        # The key already contains every value, so agreement is tautological.
        value_fid, vdet = None, {"reason": "row-keyed — the key is the row, "
                                           "so value agreement is implied"}
    else:
        value_fid, vdet = value_fidelity(g, a, platform, shared)
    time_cov, tdet = time_coverage(g, a, platform)

    detail.update({
        "gold_rows": len(gk), "agent_rows": len(ak), "matched_rows": len(shared),
        "row_keyed": row_keyed,
        "value": vdet, "time": tdet,
        "missing_examples": [k for k in gk if k not in ak][:5],
    })
    return _finalise({"record_cov": record_cov, "value_fid": value_fid,
                      "time_cov": time_cov, "over": over}, detail, platform)


def _finalise(m: dict, detail: dict, platform: str) -> dict:
    comps = [m[k] for k in ("record_cov", "value_fid", "time_cov")
             if m.get(k) is not None]
    score = sum(comps) / len(comps) if comps else 0.0

    ok_rec = m["record_cov"] >= 1 - EPS_RECORD
    ok_val = m["value_fid"] is None or m["value_fid"] >= 1 - EPS_VALUE
    ok_time = m["time_cov"] is None or m["time_cov"] >= 1 - EPS_TIME
    over = m.get("over") or 0.0

    pass_suff = ok_rec and ok_val and ok_time and over <= OVER_CEILING
    pass_strict = pass_suff and over <= 1 + EPS_OVER

    if pass_strict:
        verdict = "PASS"
    elif pass_suff:
        verdict = "OVER-BROAD"
    else:
        verdict = "WRONG-SLICE"

    return {
        "verdict": verdict,
        "binary_pass": bool(pass_suff),      # containment is the primary metric
        "score": round(score, 4),
        "details": {
            **detail,
            "metrics": {k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in m.items()},
            "components_averaged": len(comps),
            "pass_suff": bool(pass_suff), "pass_strict": bool(pass_strict),
            "thresholds": {"record": 1 - EPS_RECORD, "value": 1 - EPS_VALUE,
                           "time": 1 - EPS_TIME, "over_strict": 1 + EPS_OVER},
            "platform": platform,
        },
    }


def _tally(xs: list[str]) -> dict:
    out: dict[str, int] = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out

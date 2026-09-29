"""Execute the API calls an agent declared in Phase 2 (paper, Section 2.2).

Phase 2 is open-loop: the agent declares `[{module, function, kwargs}, ...]`
and never touches the network. These calls are executed afterwards, and the
data they return is what Phase 2 is graded on (grading/phase2/).

Storage is content-addressed rather than per run, because the same call is
declared many times across models and conditions:

    <exec-root>/exec_cache/<sha[:2]>/<sha>/
        meta.json          platform, module, function, kwargs, status, rows,
                           columns, elapsed_s, downloaded_at, package_versions
        call_00.parquet    payload (name and format chosen by the handler)

    sha = sha256(platform | module | function | normalised kwargs |
                 package versions)

Package versions are part of the key, so upgrading a client library
invalidates exactly the calls it can affect. Failures are cached too,
except transient ones (a 5xx, a timeout), which are retried on the next run.

Dispatch
--------
1. The platform handler from `executor/handlers.py` — the same code that
   builds the gold snapshot — when the call is inside its real surface.
2. Generic `importlib` dispatch for anything the handler does not know, so a
   function that does not exist fails honestly.
3. Otherwise `not_callable`, with the reason recorded.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import re
import signal
import time
import traceback


from executor import handlers as dh


# Handler options. The row caps guard against a single query trying to
# materialise tens of millions of records; they are the same caps the gold
# snapshot uses, so agent calls and gold calls are truncated identically.
DEFAULT_OPTS = {
    "dry_run": False,
    "force": False,
    "redo_empty": False,
    "obis_max_rows": dh.OBIS_MAX_ROWS_DEFAULT,
    "inat_max_rows": dh.INAT_MAX_ROWS_DEFAULT,
    "pangaea_max_rows": dh.PANGAEA_MAX_ROWS_DEFAULT,
}

# Calls that configure a client rather than retrieve data. They carry no
# data need, so they are neither executed nor counted against the agent.
SETUP_CALLS = {
    ("epa", "aqs_credentials"),
    ("epa", "aqs_sign_up"),
}


# Declared steps that cannot be executed standalone, and are not meant to be.
#
# EVERY gold call in SciDataBench-Onboard is a single self-contained retrieval:
# no gold entry consumes another entry's return value. (Twelve scenarios list
# two functions, but those are parallel lookups — `lookup_symbol` +
# `sequence_id`, `materials/summary` + `materials/thermo` — not a chain.)
#
# Some agents instead wrote the pipeline out step by step. The kwargs give
# them away: `Observations.get_product_list(observations=...)` and
# `download_products(products=...)` name the PREVIOUS call's return object,
# and `ESGFCatalog.to_dataset_dict()` takes no arguments at all. A JSON
# envelope cannot carry an in-memory object, so there is nothing to execute.
#
# These are recorded as `chained` — neither a success nor a failed call
# construction — so the equivalence layer can judge the plan on the calls
# that DO retrieve data. Two groups:
#
#   downstream : consumes an upstream result
#   helper     : builds an argument value (a time, a coordinate, a unit),
#                retrieving nothing — the same treatment SETUP_CALLS gets
#
# Matching is on the last dotted component of `function`, so it holds however
# the agent split the module/function boundary.
CHAINED_CALLS: dict[str, set[str]] = {
    # `model_groups` summarises the catalog a prior `.search()` populated,
    # exactly like `remove_ensembles`. Standalone it raises
    # "'NoneType' object has no attribute 'model_facet'" because there is
    # no search result to summarise — which the executor was reporting as
    # not-callable, i.e. blaming the agent for a chain step we had simply
    # not registered.
    "cmip6":   {"to_dataset_dict", "remove_ensembles", "model_groups"},
    "obis":    {"execute", "to_pandas"},
    "argo":    {"to_xarray", "to_dataframe", "open_dataset"},
    "usgs_eq": {"UTCDateTime", "kilometers2degrees"},
    "vizier":  {"SkyCoord", "Quantity"},
    "inaturalist": {"paginate_all"},
    # Stack/parse steps that operate on an already-downloaded directory.
    "neon":    {"stack_by_table", "stack_eddy", "read_table_neon"},
    # `download_get` retrieves a previously requested download by key, and
    # `download_meta` polls its status; neither retrieves without the key a
    # prior `download` call returned.
    "gbif":    {"download_get", "download_meta", "get_download"},
}


def is_chained(platform: str, function: str) -> bool:
    return function.split(".")[-1] in CHAINED_CALLS.get(platform, set())


# What each handler ACTUALLY implements.
#
# The handlers were written for gold, which is correct by construction, so
# most of them ignore the declared `module` and `function` and go straight to
# the one endpoint they know. Feeding them an agent's call unchecked makes a
# hallucinated function silently succeed: `pyobis.occurrences.searchxyz` and
# even `pyobis_typo.search` both returned 7,097 rows in testing. So the
# executor gates the handler on this surface, and anything outside it falls
# through to generic dispatch — which fails honestly.
#
#   modules   : accepted prefixes for the declared `module`
#   functions : accepted function names, matched on the last dotted component
#               (so `DataFetcher.float` and `float` both match). None means
#               the handler validates `function` itself.
#   prefixes  : accepted `function` prefixes, for REST endpoint paths.
PLATFORM_SURFACE: dict[str, dict] = {
    # --- SciDataBench ------------------------------------------------
    # `functions: None` means the handler validates the name itself. These
    # four packages expose dozens of real query functions and the agents used
    # most of them; enumerating a subset here would report a real function as
    # "not implemented by the handler" and blame the agent for our list. The
    # handlers do an attribute lookup instead, so a name that does not exist
    # raises AttributeError and is recorded as not-callable — which is the
    # honest verdict.
    "neon":        {"modules": ("neonutilities",), "functions": None},
    "gbif":        {"modules": ("pygbif",),        "functions": None},
    "usgs":        {"modules": ("dataretrieval",), "functions": None},
    "epa":         {"modules": ("pyaqsapi",),      "functions": None},

    # --- SciDataBench-Onboard ------------------------------------------
    "argo":        {"modules": ("argopy",),
                    "functions": {"float", "region", "profile"}},
    "census_acs":  {"modules": ("census",),
                    "functions": {"acs_data"}},
    "cmip6":       {"modules": ("intake_esgf",),
                    "functions": {"search"}},
    "ensembl":     {"modules": ("ensembl_rest",),
                    "functions": None},            # h_ensembl validates
    "inaturalist": {"modules": ("pyinaturalist",),
                    "functions": {"get_observations"}},
    # Any path-shaped function is forwarded to the REST API and the service
    # decides. Hardcoding MP's endpoint list here would make our snapshot of
    # it the arbiter — a path we had not listed would be reported as "not
    # callable" even when the API serves it.
    "matproj":     {"modules": ("mp_api",),
                    "functions": set(), "prefixes": ("",), "path_like": True},
    "noaa_ghcn":   {"modules": ("noaa_ncei",),
                    "functions": {"access_data"}},
    "obis":        {"modules": ("pyobis",),
                    "functions": {"search"}},
    "pangaea":     {"modules": ("pangaeapy",),
                    "functions": {"PanDataSet"}},
    "usgs_eq":     {"modules": ("obspy",),
                    "functions": {"get_events"}},
    "vizier":      {"modules": ("astroquery",),
                    # get_catalogs belongs here as well as in h_vizier: this
                    # gate runs FIRST, so a handler branch on its own is dead
                    # code — the call is rejected before the handler sees it.
                    # (ensembl sets functions=None, which is why its new
                    # branch needed no change here.)
                    "functions": {"query_region", "query_constraints",
                                  "query_object", "get_catalogs"}},
}

# Platforms reached over HTTP: there is no module to import, so a call the
# handler rejects cannot be rescued by generic dispatch either.
REST_PLATFORMS = frozenset({"census_acs", "ensembl", "matproj", "noaa_ghcn"})

# `h_obis` filters kwargs down to the OBIS query vocabulary, so a misspelled
# parameter is silently dropped and the query widens instead of failing.
# Recorded (not corrected) so grading can see the widening for what it is.
_OBIS_ACCEPTED = dh._OBIS_KEYS


def handler_accepts(platform: str, module: str, function: str) -> tuple[bool, str]:
    """Is this (module, function) inside the platform handler's real surface?"""
    spec = PLATFORM_SURFACE.get(platform)
    if spec is None:
        return False, "no handler surface registered"
    mods = spec.get("modules") or ()
    if mods and not any(module == m or module.startswith(m + ".")
                        for m in mods):
        return False, f"module {module!r} is outside {mods}"
    fns = spec.get("functions")
    if fns is None:
        return True, ""                            # handler validates itself
    if spec.get("path_like"):
        # REST endpoint path — forwarded verbatim; the service decides.
        return (True, "") if "/" in function else (
            False, f"{function!r} is not an endpoint path")
    if function.split(".")[-1] in fns:
        return True, ""
    for pre in spec.get("prefixes") or ():
        if function.startswith(pre):
            return True, ""
    return False, f"function {function!r} is not implemented by the handler"


# ---------------------------------------------------------------------------
# kwargs normalisation
# ---------------------------------------------------------------------------

# JSON has no date type, so agents encode `datetime.date` arguments as a
# string holding the Python repr. Parsed with a regex, never eval'd.
_DATE_REPR = re.compile(
    r"^\s*(?:datetime\.)?date\s*\(\s*(\d{1,4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)\s*$")
_DATE_KW = re.compile(
    r"^\s*(?:datetime\.)?date\s*\(\s*year\s*=\s*(\d{1,4})\s*,\s*"
    r"month\s*=\s*(\d{1,2})\s*,\s*day\s*=\s*(\d{1,2})\s*\)\s*$")


def _norm_value(v):
    if isinstance(v, str):
        s = v.strip()
        for pat in (_DATE_REPR, _DATE_KW):
            m = pat.match(s)
            if m:
                y, mo, d = (int(g) for g in m.groups())
                if 1 <= mo <= 12 and 1 <= d <= 31:
                    return f"{y:04d}-{mo:02d}-{d:02d}"
        return s
    if isinstance(v, tuple):
        return [_norm_value(x) for x in v]
    if isinstance(v, list):
        return [_norm_value(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _norm_value(x) for k, x in v.items()}
    return v


def normalize_function(platform: str, function: str) -> str:
    """Strip URL punctuation from REST endpoint paths.

    `materials/summary/` and `materials/summary` address the same endpoint;
    the difference is a slash in a URL, not a different call. Normalising it
    also keeps the two spellings on one cache entry. Nothing else about the
    function name is touched.
    """
    if platform in REST_PLATFORMS and "/" in function:
        return function.strip().strip("/")
    return function.strip()


def normalize_kwargs(kwargs) -> dict:
    """Canonical form used both for execution and for the cache key.

    Only representation is normalised — never semantics. A dropped or
    rewritten argument would change which data comes back, which is exactly
    what we are trying to measure.

    Declaration ORDER is preserved: some client functions take `*args` only
    (argopy's `DataFetcher.profile(*args)`), and there the declared order is
    the only thing that can map an envelope's kwargs onto parameters. The
    cache key sorts separately, so ordering never splits the cache.
    """
    if not isinstance(kwargs, dict):
        return {}
    return {str(k): _norm_value(v) for k, v in kwargs.items()}


def call_sha(platform: str, module: str, function: str,
             kwargs: dict, versions: dict) -> str:
    blob = json.dumps(
        {"platform": platform, "module": module, "function": function,
         "kwargs": normalize_kwargs(kwargs), "versions": versions},
        sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Generic dispatch (fallback for functions the platform handler doesn't know)
# ---------------------------------------------------------------------------

def _resolve(module: str, function: str):
    """Resolve `module` + a possibly dotted `function` to a callable.

    Agents split the module/function boundary wherever they like, and the
    envelope schema gives them no way to say which side a class belongs on.
    All of these name the same callable:

        module="argopy",                          function="DataFetcher.float"
        module="argopy.fetchers.ArgoDataFetcher", function="float"
        module="astroquery.mast",                 function="Observations.query_criteria"
        module="astroquery.mast.Observations",    function="query_criteria"

    So `module` is not assumed to be importable in full: we import its
    longest importable prefix and treat the remainder as the head of the
    attribute path. A class reached mid-path is instantiated with no
    arguments so the method after it can be bound.

    This is notation, not composition — it never turns a call that would
    fail in a Python session into one that succeeds. A class that needs
    constructor arguments (obspy's `Client("USGS")`), a method that needs an
    upstream result (`to_xarray` with no fetcher), or a name that does not
    exist still raise, and are reported as not-callable.
    """
    import importlib
    parts = [p for p in module.split(".") if p]
    mod = None
    rest: list[str] = []
    for i in range(len(parts), 0, -1):
        try:
            mod = importlib.import_module(".".join(parts[:i]))
            rest = parts[i:]
            break
        except ImportError:
            continue
    if mod is None:
        raise ModuleNotFoundError(f"No module named {module!r}")

    path = rest + [p for p in function.split(".") if p]
    obj = mod
    for j, part in enumerate(path):
        if not hasattr(obj, part):
            raise AttributeError(
                f"{module}.{function}: no attribute {part!r}"
                + (f" on {'.'.join(parts[:len(parts)-len(rest)] + path[:j])}"
                   if j else ""))
        nxt = getattr(obj, part)
        if isinstance(nxt, type) and j < len(path) - 1:
            nxt = nxt()          # instantiate so the next attribute can bind
        obj = nxt
    if not callable(obj):
        raise TypeError(f"{module}.{function} is not callable")
    return obj


def _to_frame(result):
    """Best-effort conversion of an arbitrary return value to a DataFrame."""
    import pandas as pd
    if result is None:
        return None
    if isinstance(result, pd.DataFrame):
        return result
    if hasattr(result, "to_dataframe"):            # xarray
        return result.to_dataframe().reset_index()
    if hasattr(result, "to_pandas"):               # astropy Table
        return result.to_pandas()
    if isinstance(result, dict):
        return pd.json_normalize([result])
    if isinstance(result, list):
        return pd.json_normalize(result) if result else pd.DataFrame()
    return None


def generic_call(platform: str, module: str, function: str,
                 kwargs: dict, d: pathlib.Path) -> dict:
    import inspect
    fn = _resolve(module, function)
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    positional_only = bool(params) and all(
        p.kind is inspect.Parameter.VAR_POSITIONAL for p in params)
    if positional_only:
        # `f(*args)` accepts no keywords at all (argopy's DataFetcher.float /
        # .profile). The envelope schema has no way to express a positional
        # argument, so failing here would penalise the agent for our format
        # rather than for its call. Pass the declared values in order.
        out = fn(*kwargs.values())
    else:
        try:
            sig.bind_partial(**kwargs)
        except TypeError as e:
            raise TypeError(f"kwargs do not fit the signature: {e}") from e
        out = fn(**kwargs)
    df = _to_frame(out)
    if df is None:
        # The call returned an opaque object — a client, a catalogue handle,
        # a fetcher — not data. `_to_frame` already converts everything that
        # carries records (DataFrame, xarray, astropy Table, dict, list), so
        # reaching here means the agent declared a constructor and stopped:
        # `Vizier(columns=...)`, `ESGFCatalog()`, `Client("USGS")`.
        #
        # Serialising its repr and calling that one row would credit a call
        # that retrieved nothing — the mirror image of the false negatives we
        # just removed, and a worse failure since it inflates the score.
        return {"status_override": "not_data", "rows": 0, "via": "generic",
                "returned_type": f"{type(out).__module__}.{type(out).__name__}",
                "note": "returned an object, not records — no retrieval"}
    name, fmt = dh.save_df(df, d / "call_00.parquet")
    return {"output": name, "format": fmt, "rows": int(len(df)),
            "columns": [str(c) for c in df.columns], "via": "generic"}


# ---------------------------------------------------------------------------
# One call
# ---------------------------------------------------------------------------

def execute_call(platform: str, module: str, function: str, kwargs: dict, *,
                 cache_root: pathlib.Path, versions: dict, opts: dict,
                 force: bool = False, dry_run: bool = False) -> dict:
    """Run one declared call, or return its cached result.

    The returned dict is the `meta.json` content; `cached` says whether the
    call was served from disk.
    """
    kwargs = normalize_kwargs(kwargs)
    function = normalize_function(platform, function)
    sha = call_sha(platform, module, function, kwargs, versions)
    d = cache_root / "exec_cache" / sha[:2] / sha
    meta_path = d / "meta.json"

    base = {"sha": sha, "platform": platform, "module": module,
            "function": function, "kwargs": kwargs, "cached": False}

    # Static classifications come BEFORE the cache lookup. They are properties
    # of the call, not results of running it, so an entry cached under an
    # earlier version of these rules must not override them.
    if (platform, function) in SETUP_CALLS:
        return {**base, "status": "setup_call", "rows": 0,
                "note": "client configuration, not a data retrieval"}

    if is_chained(platform, function):
        return {**base, "status": "chained", "rows": 0,
                "note": "consumes an upstream result or builds an argument; "
                        "not a standalone retrieval, so nothing to execute"}

    if meta_path.exists() and not force:
        try:
            meta = json.loads(meta_path.read_text())
            meta["cached"] = True
            meta["sha"] = sha
            return meta
        except Exception:
            pass                                  # corrupt entry -> re-run

    if dry_run:
        return {**base, "status": "dry_run", "rows": 0}

    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    meta: dict = {}
    for wait in (5, 20, 60, None):
        meta = _attempt(platform, module, function, kwargs, d, opts)
        if meta["status"] != "transient_error" or wait is None:
            break
        time.sleep(wait)

    meta = {**base, **meta}
    meta["elapsed_s"] = round(time.time() - t0, 2)
    meta["downloaded_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    meta["package_versions"] = versions
    if meta["status"] != "transient_error":
        meta_path.write_text(json.dumps(meta, indent=2, default=str))
    return meta


def _attempt(platform: str, module: str, function: str, kwargs: dict,
             d: pathlib.Path, opts: dict) -> dict:
    """One execution attempt. Never raises; classifies the outcome."""
    handler = dh.HANDLERS.get(platform)
    use_handler, why = handler_accepts(platform, module, function)
    budget = int(opts.get("call_timeout") or 0)
    global _alarm_armed
    if budget > 0:
        signal.signal(signal.SIGALRM, _alarm)
        _alarm_armed = True
        signal.alarm(budget)
    try:
        if handler is not None and use_handler:
            try:
                # The four SciDataBench platforms expose the same
                # function from several modules (`dataretrieval.get_daily` /
                # `dataretrieval.waterdata.get_daily`, `pyaqsapi.bysite` /
                # `pyaqsapi.bystate`), and which module was declared IS part
                # of the call. The onboard handlers ignore it.
                res = handler(kwargs, function, d, 0, {**opts, "_module": module})
                res.setdefault("via", "handler")
            except ValueError as e:
                # Handlers that do validate raise ValueError("unsupported
                # <platform> function"). Anything else they raise is a real
                # execution failure and must not be retried by another path.
                if "unsupported" not in str(e).lower():
                    raise
                res = generic_call(platform, module, function, kwargs, d)
        elif platform in REST_PLATFORMS:
            # No importable module to fall back to — the declared endpoint
            # simply is not part of this API.
            raise AttributeError(why or f"unknown endpoint {module}.{function}")
        else:
            res = generic_call(platform, module, function, kwargs, d)
        meta = {"status": res.pop("status_override", "success"), **res}
        if platform == "obis":
            dropped = sorted(set(kwargs) - set(_OBIS_ACCEPTED))
            if dropped:
                # Not an error: the query still ran, just wider than declared.
                meta["dropped_kwargs"] = dropped
        return meta
    except CallBudgetExceeded:
        _disarm_budget()
        # Cached, and NOT retried: the budget is a property of the call, so a
        # re-run would time out again. Distinct from `error` because the call
        # may well be correct — it is simply too big to grade under budget.
        return {"status": "timeout", "rows": 0,
                "error": f"CallBudgetExceeded: exceeded {budget}s",
                "call_timeout_s": budget}
    except (ImportError, ModuleNotFoundError, AttributeError, TypeError) as e:
        _disarm_budget()
        return {"status": "not_callable", "rows": 0,
                "error": f"{type(e).__name__}: {e}",
                "reason": _not_callable_reason(e)}
    except Exception as e:
        _disarm_budget()
        return {"status": "transient_error" if is_transient(e) else "error",
                "rows": 0, "error": f"{type(e).__name__}: {e}",
                "traceback_tail": traceback.format_exc().splitlines()[-4:]}
    finally:
        _disarm_budget()


class CallBudgetExceeded(Exception):
    """One declared call exceeded the per-call wall budget (--call-timeout).

    Deliberately NOT named *Timeout*: `handlers.retry` decides what
    is transient by substring-matching the exception text against a list that
    includes "timeout", so a class named CallTimeout gets swallowed and
    retried by the very handlers we are trying to interrupt.
    """


# The re-arm below must stop the moment the call is abandoned. Without this
# guard it kept firing every second through the cleanup path and escaped
# `attempt()` — whose docstring promises it never raises — killing the whole
# process. Same defect, and same fix, as the scenario budget in
# scripts/run_eval.py.
_alarm_armed = False


def _alarm(_signum, _frame):
    if not _alarm_armed:
        return
    # Re-arm before raising. Handlers wrap their network calls in broad
    # `except Exception` retry loops, so a single alarm can be caught and
    # discarded; re-arming means the next attempt is interrupted too, and
    # the budget holds no matter how many layers try to swallow it.
    signal.alarm(1)
    raise CallBudgetExceeded


def _disarm_budget() -> None:
    """Stop the call budget alarm. Safe to call when it was never armed.

    SIGALRM is masked around the disarm because the re-armed alarm fires every
    second: without the mask it can land between entering a handler and
    reaching `signal.alarm(0)`, and then it escapes.
    """
    global _alarm_armed
    _alarm_armed = False
    blocked = False
    try:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        blocked = True
    except (AttributeError, ValueError, OSError):
        pass
    signal.alarm(0)
    if blocked:
        try:
            signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
        except (AttributeError, ValueError, OSError):
            pass


def is_transient(e: Exception) -> bool:
    """Is this the service failing, rather than the call being wrong?

    Transient failures must NOT be cached: an agent whose call happened to
    land during an Ensembl 500 would otherwise carry that verdict forever,
    and re-grading would never re-examine it. Permanent failures (a 4xx, an
    unknown function, kwargs that don't fit) are cached — they are the
    answer.
    """
    s = f"{type(e).__name__}: {e}".lower()
    if any(t in s for t in dh._TRANSIENT):
        return True
    return any(f" {code} " in f" {s} " or f"{code} server error" in s
               for code in ("500", "502", "503", "504", "429"))


def _not_callable_reason(e: Exception) -> str:
    if isinstance(e, (ImportError, ModuleNotFoundError)):
        return "unknown_module"
    if isinstance(e, AttributeError):
        return "unknown_function"
    return "bad_kwargs"


# ---------------------------------------------------------------------------
# Sources of calls: a run's declared envelopes, or the benchmark gold
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    main()

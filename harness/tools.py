"""Tools available to the agents.

Task agent
    run_python  persistent REPL with pd/np/Path/zipfile pre-loaded
    run_bash    shell command with stdin closed and a timeout
    Phases 1 and 2 bind run_python only (nothing has been downloaded yet);
    phases 3 and 4 bind both.

Onboarding agent (scripts/run_onboarding.py)
    web_search, fetch_url   read a platform's documentation (`search`)
    run_python              import and probe the client (`exec`)

`run_python` keeps a persistent namespace that is reset per scenario and
phase by `reset_python_namespace(cache_root)`. `run_bash` is stateless.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import signal
import subprocess
import sys
import textwrap
import traceback
from pathlib import Path
from typing import Any

import pandas as pd
from langchain_core.tools import tool


_py_namespace: dict[str, Any] = {}


def _scrub_nan(obj: Any) -> Any:
    """Replace pandas NaN / numpy nan with None recursively.

    Gemini's tool-result transport rejects literal `NaN` tokens in JSON, so
    every tool that returns DataFrame samples must scrub them first.
    """
    import math
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _scrub_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_nan(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_scrub_nan(v) for v in obj)
    return obj


def _dumps(obj: Any, **kw) -> str:
    return json.dumps(_scrub_nan(obj), default=str, allow_nan=False, **kw)


# Platform-credential env vars that are pre-bound as top-level names in
# the run_python REPL. The values are read from the host environment at
# scenario start; missing vars are bound to `None` rather than left
# undefined so the agent can probe them without raising `NameError`.
_CRED_ENV_VARS: tuple[str, ...] = (
    "NEON_TOKEN", "NEON_DOWNLOAD_ROOT",
    "GBIF_USER", "GBIF_PWD", "GBIF_EMAIL",
    "API_USGS_PAT",
    "AQS_USER", "AQS_KEY",
)


def _prime_namespace(ns: dict, cache_root: Path | str | None) -> None:
    """Populate a REPL namespace dict with the standard scenario bindings."""
    import glob as _glob
    import zipfile as _zipfile
    import numpy as _np
    try:
        import polars as _pl
    except Exception:
        _pl = None

    ns.clear()
    ns.update({
        "__builtins__": __builtins__,
        "pd": pd,
        "pandas": pd,
        "np": _np,
        "numpy": _np,
        "pl": _pl,
        "polars": _pl,
        "zipfile": _zipfile,
        "Path": Path,
        "glob": _glob,
        "os": os,
        "io": io,
        "CACHE_ROOT": str(cache_root) if cache_root else None,
    })
    # Pre-bind platform credentials so the agent can reference them by
    # their conventional env-var names without an extra os.getenv call.
    for var in _CRED_ENV_VARS:
        ns[var] = os.environ.get(var)


def reset_python_namespace(cache_root: Path | str | None) -> None:
    """Reset the run_python REPL and prime it for one scenario and phase."""
    _prime_namespace(_py_namespace, cache_root)


_BASH_OUTPUT_CAP = 20_000
_BASH_TIMEOUT_DEFAULT = 60
_BASH_TIMEOUT_MAX = 120


def _bash_exec(command: str, timeout_s: int, cache_root: str | None) -> str:
    """Namespace-parameterized run_bash body (see run_bash for docs)."""
    t = max(1, min(int(timeout_s or _BASH_TIMEOUT_DEFAULT), _BASH_TIMEOUT_MAX))
    cwd = cache_root or None
    if cwd and not Path(cwd).is_dir():
        cwd = None

    timed_out = False
    try:
        proc = subprocess.run(
            ["bash", "-c", command],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=t,
            cwd=cwd,
        )
        out, err, rc = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) \
            else (e.stdout or "")
        err = e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, bytes) \
            else (e.stderr or "")
        rc = -1
    except FileNotFoundError as e:
        return _dumps({"error": f"bash not available: {e}"})

    if len(out) > _BASH_OUTPUT_CAP:
        out = out[:_BASH_OUTPUT_CAP] + "\n...[truncated]..."
    if len(err) > _BASH_OUTPUT_CAP:
        err = err[:_BASH_OUTPUT_CAP] + "\n...[truncated]..."
    return _dumps({
        "stdout": out,
        "stderr": err,
        "returncode": rc,
        "timed_out": timed_out,
        "cwd": cwd,
    })


@tool
def run_bash(command: str, timeout_s: int = 60) -> str:
    """Execute a bash command and return its captured stdout / stderr.

    Stdin is wired to /dev/null so any command that pauses for keyboard
    input (package installer y/n, `read`, etc.) fails immediately rather
    than hanging. The working directory is set to CACHE_ROOT when the
    scenario has one, so relative paths resolve under the downloaded
    cache.

    Use this for cheap filesystem exploration that one call can answer:
    `find <path> -maxdepth N -type f`, `du -sh <dir>/*`, `unzip -l
    <file.zip>`, `head -n 5 <csv>`, `grep -c <pattern> <file>`,
    `wc -l <files>`. For loading data, computing statistics, or making
    plots, prefer `run_python` (pandas, numpy already imported).

    Args:
        command: A single shell command line, run via `bash -c`. Pipes,
            redirections, and `&&` chains are fine.
        timeout_s: Hard wall-clock timeout in seconds (1-120, default 60).
            A timed-out command returns whatever stdout/stderr it managed
            to produce with `timed_out=true`.

    Returns:
        JSON `{stdout, stderr, returncode, timed_out, cwd}`. Output streams
        are truncated at 20000 chars each.
    """
    return _bash_exec(command, timeout_s, _py_namespace.get("CACHE_ROOT"))


# ---------------------------------------------------------------------------
# Answer seal
#
# scripts/run_eval.py's sandbox relocates the benchmark, the gold snapshots,
# the results tree and the skills under one root and masks their real paths,
# so agent code that globs the repository finds nothing. That alone is only
# obscurity: the agent shares this process and its mount namespace, so a glob
# of the sealed root would still work.
#
# This closes it. An audit hook — which CPython does not allow to be removed
# once installed — refuses filesystem and subprocess events that touch the
# sealed root, but only while agent code is on the stack. The runner reads the
# same paths freely, because the flag is set only around exec of agent code.
# ---------------------------------------------------------------------------

_SEALED_ROOT = os.environ.get("SCIDATABENCH_SEALED_ROOT") or ""
_in_agent_code = False

# Tool ablation (paper, Section 4.2): cut the agent off from the network while
# leaving the REPL intact. `--phase1-mode offline` sets this. Offline,
# `import argopy; help(...)` still works, so the agent can still find out
# WHICH call to make; what it cannot do is ask the service for the answer.
_offline = False

# Every HTTP client in the benchmark's dependency set ultimately goes through
# one of these, so blocking them covers requests, urllib, httpx and the
# platform clients alike without having to enumerate libraries.
_NETWORK_EVENTS = frozenset({
    "socket.connect", "socket.getaddrinfo", "socket.gethostbyname",
    "urllib.Request",
})


# The harness source itself. It cannot be masked — the runner imports from
# these directories — but nothing in agent code has a reason to read them,
# and an agent that reads the grader learns the scoring rule. The audit hook
# refuses them only while agent code is on the stack.
_HARNESS_DIRS = tuple(
    str(pathlib.Path(__file__).resolve().parent.parent / d) + os.sep
    for d in ("harness", "grading", "executor", "scripts")
)


class SealedPathError(PermissionError):
    """Agent code tried to reach the benchmark, gold data, or results tree."""


class OfflineError(PermissionError):
    """Agent code tried to reach the network while the offline ablation is on."""


def set_offline(flag: bool) -> None:
    """Turn the network block on or off. Called by the runner per phase."""
    global _offline
    _offline = bool(flag)


def _seal_audit(event: str, args) -> None:
    if not _in_agent_code:
        return
    if _offline and event in _NETWORK_EVENTS:
        raise OfflineError(
            "network access is disabled in this condition; answer from what "
            "you already know and from local package introspection only")
    # No early return on an empty _SEALED_ROOT any more: the harness-source
    # refusal below has to hold under --no-sandbox too, and the sealed-root
    # test is a substring check that an empty string would make vacuously true
    # — so it is guarded at its own site instead.
    if event in ("open", "os.listdir", "os.scandir", "os.stat", "os.rename",
                 "shutil.copyfile", "pathlib.Path.glob", "glob.glob"):
        probe = args[0] if args else ""
    elif event in ("subprocess.Popen", "os.exec", "os.posix_spawn"):
        probe = repr(args)
    else:
        return
    try:
        text = probe if isinstance(probe, str) else (
            os.fsdecode(probe) if isinstance(probe, (bytes, os.PathLike)) else repr(probe))
    except Exception:
        return
    # `open("eval/compare.py")` is the form agents actually use, and it never
    # matches an absolute prefix. Resolve against the CWD before testing.
    if text and not text.startswith(os.sep):
        try:
            text = os.path.abspath(text)
        except Exception:
            pass
    if _SEALED_ROOT and _SEALED_ROOT in text:
        raise SealedPathError(
            "this path holds benchmark answers and is not readable from agent "
            "code; work from the request and the platform's own API instead")
    if text.startswith(_HARNESS_DIRS):
        raise SealedPathError(
            "the evaluation harness source is not readable from agent code; "
            "work from the request and the platform's own API instead")


# Installed unconditionally: the hook returns immediately unless agent code is
# on the stack, and the offline ablation needs it even when --no-sandbox has
# left _SEALED_ROOT empty. CPython does not allow removing an audit hook, so
# installing it once at import is the only option either way.
sys.addaudithook(_seal_audit)


def reset_agent_flag() -> None:
    """Force the seal's "agent code is running" flag off.

    `_python_exec` clears it in a finally, but a signal handler firing inside
    that finally can skip the assignment and leave it set. Everything the
    runner writes afterwards — summary.<platform>.json, the per-scenario
    records — lives under the sealed root, so a stuck flag turns the runner's
    own bookkeeping into a SealedPathError and ends the platform.
    """
    global _in_agent_code
    _in_agent_code = False


def _python_exec(code: str, ns: dict) -> str:
    """Namespace-parameterized run_python body (see run_python for docs)."""
    stdout = io.StringIO()
    result: Any = None
    err: str | None = None
    stripped = textwrap.dedent(code).strip("\n")

    try:
        compile(stripped, "<agent>", "exec")
    except SyntaxError as e:
        return _dumps({"error": f"SyntaxError: {e}"})

    lines = stripped.split("\n")
    tail_expr: str | None = None
    if lines:
        last = lines[-1]
        try:
            compile(last, "<agent>", "eval")
            tail_expr = last
            exec_body = "\n".join(lines[:-1])
        except SyntaxError:
            exec_body = stripped
    else:
        exec_body = stripped

    global _in_agent_code
    try:
        with contextlib.redirect_stdout(stdout):
            _in_agent_code = True
            if exec_body.strip():
                exec(compile(exec_body, "<agent-exec>", "exec"), ns)
            if tail_expr:
                result = eval(compile(tail_expr, "<agent-eval>", "eval"), ns)
    except Exception as e:
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}"
    finally:
        # Clear before anything else runs: the runner reads the sealed paths
        # on its way to the next scenario and must not be blocked by them.
        #
        # The assignment is one bytecode, but an async signal can still land
        # between entering this finally and executing it, and the scenario
        # budget's alarm re-arms every 5s once it has fired — so it WILL hit
        # that window eventually. When it does the flag stays set and the
        # runner's own write of the scenario record (eval/runner.py) raises
        # SealedPathError: the seal ends up blocking the runner, not the
        # agent. Masking SIGALRM here closes the window deterministically —
        # a signal raised while blocked is delivered on unblock, by which
        # point the flag is already down.
        #
        # Clearing the flag from the signal handler instead would be wrong:
        # agent code catches broad exceptions, so it can swallow the timeout
        # and keep running — with the seal off.
        _blocked = False
        try:
            signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
            _blocked = True
        except (AttributeError, ValueError, OSError):
            pass
        _in_agent_code = False
        if _blocked:
            try:
                signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
            except (AttributeError, ValueError, OSError):
                pass

    out_text = stdout.getvalue()
    if len(out_text) > 20000:
        out_text = out_text[:20000] + "\n...[truncated]..."
    repr_text: str | None = None
    if result is not None:
        try:
            repr_text = repr(result)
        except Exception as e:
            repr_text = f"<repr failed: {e}>"
        if repr_text and len(repr_text) > 5000:
            repr_text = repr_text[:5000] + " ...[truncated]"

    return _dumps({
        "stdout": out_text,
        "last_expression": repr_text,
        "error": err,
    })


@tool
def run_python(code: str) -> str:
    """Execute Python in a persistent namespace and return stdout.

    Pre-loaded names: `pd`, `np`, `pl` (polars, may be None), `zipfile`,
    `Path`, `glob`, `os`, `io`, `CACHE_ROOT`.

    Platform credentials are also pre-loaded as top-level variables —
    use them directly instead of hardcoding placeholders:
        NEON_TOKEN, NEON_DOWNLOAD_ROOT,
        GBIF_USER, GBIF_PWD, GBIF_EMAIL,
        API_USGS_PAT,
        AQS_USER, AQS_KEY.
    Each is `None` when not configured. For example, EPA scenarios should
    call `pyaqsapi.aqs_credentials(username=AQS_USER, key=AQS_KEY)`.

    Variables persist across calls.

    Args:
        code: Python source. Use `print()` or leave a bare expression on
            the last line to echo its repr.

    Returns:
        JSON with `stdout`, `last_expression`, `error`.
    """
    return _python_exec(code, _py_namespace)


# ---------------------------------------------------------------------------
# Research tools — used by the onboarding agent, never by a task agent.
#
# These let an agent read a platform's public documentation instead of
# guessing from the package alone. They are deliberately not given to a task
# agent: one that can see the scenario could search for the source paper,
# and scenarios are named by DOI. The onboarding agent never sees a scenario
# — it is told only the platform name — so that leak is not available to it.
#
# Every fetched URL is recorded in `_RESEARCH_URL_LOG` so a run can be
# audited after the fact.
# ---------------------------------------------------------------------------

_RESEARCH_URL_LOG: list[dict] = []
_FETCH_CHAR_CAP = 30_000
_SEARCH_TIMEOUT_S = 30
_BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Publisher and aggregator domains. A skill is supposed to describe the API,
# not restate a paper's methods, and blocking these keeps the two apart.
_RESEARCH_BLOCKED = (
    "doi.org", "sci-hub", "researchgate.net", "semanticscholar.org",
    "sciencedirect.com", "springer.com", "nature.com", "wiley.com",
    "tandfonline.com", "jstor.org", "academia.edu", "arxiv.org",
    "biorxiv.org", "medrxiv.org", "europepmc.org", "ncbi.nlm.nih.gov/pmc",
)


def _blocked(url: str) -> bool:
    u = url.lower()
    return any(b in u for b in _RESEARCH_BLOCKED)


def research_url_log() -> list[dict]:
    """Every search and fetch this process performed, for auditing."""
    return list(_RESEARCH_URL_LOG)


def reset_research_log() -> None:
    _RESEARCH_URL_LOG.clear()


def _search_tavily(query: str, max_results: int, key: str) -> dict:
    """Tavily returns an extract of each page alongside the link, which
    saves the agent a `fetch_url` round trip for most results."""
    import requests
    r = requests.post(
        "https://api.tavily.com/search",
        json={"query": query, "max_results": max_results,
              "search_depth": "basic", "include_answer": False},
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        timeout=_SEARCH_TIMEOUT_S + 20,
    )
    r.raise_for_status()
    out = []
    for x in r.json().get("results", []):
        url = x.get("url", "")
        if _blocked(url):
            continue
        out.append({"title": x.get("title", ""), "url": url,
                    "snippet": (x.get("content") or "")[:600]})
    return {"results": out, "provider": "tavily"}


def _search_serper(query: str, max_results: int, key: str) -> dict:
    import requests
    r = requests.post(
        "https://google.serper.dev/search",
        json={"q": query, "num": max_results},
        headers={"X-API-KEY": key, "Content-Type": "application/json"},
        timeout=_SEARCH_TIMEOUT_S,
    )
    r.raise_for_status()
    out = []
    for x in r.json().get("organic", []):
        url = x.get("link", "")
        if _blocked(url):
            continue
        out.append({"title": x.get("title", ""), "url": url,
                    "snippet": (x.get("snippet") or "")[:600]})
    return {"results": out[:max_results], "provider": "serper"}


@tool
def web_search(query: str, max_results: int = 8) -> str:
    """Search the web for API documentation, guides and usage examples.

    Use it to find a platform's official docs, parameter references and
    worked examples. Each result carries an extract of the page; call
    `fetch_url` when you need to read one in full.

    Args:
        query: search terms, e.g. "argopy DataFetcher region documentation".
        max_results: how many results to return (default 8).

    Returns:
        JSON with a `results` list of {title, url, snippet}.
    """
    import html as _html
    import re as _re
    import requests
    from urllib.parse import unquote

    # Provider order: a keyed API when one is configured, DuckDuckGo only as
    # a last resort. Scraping DDG is not viable for a real run — it serves an
    # HTTP 202 challenge page after roughly seventy requests from one IP, and
    # an agent that reads that as "no results exist" keeps searching until it
    # exhausts its turn budget.
    for env, fn in (("TAVILY_API_KEY", _search_tavily),
                    ("SERPER_API_KEY", _search_serper)):
        key = os.environ.get(env)
        if not key:
            continue
        try:
            res = fn(query, max_results, key)
        except Exception as e:
            _RESEARCH_URL_LOG.append({"kind": "search", "query": query,
                                      "provider": env, "error":
                                      f"{type(e).__name__}: {e}"})
            continue
        _RESEARCH_URL_LOG.append({"kind": "search", "query": query,
                                  "provider": res["provider"],
                                  "n_results": len(res["results"]),
                                  "urls": [r["url"] for r in res["results"]]})
        return _dumps({"query": query, **res})

    try:
        # GET, and a browser User-Agent: the POST form and a generic UA both
        # come back as a 3 KB interstitial with no results.
        resp = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": _BROWSER_UA},
            timeout=_SEARCH_TIMEOUT_S,
        )
        resp.raise_for_status()
    except Exception as e:
        return _dumps({"error": f"{type(e).__name__}: {e}", "results": []})

    # Links and snippets sit in separate blocks, so parse each and zip by
    # position rather than trying to match them in one expression.
    strip = lambda s: _html.unescape(_re.sub(r"<[^>]+>", "", s)).strip()  # noqa: E731
    links = _re.findall(
        r'class="result__a"\s+href="([^"]+)"[^>]*>(.*?)</a>', resp.text, _re.S)
    snippets = _re.findall(
        r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, _re.S)

    out: list[dict] = []
    for i, (href, title) in enumerate(links):
        url = _html.unescape(href)
        m = _re.search(r"uddg=([^&]+)", url)
        if m:
            url = unquote(m.group(1))
        if url.startswith("//"):
            url = "https:" + url
        if _blocked(url):
            continue
        out.append({
            "title": strip(title),
            "url": url,
            "snippet": strip(snippets[i])[:300] if i < len(snippets) else "",
        })
        if len(out) >= max_results:
            break
    if not out and len(resp.text) < 20_000:
        # The challenge page. Say so, so the caller does not read it as
        # "this platform has no documentation" and search again.
        msg = ("search backend is rate-limiting this host; no keyed search "
               "provider is configured (set TAVILY_API_KEY or SERPER_API_KEY)")
        _RESEARCH_URL_LOG.append({"kind": "search", "query": query,
                                  "provider": "duckduckgo", "error": msg})
        return _dumps({"query": query, "error": msg, "results": []})
    _RESEARCH_URL_LOG.append({"kind": "search", "query": query,
                              "provider": "duckduckgo",
                              "n_results": len(out),
                              "urls": [r["url"] for r in out]})
    return _dumps({"query": query, "results": out, "provider": "duckduckgo"})


@tool
def fetch_url(url: str) -> str:
    """Fetch a documentation page and return its text.

    HTML is stripped to plain text. Long pages are truncated — fetch a
    more specific URL (an API reference page rather than a whole manual)
    when that happens.

    Args:
        url: the page to read.

    Returns:
        JSON with `url`, `text` and `truncated`.
    """
    import html as _html
    import re as _re
    import requests
    if _blocked(url):
        _RESEARCH_URL_LOG.append({"kind": "fetch", "url": url,
                                  "status": "blocked"})
        return _dumps({"url": url, "error":
                       "publisher/preprint domains are blocked — a skill "
                       "should describe the API, not a paper"})
    try:
        r = requests.get(url, timeout=_SEARCH_TIMEOUT_S,
                         headers={"User-Agent": _BROWSER_UA})
        r.raise_for_status()
    except Exception as e:
        _RESEARCH_URL_LOG.append({"kind": "fetch", "url": url,
                                  "status": f"error: {type(e).__name__}"})
        return _dumps({"url": url, "error": f"{type(e).__name__}: {e}"})

    ctype = r.headers.get("content-type", "")
    body = r.text
    if "json" not in ctype:
        body = _re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>",
                       " ", body)
        body = _re.sub(r"(?s)<[^>]+>", " ", body)
        body = _html.unescape(body)
        body = _re.sub(r"[ \t\r\f\v]+", " ", body)
        body = _re.sub(r"\n\s*\n\s*\n+", "\n\n", body)
    truncated = len(body) > _FETCH_CHAR_CAP
    _RESEARCH_URL_LOG.append({"kind": "fetch", "url": url,
                              "status": str(r.status_code),
                              "chars": len(body)})
    return _dumps({"url": url, "truncated": truncated,
                   "text": body[:_FETCH_CHAR_CAP].strip()})


RESEARCH_TOOLS = [web_search, fetch_url]


# ---------------------------------------------------------------------------
# Tool selection for the task agent
#
# Phase 1 modes (paper, Section 4.2, Table 4):
#   default   run_python
#   offline   run_python, network blocked (see `set_offline`)
#   notools   no tool at all; the agent answers from its own knowledge
# ---------------------------------------------------------------------------

PHASE1_MODE_CHOICES = ("default", "offline", "notools")


def tools_for_run(phase: int, phase1_mode: str = "default") -> list:
    """The tools bound to the task agent for one phase."""
    if phase == 1 and phase1_mode == "notools":
        return []
    if phase in (1, 2):
        return [run_python]
    return [run_bash, run_python]

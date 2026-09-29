#!/usr/bin/env python
"""Onboarding agent — learn a platform's API and write it down as a skill
(paper, Section 4).

One agent per (platform, condition). It is told the platform's name and its
interface, explores with the tools its condition allows, and writes two
reference documents that a task agent later reads:

    <out-dir>/SKILL_phase1_<platform>.md   how to find identifiers
    <out-dir>/SKILL_phase2_<platform>.md   how to construct calls
    <out-dir>/run_<platform>.json          what the run cost and looked at

Conditions
    search   web_search + fetch_url   read the documentation
    exec     run_python               import, introspect, call it

Model, prompt, output contract and budget are held constant, so a
difference in downstream pass rate is attributable to the knowledge source.

The agent is given no scenario, no gold and no research question — only the
platform name and its interface. The skill has to generalise rather than
memorise, and `web_search` cannot be steered toward the source papers, whose
DOIs name the benchmark's scenarios.

`web_search` uses Tavily or Serper when TAVILY_API_KEY or SERPER_API_KEY is
set, and falls back to DuckDuckGo otherwise.

Usage
    python scripts/run_onboarding.py --condition exec --platform argo \
        --model gemini-3.7-flash --out-dir skills/gemini-3.7-flash/exec
    python scripts/run_onboarding.py --condition search --platform all \
        --model gemini-3-flash-preview --out-dir skills/gemini-3-flash/search
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import signal
import sys
import time
import warnings

warnings.filterwarnings("ignore")

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from langchain_core.messages import HumanMessage                # noqa: E402

from harness import agent as eagent, records, tools as etools   # noqa: E402
from harness import schemas                                     # noqa: E402

ONBOARD_PLATFORMS = ("argo", "census_acs", "cmip6", "ensembl", "inaturalist",
                     "matproj", "noaa_ghcn", "obis", "pangaea", "usgs_eq",
                     "vizier")

CONDITIONS = {
    "search": {"tools": "research",
               "label": "documentation only (web_search + fetch_url)"},
    "exec":   {"tools": "python",
               "label": "execution only (run_python)"},
}

MARK1 = "<<<SKILL_PHASE1>>>"
MARK2 = "<<<SKILL_PHASE2>>>"
MARKEND = "<<<END>>>"


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_TOOL_GUIDANCE = {
    "search": (
        "## How to learn\n"
        "You have `web_search` and `fetch_url`. Find the platform's official "
        "documentation, its API reference, and worked examples, and read "
        "them. You canNOT run code, so everything you write must be "
        "supported by something you actually read — do not guess a signature.\n"
        "Publisher and preprint domains are blocked: describe the API, not "
        "anyone's research."
    ),
    "exec": (
        "## How to learn\n"
        "You have `run_python`. Import the package and interrogate it: "
        "`dir()`, `help()`, `inspect.signature()`, and — this is the point — "
        "actually CALL the functions with small arguments and look at what "
        "comes back. A tiny query that returns in seconds teaches you more "
        "than any docstring: which arguments are required, what the response "
        "looks like, which spellings fail.\n"
        "You have no web access, so everything you write must come from the "
        "package itself."
    ),
}


def build_prompt(platform: str, condition: str, budget: int = 25) -> str:
    iface = schemas.phase2_interface(platform)
    pkg = schemas.PHASE2_PACKAGE.get(platform, "?")
    keys = schemas.PHASE1_KEYS.get(platform, [])

    if iface == "rest":
        access = (
            f"This platform is reached over HTTP: **{pkg}**. This benchmark "
            f"addresses it through that API, and a call is written down as "
            f"`{{module, function, kwargs}}` in the namespace below.\n\n"
            + schemas.REST_INTERFACE_SPEC.get(platform, "")
        )
    else:
        access = (
            f"This platform is reached through the Python package "
            f"**`{pkg}`**, which is installed. A call is written down as "
            f"`{{module, function, kwargs}}` using the package's own "
            f"function and argument names."
        )

    return f"""\
You are onboarding onto a scientific data platform so that ANOTHER agent,
who will not have your tools or your time, can use it correctly from your
notes alone.

# Platform: `{platform}`

{access}

# What the reader has to do

The reader is handed a request for data — some of it named in the platform's
own vocabulary, some of it in plain language — and works it in two steps.
They will face many different requests against this platform, so write for
the platform, not for any one request.

**Phase 1 — identify.** Turn the request into this platform's own
identifiers:

{chr(10).join(f"  - `{k}`" for k in keys) or "  (none registered)"}

They must produce real identifier values, in the exact form the platform
uses. They cannot see any data yet. Anything the request did not ask for is
left empty — a plausible-looking default is worse than nothing.

**Phase 2 — construct the calls.** Write the exact calls that retrieve that
data, as a JSON list of `{{module, function, kwargs}}`. The calls are NOT
executed by the reader — they are handed to a runner — so the reader gets no
error message and no second chance. A wrong argument name or a wrong date
format simply fails.

## The call contract — this constrains what you should teach

Every entry must be **one self-contained retrieval**. The runner executes
each entry independently, and JSON carries only strings, numbers, booleans,
lists and dicts.

So an entry canNOT:
  - be a constructor that returns a client or handle and fetches nothing
    (`DataFetcher()`, `Client("USGS")`, `Vizier(...)`)
  - consume another entry's return value (`.to_xarray()`, `.to_dataframe()`,
    `get_product_list(observations=...)`, `to_dataset_dict()`)
  - pass an object that has to be constructed in Python (a `SkyCoord`, a
    `datetime`, a `Quantity`) — write the value as a string or number

A fluent chain such as `Client(...).query(...).to_frame()` must be written
as the ONE entry that carries the query, with the constructor's settings
folded into its kwargs and the conversion step dropped. `function` may be a
dotted path (`DataFetcher.float`, `Observations.query_criteria`) — that is
one entry, not three.

Teach the reader the single call that retrieves the data. If the package's
natural style is a multi-step chain, say so, and then show how it collapses
into one entry.

{_TOOL_GUIDANCE[condition]}

# Budget — read this before you start

You have about **{budget} tool calls**. Spend them deliberately: plan two or
three things worth establishing, establish them, then STOP and write.

Do not repeat a call that already failed with different wording — if a
search returns nothing twice, or an import keeps erroring, that IS the
finding, and the reader needs to know it. Running out of budget without
producing the two documents is the one outright failure here; a shorter
document written from less evidence still beats no document.

# What to write

Two reference documents for someone competent who has never used this
platform. You are not writing a tutorial or an overview — say nothing about
what the platform is for, who runs it, or why it exists. The reader needs to
make a correct call, and the only thing that helps is knowing which
specific mistake they are about to make.

Aim at these, in roughly this order of value:

**1. The canonical function, and the near neighbours that are wrong.**
Most platforms expose several functions that could plausibly retrieve the
data. Name the one to use, then name the ones that look right and say why
each is not — asynchronous when you need synchronous, needs credentials,
loads everything into memory, returns a listing rather than the records. A
short comparison is worth more than a paragraph of description.

**2. One fully worked call, every argument annotated.** Real values, not
placeholders. For each argument give the exact spelling, the type, whether
it is required, and the accepted value format. Argument names that differ
from what a reader would guess deserve their own note.

**3. Value formats that bite.** Date formats (they differ everywhere, and
`YYYY-MM` is not `YYYY-MM-DD`), leading zeros that must survive, case
sensitivity, integer versus string, scalar versus list. State these as
absolutes.

**4. How a request decomposes into entries.** This is the plan's shape and
it is easy to get wrong: given several entities, or a long time range, or
more results than one response holds — is that ONE entry with a list, or
one entry per entity? Say which, and say what the wrong choice looks like.

**5. Resolving an identifier from a name.** How does the reader get from
"the thing the request names" to "the code this platform uses"? If there is
a lookup endpoint or function for it, show the call. If the values are
enumerable and few, list them outright — a table the reader can copy beats
an instruction to go and search.

**6. What failure looks like.** Does a wrong argument raise, return empty,
or silently widen the query? Silent widening is the dangerous one and is
worth calling out wherever you find it.

Where you can, state a point as a directive with a concrete wrong-versus-
right pair rather than as prose — a reader skimming under time pressure
acts on `✗ ... / ✓ ...` and skims past explanation.

Two limits. Do not invent identifiers or values you did not verify; mark
anything you are unsure of as unverified rather than stating it flatly. And
prefer a short document that is right to a long one that is padded.

# Output format

End your reply with exactly this, and nothing after it:

{MARK1}
# Phase 1: <title>
...markdown...
{MARK2}
# Phase 2: <title>
...markdown...
{MARKEND}
"""


# ---------------------------------------------------------------------------
# Run one (platform, condition)
# ---------------------------------------------------------------------------

def tools_for(condition: str) -> list:
    if CONDITIONS[condition]["tools"] == "research":
        return list(etools.RESEARCH_TOOLS)
    return [etools.run_python]


def split_output(text: str) -> tuple[str, str] | None:
    if MARK1 not in text or MARK2 not in text:
        return None
    after = text.split(MARK1, 1)[1]
    p1, _, rest = after.partition(MARK2)
    p2 = rest.split(MARKEND, 1)[0] if MARKEND in rest else rest
    p1, p2 = p1.strip(), p2.strip()
    return (p1, p2) if p1 and p2 else None


class _PlatformTimeout(BaseException):
    """One (platform, condition) exceeded its wall budget.

    BaseException, not Exception: the alarm usually fires while the agent is
    inside a tool, and every tool wraps its body in `except Exception` to hand
    the model a readable error instead of crashing. An Exception subclass gets
    absorbed there, the one-shot alarm is spent, and the wall silently stops
    existing — mast/exec ran 1353s against a 900s budget exactly this way.
    """


def _timeout_handler(_signum, _frame):
    # Re-arm before raising. Belt and braces alongside BaseException: if any
    # frame in the stack does catch it, the alarm fires again shortly instead
    # of the budget evaporating on the first swallow.
    signal.alarm(5)
    raise _PlatformTimeout


def _text(m) -> str:
    c = getattr(m, "content", "")
    if isinstance(c, list):
        c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return c if isinstance(c, str) else ""


def run_one(platform: str, condition: str, args) -> dict:
    out_dir = pathlib.Path(args.out_dir)
    f1 = out_dir / f"SKILL_phase1_{platform}.md"
    f2 = out_dir / f"SKILL_phase2_{platform}.md"
    if f1.exists() and f2.exists() and not args.force:
        return {"platform": platform, "condition": condition,
                "status": "skipped (already written)"}

    prompt = build_prompt(platform, condition, args.tool_budget)
    if args.dry_run:
        print(prompt)
        return {"platform": platform, "condition": condition,
                "status": "dry_run", "prompt_chars": len(prompt)}

    etools.reset_research_log()
    etools.reset_python_namespace(None)
    model = eagent.build_model(model_id=args.model, provider=args.provider,
                               base_url=args.base_url,
                               api_key_env=args.api_key_env,
                               thinking_budget=args.thinking_budget)
    runnable = eagent.build_agent(model, tools=tools_for(condition))

    t0 = time.time()
    err = None
    msgs: list = []
    # A wall clock, because the recursion limit does not bound time: one slow
    # API call inside run_python can sit for an hour.
    if args.platform_timeout:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(args.platform_timeout)
    # Stream rather than invoke: exploration can hit the recursion limit, and
    # `invoke` then raises with no state at all. Streaming keeps every step
    # that did run, so an overrun still reports what it cost.
    try:
        for chunk in runnable.stream(
                {"messages": [HumanMessage(content=prompt)]},
                {"recursion_limit": args.recursion_limit},
                stream_mode="updates"):
            for node_state in chunk.values():
                msgs.extend(node_state.get("messages") or [])
    except (_PlatformTimeout, Exception) as e:
        err = f"{type(e).__name__}: {e}"
    finally:
        if args.platform_timeout:
            signal.alarm(0)
    elapsed = round(time.time() - t0, 1)

    final = next((t for t in map(_text, reversed(msgs)) if MARK1 in t), "")
    parts = split_output(final) if final else None

    rec = {"platform": platform, "condition": condition,
           "model": args.model, "elapsed_s": elapsed,
           # Same accounting as the task agent's phase records.
           "tokens": records._sum_tokens(msgs),
           "tool_call_turns": sum(1 for m in msgs
                                  if getattr(m, "tool_calls", None)),
           "research_log": etools.research_url_log(),
           "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat()}

    out_dir.mkdir(parents=True, exist_ok=True)
    if not parts:
        rec["status"] = "no usable output" if err is None else "error"
        rec["error"] = err
        tail = next((t for t in map(_text, reversed(msgs)) if t.strip()), "")
        rec["final_text_tail"] = tail[-3000:]
        (out_dir / f"failed_{platform}.json").write_text(
            json.dumps(rec, indent=2, default=str))
        return rec

    header = (f"<!-- generated by scripts/run_onboarding.py\n"
              f"     platform={platform} condition={condition} "
              f"model={args.model}\n"
              f"     {rec['generated_utc']} -->\n\n")
    f1.write_text(header + parts[0] + "\n")
    f2.write_text(header + parts[1] + "\n")
    (out_dir / f"run_{platform}.json").write_text(
        json.dumps(rec, indent=2, default=str))
    rec["status"] = "ok"
    return rec


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--condition", required=True, choices=list(CONDITIONS))
    ap.add_argument("--platform", default="all",
                    help="comma-separated, or 'all'")
    ap.add_argument("--out-dir", required=True,
                    help="directory the skill documents are written to, "
                         "e.g. skills/gemini-3.7-flash/exec")
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", choices=["google-genai", "openai"],
                    default="google-genai")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default=None)
    ap.add_argument("--thinking-budget", type=int, default=2048)
    ap.add_argument("--recursion-limit", type=int, default=120,
                    help="graph steps; roughly twice the tool-call budget")
    ap.add_argument("--platform-timeout", type=int, default=900,
                    help="seconds per platform before moving on; 0 disables")
    ap.add_argument("--tool-budget", type=int, default=25,
                    help="tool calls the prompt tells the agent it has")
    ap.add_argument("--force", action="store_true",
                    help="regenerate skills that already exist")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the prompt and exit")
    args = ap.parse_args()

    plats = (list(ONBOARD_PLATFORMS) if args.platform == "all"
             else [p.strip() for p in args.platform.split(",") if p.strip()])
    for p in plats:
        if p not in ONBOARD_PLATFORMS:
            raise SystemExit(f"unknown platform: {p}")

    print(f"condition : {args.condition} "
          f"({CONDITIONS[args.condition]['label']})", flush=True)
    print(f"model     : {args.model}", flush=True)
    print(f"platforms : {len(plats)}\n", flush=True)
    for plat in plats:
        print(f"  {plat:<13} ... ", end="", flush=True)
        r = run_one(plat, args.condition, args)
        tk = (r.get("tokens") or {}).get("total", 0)
        print(f"{r['status']:<24} {r.get('elapsed_s', 0):>6}s  {tk:>7} tok  "
              f"turns={r.get('tool_call_turns', 0):>3}", flush=True)


if __name__ == "__main__":
    main()

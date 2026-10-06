"""Comparators for Phases 1, 3 and 4 (paper, Section 2.2).

Phase 2 is graded separately, on the data its calls return
(grading/phase2/, scripts/grade_phase2.py).

Every comparator returns a dict:
    {
        "verdict":     "match" | "partial" | "mismatch" | "error" | "deferred",
        "binary_pass": bool | None,   # the pass criterion
        "score":       float in [0, 1] | None,
        "details":     {...}          # phase-specific breakdown
    }

Phase 1   per-key F1 over identifier sets, averaged over the platform's
          graded keys; pass iff the mean is at least PHASE1_PASS_F1.
Phases 3  the answer is within the relative tolerance PHASE34_REL_TOLERANCE
and 4     of the gold value; for an object or list, every element must be.
"""
from __future__ import annotations

import math
from typing import Any

from harness.schemas import phase1_graded_keys

PHASE1_PASS_F1 = 0.9
PHASE34_REL_TOLERANCE = 0.05
_EPS = 1e-9


# ---------------------------------------------------------------------------
# Helpers — set ops + F1
# ---------------------------------------------------------------------------

def _as_set(values: Any) -> set:
    if values is None:
        return set()
    if isinstance(values, (list, tuple, set)):
        return {str(v) for v in values}
    return {str(values)}


def _f1(agent: set, gold: set) -> tuple[float, float, float]:
    """Return (precision, recall, F1). Empty-set conventions:
        agent=∅ ∧ gold=∅ → P=R=F=1   (vacuously correct)
        agent=∅ ∧ gold≠∅ → P=R=F=0
        agent≠∅ ∧ gold=∅ → P=R=F=0
    """
    if not agent and not gold:
        return 1.0, 1.0, 1.0
    if not agent or not gold:
        return 0.0, 0.0, 0.0
    inter = len(agent & gold)
    p = inter / len(agent)
    r = inter / len(gold)
    f = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
    return p, r, f


# ---------------------------------------------------------------------------
# Helpers — numeric
# ---------------------------------------------------------------------------

def _numeric_score(agent: Any, gold: Any) -> float | None:
    """Continuous 1 − relative-error, capped at 0. None if either side is
    not a finite number. gold == 0 scores 1.0 only for agent == 0."""
    try:
        a = float(agent)
        g = float(gold)
    except (TypeError, ValueError):
        return None
    if math.isnan(a) or math.isnan(g) or math.isinf(a) or math.isinf(g):
        return None
    if abs(g) < _EPS:
        return 1.0 if abs(a) < _EPS else 0.0
    rel_err = abs(a - g) / abs(g)
    return max(0.0, 1.0 - rel_err)


def _numeric_within_tol(a: float, g: float) -> bool:
    if math.isnan(a) or math.isnan(g):
        return False
    return abs(a - g) / max(abs(g), _EPS) <= PHASE34_REL_TOLERANCE


# ---------------------------------------------------------------------------
# Phase 1 — mean F1 over the graded keys
# ---------------------------------------------------------------------------

def _has_content(v: Any) -> bool:
    """Does this gold value name at least one identifier?"""
    if v is None:
        return False
    if isinstance(v, (list, tuple, set, dict)):
        return len(v) > 0
    return str(v).strip() != ""


def compare_phase1(*, agent: Any, gold: dict, platform: str) -> dict:
    keys = phase1_graded_keys(platform)
    if not isinstance(agent, dict):
        return _err("agent output is not a dict", phase=1)

    # A scenario whose gold names no identifier under a graded key cannot be
    # graded: every key would compare ∅ with ∅. No published scenario is in
    # that state; the check stays so a new scenario cannot silently enter it.
    gradable = [k for k in keys if _has_content(gold.get(k))]
    if not gradable:
        return {
            "verdict": "deferred",
            "binary_pass": None,
            "score": None,
            "details": {
                "reason": "no graded key carries an identifier in the gold",
                "keys_total": len(keys),
                "keys_gradable": 0,
            },
        }

    per_key: dict[str, dict] = {}
    f1s: list[float] = []
    n_match = 0
    for k in keys:
        a = _as_set(agent.get(k))
        g = _as_set(gold.get(k))
        p, r, f = _f1(a, g)
        match = a == g
        per_key[k] = {
            "match":  match,
            "precision": round(p, 4),
            "recall":    round(r, 4),
            "f1":        round(f, 4),
            "missing":   sorted(g - a),
            "extra":     sorted(a - g),
            "agent_count": len(a),
            "gold_count":  len(g),
        }
        f1s.append(f)
        if match:
            n_match += 1

    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    exact_match = (n_match == len(keys))
    if exact_match:
        verdict = "match"
    elif n_match == 0:
        verdict = "mismatch"
    else:
        verdict = "partial"
    return {
        "verdict": verdict,
        "binary_pass": macro_f1 >= PHASE1_PASS_F1,
        "score": round(macro_f1, 4),
        "details": {
            "macro_f1":      round(macro_f1, 4),
            "keys_total":    len(keys),
            "keys_gradable": len(gradable),
            "keys_matched":  n_match,
            "exact_match":   exact_match,
            "pass_threshold": PHASE1_PASS_F1,
            "per_key":       per_key,
        },
    }


# ---------------------------------------------------------------------------
# Phase 3 — number, or an object / list of numbers
# ---------------------------------------------------------------------------

def compare_phase3(*, agent: Any, gold: Any) -> dict:
    if not isinstance(agent, dict) or "value" not in agent:
        return _err("agent output missing `value` key", phase=3)
    return _compare_value(agent["value"], gold)


def _compare_value(a_val: Any, g_val: Any) -> dict:
    # Object — keys must match exactly; per-key element comparison
    if isinstance(g_val, dict):
        if not isinstance(a_val, dict):
            return _wrong_shape("expected dict", got=type(a_val).__name__)
        a_keys = set(a_val.keys())
        g_keys = set(g_val.keys())
        _, _, key_f1 = _f1(a_keys, g_keys)
        shared = a_keys & g_keys
        per: dict = {}
        n_pass = 0
        elt_scores: list[float] = []
        for k in g_keys:
            if k in shared:
                sub = _compare_value(a_val[k], g_val[k])
                per[k] = sub
                if sub.get("binary_pass"):
                    n_pass += 1
                if sub.get("score") is not None:
                    elt_scores.append(sub["score"])
            else:
                per[k] = {"verdict": "mismatch", "binary_pass": False,
                          "score": 0.0,
                          "details": {"reason": "key missing from agent"}}
                elt_scores.append(0.0)
        elt_mean = (sum(elt_scores) / len(elt_scores)) if elt_scores else 0.0
        overall = key_f1 * elt_mean
        if n_pass == len(g_keys) and a_keys == g_keys:
            verdict = "match"
        elif n_pass == 0:
            verdict = "mismatch"
        else:
            verdict = "partial"
        return {
            "verdict": verdict,
            "binary_pass": verdict == "match",
            "score": round(overall, 4),
            "details": {
                "key_f1":       round(key_f1, 4),
                "element_mean": round(elt_mean, 4),
                "keys_total":   len(g_keys),
                "keys_matched": n_pass,
                "extra_keys":   sorted(a_keys - g_keys),
                "missing_keys": sorted(g_keys - a_keys),
                "per_key":      per,
            },
        }

    # List — length must match
    if isinstance(g_val, list):
        if not isinstance(a_val, list):
            return _wrong_shape("expected list", got=type(a_val).__name__)
        if len(a_val) != len(g_val):
            return {
                "verdict": "mismatch",
                "binary_pass": False,
                "score": 0.0,
                "details": {"reason": "length mismatch",
                            "agent_len": len(a_val),
                            "gold_len":  len(g_val)},
            }
        per_item: list[dict] = []
        n_pass = 0
        elt_scores: list[float] = []
        for ai, gi in zip(a_val, g_val):
            sub = _compare_value(ai, gi)
            per_item.append(sub)
            if sub.get("binary_pass"):
                n_pass += 1
            if sub.get("score") is not None:
                elt_scores.append(sub["score"])
        elt_mean = (sum(elt_scores) / len(elt_scores)) if elt_scores else 0.0
        if n_pass == len(g_val):
            verdict = "match"
        elif n_pass == 0:
            verdict = "mismatch"
        else:
            verdict = "partial"
        return {
            "verdict": verdict,
            "binary_pass": verdict == "match",
            "score": round(elt_mean, 4),
            "details": {
                "items_total":   len(g_val),
                "items_matched": n_pass,
                "per_item":      per_item,
            },
        }

    return _compare_scalar(a_val, g_val)


def _compare_scalar(a_val: Any, g_val: Any) -> dict:
    if g_val is None:
        match = (a_val is None)
        return {
            "verdict": "match" if match else "mismatch",
            "binary_pass": match,
            "score": 1.0 if match else 0.0,
            "details": {"agent": a_val, "gold": g_val},
        }
    if isinstance(g_val, str):
        ok = isinstance(a_val, str) and a_val.strip().lower() == g_val.strip().lower()
        return {
            "verdict": "match" if ok else "mismatch",
            "binary_pass": ok,
            "score": 1.0 if ok else 0.0,
            "details": {"agent": a_val, "gold": g_val, "kind": "string"},
        }
    try:
        a = float(a_val)
        g = float(g_val)
    except (TypeError, ValueError):
        return {
            "verdict": "mismatch",
            "binary_pass": False,
            "score": 0.0,
            "details": {"agent": a_val, "gold": g_val,
                        "reason": "non-numeric"},
        }
    if math.isnan(a) or math.isnan(g):
        return {
            "verdict": "mismatch",
            "binary_pass": False,
            "score": 0.0,
            "details": {"agent": a, "gold": g, "reason": "NaN"},
        }
    binary = _numeric_within_tol(a, g)
    cont = _numeric_score(a, g)
    return {
        "verdict": "match" if binary else "mismatch",
        "binary_pass": binary,
        "score": round(cont if cont is not None else 0.0, 4),
        "details": {"agent": a, "gold": g, "abs_diff": abs(a - g)},
    }


# ---------------------------------------------------------------------------
# Phase 4 — the numeric answer. A qualitative answer, where the request asks
# for one, is recorded in the phase record but not graded.
# ---------------------------------------------------------------------------

def compare_phase4(*, agent: Any, gold: Any, unit: str | None = None) -> dict:
    if not isinstance(agent, dict):
        return _err("agent output is not a dict", phase=4)
    out = _compare_scalar(agent.get("numeric_answer"), gold)
    out["details"]["unit"] = unit
    return out


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _err(reason: str, *, phase: int) -> dict:
    return {
        "verdict": "error",
        "binary_pass": False,
        "score": 0.0,
        "details": {"phase": phase, "reason": reason},
    }


def _wrong_shape(reason: str, *, got: str) -> dict:
    return {
        "verdict": "mismatch",
        "binary_pass": False,
        "score": 0.0,
        "details": {"reason": reason, "got": got},
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def compare_phase(phase: int, *, agent: Any, scenario: dict,
                  platform: str) -> dict | None:
    """Grade one phase. Returns None for Phase 2, which is graded later on
    the data its calls return."""
    if phase == 1:
        gold = scenario.get("phase_1", {}).get("expected") or {}
        return compare_phase1(agent=agent, gold=gold, platform=platform)
    if phase == 2:
        return None
    if phase == 3:
        return compare_phase3(agent=agent,
                              gold=scenario.get("phase_3", {}).get("expected"))
    if phase == 4:
        p4 = scenario.get("phase_4", {})
        return compare_phase4(agent=agent, gold=p4.get("expected"),
                              unit=p4.get("unit"))
    raise ValueError(f"unknown phase: {phase}")

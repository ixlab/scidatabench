"""Result-equivalence grading for Phase 2.

`registry`  per-platform merge unit, record key and comparison columns
`grader`    metric computation and verdict
"""
from .grader import grade_scenario, load_call, merge          # noqa: F401
from .registry import REGISTRY, spec_for                      # noqa: F401

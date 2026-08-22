"""GP primitives: the function set, the per-hook feature lists, the DEAP
primitive sets, and the warm-start trees that reproduce the Pham rules."""
from __future__ import annotations

import random

from deap import gp


def add(a: float, b: float) -> float:
    return a + b


def sub(a: float, b: float) -> float:
    return a - b


def mul(a: float, b: float) -> float:
    return a * b


def protected_div(a: float, b: float) -> float:
    return a / b if abs(b) > 1e-9 else 1.0


def min2(a: float, b: float) -> float:
    return a if a < b else b


def max2(a: float, b: float) -> float:
    return a if a > b else b


def neg(a: float) -> float:
    return -a


def absv(a: float) -> float:
    return a if a >= 0.0 else -a


def if_gt(a: float, b: float, c: float, d: float) -> float:
    return c if a > b else d


def _rand_const() -> float:
    return random.uniform(-2.0, 2.0)


FEATURES_4: tuple[str, ...] = (
    "is_downstream",
    "is_upstream",
    "blocks_above",
    "successor_count",
    "move_age",
    "pd_dist",
    "nearest_crane_dist",
    "total_moves",
)

FEATURES_5: tuple[str, ...] = (
    "dist_pickup",
    "dist_dropoff",
    "crane_pos_norm",
    "crane_load",
    "range_headroom",
    "gap_to_other",
)

FEATURES_2: tuple[str, ...] = (
    "dist_source",
    "dist_handover",
    "buf_free",
    "is_empty",
    "blocks_requested_in_buf",
    "reach_count",
)


def _build_pset(name: str, features: tuple[str, ...], const_name: str) -> gp.PrimitiveSet:
    pset = gp.PrimitiveSet(name, len(features))
    pset.addPrimitive(add, 2, name="add")
    pset.addPrimitive(sub, 2, name="sub")
    pset.addPrimitive(mul, 2, name="mul")
    pset.addPrimitive(protected_div, 2, name="protected_div")
    pset.addPrimitive(min2, 2, name="min2")
    pset.addPrimitive(max2, 2, name="max2")
    pset.addPrimitive(neg, 1, name="neg")
    pset.addPrimitive(absv, 1, name="abs")
    pset.addPrimitive(if_gt, 4, name="if_gt")
    pset.addEphemeralConstant(const_name, _rand_const)
    pset.renameArguments(**{f"ARG{i}": feat for i, feat in enumerate(features)})
    return pset


PSET4 = _build_pset("HOOK4", FEATURES_4, "rnd4")
PSET5 = _build_pset("HOOK5", FEATURES_5, "rnd5")
PSET2 = _build_pset("HOOK2", FEATURES_2, "rnd2")

DEFAULT_TREE5 = "mul(dist_pickup, dist_dropoff)"
DEFAULT_TREE4 = "sub(neg(mul(is_downstream, 10.0)), move_age)"
DEFAULT_TREE2 = "dist_source"

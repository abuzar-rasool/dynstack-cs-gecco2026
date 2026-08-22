"""
A   hooks 4 and 5, seeded with the Pham rules
B   hook 2, on the frozen Stage-A champion
C   hooks 2/4/5 jointly, warm-started from A and B
D   as C, fitness averaged over 3 seeds instead of 1
E   as D, with both overlays active, which is what the champion serves
"""
from __future__ import annotations

from strategies.sca_gphh import genomes as g
from strategies.sca_gphh.primitives import (
    DEFAULT_TREE2,
    DEFAULT_TREE4,
    DEFAULT_TREE5,
    PSET2,
    PSET4,
    PSET5,
)


PSET_BY_KEY = {"tree2": PSET2, "tree4": PSET4, "tree5": PSET5}

STAGES: dict[str, dict] = {
    "A": {
        "strategy": "gp_stage_a",
        "tree_keys": ("tree4", "tree5"),
        "warm_trees": (DEFAULT_TREE4, DEFAULT_TREE5),
        "extra_params": {},
        "seeds_per_gen": 1,
        "pop_size": 80,
    },
    "B": {
        "strategy": "gp_stage_b",
        "tree_keys": ("tree2",),
        "warm_trees": (DEFAULT_TREE2,),
        "extra_params": {},
        "seeds_per_gen": 1,
        "pop_size": 80,
    },
    "C": {
        "strategy": "gp_stage_c",
        "tree_keys": ("tree2", "tree4", "tree5"),
        "warm_trees": (g.STAGE_B_TREE2, g.STAGE_A_TREE4, g.STAGE_A_TREE5),
        "extra_params": {},
        "seeds_per_gen": 1,
        "pop_size": 80,
    },
    "D": {
        "strategy": "gp_stage_d",
        "tree_keys": ("tree2", "tree4", "tree5"),
        "warm_trees": (g.STAGE_C_TREE2, g.STAGE_C_TREE4, g.STAGE_C_TREE5),
        "extra_params": {},
        "seeds_per_gen": 3,
        "pop_size": 60,
    },
    "E": {
        "strategy": "gp_stage_e",
        "tree_keys": ("tree2", "tree4", "tree5"),
        "warm_trees": (g.STAGE_D_TREE2, g.STAGE_D_TREE4, g.STAGE_D_TREE5),
        "extra_params": {"digout": "True", "headline_fix": "True"},
        "seeds_per_gen": 3,
        "pop_size": 80,
    },
}


class StageConfig:
    """One stage's settings, resolved once at startup."""

    def __init__(self, stage: str, *, smoke: bool, seeds_per_gen: int | None) -> None:
        cfg = STAGES[stage]
        self.stage = stage
        self.strategy = cfg["strategy"]
        self.tree_keys = cfg["tree_keys"]
        self.psets = tuple(PSET_BY_KEY[k] for k in self.tree_keys)
        self.warm_trees = cfg["warm_trees"]
        self.extra_params = dict(cfg["extra_params"])
        self.n_trees = len(self.tree_keys)
        self.pop_size = 6 if smoke else cfg["pop_size"]
        if smoke:
            self.seeds_per_gen = 1
        else:
            self.seeds_per_gen = seeds_per_gen or cfg["seeds_per_gen"]

    def params(self, trees: list[str]) -> dict[str, str]:
        params = {key: str(tree) for key, tree in zip(self.tree_keys, trees)}
        params["interleave"] = "True"
        params.update(self.extra_params)
        return params

"""Stage-D runtime: hooks 2, 4 and 5 as free trees, no overlays.

Structurally this is Stage C; what changes at Stage D is the fitness,
which averages three fresh seeds per scenario instead of one. The
defaults warm-start from the Stage-C champion. Overlays enter at Stage E.
"""
from __future__ import annotations

from . import genomes as g
from .policy import ScoredStrategy, tree_scorer
from .primitives import PSET2, PSET4, PSET5


class GPStageD(ScoredStrategy):

    def __init__(
        self,
        *,
        tree2: str = g.STAGE_C_TREE2,
        tree4: str = g.STAGE_C_TREE4,
        tree5: str = g.STAGE_C_TREE5,
        interleave: bool = True,
    ) -> None:
        super().__init__(
            score2=tree_scorer(tree2, PSET2),
            score4=tree_scorer(tree4, PSET4),
            score5=tree_scorer(tree5, PSET5),
            interleave=interleave,
        )

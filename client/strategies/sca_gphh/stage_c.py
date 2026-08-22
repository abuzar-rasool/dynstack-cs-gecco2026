"""Stage-C runtime: hooks 2, 4 and 5 as free trees, co-adapted jointly, no
overlays. The defaults reproduce the Stage A and B champions, so the joint
search starts from that baseline."""
from __future__ import annotations

from . import genomes as g
from .policy import ScoredStrategy, tree_scorer
from .primitives import PSET2, PSET4, PSET5


class GPStageC(ScoredStrategy):

    def __init__(
        self,
        *,
        tree2: str = g.STAGE_B_TREE2,
        tree4: str = g.STAGE_A_TREE4,
        tree5: str = g.STAGE_A_TREE5,
        interleave: bool = True,
    ) -> None:
        super().__init__(
            score2=tree_scorer(tree2, PSET2),
            score4=tree_scorer(tree4, PSET4),
            score5=tree_scorer(tree5, PSET5),
            interleave=interleave,
        )

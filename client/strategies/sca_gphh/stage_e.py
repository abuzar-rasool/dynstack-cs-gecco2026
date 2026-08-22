"""Stage-E runtime: hooks 2, 4 and 5 as free trees with both structural
overlays active.

This is the final stage and the configuration the champion is deployed
in, so the genome is selected under exactly the conditions it will serve
under. The defaults warm-start from the Stage-D champion. Both overlays
can be switched off individually.
"""
from __future__ import annotations

from framework.overlays import OverlayMixin

from . import genomes as g
from .policy import ScoredStrategy, tree_scorer
from .primitives import PSET2, PSET4, PSET5


class GPStageE(OverlayMixin, ScoredStrategy):

    def __init__(
        self,
        *,
        tree2: str = g.STAGE_D_TREE2,
        tree4: str = g.STAGE_D_TREE4,
        tree5: str = g.STAGE_D_TREE5,
        interleave: bool = True,
        headline_fix: bool = True,
        digout: bool = True,
    ) -> None:
        super().__init__(
            score2=tree_scorer(tree2, PSET2),
            score4=tree_scorer(tree4, PSET4),
            score5=tree_scorer(tree5, PSET5),
            interleave=interleave,
        )
        self._init_overlays(headline_fix=headline_fix, digout=digout)

"""Stage-B runtime: hook 2 (which buffer an override drops on) as a GP
tree, with hooks 4 and 5 frozen to the Stage-A champion and no overlays.
The warm start reproduces the Pham nearest-buffer rule."""
from __future__ import annotations

from . import genomes as g
from .policy import ScoredStrategy, tree_scorer
from .primitives import DEFAULT_TREE2, PSET2, PSET4, PSET5


class GPStageB(ScoredStrategy):

    def __init__(self, *, tree2: str = DEFAULT_TREE2, interleave: bool = True) -> None:
        super().__init__(
            score2=tree_scorer(tree2, PSET2),
            score4=tree_scorer(g.STAGE_A_TREE4, PSET4),
            score5=tree_scorer(g.STAGE_A_TREE5, PSET5),
            interleave=interleave,
        )

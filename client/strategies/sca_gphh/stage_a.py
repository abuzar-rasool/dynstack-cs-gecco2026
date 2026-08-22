"""Stage-A runtime: hooks 4 (move order) and 5 (crane choice) as GP trees.

Dispatch only: it returns no override requests, so Phase B is a no-op and
the simulator owns every move. Establishes what evolved sequencing and
routing are worth before placement enters at Stage B.
"""
from __future__ import annotations

from framework.generic import TickContext
from models.cranescheduling_model_pb2 import MoveRequest

from .policy import ScoredStrategy, tree_scorer
from .primitives import DEFAULT_TREE4, DEFAULT_TREE5, PSET4, PSET5


class GPStageA(ScoredStrategy):

    def __init__(
        self,
        *,
        tree4: str = DEFAULT_TREE4,
        tree5: str = DEFAULT_TREE5,
        interleave: bool = True,
    ) -> None:
        super().__init__(
            score4=tree_scorer(tree4, PSET4),
            score5=tree_scorer(tree5, PSET5),
            interleave=interleave,
        )

    def pick_requests_to_override(self, ctx: TickContext) -> list[MoveRequest]:
        """Hook 1: none. Placement is not learned until Stage B."""
        return []

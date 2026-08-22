"""ScoredStrategy: a Strategy whose three learned hooks are scoring functions.

One scorer per learned hook, so the same class serves GP trees and the
CMA-ES weight vector. Hooks 1, 3, 6 and 7 stay at their framework
defaults. Phase C is overridden here to add the ready-first tiering and
the round-robin interleave that the evolved policies are trained under.
"""
from __future__ import annotations

from typing import Callable

from deap import gp

from framework.generic import Strategy, TickContext
from models.cranescheduling_model_pb2 import Crane, CraneMove, Location, MoveRequest, World

from .features import DispatchFeatures, PlacementFeatures, finite, interleave_by_crane


Scorer = Callable[..., float]


def tree_scorer(tree: str, pset: gp.PrimitiveSet) -> Scorer:
    compiled = gp.compile(gp.PrimitiveTree.from_string(tree, pset), pset)
    return lambda *feats: finite(compiled(*feats))


class ScoredStrategy(Strategy):

    def __init__(
        self,
        *,
        score2: Scorer | None = None,
        score4: Scorer,
        score5: Scorer,
        interleave: bool = True,
    ) -> None:
        super().__init__()
        self._score2 = score2
        self._score4 = score4
        self._score5 = score5
        self._interleave = bool(interleave)

    def plan(self, world: World):
        """Build the placement features once, then run the normal tick."""
        self._placement = PlacementFeatures(world)
        return super().plan(world)

    def select_buffer(
        self,
        ctx: TickContext,
        req: MoveRequest,
        source_loc: Location,
        candidates: list[Location],
    ) -> Location | None:
        """Hook 2: the candidate buffer with the lowest placement score.

        Returns None when no scorer was supplied, which makes the strategy
        dispatch-only.
        """
        if self._score2 is None or not candidates:
            return None
        loads = self._tracker.buffer_loads(candidates)
        return min(
            candidates,
            key=lambda buf: self._score2(
                *self._placement.buffer_feats(source_loc, buf, loads[buf.Id])
            ),
        )

    def move_priority(self, ctx: TickContext, move: CraneMove) -> float:
        """Hook 4: the move's sequencing score, lower running first."""
        return self._score4(*self._dispatch.move_feats(move))

    def select_crane_for_move(
        self,
        ctx: TickContext,
        move: CraneMove,
        eligible: list[Crane],
    ) -> int | None:
        """Hook 5: the eligible crane with the lowest routing score."""
        if not eligible:
            return None
        best = min(
            eligible,
            key=lambda c: self._score5(*self._dispatch.crane_feats(move, c)),
        )
        return best.Id

    def _assign_and_order(self, ctx: TickContext) -> list[tuple[CraneMove, int]]:
        """Phase C, with the tiering the evolved policies are trained under.

        Moves the simulator could start now come before blocked ones, hook 4
        orders within each tier, and the result is interleaved across cranes
        so neither sits idle behind the other's queue.
        """
        self._dispatch = DispatchFeatures(ctx.world)
        sim_moves: list[CraneMove] = [m for m in ctx.world.CraneMoves if m.Id < 0]
        ready = {m.Id: self._dispatch.is_ready(m) for m in sim_moves}
        sim_moves.sort(key=lambda m: (0 if ready[m.Id] else 1, self.move_priority(ctx, m)))
        assignments: list[tuple[CraneMove, int]] = []
        for move in sim_moves:
            crane_id = self._select_crane_with_required(ctx, move)
            if crane_id is None:
                continue
            self._dispatch.note_assignment(crane_id)
            assignments.append((move, crane_id))
        if self._interleave:
            assignments = interleave_by_crane(assignments)
        return assignments

"""Pham-inspired rule-based baseline.

Nearest feasible buffer, earliest due date, nearest crane. Hooks 3 and 6
(nearest crane for an override, round-robin dispatch) are the framework
defaults and already match these rules. Also the warm start for Stage A,
whose seed trees reproduce the same behaviour.
"""
from __future__ import annotations

from framework.base import distance
from framework.generic import Strategy, TickContext
from framework.utils import argmin_or_none
from models.cranescheduling_model_pb2 import Crane, CraneMove, Location, MoveRequest


class PhamRuleBased(Strategy):

    def select_buffer(
        self,
        ctx: TickContext,
        req: MoveRequest,
        source_loc: Location,
        candidates: list[Location],
    ) -> Location | None:
        """Hook 2: nearest feasible buffer to the source."""
        return argmin_or_none(
            candidates,
            key=lambda buf: abs(buf.GirderPosition - source_loc.GirderPosition),
        )

    def move_priority(self, ctx: TickContext, move: CraneMove) -> float:
        """Hook 4: earliest due date first."""
        return move.DueDate.MilliSeconds

    def select_crane_for_move(
        self,
        ctx: TickContext,
        move: CraneMove,
        eligible: list[Crane],
    ) -> int | None:
        """Hook 5: the crane currently closest to the pickup."""
        crane = argmin_or_none(
            eligible, key=lambda c: distance(c, move.PickupGirderPosition)
        )
        return crane.Id if crane is not None else None

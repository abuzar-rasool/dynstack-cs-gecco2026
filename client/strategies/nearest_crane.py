"""Nearest-crane baseline, dispatch tier only.

No custom moves: it orders the simulator's moves by due date and gives each
to the crane nearest the pickup. The lower bound for every comparison.
"""
from __future__ import annotations

from framework.base import distance
from framework.generic import Strategy, TickContext
from framework.utils import argmin_or_none
from models.cranescheduling_model_pb2 import Crane, CraneMove, MoveRequest


class NearestCraneBaseline(Strategy):

    def pick_requests_to_override(self, ctx: TickContext) -> list[MoveRequest]:
        """Hook 1: none. Dispatch tier, so the simulator owns every move."""
        return []

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

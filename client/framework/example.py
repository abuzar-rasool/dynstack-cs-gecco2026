"""A hand-written strategy that overrides all seven hooks.

No evolution involved: every decision is an explicit rule. Use it as a
template, keep the hooks you care about and delete the rest to fall back
on the framework defaults.

Just an example to demostrate the framework use.
"""
from __future__ import annotations

from framework.base import distance
from framework.generic import Strategy, TickContext
from framework.overlays import OverlayMixin
from framework.utils import argmin_or_none
from models.cranescheduling_model_pb2 import Crane, CraneMove, Location, MoveRequest


MAX_OVERRIDES_PER_TICK = 4


class HandWrittenStrategy(Strategy):
    """A complete policy with every hook written by hand.

    Places arriving blocks on the emptiest reachable buffer, runs
    deliveries to the handover before anything else, and sends whichever
    crane is closest. Overrides all seven hooks so each decision point is
    visible; delete any of them to fall back on the framework default.
    """

    def pick_requests_to_override(self, ctx: TickContext) -> list[MoveRequest]:
        """Hook 1: which requests to place myself, oldest first, capped."""
        ready = [
            req
            for req in ctx.world.MoveRequests
            if req.TargetLocationId < 0
            and (loc := ctx.source_of(req.BlockId)) is not None
            and loc.Stack.BottomToTop
            and loc.Stack.BottomToTop[-1].Id == req.BlockId
        ]
        ready.sort(key=lambda r: r.Id)
        return ready[:MAX_OVERRIDES_PER_TICK]

    def select_buffer(
        self,
        ctx: TickContext,
        req: MoveRequest,
        source_loc: Location,
        candidates: list[Location],
    ) -> Location | None:
        """Hook 2: emptiest reachable buffer, ties broken by travel distance."""
        loads = self._tracker.buffer_loads(candidates)
        return argmin_or_none(
            candidates,
            key=lambda buf: (
                loads[buf.Id],
                abs(buf.GirderPosition - source_loc.GirderPosition),
            ),
        )

    def select_crane_for_override(
        self,
        ctx: TickContext,
        req: MoveRequest,
        source_loc: Location,
        target_buf: Location,
        eligible: list[Crane],
    ) -> int | None:
        """Hook 3: whichever eligible crane is closest to the pickup."""
        crane = argmin_or_none(
            eligible, key=lambda c: distance(c, source_loc.GirderPosition)
        )
        return crane.Id if crane is not None else None

    def move_priority(self, ctx: TickContext, move: CraneMove) -> float:
        """Hook 4: deliveries to the handover first, then the oldest move."""
        handovers = {loc.Id for loc in ctx.handovers}
        tier = 0 if move.DropoffLocationId in handovers else 1
        return tier * 1e12 - move.ReleaseTime.MilliSeconds

    def select_crane_for_move(
        self,
        ctx: TickContext,
        move: CraneMove,
        eligible: list[Crane],
    ) -> int | None:
        """Hook 5: shortest travel to the pickup wins."""
        crane = argmin_or_none(
            eligible, key=lambda c: distance(c, move.PickupGirderPosition)
        )
        return crane.Id if crane is not None else None

    def custom_dispatch_order(
        self, ctx: TickContext, tracked: list[tuple[CraneMove, int]],
    ) -> list[tuple[int, int]]:
        """Hook 6: one move per crane in turn, so neither crane starves."""
        per_crane: dict[int, list[int]] = {}
        for move, crane_id in tracked:
            per_crane.setdefault(crane_id, []).append(move.Id)
        order: list[tuple[int, int]] = []
        depth = max((len(q) for q in per_crane.values()), default=0)
        for i in range(depth):
            for crane_id, queue in per_crane.items():
                if i < len(queue):
                    order.append((queue[i], crane_id))
        return order

    def custom_first(self, ctx: TickContext) -> bool:
        """Hook 7: my own moves go ahead of the simulator's."""
        return True


class HandWrittenWithOverlays(OverlayMixin, HandWrittenStrategy):
    """The same rules plus dig-out and the head-of-line reorder.

    The overlays are independent of how a policy scores, so they attach to
    a hand-written strategy exactly as they do to the evolved ones. Pass
    digout=False or headline_fix=False to run with only one of them.
    """

    def __init__(self) -> None:
        super().__init__()
        self._init_overlays()
        

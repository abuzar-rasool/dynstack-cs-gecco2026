"""The two structural overlays, independent of any scoring policy.

Dig-out: the framework only relocates topmost blocks, so a buried requested
block waits for an unrelated move to free it. This adds one synthetic
request per buried block naming the topmost blocker, and lets the normal
hooks and the tracker place it, so it can never cause a delivery error.

Head-of-line: the simulator serves a crane only when the schedule head is
its own move, so a busy crane can stall an idle one. This re-prioritises
ready moves first, idle cranes leading.

Mix into any custom-move strategy and call _init_overlays() in __init__.
"""
from __future__ import annotations

from framework.generic import TickContext
from models.cranescheduling_model_pb2 import (
    CraneMove,
    CraneSchedulingSolution,
    CraneScheduleActivityState,
    MoveRequest,
    World,
)


def _interleave_activities(activities, idle_first):
    """Round-robin activities across cranes, idle cranes leading.

    Each crane keeps its own relative order; only the interleaving changes.
    """
    per_crane: dict[int, list] = {}
    for act in activities:
        per_crane.setdefault(act.CraneId, []).append(act)
    order = sorted(per_crane, key=lambda c: (0 if c in idle_first else 1, c))
    out: list = []
    max_len = max((len(q) for q in per_crane.values()), default=0)
    for i in range(max_len):
        for crane_id in order:
            queue = per_crane[crane_id]
            if i < len(queue):
                out.append(queue[i])
    return out


def _move_is_ready(move: CraneMove, alive_ids: set[int], loc_by_id: dict) -> bool:
    """Whether the simulator could start this move right now.

    Ready means every predecessor has completed and the block is topmost
    on its stack; an unready move at the head of the queue stalls the
    crane behind it.
    """
    if any(pred in alive_ids for pred in move.ProtobufPredecessorIds):
        return False
    src = loc_by_id.get(move.PickupLocationId)
    if src is None or not src.Stack.BottomToTop:
        return True
    moved = set(move.ProtobufMovedBlockIds)
    if not moved:
        return True
    return src.Stack.BottomToTop[-1].Id in moved


class OverlayMixin:
    """Dig-out + head-of-line reorder on top of any custom-move strategy."""

    _headline_fix: bool = True
    _digout: bool = True

    def _init_overlays(self, *, headline_fix: bool = True, digout: bool = True) -> None:
        """Enable the overlays. Call from the subclass __init__.

        Args:
            headline_fix: re-prioritise the finished schedule so its head is
                startable by an idle crane.
            digout: propose relocations that uncover buried requested blocks.
        """
        self._headline_fix = bool(headline_fix)
        self._digout = bool(digout)
        self._dig_source_ids: set[int] = set()

    def plan(self, world: World) -> CraneSchedulingSolution | None:
        """Run the underlying policy, then re-prioritise its schedule."""
        solution = super().plan(world)
        if solution is not None and self._headline_fix:
            self._fix_head_idle_first(world, solution)
        return solution

    def _fix_head_idle_first(self, world: World, solution: CraneSchedulingSolution) -> None:
        """Put a startable move at the head of the shared schedule.

        The simulator serves a crane only when the global head is its own
        move, so a busy crane's queued move can stall an idle one. Ready
        moves are promoted, idle cranes first.
        """
        acts = solution.Schedule.Activities
        if len(acts) <= 1:
            return
        sched = world.CraneSchedule
        active_acts = sched.Activities if sched is not None else []
        busy = {
            a.CraneId for a in active_acts
            if a.State == CraneScheduleActivityState.Active
        }
        active_ids = {
            a.MoveId for a in active_acts
            if a.State == CraneScheduleActivityState.Active
        }
        idle_first = frozenset(c.Id for c in world.Cranes if c.Id not in busy)
        move_by_id = {m.Id: m for m in world.CraneMoves}
        alive_ids = set(move_by_id)
        loc_by_id = {loc.Id: loc for loc in world.Locations}

        def head_eligible(act) -> bool:
            if act.MoveId in active_ids:
                return False
            if act.MoveId > 0:
                return True
            move = move_by_id.get(act.MoveId)
            return move is not None and _move_is_ready(move, alive_ids, loc_by_id)

        ready = [a for a in acts if head_eligible(a)]
        rest = [a for a in acts if not head_eligible(a)]
        ordered = _interleave_activities(ready, idle_first) + rest
        for priority, act in enumerate(ordered):
            act.Priority = priority

    def pick_requests_to_override(self, ctx: TickContext) -> list[MoveRequest]:
        """The policy's own requests plus one dig-out request per buried block."""
        base = super().pick_requests_to_override(ctx)
        self._dig_source_ids = set()
        out = list(base)
        if self._digout:
            out += self._digout_requests(ctx)
        return out

    def _digout_requests(self, ctx: TickContext) -> list[MoveRequest]:
        """One synthetic request per buried requested block.

        Each names the topmost blocker above it. Skips a blocker that is
        itself requested, or one already being moved.
        """
        world = ctx.world
        requested = {req.BlockId for req in world.MoveRequests}
        out: list[MoveRequest] = []
        for req in world.MoveRequests:
            source_loc = ctx.source_of(req.BlockId)
            if source_loc is None or source_loc.Id in self._dig_source_ids:
                continue
            stack = source_loc.Stack.BottomToTop
            if not stack or stack[-1].Id == req.BlockId:
                continue
            blocker_id = stack[-1].Id
            if blocker_id in requested:
                continue
            if self._tracker.is_block_tracked(blocker_id):
                continue
            out.append(MoveRequest(Id=req.Id, BlockId=blocker_id))
            self._dig_source_ids.add(source_loc.Id)
        return out

    def _candidate_buffers(self, ctx: TickContext, source_loc):
        """Narrow dig-out destinations so a dig never buries another request."""
        bufs = super()._candidate_buffers(ctx, source_loc)
        if source_loc.Id not in self._dig_source_ids:
            return bufs
        requested = {req.BlockId for req in ctx.world.MoveRequests}
        return [
            buf
            for buf in bufs
            if not any(blk.Id in requested for blk in buf.Stack.BottomToTop)
        ]

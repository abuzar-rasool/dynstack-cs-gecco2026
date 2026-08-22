"""The crane-scheduling framework: one strategy class, seven hooks.

A tick runs in four phases. Phase A builds a read-only TickContext.
Phase B proposes custom-move overrides: for each request from
pick_requests_to_override the framework computes the cleared candidate
buffers, calls select_buffer, then select_crane_for_override, and finally
checks the proposal with the tracker; a None anywhere skips it cleanly.
Phase C sorts the sim moves by move_priority and assigns them via
select_crane_for_move. Phase D merges everything into one solution. The
constraint logic lives in the sealed phase methods and CustomMoveTracker,
which holds no scoring policy.

Of the seven hooks, three carry policy worth learning (select_buffer,
move_priority, select_crane_for_move) and four are pinned to framework
defaults: pick_requests_to_override (FIFO over free-target requests whose
block is topmost, mirroring a simulator invariant), select_crane_for_override
(nearest crane to the source), custom_dispatch_order (round-robin across
cranes) and custom_first (True). Any of them may be overridden. A
dispatch-only strategy returns [] from pick_requests_to_override, which
makes Phase B a no-op.

Two things are deliberately not hooks: overrides claim resources before sim
moves, and Phase B is a per-request greedy walk, so joint matching has to
happen inside pick_requests_to_override.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from framework.base import (
    LOC_TYPE_ARRIVAL,
    LOC_TYPE_BUFFER,
    LOC_TYPE_HANDOVER,
    can_serve,
    can_serve_positions,
    cranes_that_can_serve,
    distance,
)
from framework.tracker import CustomMoveTracker
from framework.utils import argmin_or_none
from models.cranescheduling_model_pb2 import (
    Crane,
    CraneMove,
    CraneSchedulingSolution,
    Location,
    MoveRequest,
    World,
)


class TickContext:
    """Read-only snapshot built once per tick.

    Exposes the raw `world` plus a few indexes the hooks would otherwise
    rebuild on every call. Anything not precomputed here is fair game
    to dig out of `ctx.world` directly inside a hook.
    """

    __slots__ = ("world", "buffers", "arrivals", "handovers", "_block_loc")

    world: World
    buffers: list[Location]
    arrivals: list[Location]
    handovers: list[Location]
    _block_loc: dict[int, Location]

    def __init__(self, world: World) -> None:
        self.world = world
        self.buffers = [loc for loc in world.Locations if loc.Type == LOC_TYPE_BUFFER]
        self.arrivals = [loc for loc in world.Locations if loc.Type == LOC_TYPE_ARRIVAL]
        self.handovers = [
            loc for loc in world.Locations if loc.Type == LOC_TYPE_HANDOVER
        ]
        self._block_loc = {}
        for loc in world.Locations:
            for block in loc.Stack.BottomToTop:
                self._block_loc[block.Id] = loc

    def source_of(self, block_id: int) -> Location | None:
        """The location currently holding `block_id`, or None if unknown."""
        return self._block_loc.get(block_id)


def _is_topmost(ctx: TickContext, block_id: int) -> bool:
    """Whether the block sits on top of its stack and can be picked now.

    The simulator silently discards a custom move on a buried block, so
    the default request filter checks this before proposing one.
    """
    loc = ctx.source_of(block_id)
    if loc is None or not loc.Stack.BottomToTop:
        return False
    return loc.Stack.BottomToTop[-1].Id == block_id


class Strategy(ABC):
    """Base class for every crane-scheduling policy.

    A policy answers seven questions per tick; this class decides when each
    is asked and enforces the simulator contract around the answers, so a
    subclass can only change decisions, never the plumbing.
    
    Attributes:
        _tracker: enforces the simulator contract (unique positive ids,
            capacity, reservations, active-move re-inclusion, predecessor
            sync). It rejects an unsafe proposal rather than repairing it,
            which is why no scoring function can produce an invalid schedule.
    """

    _tracker: CustomMoveTracker

    def __init__(self) -> None:
        self._tracker = CustomMoveTracker()

    def plan(self, world: World) -> CraneSchedulingSolution | None:
        """One tick: phases A, B, C, D in order."""
        self._tracker.begin_tick(world)
        ctx = TickContext(world)
        self._propose_overrides(ctx)
        assignments = self._assign_and_order(ctx)
        return self._tracker.build_solution(
            assignments,
            custom_dispatch=self.custom_dispatch_order(ctx, self._tracker.tracked_moves()),
            custom_first=self.custom_first(ctx),
        )

    def pick_requests_to_override(self, ctx: TickContext) -> list[MoveRequest]:
        """Hook 1: choose which open requests this policy will place itself.

        Called once per tick, at the start of Phase B. Each returned
        request is then walked through `select_buffer` and
        `select_crane_for_override`; anything not returned is left for the
        simulator to route on its own.

        Args:
            ctx: this tick's read-only snapshot. `ctx.world.MoveRequests`
                holds every open request; `ctx.source_of(block_id)` gives
                the location a block currently sits on.

        Returns:
            The requests to place, in the order they should be attempted.
            Return `[]` to make this a dispatch-only policy, which turns
            Phase B into a no-op.

        Default:
            Requests the simulator has not yet routed (`TargetLocationId`
            unset) whose block is topmost on its stack, oldest id first.
            Both filters mirror simulator invariants: a custom move on a
            buried block is silently discarded, and hijacking an
            already-routed request fights the simulator's own plan.
        """
        return [
            req
            for req in sorted(ctx.world.MoveRequests, key=lambda r: r.Id)
            if req.TargetLocationId < 0 and _is_topmost(ctx, req.BlockId)
        ]

    def select_buffer(
        self,
        ctx: TickContext,
        req: MoveRequest,
        source_loc: Location,
        candidates: list[Location],
    ) -> Location | None:
        """Hook 2: pick the buffer a relocated block should be dropped on.

        Called once per request returned by `pick_requests_to_override`,
        after the framework has already filtered the buffers down to the
        legal ones. This is one of the three decisions worth learning.

        Args:
            ctx: this tick's read-only snapshot.
            req: the request being placed.
            source_loc: where the block sits right now.
            candidates: buffers that are already known to be legal targets,
                excluding the source itself, any location reserved by
                another move this tick, buffers at capacity, and buffers no
                crane can reach from `source_loc`.

        Returns:
            One buffer from `candidates`, or `None` to abandon this
            override (`select_crane_for_override` is then not called and
            the simulator keeps the request).

        Default:
            `None`, so a policy that does not override this places nothing.
        """
        return None

    def select_crane_for_override(
        self,
        ctx: TickContext,
        req: MoveRequest,
        source_loc: Location,
        target_buf: Location,
        eligible: list[Crane],
    ) -> int | None:
        """Hook 3: pick the crane that will carry out a placement.

        Called only when `select_buffer` chose a target, once per accepted
        request. Measurement showed no learnable signal here, so it is
        pinned to the default below.

        Args:
            ctx: this tick's read-only snapshot.
            req: the request being placed.
            source_loc: where the block sits right now.
            target_buf: the buffer chosen by `select_buffer`.
            eligible: cranes that can reach both `source_loc` and
                `target_buf`. May be empty when the two ends have no crane
                in common.

        Returns:
            The `Id` of a crane from `eligible`, or `None` to abandon this
            override. The proposal still has to pass the tracker's
            constraint checks afterwards, so returning an id is a request,
            not a guarantee.

        Default:
            The eligible crane closest to `source_loc`.
        """
        crane = argmin_or_none(
            eligible, key=lambda c: distance(c, source_loc.GirderPosition)
        )
        return crane.Id if crane is not None else None

    @abstractmethod
    def move_priority(self, ctx: TickContext, move: CraneMove) -> float:
        """Hook 4: score a simulator-issued move for ordering. Required.

        Called once per pending move per tick, in Phase C, and used purely
        as a sort key. One of the three decisions worth learning.

        Args:
            ctx: this tick's read-only snapshot.
            move: a move the simulator generated. `move.DueDate`,
                `move.ReleaseTime`, and the pickup/dropoff positions and
                location ids are the usual inputs.

        Returns:
            Any finite float; the smallest value is scheduled first. Ties
            keep the order the moves arrived in from the world message.
            Returning a non-finite value would corrupt the sort, so guard
            divisions.
        """

    @abstractmethod
    def select_crane_for_move(
        self,
        ctx: TickContext,
        move: CraneMove,
        eligible: list[Crane],
    ) -> int | None:
        """Hook 5: choose which crane executes a simulator-issued move. Required.

        Called once per pending move per tick, in Phase C, after ordering.
        Skipped when the move names a `RequiredCraneId` that can reach it,
        since the framework honours that itself. One of the three decisions
        worth learning.

        Args:
            ctx: this tick's read-only snapshot.
            move: the move being assigned.
            eligible: every crane whose travel range covers both the pickup
                and the dropoff. May be empty, in which case no crane can
                run this move at all.

        Returns:
            The `Id` of a crane from `eligible`, or `None` to leave the move
            unassigned this tick and let the simulator offer it again later.
        """

    def custom_dispatch_order(
        self, ctx: TickContext, tracked: list[tuple[CraneMove, int]],
    ) -> list[tuple[int, int]]:
        """Hook 6: order this policy's own moves inside the schedule.

        Called once per tick, in Phase D, after every override has been
        accepted or rejected. Only affects custom moves; the simulator's
        moves are ordered by `move_priority`. Measurement showed no
        learnable signal here, so it is pinned to the default below.

        Args:
            ctx: this tick's read-only snapshot.
            tracked: every live custom move paired with the crane assigned
                to it, sorted by move id.

        Returns:
            `(move_id, crane_id)` pairs in dispatch order. Moves left out
            are simply not dispatched this tick.

        Default:
            One move per crane in turn, so a long queue on one crane cannot
            starve the other.
        """
        per_crane: dict[int, list[int]] = {}
        for move, crane_id in tracked:
            per_crane.setdefault(crane_id, []).append(move.Id)
        order: list[tuple[int, int]] = []
        max_len = max((len(queue) for queue in per_crane.values()), default=0)
        for i in range(max_len):
            for crane_id, queue in per_crane.items():
                if i < len(queue):
                    order.append((queue[i], crane_id))
        return order

    def custom_first(self, ctx: TickContext) -> bool:
        """Hook 7: decide whether this policy's moves outrank the simulator's.

        Called once per tick, in Phase D, and flips the order of the two
        blocks of activities in the emitted schedule. Measurement showed no
        learnable signal here, so it is pinned to the default below.

        Args:
            ctx: this tick's read-only snapshot, for policies that want to
                switch on live state such as crane load.

        Returns:
            `True` to emit custom moves ahead of simulator moves, `False`
            to emit them after. Irrelevant when the policy has no custom
            moves in flight.

        Default:
            `True`.
        """
        return True

    def _propose_overrides(self, ctx: TickContext) -> None:
        """Phase B: walk override candidates, committing each before the next."""
        for req in self.pick_requests_to_override(ctx):
            if self._tracker.is_block_tracked(req.BlockId):
                continue
            source_loc = ctx.source_of(req.BlockId)
            if source_loc is None or not source_loc.Stack.BottomToTop:
                continue
            candidates = self._candidate_buffers(ctx, source_loc)
            target = self.select_buffer(ctx, req, source_loc, candidates)
            if target is None:
                continue
            eligible: list[Crane] = [
                c for c in ctx.world.Cranes
                if can_serve_positions(
                    c, source_loc.GirderPosition, target.GirderPosition,
                )
            ]
            crane_id = self.select_crane_for_override(
                ctx, req, source_loc, target, eligible,
            )
            if crane_id is None:
                continue
            self._tracker.try_add_upstream_buffer_move(
                ctx.world, req, source_loc, target, crane_id,
            )

    def _candidate_buffers(
        self, ctx: TickContext, source_loc: Location,
    ) -> list[Location]:
        """Buffers the strategy may pick from: constraint filter only.

        Drops the source itself, anything reserved by a tracked move,
        full buffers, and buffers no crane can reach from the source.
        """
        buf_used = self._tracker.buffer_loads(ctx.buffers)
        reserved = self._tracker.reserved_locations()
        return [
            loc
            for loc in ctx.buffers
            if loc.Id != source_loc.Id
            and loc.Id not in reserved
            and buf_used[loc.Id] < loc.MaxHeight
            and any(
                can_serve_positions(crane, source_loc.GirderPosition, loc.GirderPosition)
                for crane in ctx.world.Cranes
            )
        ]

    def _assign_and_order(self, ctx: TickContext) -> list[tuple[CraneMove, int]]:
        """Phase C: sort sim moves by `move_priority`, assign a crane each."""
        sim_moves: list[CraneMove] = [m for m in ctx.world.CraneMoves if m.Id < 0]
        sim_moves.sort(key=lambda m: self.move_priority(ctx, m))
        assignments: list[tuple[CraneMove, int]] = []
        for move in sim_moves:
            crane_id = self._select_crane_with_required(ctx, move)
            if crane_id is None:
                continue
            assignments.append((move, crane_id))
        return assignments

    def _select_crane_with_required(
        self, ctx: TickContext, move: CraneMove,
    ) -> int | None:
        """Honour the simulator's crane requirement, else ask hook 5.

        A move may name a crane it must run on; that wins whenever the crane
        can reach it, and only otherwise does the policy get to choose.
        """
        if move.RequiredCraneId > 0:
            required: Crane | None = next(
                (c for c in ctx.world.Cranes if c.Id == move.RequiredCraneId), None
            )
            if required is not None and can_serve(required, move):
                return required.Id
        eligible: list[Crane] = cranes_that_can_serve(ctx.world, move)
        return self.select_crane_for_move(ctx, move, eligible)

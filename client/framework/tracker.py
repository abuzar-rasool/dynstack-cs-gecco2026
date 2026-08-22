"""
Custom-move tracker: pure constraint enforcer for upstream-buffer overrides.

Owns the simulator contract: positive unique IDs, active-move protection
across ticks, predecessor sync against the live sim move, capacity and
reservation checks, and mixed custom/sim solution assembly with
consistent priorities across cranes.

It does not pick cranes or buffers. Strategies make those choices and
pass the result in through `try_add_upstream_buffer_move`; the tracker
rejects the call when a simulator constraint is violated, never on the
basis of policy.

Latent policy notice (T1): `begin_tick` overwrites every tracked move's
`ProtobufPredecessorIds` with the simulator's current list every tick.
Safe today because no strategy-facing API sets predecessors; if one
ever does, the overwrite will silently wipe it.
"""

from __future__ import annotations

from framework.base import LOC_TYPE_BUFFER
from models.cranescheduling_model_pb2 import (
    CraneMove,
    CraneScheduleActivity,
    CraneSchedulingSolution,
    Location,
    MoveRequest,
    PickupAndDropoff,
    World,
)


_STATE_ACTIVE = 2


class CustomMoveTracker:
    """Enforces the simulator contract for custom moves.

    Strategies decide which block goes where; this class decides whether
    the simulator will accept that decision. It rejects a proposal that
    would break an invariant rather than repairing it, so a policy can
    score badly but never emit an invalid schedule.

    Enforced per tick: unique positive move ids, stack capacity, one
    tracked move per location, no block in two moves at once, predecessor
    ids kept in sync with the simulator, and re-inclusion of moves already
    executing.
    """

    _next_id: int
    _tracked: dict[int, tuple[CraneMove, int]]
    _active_ids: set[int]

    def __init__(self) -> None:
        self._next_id = 1
        self._tracked = {}
        self._active_ids = set()

    def begin_tick(self, world: World) -> None:
        """Sync the tracker to the start-of-tick world.

        Two jobs: garbage-collect tracked moves the simulator has already
        completed, and overwrite each surviving move's
        `ProtobufPredecessorIds` with the simulator's current list: see
        T1 in the module docstring.
        """
        sim_moves_by_id: dict[int, CraneMove] = {
            move.Id: move for move in world.CraneMoves if move.Id > 0
        }
        alive_ids: set[int] = set(sim_moves_by_id)
        self._active_ids = {
            activity.MoveId
            for activity in (
                world.CraneSchedule.Activities if world.CraneSchedule else []
            )
            if activity.State == _STATE_ACTIVE
        }
        self._tracked = {
            move_id: entry
            for move_id, entry in self._tracked.items()
            if move_id in alive_ids
        }
        for move_id, (move, _) in self._tracked.items():
            del move.ProtobufPredecessorIds[:]
            sim_move = sim_moves_by_id[move_id]
            move.ProtobufPredecessorIds.extend(sim_move.ProtobufPredecessorIds)

    def is_block_tracked(
        self, block_id: int, source_loc_id: int | None = None,
    ) -> bool:
        """Whether a live custom move already carries this block.

        Pass `source_loc_id` to restrict the check to moves picking it up
        from that location.
        """
        return any(
            block_id in move.ProtobufMovedBlockIds
            and (source_loc_id is None or move.PickupLocationId == source_loc_id)
            for move, _ in self._tracked.values()
        )

    def reserved_locations(self) -> set[int]:
        """Locations already claimed this tick, as pickup or dropoff.

        A second move touching one of these would race the first, so
        candidate buffers exclude them.
        """
        return {
            loc_id
            for move, _ in self._tracked.values()
            for loc_id in (move.PickupLocationId, move.DropoffLocationId)
        }

    def buffer_loads(self, buffers: list[Location]) -> dict[int, int]:
        """Height of each buffer counting blocks already in flight to it.

        Without the in-flight count two proposals in one tick could both
        fit a buffer that only has room for one.
        """
        loads: dict[int, int] = {
            loc.Id: len(loc.Stack.BottomToTop) for loc in buffers
        }
        for move, _ in self._tracked.values():
            if move.DropoffLocationId in loads:
                loads[move.DropoffLocationId] += 1
        return loads

    def tracked_moves(self) -> list[tuple[CraneMove, int]]:
        """Live custom moves with their cranes, ordered by move id."""
        return [entry for _, entry in sorted(self._tracked.items())]

    def try_add_upstream_buffer_move(
        self,
        world: World,
        req: MoveRequest,
        source_loc: Location,
        target_buffer: Location,
        crane_id: int,
    ) -> bool:
        """Register a custom move for `req`, or reject on constraint failure.

        Returning False means the override would violate the sim contract
        or step on another tracked move. The structural filters
        (free-target, topmost-source) live in
        `Strategy.pick_requests_to_override`'s framework
        default, not here, because they mirror simulator-level
        invariants rather than tracker constraints.
        """
        if crane_id is None:
            return False
        if target_buffer.Type != LOC_TYPE_BUFFER:
            return False
        if not source_loc.Stack.BottomToTop:
            return False
        if self.is_block_tracked(req.BlockId, source_loc.Id):
            return False
        reserved = self.reserved_locations()
        if source_loc.Id in reserved or target_buffer.Id in reserved:
            return False
        if self.buffer_loads([target_buffer])[target_buffer.Id] >= target_buffer.MaxHeight:
            return False

        move = CraneMove()
        move.Id = self._next_id
        self._next_id += 1
        move.Type = PickupAndDropoff
        move.PickupLocationId = source_loc.Id
        move.PickupGirderPosition = source_loc.GirderPosition
        move.DropoffLocationId = target_buffer.Id
        move.DropoffGirderPosition = target_buffer.GirderPosition
        move.Amount = 1
        move.ProtobufMovedBlockIds.append(req.BlockId)

        self._tracked[move.Id] = (move, crane_id)
        return True

    def build_solution(
        self,
        generated_assignments: list[tuple[CraneMove, int]],
        custom_dispatch: list[tuple[int, int]],
        custom_first: bool,
    ) -> CraneSchedulingSolution | None:
        """Merge custom moves and sim assignments into one sim solution.

        Re-declares only custom moves the sim hasn't picked up yet, drops
        sim moves that would race a tracked one, and emits ordered
        activities. `custom_first` flips global ordering;
        `custom_dispatch` carries the per-crane sequence.
        """
        solution = CraneSchedulingSolution()

        custom_moves: list[CraneMove] = [
            move for move_id, (move, _) in sorted(self._tracked.items())
            if move_id not in self._active_ids
        ]
        solution.CustomMoves.extend(custom_moves)

        custom_blocks: set[int] = {
            block_id
            for move, _ in self._tracked.values()
            for block_id in move.ProtobufMovedBlockIds
        }
        reserved = self.reserved_locations()
        sim_assignments: list[tuple[CraneMove, int]] = [
            (move, crane_id)
            for move, crane_id in generated_assignments
            if not any(block_id in custom_blocks for block_id in move.ProtobufMovedBlockIds)
            and move.PickupLocationId not in reserved
            and move.DropoffLocationId not in reserved
        ]

        priority = 0
        emitters = (
            (self._emit_custom_activities, self._emit_sim_activities)
            if custom_first
            else (self._emit_sim_activities, self._emit_custom_activities)
        )
        for emit in emitters:
            priority = emit(solution, custom_dispatch, sim_assignments, priority)

        if not solution.CustomMoves and not solution.Schedule.Activities:
            return None
        return solution

    def _emit_custom_activities(
        self,
        solution: CraneSchedulingSolution,
        custom_dispatch: list[tuple[int, int]],
        _sim_assignments: list[tuple[CraneMove, int]],
        priority: int,
    ) -> int:
        """Append custom-move activities in hook-6 order, skipping active ones.

        Returns the next free priority number.
        """
        for move_id, crane_id in custom_dispatch:
            if move_id in self._active_ids:
                continue
            activity = CraneScheduleActivity()
            activity.MoveId = move_id
            activity.CraneId = crane_id
            activity.Priority = priority
            solution.Schedule.Activities.append(activity)
            priority += 1
        return priority

    def _emit_sim_activities(
        self,
        solution: CraneSchedulingSolution,
        _custom_dispatch: list[tuple[int, int]],
        sim_assignments: list[tuple[CraneMove, int]],
        priority: int,
    ) -> int:
        """Append the simulator's own moves in hook-4 order.

        Returns the next free priority number.
        """
        for move, crane_id in sim_assignments:
            activity = CraneScheduleActivity()
            activity.MoveId = move.Id
            activity.CraneId = crane_id
            activity.Priority = priority
            solution.Schedule.Activities.append(activity)
            priority += 1
        return priority

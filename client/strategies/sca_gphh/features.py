"""Feature extraction for the three learned hooks.

DispatchFeatures covers hooks 4 and 5 (built once per tick from the world),
PlacementFeatures covers hook 2 (built once per tick before Phase B). The
tuples line up with primitives.FEATURES_4/5/2, in that order.
"""
from __future__ import annotations

import math

from framework.base import (
    LOC_TYPE_ARRIVAL,
    LOC_TYPE_HANDOVER,
    can_serve,
    can_serve_positions,
)
from models.cranescheduling_model_pb2 import Crane, CraneMove, Location, World


def finite(value: float) -> float:
    return value if math.isfinite(value) else 1e9


def interleave_by_crane(
    assignments: list[tuple[CraneMove, int]],
) -> list[tuple[CraneMove, int]]:
    per_crane: dict[int, list[tuple[CraneMove, int]]] = {}
    for move, crane_id in assignments:
        per_crane.setdefault(crane_id, []).append((move, crane_id))
    out: list[tuple[CraneMove, int]] = []
    max_len = max((len(q) for q in per_crane.values()), default=0)
    for i in range(max_len):
        for queue in per_crane.values():
            if i < len(queue):
                out.append(queue[i])
    return out


class DispatchFeatures:

    def __init__(self, world: World) -> None:
        self.cranes = list(world.Cranes)
        self._loc_by_id = {loc.Id: loc for loc in world.Locations}
        self._alive_ids = {m.Id for m in world.CraneMoves}
        self._succ: dict[int, int] = {}
        for m in world.CraneMoves:
            for pred in m.ProtobufPredecessorIds:
                self._succ[pred] = self._succ.get(pred, 0) + 1
        self._n_sim = sum(1 for m in world.CraneMoves if m.Id < 0)
        self._now_ms = world.Now.MilliSeconds
        self._width = world.Width if world.Width > 0 else 1.0
        self._crane_load: dict[int, int] = {}

    def note_assignment(self, crane_id: int) -> None:
        self._crane_load[crane_id] = self._crane_load.get(crane_id, 0) + 1

    def is_ready(self, move: CraneMove) -> bool:
        if any(pred in self._alive_ids for pred in move.ProtobufPredecessorIds):
            return False
        src = self._loc_by_id.get(move.PickupLocationId)
        if src is None or not src.Stack.BottomToTop:
            return True
        moved = set(move.ProtobufMovedBlockIds)
        if not moved:
            return True
        return src.Stack.BottomToTop[-1].Id in moved

    def move_feats(self, move: CraneMove) -> tuple[float, ...]:
        w = self._width
        dropoff_loc = self._loc_by_id.get(move.DropoffLocationId)
        pickup_loc = self._loc_by_id.get(move.PickupLocationId)
        is_downstream = (
            1.0 if dropoff_loc is not None and dropoff_loc.Type == LOC_TYPE_HANDOVER else 0.0
        )
        is_upstream = (
            1.0 if pickup_loc is not None and pickup_loc.Type == LOC_TYPE_ARRIVAL else 0.0
        )
        blocks_above = 0.0
        if pickup_loc is not None and pickup_loc.Stack.BottomToTop and move.ProtobufMovedBlockIds:
            moved = set(move.ProtobufMovedBlockIds)
            idxs = [i for i, b in enumerate(pickup_loc.Stack.BottomToTop) if b.Id in moved]
            if idxs:
                blocks_above = float(len(pickup_loc.Stack.BottomToTop) - 1 - max(idxs))
        successor_count = float(self._succ.get(move.Id, 0))
        move_age = max(0.0, (self._now_ms - move.ReleaseTime.MilliSeconds) / 1000.0 / 3600.0)
        pd_dist = abs(move.PickupGirderPosition - move.DropoffGirderPosition) / w
        reachable = [c for c in self.cranes if can_serve(c, move)] or self.cranes
        nearest_crane_dist = min(
            (abs(c.GirderPosition - move.PickupGirderPosition) for c in reachable),
            default=0.0,
        ) / w
        total_moves = self._n_sim / 10.0
        return (
            is_downstream,
            is_upstream,
            blocks_above,
            successor_count,
            move_age,
            pd_dist,
            nearest_crane_dist,
            total_moves,
        )

    def crane_feats(self, move: CraneMove, crane: Crane) -> tuple[float, ...]:
        w = self._width
        dist_pickup = abs(crane.GirderPosition - move.PickupGirderPosition) / w
        dist_dropoff = abs(crane.GirderPosition - move.DropoffGirderPosition) / w
        crane_pos_norm = crane.GirderPosition / w
        crane_load = float(self._crane_load.get(crane.Id, 0))
        range_headroom = min(
            move.PickupGirderPosition - crane.MinPosition,
            crane.MaxPosition - move.PickupGirderPosition,
        ) / w
        others = [c for c in self.cranes if c.Id != crane.Id]
        gap_to_other = min(
            (abs(move.DropoffGirderPosition - o.GirderPosition) for o in others),
            default=0.0,
        ) / w
        return (
            dist_pickup,
            dist_dropoff,
            crane_pos_norm,
            crane_load,
            range_headroom,
            gap_to_other,
        )


class PlacementFeatures:

    def __init__(self, world: World) -> None:
        self._width = world.Width if world.Width > 0 else 1.0
        self._cranes = list(world.Cranes)
        self._handover_pos = [
            loc.GirderPosition
            for loc in world.Locations
            if loc.Type == LOC_TYPE_HANDOVER
        ]
        block_loc: dict[int, int] = {}
        for loc in world.Locations:
            for block in loc.Stack.BottomToTop:
                block_loc[block.Id] = loc.Id
        self._req_count_by_loc: dict[int, int] = {}
        for req in world.MoveRequests:
            loc_id = block_loc.get(req.BlockId)
            if loc_id is not None:
                self._req_count_by_loc[loc_id] = self._req_count_by_loc.get(loc_id, 0) + 1

    def buffer_feats(
        self, source_loc: Location, buf: Location, load: int,
    ) -> tuple[float, ...]:
        w = self._width
        dist_source = abs(buf.GirderPosition - source_loc.GirderPosition) / w
        dist_handover = (
            min(abs(buf.GirderPosition - h) for h in self._handover_pos) / w
            if self._handover_pos
            else 0.0
        )
        cap = buf.MaxHeight if buf.MaxHeight > 0 else 1
        buf_free = (cap - load) / cap
        is_empty = 1.0 if load == 0 else 0.0
        blocks_requested_in_buf = float(self._req_count_by_loc.get(buf.Id, 0))
        reach_count = float(
            sum(
                1
                for c in self._cranes
                if can_serve_positions(
                    c, source_loc.GirderPosition, buf.GirderPosition,
                )
            )
        )
        return (
            dist_source,
            dist_handover,
            buf_free,
            is_empty,
            blocks_requested_in_buf,
            reach_count,
        )

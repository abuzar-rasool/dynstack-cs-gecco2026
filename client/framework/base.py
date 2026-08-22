"""Geometry helpers and location-type constants shared by every strategy.

A crane spans a fixed girder range, so reachability is a range check;
these helpers wrap it so strategies never test positions by hand.
"""
from __future__ import annotations

from models.cranescheduling_model_pb2 import Crane, CraneMove, World


LOC_TYPE_ARRIVAL = 0
LOC_TYPE_BUFFER = 1
LOC_TYPE_HANDOVER = 2


def crane_can_reach(crane: Crane, girder_position: float) -> bool:
    """Whether `girder_position` lies inside the crane's travel range."""
    return crane.MinPosition <= girder_position <= crane.MaxPosition


def can_serve_positions(
    crane: Crane, pickup_pos: float, dropoff_pos: float,
) -> bool:
    """Whether one crane can reach both ends of a move."""
    return crane_can_reach(crane, pickup_pos) and crane_can_reach(crane, dropoff_pos)


def can_serve(crane: Crane, move: CraneMove) -> bool:
    """Whether the crane can reach both ends of `move`."""
    return can_serve_positions(
        crane, move.PickupGirderPosition, move.DropoffGirderPosition,
    )


def cranes_that_can_serve(world: World, move: CraneMove) -> list[Crane]:
    """Every crane in the world that could execute `move`."""
    return [c for c in world.Cranes if can_serve(c, move)]


def distance(crane: Crane, position: float) -> float:
    """Girder distance the crane would travel to reach `position`."""
    return abs(crane.GirderPosition - position)

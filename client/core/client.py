from __future__ import annotations

import os

import zmq

from models.cranescheduling_model_pb2 import World
from framework.generic import Strategy

_INITIAL_TIMEOUT_MS = 20_000
_STEADY_TIMEOUT_MS  = 3_000

_QUIET = bool(os.environ.get("DYNSTACK_QUIET"))


class DynStackClient:

    def __init__(self, address: str, simulation_id: str, strategy: Strategy):
        self.address = address
        self.simulation_id = simulation_id
        self.strategy = strategy

        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.DEALER)
        self._socket.setsockopt_string(zmq.IDENTITY, simulation_id)
        self._socket.setsockopt(zmq.RCVTIMEO, _INITIAL_TIMEOUT_MS)

        self._schedule_nr = 0
        self._last_world: World | None = None
        self._got_first_tick = False

    def connect(self) -> None:
        self._socket.connect(self.address)
        print(f"[client] Connected to {self.address} as simulation '{self.simulation_id}'")

    def run(self) -> None:
        print(f"[client] Running with strategy: {self.strategy.__class__.__name__}")
        try:
            while self._step():
                pass
        except KeyboardInterrupt:
            print("\n[client] Interrupted by user.")
        finally:
            if self._last_world is not None:
                self._print_results(self._last_world)
            self.close()

    def _step(self) -> bool:
        try:
            msg = self._socket.recv_multipart()
        except zmq.Again:
            print("\n[client] No message received: simulation run complete.")
            return False

        if len(msg) >= 2 and msg[1] == b"done":
            print("\n[client] Received 'done': simulation run complete.")
            return False

        if not self._got_first_tick:
            self._socket.setsockopt(zmq.RCVTIMEO, _STEADY_TIMEOUT_MS)
            self._got_first_tick = True

        if len(msg) < 3 or not msg[2]:
            self._socket.send_multipart([b"", b"crane", b""])
            return True

        world = World()
        world.ParseFromString(msg[2])
        self._last_world = world

        solution = self.strategy.plan(world)
        if solution is None:
            self._socket.send_multipart([b"", b"crane", b""])
            return True

        self._schedule_nr += 1
        solution.Schedule.ScheduleNr = self._schedule_nr
        self._socket.send_multipart([b"", b"crane", solution.SerializeToString()])
        if not _QUIET:
            print(
                f"[client] schedule #{self._schedule_nr:>4} | "
                f"moves={len(solution.Schedule.Activities):>2} | "
                f"t={world.Now.MilliSeconds / 1000:>7.1f}s"
            )
        return True

    def _print_results(self, world: World) -> None:
        kpi = world.KPIs
        sim_minutes = world.Now.MilliSeconds / 60_000
        total_ticks = round(world.Now.MilliSeconds / 1000)
        handled = kpi.UpstreamBlocks + kpi.DownstreamBlocks
        perfect = "OK" if kpi.DeliveryErrors == 0 else "FIX THIS FIRST"

        print()
        print("=" * 52)
        print("  SIMULATION RESULTS")
        print("=" * 52)
        print(
            f"  Sim time          : {sim_minutes:.1f} min  "
            f"({total_ticks} ticks, {self._schedule_nr} schedules sent)"
        )
        print(f"  Strategy          : {self.strategy.__class__.__name__}")
        print()
        print("  ── COMPETITION OBJECTIVES (lexicographic) ──")
        print(f"  [1] Delivery Errors       : {kpi.DeliveryErrors:>6}   {perfect}")
        print(f"  [2] Handled Blocks        : {handled:>6}   (higher is better)")
        print(f"  [3] Max Parking Duration  : {kpi.MaxParkingDuration:>9.1f}s  (lower is better)")
        print()
        print("  ── ADDITIONAL KPIs ──")
        print(f"  Crane Manipulations       : {kpi.CraneManipulations:>6}")
        print(f"  Total Girder Distance     : {kpi.TotalGirderDistance:>9.1f}")
        print(f"  Total Hoist Distance      : {kpi.TotalHoistDistance:>9.1f}")
        print(f"  Serviced Upstream Vehicles: {kpi.ServicedUpstreamVehicles:>6}")
        print(f"  Serviced Downstream Veh.  : {kpi.ServicedDownstreamVehicles:>6}")
        print(f"  Upstream Parking Time     : {kpi.UpstreamParkingTime:>9.1f}s")
        print(f"  Downstream Parking Time   : {kpi.DownstreamParkingTime:>9.1f}s")
        print()
        serviced = kpi.ServicedUpstreamVehicles + kpi.ServicedDownstreamVehicles
        parked = kpi.ParkingUpstreamVehicles + kpi.ParkingDownstreamVehicles
        mean_service = (kpi.UpstreamServiceTime + kpi.DownstreamServiceTime) / serviced if serviced else 0.0
        mean_parking = (kpi.UpstreamParkingTime + kpi.DownstreamParkingTime) / parked if parked else 0.0
        print("  ── COMPETITION SCOREBOARD ROW ──")
        print(
            f"  Errors={kpi.DeliveryErrors} Blocks={handled} "
            f"MaxParking={kpi.MaxParkingDuration:.2f} MeanService={mean_service:.2f} "
            f"MeanParking={mean_parking:.2f} Moves={kpi.CraneManipulations} "
            f"Distance={kpi.TotalGirderDistance:.2f}"
        )
        print("=" * 52)

    def close(self) -> None:
        self._socket.close()
        self._context.term()
        print("[client] Socket closed.")

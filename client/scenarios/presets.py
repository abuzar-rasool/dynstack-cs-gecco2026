"""
Crane Scheduling scenarios, defined in Python.

Each preset is a zero-arg function returning a `Settings` protobuf that
the C# server can deserialise via `--settings /path/to/file.buf`. The
server has no special knowledge of these names: every preset is just a
serialised `Settings` payload.

Presets describe structural variation only (arrival rate, vehicle size,
buffer fill, layout topology). The RNG `Seed` is an evaluation-time
parameter, not a separate scenario: the eval harness overrides it per
run, which is how one preset yields many paired instances.

The evaluation matrix has two layers:

  TRAIN (12 presets)
    Systematic single-axis variations across {topology, load, buffer
    fill, structure}. These are synthetic, designed for maximum coverage
    of the strategy-relevant parameter space. Fair game for optimisers.

  HELD_OUT (3 presets)
    Real competition instances, reconstructed from runtime observations.
    Lane positions and buffer fill are exact; demand parameters are
    rounded estimates (N~24 events, so expect ±15% noise on means).
    Never used during strategy development: reserved for final
    generalisation claims.

To add a preset: register it in `PRESETS` and drop the name into either
`TRAIN_PRESETS` or `HELD_OUT_PRESETS`: the assert at the bottom enforces
exact coverage.
"""
from __future__ import annotations
from collections.abc import Callable

from scenarios.settings_pb2 import Settings, TimeSpan


def _ms(value: int) -> TimeSpan:
    return TimeSpan(value=value, scale=TimeSpan.Scale.MILLISECONDS)

def hours(h: float)   -> TimeSpan: return _ms(int(h * 3_600_000))
def minutes(m: float) -> TimeSpan: return _ms(int(m * 60_000))
def seconds(s: float) -> TimeSpan: return _ms(int(s * 1_000))


def default() -> Settings:
    """The DynStack CS Default scenario (matches the upstream C# template)."""
    return Settings(
        Seed=40,
        SimulationDuration=hours(1.0),
        Height=8,
        Width=400.0,
        MaxHeightForArrival=5,
        MaxHeightForBuffer=5,
        MaxHeightForHandover=5,
        ArrivalStackPositions=[40.0, 50.0, 60.0, 240.0, 250.0, 260.0],
        BufferStackPositions=[float(x) for x in range(0, 401)],
        HandoverStackPositions=[140.0, 150.0, 160.0, 340.0, 350.0, 360.0],
        BlockClasses=1,
        BufferStackClasses=[1] * 401,
        SafetyDistance=15.0,
        CraneMoveTimeMean=seconds(20),
        CraneMoveTimeStd=seconds(20 * 0.1),
        HoistMoveTimeMean=seconds(5),
        HoistMoveTimeStd=seconds(5 * 0.1),
        CraneManipulationTimeMean=seconds(3),
        CraneManipulationTimeStd=seconds(3 * 0.1),
        ArrivalTimeMean=minutes(2),
        ArrivalTimeStd=minutes(2 * 0.2),
        ArrivalCountMean=3.0,
        ArrivalCountStd=0.75,
        ArrivalServiceTimeMean=seconds(10),
        ArrivalServiceTimeStd=seconds(10 * 0.2),
        HandoverTimeMean=minutes(2),
        HandoverTimeStd=minutes(2 * 0.2),
        HandoverCountMean=3.0,
        HandoverCountStd=0.75,
        HandoverServiceTimeMean=seconds(10),
        HandoverServiceTimeStd=seconds(10 * 0.2),
        InitialBufferUtilization=0.25,
    )


_UNIFORM_ARRIVAL_POSITIONS:  list[float] = [33.0, 100.0, 167.0, 233.0, 300.0, 367.0]
_UNIFORM_HANDOVER_POSITIONS: list[float] = [37.0, 104.0, 171.0, 237.0, 304.0, 371.0]


def default_uniform_interleaved() -> Settings:
    """Default load on the uniform-interleaved layout. Same demand
    parameters as `default`, radically different spatial arrangement."""
    s = default()
    s.Seed = 41
    s.ArrivalStackPositions[:]  = _UNIFORM_ARRIVAL_POSITIONS
    s.HandoverStackPositions[:] = _UNIFORM_HANDOVER_POSITIONS
    return s


def busy() -> Settings:
    """High load on clustered topology (arrivals every 80 s)."""
    s = default()
    s.Seed = 55
    s.ArrivalTimeMean.CopyFrom(seconds(80))
    s.ArrivalTimeStd.CopyFrom(seconds(80 * 0.2))
    s.HandoverTimeMean.CopyFrom(seconds(80))
    s.HandoverTimeStd.CopyFrom(seconds(80 * 0.2))
    return s


def busy_uniform_interleaved() -> Settings:
    """High load on uniform-interleaved topology. Arrival rate is 4×
    faster than `busy` because per-transfer distance is ~4× shorter."""
    s = default_uniform_interleaved()
    s.Seed = 56
    s.ArrivalTimeMean.CopyFrom(seconds(30))
    s.ArrivalTimeStd.CopyFrom(seconds(30 * 0.2))
    s.HandoverTimeMean.CopyFrom(seconds(30))
    s.HandoverTimeStd.CopyFrom(seconds(30 * 0.2))
    return s


def quiet() -> Settings:
    """Low load on clustered topology (arrivals every 3 min)."""
    s = default()
    s.Seed = 66
    s.ArrivalTimeMean.CopyFrom(minutes(3))
    s.ArrivalTimeStd.CopyFrom(minutes(3 * 0.2))
    s.HandoverTimeMean.CopyFrom(minutes(3))
    s.HandoverTimeStd.CopyFrom(minutes(3 * 0.2))
    return s


def quiet_uniform_interleaved() -> Settings:
    """Low load on uniform-interleaved topology."""
    s = default_uniform_interleaved()
    s.Seed = 67
    s.ArrivalTimeMean.CopyFrom(minutes(3))
    s.ArrivalTimeStd.CopyFrom(minutes(3 * 0.2))
    s.HandoverTimeMean.CopyFrom(minutes(3))
    s.HandoverTimeStd.CopyFrom(minutes(3 * 0.2))
    return s


def empty_buffer() -> Settings:
    """Buffers start ~empty (5% fill): cold-start regime."""
    s = default()
    s.Seed = 99
    s.InitialBufferUtilization = 0.05
    return s


def high_buffer() -> Settings:
    """Buffers start 50% full: initial congestion, clustered topology."""
    s = default()
    s.Seed = 88
    s.InitialBufferUtilization = 0.50
    return s


def high_buffer_uniform_interleaved() -> Settings:
    """Buffers start 50% full: initial congestion, uniform topology."""
    s = default_uniform_interleaved()
    s.Seed = 89
    s.InitialBufferUtilization = 0.50
    return s


def saturation() -> Settings:
    """Asymmetric loading: arrivals every 50 s vs default 2 min handovers.
    Inflow~2.4× outflow: buffer fills, parking explodes."""
    s = default()
    s.Seed = 600
    s.ArrivalTimeMean.CopyFrom(seconds(50))
    s.ArrivalTimeStd.CopyFrom(seconds(50 * 0.2))
    return s


def large_vehicle() -> Settings:
    """Downstream vehicles take 5 blocks each (vs 3)."""
    s = default()
    s.Seed = 77
    s.HandoverCountMean = 5.0
    s.HandoverCountStd = 1.0
    s.MaxHeightForHandover = 6
    return s


def shallow_stacks() -> Settings:
    """Stacks half as deep (Height=4, MaxHeight*=3): tighter routing."""
    s = default()
    s.Seed = 601
    s.Height = 4
    s.MaxHeightForArrival  = 3
    s.MaxHeightForBuffer   = 3
    s.MaxHeightForHandover = 3
    return s


def comp_scenario_1() -> Settings:
    """Competition scenario_1: clustered topology, both arrival and
    handover lanes saturated, buffer fill~default."""
    s = default()
    s.Seed = 800
    s.ArrivalTimeMean.CopyFrom(seconds(127))
    s.ArrivalTimeStd.CopyFrom(seconds(round(127 * 0.2)))
    s.HandoverTimeMean.CopyFrom(seconds(131))
    s.HandoverTimeStd.CopyFrom(seconds(round(131 * 0.2)))
    s.InitialBufferUtilization = 0.256
    return s


def comp_scenario_2() -> Settings:
    """Competition scenario_2: uniform-interleaved topology (57 m
    spacing, 4 m arrival-to-handover gap), neither lane type saturated, low buffer."""
    s = default()
    s.Seed = 801
    s.ArrivalStackPositions[:]  = [55.0, 112.0, 169.0, 226.0, 283.0, 340.0]
    s.HandoverStackPositions[:] = [59.0, 116.0, 173.0, 230.0, 287.0, 344.0]
    s.ArrivalTimeMean.CopyFrom(seconds(121))
    s.ArrivalTimeStd.CopyFrom(seconds(round(121 * 0.2)))
    s.HandoverTimeMean.CopyFrom(seconds(126))
    s.HandoverTimeStd.CopyFrom(seconds(round(126 * 0.2)))
    s.InitialBufferUtilization = 0.237
    return s


def comp_scenario_3() -> Settings:
    """Competition scenario_3: uniform-interleaved topology (57 m
    spacing, 10 m arrival-to-handover gap), arrivals saturated / handovers not,
    higher buffer fill."""
    s = default()
    s.Seed = 802
    s.ArrivalStackPositions[:]  = [52.0, 109.0, 166.0, 233.0, 290.0, 347.0]
    s.HandoverStackPositions[:] = [62.0, 119.0, 176.0, 223.0, 280.0, 337.0]
    s.ArrivalTimeMean.CopyFrom(seconds(124))
    s.ArrivalTimeStd.CopyFrom(seconds(round(124 * 0.2)))
    s.HandoverTimeMean.CopyFrom(seconds(140))
    s.HandoverTimeStd.CopyFrom(seconds(round(140 * 0.2)))
    s.InitialBufferUtilization = 0.340
    return s


PRESETS: dict[str, Callable[[], Settings]] = {
    "default":                        default,
    "default_uniform_interleaved":    default_uniform_interleaved,
    "busy":                           busy,
    "busy_uniform_interleaved":       busy_uniform_interleaved,
    "quiet":                          quiet,
    "quiet_uniform_interleaved":      quiet_uniform_interleaved,
    "empty_buffer":                   empty_buffer,
    "high_buffer":                    high_buffer,
    "high_buffer_uniform_interleaved": high_buffer_uniform_interleaved,
    "saturation":                     saturation,
    "large_vehicle":                  large_vehicle,
    "shallow_stacks":                 shallow_stacks,
    "comp_scenario_1":                comp_scenario_1,
    "comp_scenario_2":                comp_scenario_2,
    "comp_scenario_3":                comp_scenario_3,
}

TRAIN_PRESETS: set[str] = {
    "default",
    "default_uniform_interleaved",
    "busy",
    "busy_uniform_interleaved",
    "quiet",
    "quiet_uniform_interleaved",
    "empty_buffer",
    "high_buffer",
    "high_buffer_uniform_interleaved",
    "saturation",
    "large_vehicle",
    "shallow_stacks",
}

HELD_OUT_PRESETS: set[str] = {
    "comp_scenario_1",
    "comp_scenario_2",
    "comp_scenario_3",
}

assert TRAIN_PRESETS.isdisjoint(HELD_OUT_PRESETS), "train/held_out overlap"
assert TRAIN_PRESETS | HELD_OUT_PRESETS == set(PRESETS), \
    "every preset must be in exactly one of TRAIN_PRESETS / HELD_OUT_PRESETS"

from __future__ import annotations

import argparse
import ast
import sys

from core.client import DynStackClient
from strategies.cmaes.cmaes_champion import CmaesChampion
from strategies.cmaes.weight_policy import WeightVectorPolicy
from strategies.nearest_crane import NearestCraneBaseline
from strategies.pham_rule_based import PhamRuleBased
from strategies.sca_gphh.champions import (
    ScaGphhStageA,
    ScaGphhStageB,
    ScaGphhStageC,
    ScaGphhStageD,
    ScaGphhStageE,
)
from strategies.sca_gphh.stage_a import GPStageA
from strategies.sca_gphh.stage_b import GPStageB
from strategies.sca_gphh.stage_c import GPStageC
from strategies.sca_gphh.stage_d import GPStageD
from strategies.sca_gphh.stage_e import GPStageE


STRATEGIES = {
    "nearest_crane": NearestCraneBaseline,
    "pham_rule_based": PhamRuleBased,
    "sca_gphh_stage_a": ScaGphhStageA,
    "sca_gphh_stage_b": ScaGphhStageB,
    "sca_gphh_stage_c": ScaGphhStageC,
    "sca_gphh_stage_d": ScaGphhStageD,
    "sca_gphh_stage_e": ScaGphhStageE,
    "cmaes_champion": CmaesChampion,
    "gp_stage_a": GPStageA,
    "gp_stage_b": GPStageB,
    "gp_stage_c": GPStageC,
    "gp_stage_d": GPStageD,
    "gp_stage_e": GPStageE,
    "cmaes_weights": WeightVectorPolicy,
}

TRAINING_BASES = frozenset({
    "gp_stage_a",
    "gp_stage_b",
    "gp_stage_c",
    "gp_stage_d",
    "gp_stage_e",
    "cmaes_weights",
})

DEFAULT_SIM_ID = "658f9b28-6686-40d2-8800-611bd8466215"

SERVER_PRESETS: list[tuple[str, str, bool]] = [
    ("Local sync", "tcp://127.0.0.1:2222", True),
    ("Local async", "tcp://127.0.0.1:8080", True),
    ("Competition", "tcp://dynstack.adaptop.at:8080", False),
]


def _coerce(raw: str) -> object:
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw


def _parse_params(items: list[str]) -> dict[str, object]:
    params: dict[str, object] = {}
    for item in items:
        key, sep, raw = item.partition("=")
        if not sep or not key.strip():
            raise SystemExit(f"--param expects KEY=VALUE, got {item!r}")
        params[key.strip()] = _coerce(raw.strip())
    return params


def _menu(label: str, options: list[str], default_idx: int) -> int:
    print(f"{label}:", file=sys.stderr)
    for i, opt in enumerate(options, start=1):
        marker = "  (default)" if i - 1 == default_idx else ""
        print(f"  {i}) {opt}{marker}", file=sys.stderr)
    raw = input(f"Select [{default_idx + 1}]: ").strip()
    if not raw:
        return default_idx
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return int(raw) - 1
    if raw in options:
        return options.index(raw)
    print(f"  invalid choice {raw!r}; using default", file=sys.stderr)
    return default_idx


def _pick_server() -> tuple[str, bool]:
    labels = [f"{name:<13} {url}" for name, url, _ in SERVER_PRESETS] + ["Custom URL"]
    idx = _menu("Server", labels, default_idx=0)
    if idx < len(SERVER_PRESETS):
        _, url, is_local = SERVER_PRESETS[idx]
        return url, is_local
    url = input("Server URL: ").strip()
    if not url:
        print("  empty URL; aborting", file=sys.stderr)
        sys.exit(1)
    return url, False


def _pick_strategy() -> str:
    names = [n for n in STRATEGIES if n not in TRAINING_BASES]
    return names[_menu("Strategy", names, default_idx=0)]


def main() -> None:
    parser = argparse.ArgumentParser(prog="dynstack-client")
    parser.add_argument(
        "address", nargs="?", help="ZMQ server address, e.g. tcp://127.0.0.1:2222"
    )
    parser.add_argument("simulation_id", nargs="?", help="Simulation UUID")
    parser.add_argument("--strategy", choices=list(STRATEGIES))
    parser.add_argument(
        "-p",
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Strategy constructor parameter; repeatable",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Menu-driven picker for server and strategy",
    )
    args = parser.parse_args()
    params = _parse_params(args.param)

    if args.interactive:
        address, is_local = _pick_server()
        sim_id = DEFAULT_SIM_ID if is_local else input(
            f"Simulation ID [{DEFAULT_SIM_ID}]: "
        ).strip() or DEFAULT_SIM_ID
        strategy_name = _pick_strategy()
    else:
        if not (args.address and args.simulation_id and args.strategy):
            parser.error(
                "address, simulation_id, and --strategy are required unless --interactive"
            )
        address = args.address
        sim_id = args.simulation_id
        strategy_name = args.strategy

    param_note = f" {params}" if params else ""
    print(f"\n{strategy_name}{param_note} @ {address} (sim={sim_id})\n", file=sys.stderr)
    try:
        strategy = STRATEGIES[strategy_name](**params)
    except TypeError as exc:
        parser.error(f"strategy {strategy_name!r} rejected parameters {params!r}: {exc}")
    client = DynStackClient(address, sim_id, strategy)
    client.connect()
    client.run()


if __name__ == "__main__":
    main()

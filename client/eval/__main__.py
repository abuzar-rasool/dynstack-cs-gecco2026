"""
Every strategy runs the same seed list per scenario (10 by default), so the
comparison is paired and ranking on the per-scenario mean is stable. Writes
results/<strategy>.json and a rebuilt summary.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from main import STRATEGIES, TRAINING_BASES
from scenarios.presets import HELD_OUT_PRESETS, PRESETS, TRAIN_PRESETS
from eval import runner
from eval.runner import RunResult
from eval.scoring import ScenarioAgg, aggregate, compute_ranks
from eval.store import rebuild_summary, save_run


EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"
SUMMARY = EVAL_DIR / "summary.json"
DEFAULT_SEEDS = 10


def _derive_seeds(scenario: str, n: int) -> list[int | None]:
    anchor = PRESETS[scenario]().Seed
    if n <= 1:
        return [anchor]
    rng = random.Random(f"{anchor}:{scenario}")
    seeds: list[int | None] = [anchor]
    while len(seeds) < n:
        candidate = rng.randrange(1_000_000)
        if candidate not in seeds:
            seeds.append(candidate)
    return seeds


def _print_per_run_table(
    aggs: dict[str, dict[str, ScenarioAgg]],
    ranks: dict[str, dict],
) -> None:
    print()
    header = (
        f"{'SCENARIO':<24}{'STRATEGY':<22}{'N':>3}"
        f"{'ERR':>5}{'BLOCKS':>20}{'PARKING':>11}{'RANK':>7}  SET"
    )
    print(header)
    print("-" * len(header))
    scenarios = sorted({sc for runs in aggs.values() for sc in runs})
    for scenario in scenarios:
        scenario_set = "train" if scenario in TRAIN_PRESETS else "held_out"
        for strategy in sorted(aggs):
            if scenario not in aggs[strategy]:
                continue
            a = aggs[strategy][scenario]
            rank = ranks[strategy]["per_scenario_ranks"].get(scenario)
            rank_str = f"{rank:.1f}" if rank is not None else "-"
            if a.errors < 0:
                err, blk = "n/a", "n/a"
            else:
                err = str(a.errors)
                blk = f"{a.mean_blocks:g} +/- {a.std_blocks:g}"
            park = f"{a.mean_parking:.1f}" if a.mean_parking != float("inf") else "n/a"
            print(
                f"{scenario:<24}{strategy:<22}{a.n_seeds:>3}"
                f"{err:>5}{blk:>20}{park:>11}{rank_str:>7}  {scenario_set}"
            )
    print("-" * len(header))


def _print_aggregate(ranks: dict[str, dict]) -> None:
    header = f"{'STRATEGY':<22}{'TRAIN_RANK':>12}{'HELD_OUT_RANK':>16}"
    print(header)
    print("-" * len(header))
    for strategy in sorted(ranks):
        a = ranks[strategy]
        train = f"{a['train_avg_rank']:.2f}" if a["train_avg_rank"] is not None else "-"
        held = f"{a['held_out_avg_rank']:.2f}" if a["held_out_avg_rank"] is not None else "-"
        print(f"{strategy:<22}{train:>12}{held:>16}")
    print()


def _cache_age(last_run_iso: str) -> str:
    last = datetime.strptime(last_run_iso, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    seconds = int((datetime.now(timezone.utc) - last).total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _load_cached(results_dir: Path) -> dict[str, dict]:
    cached: dict[str, dict] = {}
    for path in sorted(results_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        cached[payload.get("strategy") or path.stem] = payload
    return cached


def _pick_strategies(all_strategies: list[str], cached: dict[str, dict]) -> list[str]:
    print("Strategies:", file=sys.stderr)
    width = max(len(n) for n in all_strategies)
    for i, name in enumerate(all_strategies, start=1):
        tag = f"cached {_cache_age(cached[name]['last_run'])}" if name in cached else "not cached"
        print(f"  {i}) {name:<{width}}  {tag}", file=sys.stderr)
    print(file=sys.stderr)
    print(
        "Pick: indices or names, 'all' to recompute everything,\n"
        "      empty for the uncached ones, 'q' to quit.",
        file=sys.stderr,
    )
    raw = input("> ").strip()
    if raw == "q":
        sys.exit(0)
    if not raw:
        return [s for s in all_strategies if s not in cached]
    if raw == "all":
        return list(all_strategies)
    selected: list[str] = []
    for token in raw.replace(",", " ").split():
        if token.isdigit() and 1 <= int(token) <= len(all_strategies):
            pick = all_strategies[int(token) - 1]
        elif token in all_strategies:
            pick = token
        else:
            print(f"  ignoring: {token!r}", file=sys.stderr)
            continue
        if pick not in selected:
            selected.append(pick)
    return selected


def _select_scenarios(args: argparse.Namespace) -> list[str]:
    all_scenarios = TRAIN_PRESETS | HELD_OUT_PRESETS
    if args.scenarios:
        unknown = [s for s in args.scenarios if s not in all_scenarios]
        if unknown:
            raise SystemExit(
                f"unknown scenarios: {unknown}\navailable: {sorted(all_scenarios)}"
            )
        return sorted(args.scenarios)
    return sorted(all_scenarios)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m eval", description=__doc__)
    parser.add_argument("strategies", nargs="*",
                        help="Keys of main.STRATEGIES. Empty = every registered strategy.")
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS,
                        help=f"Paired seeds per scenario (default {DEFAULT_SEEDS}). The "
                             "SAME seed list is used for every strategy, so comparisons "
                             "are paired and per-instance noise cancels. --seeds 1 "
                             "reproduces the legacy single-seed numbers.")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--no-build", action="store_true",
                        help="Skip the dotnet build check")
    parser.add_argument("--scenarios", nargs="*",
                        help="Restrict to these scenarios (e.g. busy_uniform_interleaved). "
                             "Defaults to all 15 presets.")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Prompt for which strategies to (re)run, "
                             "showing cache status from results/. Strategies "
                             "you don't pick stay in the summary via their "
                             "cached JSON.")
    args = parser.parse_args()

    cached = _load_cached(RESULTS_DIR)
    benchmarkable = [s for s in sorted(STRATEGIES) if s not in TRAINING_BASES]
    if args.interactive and not args.strategies:
        if not sys.stdin.isatty():
            print("--interactive requires a TTY on stdin", file=sys.stderr)
            return 2
        strategies = _pick_strategies(benchmarkable, cached)
    else:
        strategies = args.strategies or benchmarkable

    unknown = [s for s in strategies if s not in STRATEGIES]
    if unknown:
        print(f"unknown strategies: {unknown}", file=sys.stderr)
        print(f"available: {sorted(STRATEGIES)}", file=sys.stderr)
        return 2

    if not strategies:
        if not cached:
            print("nothing to run and no cached results: exiting", file=sys.stderr)
            return 0
        print(
            f"running nothing; rebuilding summary from {len(cached)} cached "
            f"strategies",
            file=sys.stderr,
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rebuild_summary(RESULTS_DIR, TRAIN_PRESETS, HELD_OUT_PRESETS, SUMMARY, timestamp)
        return 0

    scenarios = _select_scenarios(args)
    n_seeds = max(1, args.seeds)
    seeds_by_scenario = {sc: _derive_seeds(sc, n_seeds) for sc in scenarios}
    total = len(strategies) * len(scenarios) * n_seeds
    print(f"Running {len(strategies)} strategies x {len(scenarios)} scenarios "
          f"x {n_seeds} paired seeds = {total} runs on {args.workers} parallel "
          f"workers")
    print(f"  strategies: {', '.join(strategies)}")
    print(f"  scenarios:  {', '.join(scenarios)}")
    print()

    if not args.no_build:
        runner.ensure_runner_built()

    started = time.monotonic()
    completed = 0

    def on_progress(strategy: str, scenario: str, r: RunResult) -> None:
        nonlocal completed
        completed += 1
        tag = "OK" if not r.parse_failed else "ERR"
        seed_str = f"{r.seed:>6}" if r.seed is not None else "     -"
        print(f"  [{completed:4}/{total}] {tag:3} {strategy:<28} {scenario:<22} "
              f"seed={seed_str} err={r.delivery_errors:>3} blocks={r.handled_blocks:>4} "
              f"park={r.max_parking_duration:8.1f}", flush=True)

    nested = runner.run_paired(
        strategies, scenarios, seeds_by_scenario,
        workers=args.workers, progress=on_progress,
    )
    print(f"\nfinished in {time.monotonic() - started:.1f}s\n")

    aggs: dict[str, dict[str, ScenarioAgg]] = {
        s: {sc: aggregate(runs[sc]) for sc in runs} for s, runs in nested.items()
    }
    lex_results = {
        s: {sc: a.lex_key for sc, a in runs.items()} for s, runs in aggs.items()
    }
    ranks = compute_ranks(lex_results, TRAIN_PRESETS, HELD_OUT_PRESETS)

    _print_per_run_table(aggs, ranks)
    _print_aggregate(ranks)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for strategy in sorted(aggs):
        runs = aggs[strategy]
        scenario_results = {}
        for sc in sorted(runs):
            a = runs[sc]
            errors, neg_blocks, parking = a.lex_key
            scenario_results[sc] = {
                "n_seeds":              a.n_seeds,
                "seeds":                a.seeds,
                "errors_by_seed":       a.errors_by_seed,
                "blocks_by_seed":       a.blocks_by_seed,
                "parking_by_seed":      [None if p == float("inf") else round(p, 1)
                                         for p in a.parking_by_seed],
                "mean_blocks":          a.mean_blocks,
                "std_blocks":           a.std_blocks,
                "mean_parking":         None if a.mean_parking == float("inf") else a.mean_parking,
                "errors":               a.errors,
                "lex_key":              [errors, neg_blocks, None if parking == float("inf") else parking],
                "set":                  "train" if sc in TRAIN_PRESETS else "held_out",
            }
        path = save_run(strategy, timestamp, scenario_results, RESULTS_DIR)
        print(f"  saved {path.relative_to(EVAL_DIR.parent)}")

    rebuild_summary(RESULTS_DIR, TRAIN_PRESETS, HELD_OUT_PRESETS, SUMMARY, timestamp)
    print(f"  rebuilt {SUMMARY.relative_to(EVAL_DIR.parent)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

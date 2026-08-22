"""
Each scenario gives three KPIs packed as (errors, -blocks, parking) so plain
tuple ordering matches the competition rule. Final ranking is the average
rank across scenarios, with average ranks for ties.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean, stdev
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eval.runner import RunResult


LexKey = tuple[int, float, float]


def lex_key(errors: int, handled_blocks: int, max_parking: float) -> LexKey:
    return (errors, -handled_blocks, max_parking)


@dataclass
class ScenarioAgg:
    n_seeds: int
    seeds: list[int | None]
    blocks_by_seed: list[int]
    parking_by_seed: list[float]
    errors_by_seed: list[int]
    mean_blocks: float
    std_blocks: float
    mean_parking: float
    errors: int
    lex_key: LexKey


def aggregate(results: list["RunResult"]) -> ScenarioAgg:
    seeds = [r.seed for r in results]
    errors_by_seed = [r.delivery_errors for r in results]
    blocks_by_seed = [r.handled_blocks for r in results]
    parking_by_seed = [r.max_parking_duration for r in results]

    valid = [r for r in results if not r.parse_failed]
    if any(r.parse_failed for r in results):
        errors = -1
    else:
        errors = max(errors_by_seed)

    if valid:
        blk = [r.handled_blocks for r in valid]
        prk = [r.max_parking_duration for r in valid]
        mean_blocks = round(mean(blk), 2)
        std_blocks = round(stdev(blk), 2) if len(blk) > 1 else 0.0
        mean_parking = round(mean(prk), 1)
    else:
        mean_blocks, std_blocks, mean_parking = -1.0, 0.0, float("inf")

    return ScenarioAgg(
        n_seeds=len(results),
        seeds=seeds,
        blocks_by_seed=blocks_by_seed,
        parking_by_seed=parking_by_seed,
        errors_by_seed=errors_by_seed,
        mean_blocks=mean_blocks,
        std_blocks=std_blocks,
        mean_parking=mean_parking,
        errors=errors,
        lex_key=(errors, round(-mean_blocks, 2), mean_parking),
    )


def _average_ranks(values: list[tuple]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def compute_ranks(
    results: dict[str, dict[str, LexKey]],
    train_set: Iterable[str],
    held_out_set: Iterable[str],
) -> dict[str, dict]:
    train_set = set(train_set)
    held_out_set = set(held_out_set)
    strategies = list(results)
    all_scenarios = sorted({sc for runs in results.values() for sc in runs})

    def rank_key(k: LexKey) -> tuple:
        return (1, 0, 0, 0.0) if k[0] < 0 else (0, k[0], k[1], k[2])

    per_scenario_ranks: dict[str, dict[str, float]] = {s: {} for s in strategies}
    for scenario in all_scenarios:
        present = [s for s in strategies if scenario in results[s]]
        ranks = _average_ranks([rank_key(results[s][scenario]) for s in present])
        for strategy, rank in zip(present, ranks):
            per_scenario_ranks[strategy][scenario] = rank

    out: dict[str, dict] = {}
    for strategy in strategies:
        ranks = per_scenario_ranks[strategy]
        out[strategy] = {
            "per_scenario_ranks": ranks,
            "train_avg_rank": _avg([r for sc, r in ranks.items() if sc in train_set]),
            "held_out_avg_rank": _avg(
                [r for sc, r in ranks.items() if sc in held_out_set]
            ),
        }
    return out


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None

"""
Each scenario's score is the mean over the stage's seed count, which is what
lets selection see past the simulator's per-run noise. A run the harness
could not measure sinks the genome instead of scoring it.
"""
from __future__ import annotations

import statistics
from concurrent.futures import ThreadPoolExecutor

from eval.runner import _reset_port_counter, run_one

from ..common.seeds import seed_variants
from .genome import Individual, key


BROKEN_SCORE = -1e12
BROKEN_PARKING = 1e9
BROKEN_ERRORS = 1000


def evaluate(
    population: list[Individual],
    cases: list[tuple[str, int]],
    config,
    pool: ThreadPoolExecutor,
) -> int:
    _reset_port_counter()
    unique: dict[tuple[str, ...], Individual] = {}
    for individual in population:
        unique.setdefault(key(individual), individual)

    futures = {}
    for genome_key, individual in unique.items():
        params = config.params([str(tree) for tree in individual])
        for scenario, seed in cases:
            for variant in seed_variants(seed, config.seeds_per_gen):
                fut = pool.submit(
                    run_one, config.strategy, scenario, seed=variant, params=params
                )
                futures[fut] = (genome_key, scenario)

    runs: dict[tuple[str, ...], dict[str, list]] = {
        k: {sc: [] for sc, _ in cases} for k in unique
    }
    for fut in futures:
        genome_key, scenario = futures[fut]
        runs[genome_key][scenario].append(fut.result())

    scored: dict[tuple[str, ...], dict[str, tuple[float, float, float]]] = {}
    for genome_key in unique:
        per_scenario = {}
        for scenario, _ in cases:
            batch = runs[genome_key][scenario]
            if any(r.delivery_errors < 0 for r in batch):
                per_scenario[scenario] = (BROKEN_SCORE, BROKEN_PARKING, BROKEN_ERRORS)
            else:
                errors = statistics.mean(r.delivery_errors for r in batch)
                blocks = statistics.mean(r.handled_blocks for r in batch)
                parking = statistics.mean(r.max_parking_duration for r in batch)
                per_scenario[scenario] = (blocks - 1e6 * errors, parking, errors)
        scored[genome_key] = per_scenario

    for individual in population:
        per_scenario = scored[key(individual)]
        individual.scores = {sc: per_scenario[sc][0] for sc, _ in cases}
        individual.parking = {sc: per_scenario[sc][1] for sc, _ in cases}
        individual.errors = {sc: per_scenario[sc][2] for sc, _ in cases}
        individual.agg = aggregate_key(individual)
    return len(futures)


def aggregate_key(individual: Individual) -> tuple[int, float, float]:
    """Reporting order: errors, then blocks (negated), then parking."""
    total_errors = sum(individual.errors.values())
    mean_blocks = statistics.mean(
        individual.scores[sc] + 1e6 * individual.errors[sc] for sc in individual.scores
    )
    return (int(total_errors), -mean_blocks, mean_parking(individual))


def mean_parking(individual: Individual) -> float:
    return statistics.mean(individual.parking.values())

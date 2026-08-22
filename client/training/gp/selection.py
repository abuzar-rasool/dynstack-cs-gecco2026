"""
Parents are chosen by automatic epsilon-lexicase: scenarios are visited in
random order and only the candidates within one median-absolute-deviation of
the best survive each filter, so a genome has to be good on a hard scenario
rather than good on average. Mean parking breaks the final tie. The Hall of
Fame only records; it never breeds back into the population.
"""
from __future__ import annotations

import random
import statistics

from .fitness import mean_parking
from .genome import Individual, key


def _mad(values: list[float]) -> float:
    median = statistics.median(values)
    return statistics.median([abs(v - median) for v in values])


def select_parents(
    population: list[Individual], cases: list[tuple[str, int]], n: int
) -> list[Individual]:
    case_names = [sc for sc, _ in cases]
    parents: list[Individual] = []
    for _ in range(n):
        candidates = list(population)
        order = case_names[:]
        random.shuffle(order)
        for scenario in order:
            if len(candidates) == 1:
                break
            values = [c.scores[scenario] for c in candidates]
            threshold = max(values) - _mad(values)
            candidates = [
                c for c, v in zip(candidates, values) if v >= threshold
            ]
        best_parking = min(mean_parking(c) for c in candidates)
        finalists = [c for c in candidates if mean_parking(c) == best_parking]
        parents.append(random.choice(finalists))
    return parents


def update_hall_of_fame(
    hall_of_fame: list[Individual], population: list[Individual], size: int
) -> list[Individual]:
    best: dict[tuple[str, ...], Individual] = {key(i): i for i in hall_of_fame}
    for individual in population:
        genome_key = key(individual)
        if genome_key not in best or individual.agg < best[genome_key].agg:
            best[genome_key] = individual
    return sorted(best.values(), key=lambda i: i.agg)[:size]

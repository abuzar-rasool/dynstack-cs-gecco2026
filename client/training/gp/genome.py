"""The multi-tree genome and its variation operators.

An individual holds one DEAP tree per evolved hook plus the evaluation
results attached after fitness. Crossover and mutation act on one tree
position at a time and reject any child that exceeds the height cap.
"""
from __future__ import annotations

import copy
import random

from deap import gp


MAX_HEIGHT = 17
CXPB = 0.7
MUTPB = 0.2


class Individual(list):
    """One tree per evolved hook, in the stage's tree order."""

    scores: dict[str, float]
    parking: dict[str, float]
    errors: dict[str, float]
    agg: tuple


def random_tree(pset: gp.PrimitiveSet) -> gp.PrimitiveTree:
    return gp.PrimitiveTree(gp.genHalfAndHalf(pset, min_=1, max_=3))


def from_strings(trees, psets) -> Individual:
    return Individual(
        [gp.PrimitiveTree.from_string(t, pset) for t, pset in zip(trees, psets)]
    )


def key(individual: Individual) -> tuple[str, ...]:
    return tuple(str(tree) for tree in individual)


def clone(individual: Individual) -> Individual:
    return Individual([copy.deepcopy(tree) for tree in individual])


def initial_population(config, n_warm_start: int) -> list[Individual]:
    warm = [from_strings(config.warm_trees, config.psets) for _ in range(n_warm_start)]
    fresh = [
        Individual([random_tree(pset) for pset in config.psets])
        for _ in range(config.pop_size - n_warm_start)
    ]
    return warm + fresh


def _mutation_expr(pset: gp.PrimitiveSet, type_=None):
    return gp.genFull(pset, min_=0, max_=2, type_=type_)


def mate(a: Individual, b: Individual) -> tuple[Individual, Individual]:
    first, second = clone(a), clone(b)
    for i in range(len(a)):
        child_a, child_b = gp.cxOnePoint(first[i], second[i])
        first[i] = child_a if child_a.height <= MAX_HEIGHT else copy.deepcopy(a[i])
        second[i] = child_b if child_b.height <= MAX_HEIGHT else copy.deepcopy(b[i])
    return first, second


def mutate(individual: Individual, psets) -> Individual:
    i = random.randrange(len(individual))
    (mutated,) = gp.mutUniform(individual[i], expr=_mutation_expr, pset=psets[i])
    if mutated.height <= MAX_HEIGHT:
        individual[i] = mutated
    return individual


def breed(parents: list[Individual], pop_size: int, psets) -> list[Individual]:
    offspring: list[Individual] = []
    while len(offspring) < pop_size:
        roll = random.random()
        if roll < CXPB and len(parents) >= 2:
            a, b = random.sample(parents, 2)
            first, second = mate(a, b)
            offspring.append(first)
            if len(offspring) < pop_size:
                offspring.append(second)
        elif roll < CXPB + MUTPB:
            offspring.append(mutate(clone(random.choice(parents)), psets))
        else:
            offspring.append(clone(random.choice(parents)))
    return offspring

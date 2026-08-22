"""GP trainer for SCA-GPHH, one entry point for all five stages.

    python -m training.train_gp --stage A        (A through E)

What each stage changes lives in training/gp/stages.py. Set
DYNSTACK_GP_SMOKE=1 for a short plumbing run, DYNSTACK_GP_WORKERS to match
your cores, and DYNSTACK_GP_SEEDS_PER_GEN to override the stage default.
"""
from __future__ import annotations

import argparse
import os
import random
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from eval.runner import ensure_runner_built
from scenarios.presets import HELD_OUT_PRESETS, TRAIN_PRESETS
from strategies.sca_gphh.primitives import FEATURES_2, FEATURES_4, FEATURES_5

from .common import runs
from .common.confirm import run_confirm
from .common.seeds import training_seed
from .gp import genome as gn
from .gp.fitness import evaluate
from .gp.selection import select_parents, update_hall_of_fame
from .gp.stages import STAGES, StageConfig


SMOKE = os.environ.get("DYNSTACK_GP_SMOKE") == "1"
WORKERS = int(os.environ.get("DYNSTACK_GP_WORKERS", "8"))

MASTER_SEED = 12345
MAX_GENERATIONS = 2 if SMOKE else 100
PATIENCE = 1 if SMOKE else 8
N_WARM_START = 1 if SMOKE else 4
HALL_OF_FAME_SIZE = 3 if SMOKE else 15
CONFIRM_SEEDS = 1 if SMOKE else 10

SMOKE_SCENARIOS = ["default", "busy", "quiet"]
TRAIN_SCENARIOS = SMOKE_SCENARIOS if SMOKE else sorted(TRAIN_PRESETS)
HELD_OUT_SCENARIOS = sorted(HELD_OUT_PRESETS)


def describe(individual: gn.Individual, config: StageConfig) -> dict:
    return {key: str(tree) for key, tree in zip(config.tree_keys, individual)}


def build_config(config: StageConfig) -> dict:
    return {
        "stage": config.stage,
        "strategy": config.strategy,
        "tree_keys": list(config.tree_keys),
        "extra_params": config.extra_params,
        "seeds_per_gen": config.seeds_per_gen,
        "smoke": SMOKE,
        "master_seed": MASTER_SEED,
        "pop_size": config.pop_size,
        "max_generations": MAX_GENERATIONS,
        "patience": PATIENCE,
        "crossover_rate": gn.CXPB,
        "mutation_rate": gn.MUTPB,
        "max_height": gn.MAX_HEIGHT,
        "workers": WORKERS,
        "warm_start_copies": N_WARM_START,
        "hall_of_fame_size": HALL_OF_FAME_SIZE,
        "confirm_seeds": CONFIRM_SEEDS,
        "train_scenarios": TRAIN_SCENARIOS,
        "held_out_scenarios": HELD_OUT_SCENARIOS,
        "features_hook2": list(FEATURES_2),
        "features_hook4": list(FEATURES_4),
        "features_hook5": list(FEATURES_5),
        "warm_start_trees": dict(zip(config.tree_keys, config.warm_trees)),
    }


def write_best(hall_of_fame, run_dir: Path, config: StageConfig) -> None:
    runs.write_json(run_dir, "best.json", [
        {
            "rank": i,
            **describe(individual, config),
            "mean_blocks": -individual.agg[1],
            "mean_parking": individual.agg[2],
            "errors": individual.agg[0],
            "train_kpis": {
                sc: {
                    "blocks": individual.scores[sc] + 1e6 * individual.errors[sc],
                    "errors": individual.errors[sc],
                    "parking": individual.parking[sc],
                }
                for sc in individual.scores
            },
        }
        for i, individual in enumerate(hall_of_fame)
    ])


def plateaued(history: list[float]) -> bool:
    if len(history) <= PATIENCE:
        return False
    return all(v <= max(history[:-PATIENCE]) + 1e-9 for v in history[-PATIENCE:])


def main() -> None:
    parser = argparse.ArgumentParser(description="SCA-GPHH GP trainer")
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    args = parser.parse_args()

    env_seeds = os.environ.get("DYNSTACK_GP_SEEDS_PER_GEN")
    config = StageConfig(
        args.stage,
        smoke=SMOKE,
        seeds_per_gen=int(env_seeds) if env_seeds else None,
    )
    ensure_runner_built()

    random.seed(MASTER_SEED)
    label = f"stage{config.stage}" + ("_smoke" if SMOKE else "")
    run_dir = runs.create_run_dir(label)
    runs.write_config(run_dir, build_config(config))
    runs.start_csv(run_dir)
    history: list[float] = []
    population = gn.initial_population(config, N_WARM_START)
    hall_of_fame: list[gn.Individual] = []
    print(
        f"run dir: {run_dir}  (stage {config.stage}, {config.strategy}, "
        f"pop {config.pop_size}, {config.seeds_per_gen} seeds/generation)"
    )

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for generation in range(MAX_GENERATIONS):
            cases = [
                (sc, training_seed(MASTER_SEED, generation, sc))
                for sc in TRAIN_SCENARIOS
            ]
            n_evals = evaluate(population, cases, config, pool)

            hall_of_fame = update_hall_of_fame(
                hall_of_fame, population, HALL_OF_FAME_SIZE
            )
            best = min(population, key=lambda i: i.agg)
            blocks = [-i.agg[1] for i in population]
            runs.append_csv(run_dir, [
                generation,
                round(-best.agg[1], 2),
                round(statistics.mean(blocks), 2),
                round(statistics.median(blocks), 2),
                round(statistics.pstdev(blocks), 2),
                best.agg[0],
                round(best.agg[2], 1),
                n_evals,
            ])
            print(
                f"generation {generation:>2}  best {-best.agg[1]:>7.2f}  "
                f"mean {statistics.mean(blocks):>7.2f}  "
                f"errors {best.agg[0]}  evals {n_evals}"
            )

            write_best(hall_of_fame, run_dir, config)
            history.append(-best.agg[1])
            if plateaued(history):
                print(f"early stop: no improvement for {PATIENCE} generations")
                break

            population = gn.breed(
                select_parents(population, cases, config.pop_size),
                config.pop_size,
                config.psets,
            )

        write_best(hall_of_fame, run_dir, config)
        run_confirm(
            candidates=hall_of_fame,
            describe=lambda i: describe(i, config),
            params_of=lambda i: config.params([str(t) for t in i]),
            strategy=config.strategy,
            master_seed=MASTER_SEED,
            train_scenarios=TRAIN_SCENARIOS,
            held_out_scenarios=HELD_OUT_SCENARIOS,
            n_seeds=CONFIRM_SEEDS,
            pool=pool,
            run_dir=run_dir,
        )

    print(f"\ndone: {run_dir}")


if __name__ == "__main__":
    sys.exit(main())

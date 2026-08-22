"""CMA-ES trainer for the linear weight-vector policy.

    python -m training.train_cmaes

Optimises the 20 weights of WeightVectorPolicy, warm-started from the
Stage-E GP champion linearised. The master seed differs from the GP
trainer's so the two never share training seeds. Set DYNSTACK_CMAES_SMOKE=1
for a short plumbing run and DYNSTACK_CMAES_WORKERS to match your cores.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cma

from eval.runner import _reset_port_counter, ensure_runner_built, run_one
from scenarios.presets import HELD_OUT_PRESETS, TRAIN_PRESETS
from strategies.sca_gphh.primitives import FEATURES_2, FEATURES_4, FEATURES_5

from .common import runs
from .common.confirm import run_confirm
from .common.seeds import training_seed


SMOKE = os.environ.get("DYNSTACK_CMAES_SMOKE") == "1"
WORKERS = int(os.environ.get("DYNSTACK_CMAES_WORKERS", "8"))

MASTER_SEED = 54321
STRATEGY = "cmaes_weights"
POP_SIZE = 5 if SMOKE else 20
MAX_GENERATIONS = 5 if SMOKE else 200
SIGMA0 = 0.3
HALL_OF_FAME_SIZE = 3 if SMOKE else 5
DENOISING_SEEDS = 1 if SMOKE else 3
CONFIRM_SEEDS = 1 if SMOKE else 10

SMOKE_SCENARIOS = ["default", "busy", "quiet", "quiet_uniform_interleaved"]
TRAIN_SCENARIOS = SMOKE_SCENARIOS if SMOKE else sorted(TRAIN_PRESETS)
HELD_OUT_SCENARIOS = sorted(HELD_OUT_PRESETS)

N_W2, N_W4, N_W5 = len(FEATURES_2), len(FEATURES_4), len(FEATURES_5)
GENOME_DIM = N_W2 + N_W4 + N_W5

WARM_START: list[float] = (
    [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    + [0.0, -1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    + [0.0, 1.0, 0.0, 0.0, 1.0, 0.0]
)
assert len(WARM_START) == GENOME_DIM


def split(weights) -> tuple[list[float], list[float], list[float]]:
    w = [float(x) for x in weights]
    return w[:N_W2], w[N_W2:N_W2 + N_W4], w[N_W2 + N_W4:]


def params_of(weights) -> dict[str, str]:
    w2, w4, w5 = split(weights)
    return {"weights2": str(w2), "weights4": str(w4), "weights5": str(w5)}


def describe(entry) -> dict:
    w2, w4, w5 = split(entry["weights"])
    return {
        "w2": {f: round(v, 6) for f, v in zip(FEATURES_2, w2)},
        "w4": {f: round(v, 6) for f, v in zip(FEATURES_4, w4)},
        "w5": {f: round(v, 6) for f, v in zip(FEATURES_5, w5)},
    }


def objective(blocks: list[float], errors: list[int], parking: list[float]) -> float:
    """Errors dominate, then mean blocks, then parking as a small tiebreaker."""
    return sum(errors) * 1e6 - statistics.mean(blocks) + statistics.mean(parking) / 3600


def evaluate(candidates, generation: int, pool: ThreadPoolExecutor) -> list[dict]:
    _reset_port_counter()
    futures = {}
    for i, weights in enumerate(candidates):
        params = params_of(weights)
        for scenario in TRAIN_SCENARIOS:
            for k in range(DENOISING_SEEDS):
                seed = training_seed(MASTER_SEED, generation, scenario, k)
                fut = pool.submit(run_one, STRATEGY, scenario, seed=seed, params=params)
                futures[fut] = (i, scenario)

    runs_by_candidate = [{sc: [] for sc in TRAIN_SCENARIOS} for _ in candidates]
    for fut, (i, scenario) in futures.items():
        runs_by_candidate[i][scenario].append(fut.result())

    results = []
    for per_scenario in runs_by_candidate:
        blocks, errors, parking, kpis = [], [], [], {}
        for sc in TRAIN_SCENARIOS:
            batch = per_scenario[sc]
            if any(r.delivery_errors < 0 for r in batch):
                sc_errors, sc_blocks, sc_parking = 1, 0.0, 360000.0
            else:
                sc_errors = max(r.delivery_errors for r in batch)
                sc_blocks = statistics.mean(r.handled_blocks for r in batch)
                sc_parking = statistics.mean(r.max_parking_duration for r in batch)
            blocks.append(sc_blocks)
            errors.append(sc_errors)
            parking.append(sc_parking)
            kpis[sc] = {"blocks": sc_blocks, "errors": sc_errors, "parking": sc_parking}
        results.append({
            "objective": objective(blocks, errors, parking),
            "kpis": kpis,
            "agg": (sum(errors), -statistics.mean(blocks), statistics.mean(parking)),
        })
    return results


def update_hall_of_fame(hall_of_fame: list[dict], candidates, results) -> list[dict]:
    entries = list(hall_of_fame)
    for weights, result in zip(candidates, results):
        entries.append({"weights": [float(x) for x in weights], **result})
    seen, unique = set(), []
    for entry in entries:
        key = tuple(round(w, 6) for w in entry["weights"])
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return sorted(unique, key=lambda e: tuple(e["agg"]))[:HALL_OF_FAME_SIZE]


def build_config() -> dict:
    return {
        "smoke": SMOKE,
        "master_seed": MASTER_SEED,
        "pop_size": POP_SIZE,
        "max_generations": MAX_GENERATIONS,
        "sigma0": SIGMA0,
        "hall_of_fame_size": HALL_OF_FAME_SIZE,
        "denoising_seeds": DENOISING_SEEDS,
        "confirm_seeds": CONFIRM_SEEDS,
        "workers": WORKERS,
        "genome_dim": GENOME_DIM,
        "features_hook2": list(FEATURES_2),
        "features_hook4": list(FEATURES_4),
        "features_hook5": list(FEATURES_5),
        "warm_start": WARM_START,
        "train_scenarios": TRAIN_SCENARIOS,
        "held_out_scenarios": HELD_OUT_SCENARIOS,
    }


def write_best(hall_of_fame: list[dict], run_dir: Path) -> None:
    runs.write_json(run_dir, "best.json", [
        {
            "rank": i,
            **describe(entry),
            "objective": entry["objective"],
            "mean_blocks": -entry["agg"][1],
            "mean_parking": entry["agg"][2],
            "errors": entry["agg"][0],
            "train_kpis": entry["kpis"],
        }
        for i, entry in enumerate(hall_of_fame)
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="CMA-ES weight-vector trainer")
    parser.parse_args()

    ensure_runner_built()

    run_dir = runs.create_run_dir("cmaes_smoke" if SMOKE else "cmaes")
    runs.write_config(run_dir, build_config())
    runs.start_csv(run_dir, [
        "gen", "best_objective", "best_blocks", "mean_blocks",
        "errors", "parking", "n_evals",
    ])
    es = cma.CMAEvolutionStrategy(WARM_START, SIGMA0, {
        "popsize": POP_SIZE,
        "maxiter": MAX_GENERATIONS,
        "tolx": 1e-4,
        "tolfun": 1e-5,
        "verbose": -9,
        "seed": MASTER_SEED,
    })
    hall_of_fame: list[dict] = []
    generation = 0
    print(
        f"run dir: {run_dir}  (popsize {POP_SIZE}, {MAX_GENERATIONS} generations, "
        f"{DENOISING_SEEDS} seeds/candidate)"
    )

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        while not es.stop() and generation < MAX_GENERATIONS:
            candidates = es.ask()
            results = evaluate(candidates, generation, pool)
            objectives = [r["objective"] for r in results]
            es.tell(candidates, objectives)
            hall_of_fame = update_hall_of_fame(hall_of_fame, candidates, results)

            best = hall_of_fame[0]
            n_evals = len(candidates) * len(TRAIN_SCENARIOS) * DENOISING_SEEDS
            runs.append_csv(run_dir, [
                generation,
                round(min(objectives), 4),
                round(-best["agg"][1], 2),
                round(statistics.mean(-r["agg"][1] for r in results), 2),
                best["agg"][0],
                round(best["agg"][2], 1),
                n_evals,
            ])
            print(
                f"generation {generation:>3}  objective {min(objectives):>10.2f}  "
                f"best {-best['agg'][1]:>7.2f}  errors {best['agg'][0]}  "
                f"evals {n_evals}"
            )

            write_best(hall_of_fame, run_dir)
            generation += 1

        write_best(hall_of_fame, run_dir)
        run_confirm(
            candidates=hall_of_fame,
            describe=describe,
            params_of=lambda entry: params_of(entry["weights"]),
            strategy=STRATEGY,
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

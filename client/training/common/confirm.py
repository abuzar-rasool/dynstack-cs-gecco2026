"""
Re-runs every Hall-of-Fame candidate on the training and held-out scenarios
with fresh seeds, then picks the champion on the held-out mean of the
competition metric. Selection uses the multi-seed mean rather than an
average rank, because a three-scenario rank average cannot separate genomes
that sit close together under the simulator's run-to-run variance.
"""
from __future__ import annotations

import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from eval.runner import _reset_port_counter, run_one
from eval.scoring import compute_ranks, lex_key

from .runs import write_json
from .seeds import confirm_seed


def run_confirm(
    *,
    candidates: list,
    describe: Callable[[object], dict],
    params_of: Callable[[object], dict],
    strategy: str,
    master_seed: int,
    train_scenarios: list[str],
    held_out_scenarios: list[str],
    n_seeds: int,
    pool: ThreadPoolExecutor,
    run_dir: Path,
) -> dict:
    _reset_port_counter()
    scenarios = train_scenarios + held_out_scenarios
    labels = [f"hof{i}" for i in range(len(candidates))]
    cases = [
        (sc, confirm_seed(master_seed, n, sc))
        for sc in scenarios
        for n in range(n_seeds)
    ]

    futures = {}
    for label, candidate in zip(labels, candidates):
        params = params_of(candidate)
        for scenario, seed in cases:
            fut = pool.submit(run_one, strategy, scenario, seed=seed, params=params)
            futures[fut] = (label, scenario)

    runs: dict[str, dict[str, list]] = {
        lbl: {sc: [] for sc in scenarios} for lbl in labels
    }
    for fut in futures:
        label, scenario = futures[fut]
        runs[label][scenario].append(fut.result())

    lex_results: dict[str, dict[str, tuple]] = {}
    kpis: dict[str, dict[str, dict]] = {}
    for label in labels:
        lex_results[label] = {}
        kpis[label] = {}
        for sc in scenarios:
            batch = runs[label][sc]
            errors = max(r.delivery_errors for r in batch)
            blocks = statistics.mean(r.handled_blocks for r in batch)
            parking = statistics.mean(r.max_parking_duration for r in batch)
            lex_results[label][sc] = lex_key(errors, round(blocks, 3), parking)
            kpis[label][sc] = {"errors": errors, "blocks": blocks, "parking": parking}

    def mean_key(label: str, scs: list[str]) -> tuple:
        errors = sum(kpis[label][sc]["errors"] for sc in scs)
        blocks = statistics.mean(kpis[label][sc]["blocks"] for sc in scs)
        parking = statistics.mean(kpis[label][sc]["parking"] for sc in scs)
        return lex_key(errors, round(blocks, 3), parking)

    ranked = sorted(
        labels,
        key=lambda lbl: (
            mean_key(lbl, held_out_scenarios),
            mean_key(lbl, train_scenarios),
        ),
    )
    winner = ranked[0]
    held_out_means = {
        label: {
            "blocks": statistics.mean(
                kpis[label][sc]["blocks"] for sc in held_out_scenarios
            ),
            "parking": statistics.mean(
                kpis[label][sc]["parking"] for sc in held_out_scenarios
            ),
            "errors": sum(kpis[label][sc]["errors"] for sc in held_out_scenarios),
        }
        for label in labels
    }
    selected = {
        "label": winner,
        **describe(candidates[labels.index(winner)]),
        **held_out_means[winner],
    }
    payload = {
        "candidates": {labels[i]: describe(candidates[i]) for i in range(len(candidates))},
        "selected": selected,
        "held_out_means": held_out_means,
        "ranks": compute_ranks(lex_results, set(train_scenarios), set(held_out_scenarios)),
        "kpis": kpis,
        "confirm_seeds": n_seeds,
    }
    write_json(run_dir, "confirm.json", payload)
    print(
        f"\nconfirm winner: {winner}  blocks={selected['blocks']:.1f} "
        f"parking={selected['parking']:.1f} errors={selected['errors']}"
    )
    return payload

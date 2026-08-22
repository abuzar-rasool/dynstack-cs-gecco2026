"""Run folders: config, per-generation CSV, and result files.
A run writes training/data/runs/<timestamp>_<label>/ holding config.json,
generations.csv, best.json and confirm.json.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path


RUNS_ROOT = Path("training/data/runs")

CSV_COLUMNS = [
    "gen",
    "best_blocks",
    "mean_blocks",
    "median_blocks",
    "std_blocks",
    "best_errors",
    "best_parking",
    "n_evals",
]


def create_run_dir(label: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    run_dir = RUNS_ROOT / f"{stamp}_{label}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_config(run_dir: Path, config: dict) -> None:
    (run_dir / "config.json").write_text(json.dumps(config, indent=2))


def start_csv(run_dir: Path, columns: list[str] = CSV_COLUMNS) -> None:
    with (run_dir / "generations.csv").open("w", newline="") as fh:
        csv.writer(fh).writerow(columns)


def append_csv(run_dir: Path, row: list) -> None:
    with (run_dir / "generations.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow(row)


def write_json(run_dir: Path, name: str, payload) -> None:
    (run_dir / name).write_text(json.dumps(payload, indent=2, allow_nan=False))

"""
Each run overwrites results/<strategy>.json. The summary is rebuilt from
every file in the directory, so strategies evaluated at different times
still rank against each other.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from eval.scoring import LexKey, compute_ranks


def save_run(
    strategy: str,
    timestamp: str,
    scenario_results: dict[str, dict],
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{strategy}.json"
    payload = {
        "strategy": strategy,
        "last_run": timestamp,
        "results": scenario_results,
    }
    path.write_text(json.dumps(payload, indent=2, allow_nan=False))
    return path


def _all_results(results_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(results_dir.glob("*.json")):
        payload = json.loads(path.read_text())
        out[payload.get("strategy") or path.stem] = payload
    return out


def rebuild_summary(
    results_dir: Path,
    train_set: Iterable[str],
    held_out_set: Iterable[str],
    summary_path: Path,
    now: str,
) -> dict:
    latest = _all_results(results_dir)
    if not latest:
        summary = {
            "last_updated": now,
            "strategies": [],
            "per_scenario_rankings": {},
            "aggregate": {},
        }
        summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False))
        summary_path.with_suffix(".md").write_text(
            _render_markdown(summary, set(train_set), set(held_out_set))
        )
        return summary

    def hydrate(key: list) -> LexKey:
        parking = float("inf") if key[2] is None else float(key[2])
        return (int(key[0]), float(key[1]), parking)

    def dehydrate(key: LexKey) -> list:
        return [key[0], key[1], None if key[2] == float("inf") else key[2]]

    results: dict[str, dict[str, LexKey]] = {
        strategy: {sc: hydrate(r["lex_key"]) for sc, r in payload["results"].items()}
        for strategy, payload in latest.items()
    }
    meta = {
        strategy: {
            sc: {"std_blocks": r.get("std_blocks", 0.0), "n_seeds": r.get("n_seeds", 1)}
            for sc, r in payload["results"].items()
        }
        for strategy, payload in latest.items()
    }

    aggregate = compute_ranks(results, train_set, held_out_set)

    per_scenario_rankings: dict[str, list[dict]] = {}
    for scenario in sorted({sc for runs in results.values() for sc in runs}):
        rows = [
            {
                "strategy": s,
                "lex_key": dehydrate(results[s][scenario]),
                "rank": aggregate[s]["per_scenario_ranks"][scenario],
                "std_blocks": meta[s][scenario]["std_blocks"],
                "n_seeds": meta[s][scenario]["n_seeds"],
            }
            for s in results
            if scenario in results[s]
        ]
        rows.sort(key=lambda r: r["rank"])
        per_scenario_rankings[scenario] = rows

    summary = {
        "last_updated": now,
        "strategies": sorted(results),
        "per_scenario_rankings": per_scenario_rankings,
        "aggregate": {
            s: {
                "train_avg_rank": a["train_avg_rank"],
                "held_out_avg_rank": a["held_out_avg_rank"],
            }
            for s, a in aggregate.items()
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False))
    summary_path.with_suffix(".md").write_text(
        _render_markdown(summary, set(train_set), set(held_out_set))
    )
    return summary


def _render_markdown(summary: dict, train_set: set[str], held_out_set: set[str]) -> str:
    iso = summary["last_updated"]
    ts = f"{iso[:4]}-{iso[4:6]}-{iso[6:8]} {iso[9:11]}:{iso[11:13]} UTC"

    by_strategy: dict[str, dict[str, dict]] = {s: {} for s in summary["aggregate"]}
    for scenario, rows in summary["per_scenario_rankings"].items():
        for row in rows:
            errors, neg_blocks, parking = row["lex_key"]
            by_strategy.setdefault(row["strategy"], {})[scenario] = {
                "errors": errors,
                "blocks": -neg_blocks,
                "parking": parking,
                "rank": row["rank"],
                "std_blocks": row.get("std_blocks", 0.0),
                "n_seeds": row.get("n_seeds", 1),
            }

    def blocks(d: dict) -> str:
        if d.get("n_seeds", 1) > 1:
            return f"{d['blocks']:g} +/- {d.get('std_blocks', 0.0):g}"
        return f"{d['blocks']:g}"

    def park(p) -> str:
        return f"{p:.1f}" if p is not None else "n/a"

    lines = ["# Evaluation results", "", f"Last updated: {ts}", ""]
    lines += [
        "## Average rank",
        "",
        "| Strategy | Train | Held-out |",
        "|---|---:|---:|",
    ]
    for s in sorted(summary["aggregate"]):
        a = summary["aggregate"][s]
        train = f"{a['train_avg_rank']:.2f}" if a["train_avg_rank"] is not None else "-"
        held = f"{a['held_out_avg_rank']:.2f}" if a["held_out_avg_rank"] is not None else "-"
        lines.append(f"| `{s}` | {train} | {held} |")
    lines.append("")

    lines += ["## Per strategy", ""]
    for strategy in sorted(by_strategy):
        scenarios = by_strategy[strategy]
        if not scenarios:
            continue
        lines += [f"### `{strategy}`", ""]
        for label, bucket in (("Train", train_set), ("Held-out", held_out_set)):
            relevant = sorted(s for s in scenarios if s in bucket)
            if not relevant:
                continue
            lines += [
                f"{label} scenarios",
                "",
                "| Scenario | Errors | Blocks | Parking (s) | Rank |",
                "|---|---:|---:|---:|---:|",
            ]
            for scenario in relevant:
                d = scenarios[scenario]
                lines.append(
                    f"| `{scenario}` | {d['errors']} | {blocks(d)} | "
                    f"{park(d['parking'])} | {d['rank']:g} |"
                )
            lines.append("")
    return "\n".join(lines)

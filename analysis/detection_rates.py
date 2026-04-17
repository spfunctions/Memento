#!/usr/bin/env python3
"""Compute detection rates and generate a summary from experiment runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_run(run_dir: Path) -> dict:
    config = json.loads((run_dir / "config.json").read_text())
    summary = json.loads((run_dir / "summary.json").read_text())

    rounds = []
    rounds_dir = run_dir / "rounds"
    for p in sorted(rounds_dir.glob("round_*.json")):
        rounds.append(json.loads(p.read_text()))

    return {"config": config, "summary": summary, "rounds": rounds}


def analyze(run_dir: Path) -> None:
    data = load_run(run_dir)
    config = data["config"]
    rounds = data["rounds"]

    print(f"\n{'='*60}")
    print(f"  Run: {run_dir.name}")
    print(f"  Model: {config['model']}")
    print(f"  Adversarial awareness: {config['adversarial_awareness']}")
    print(f"  Attacks: {[a['name'] for a in config['attacks']]}")
    print(f"{'='*60}\n")

    # Per-attack detection timeline
    attack_names = {a["name"] for a in config["attacks"]}
    for attack_name in sorted(attack_names):
        print(f"  [{attack_name}]")
        detections = 0
        for r in rounds:
            sig = r.get("detection_signals", {}).get(attack_name, {})
            detected = sig.get("detected", False)
            indicators = sig.get("indicators", [])
            if detected:
                detections += 1
                print(f"    Round {r['round_num']:2d}: DETECTED — {indicators}")
            else:
                print(f"    Round {r['round_num']:2d}: not detected")

        rate = detections / len(rounds) if rounds else 0
        print(f"    Detection rate: {detections}/{len(rounds)} ({rate:.0%})\n")

    # Tool usage summary
    total_tools = sum(len(r.get("tool_calls", [])) for r in rounds)
    tampered_tools = sum(
        sum(1 for tc in r.get("tool_calls", []) if tc.get("tampered"))
        for r in rounds
    )
    print(f"  Tool calls: {total_tools} total, {tampered_tools} tampered")

    # Conclusion progression
    for r in rounds:
        conclusions = r.get("post_attack_state", {}).get("conclusions", [])
        attacks_applied = len(r.get("attack_results", []))
        print(
            f"  Round {r['round_num']:2d}: "
            f"{len(conclusions)} conclusions, "
            f"{attacks_applied} attacks applied"
        )


def compare_runs(*run_dirs: Path) -> None:
    """Compare control vs experimental runs."""
    runs = [load_run(d) for d in run_dirs]

    print(f"\n{'='*60}")
    print("  Comparison")
    print(f"{'='*60}\n")

    for run, run_dir in zip(runs, run_dirs):
        config = run["config"]
        summary = run["summary"]
        label = "CONTROL" if not config["attacks"] else "EXPERIMENTAL"
        if config["adversarial_awareness"]:
            label += " (adversarial-aware)"

        print(
            f"  {label}: {run_dir.name}\n"
            f"    Detection rounds: "
            f"{summary['rounds_with_detection']}/{summary['total_rounds']}\n"
            f"    Total tool calls: {summary['total_tool_calls']}\n"
            f"    Final conclusions: {summary['total_conclusions']}\n"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m analysis.detection_rates <run_dir> [run_dir2 ...]")
        sys.exit(1)

    dirs = [Path(d) for d in sys.argv[1:]]

    if len(dirs) == 1:
        analyze(dirs[0])
    else:
        for d in dirs:
            analyze(d)
        compare_runs(*dirs)

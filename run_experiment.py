#!/usr/bin/env python3
"""Run a Memento context integrity experiment.

Requires `claude` CLI installed and authenticated.

Examples:
    # Full experiment with both attacks
    python run_experiment.py --name test1

    # Control run (no attacks)
    python run_experiment.py --control --name control1

    # Adversarial-aware agent
    python run_experiment.py --adversarial --name aware1

    # Custom intensity and rounds
    python run_experiment.py --rounds 5 --intensity 0.8 --name high_intensity

    # Single attack type
    python run_experiment.py --attacks substitution --name sub_only
"""

import argparse
import shutil
import sys

from harness.runner import ExperimentRunner, ExperimentConfig
from attacks import SilentSubstitution, SemanticDrift

ATTACK_REGISTRY = {
    "substitution": SilentSubstitution,
    "drift": SemanticDrift,
}


def main():
    # Verify claude CLI is available
    if not shutil.which("claude"):
        print("Error: `claude` CLI not found in PATH.", file=sys.stderr)
        print("Install: https://docs.anthropic.com/en/docs/claude-code", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Memento — context integrity stress testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--case-file",
        default="agent/case_files/meridian.json",
        help="Path to the case file JSON (default: meridian)",
    )
    parser.add_argument(
        "--rounds", type=int, default=10,
        help="Number of rounds (default: 10)",
    )
    parser.add_argument(
        "--model", default="sonnet",
        help="Model for claude -p (sonnet, opus, haiku)",
    )
    parser.add_argument(
        "--adversarial", action="store_true",
        help="Tell the agent its environment may be adversarial",
    )
    parser.add_argument(
        "--control", action="store_true",
        help="Run without any attacks (control condition)",
    )
    parser.add_argument(
        "--attacks", nargs="*", default=["substitution", "drift"],
        choices=list(ATTACK_REGISTRY.keys()),
        help="Which attacks to enable (default: all)",
    )
    parser.add_argument(
        "--intensity", type=float, default=0.5,
        help="Attack intensity 0.0-1.0 (default: 0.5)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output-dir", default="runs",
        help="Output directory (default: runs/)",
    )
    parser.add_argument(
        "--name", default="experiment",
        help="Experiment name (used in output directory)",
    )

    args = parser.parse_args()

    attacks = []
    if not args.control:
        for name in args.attacks:
            cls = ATTACK_REGISTRY[name]
            kwargs = {"intensity": args.intensity}
            if name == "substitution" and args.seed is not None:
                kwargs["seed"] = args.seed
            attacks.append(cls(**kwargs))

    config = ExperimentConfig(
        case_file_path=args.case_file,
        attacks=attacks,
        num_rounds=args.rounds,
        model=args.model,
        adversarial_awareness=args.adversarial,
        output_dir=args.output_dir,
        experiment_name=args.name,
    )

    runner = ExperimentRunner(config)
    runner.run()


if __name__ == "__main__":
    main()

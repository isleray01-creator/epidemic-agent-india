#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from epidemic_agent.cli import run_simulation


def main():
    parser = argparse.ArgumentParser(description="Run epidemic simulation (headless)")
    parser.add_argument("--country", default="India")
    parser.add_argument("--states", nargs="+", default=["Maharashtra", "Kerala", "Delhi"])
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--initial-infected", type=int, default=100)
    parser.add_argument("--variant", default="wildtype")
    parser.add_argument("--interventions", nargs="+", default=["contact_tracing"])
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--save-state", help="Save state file")
    args = parser.parse_args()

    sys.argv = ["epidemic-agent", "run"] + [
        "--country", args.country,
        "--states", *args.states,
        "--days", str(args.days),
        "--initial-infected", str(args.initial_infected),
        "--variant", args.variant,
        "--interventions", *args.interventions,
    ]
    if args.output:
        sys.argv.extend(["--output", args.output])
    if args.save_state:
        sys.argv.extend(["--save-state", args.save_state])

    sys.exit(run_simulation(args))


if __name__ == "__main__":
    main()
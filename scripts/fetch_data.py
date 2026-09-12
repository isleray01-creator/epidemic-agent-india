#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from epidemic_agent.tools import fetch_epidemic_data, fetch_vaccination_data, fetch_demographics


def main():
    parser = argparse.ArgumentParser(description="Fetch India epidemic data")
    parser.add_argument("--country", default="India", choices=["India"])
    parser.add_argument("--states", nargs="+", default=["Maharashtra", "Kerala", "Delhi", "Karnataka", "Tamil Nadu"])
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--output-dir", default="data/raw")
    parser.add_argument("--include-vaccination", action="store_true")
    parser.add_argument("--include-demographics", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching epidemic data for {args.states} (last {args.days} days)...")
    epi_result = fetch_epidemic_data.invoke({
        "states": args.states,
        "days_back": args.days,
    })

    epi_file = output_dir / f"epidemic_data_{args.days}d.json"
    epi_file.write_text(json.dumps(epi_result, indent=2, default=str))
    print(f"Saved to {epi_file}")

    if args.include_vaccination:
        print("Fetching vaccination data...")
        vax_result = fetch_vaccination_data.invoke({
            "states": args.states,
            "days_back": args.days,
        })
        vax_file = output_dir / f"vaccination_data_{args.days}d.json"
        vax_file.write_text(json.dumps(vax_result, indent=2, default=str))
        print(f"Saved to {vax_file}")

    if args.include_demographics:
        print("Fetching demographics...")
        demo_result = fetch_demographics.invoke({"states": args.states})
        demo_file = output_dir / "demographics.json"
        demo_file.write_text(json.dumps(demo_result, indent=2, default=str))
        print(f"Saved to {demo_file}")

    print("Done!")


if __name__ == "__main__":
    main()
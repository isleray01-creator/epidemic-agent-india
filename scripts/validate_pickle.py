#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from epidemic_agent.persistence import get_state_store, SecurityError


def main():
    parser = argparse.ArgumentParser(description="Validate trusted pickle files")
    parser.add_argument("file", help="Pickle file to validate")
    parser.add_argument("--load", action="store_true", help="Load and display state")
    args = parser.parse_args()

    store = get_state_store()

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return 1

    try:
        state = store.load(filepath.name)
        print(f"✓ HMAC verification passed for {filepath.name}")
        print(f"State type: {type(state)}")

        if args.load:
            import json
            print(json.dumps({k: str(v) for k, v in state.items()}, indent=2))

    except SecurityError as e:
        print(f"✗ HMAC verification FAILED: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
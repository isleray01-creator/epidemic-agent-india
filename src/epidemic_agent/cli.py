from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import VARIANT_PARAMS, get_state_population
from .graph import get_workflow
from .persistence import load_state, save_state
from .simulation.variant import VariantParameterLearner
from .state import EpidemicState, SimulationConfig
from .tools import fetch_epidemic_data


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epidemic-agent",
        description="Epidemic Response Agent for India",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Run epidemic simulation")
    run_parser.add_argument("--country", default="India", choices=["India"])
    run_parser.add_argument("--states", nargs="+", default=["Maharashtra", "Kerala", "Delhi"])
    run_parser.add_argument("--days", type=int, default=60)
    run_parser.add_argument("--initial-infected", type=int, default=100)
    run_parser.add_argument("--variant", default="wildtype", choices=list(VARIANT_PARAMS.keys()))
    run_parser.add_argument("--interventions", nargs="+", default=["contact_tracing"])
    run_parser.add_argument("--output", help="Output JSON file")
    run_parser.add_argument("--save-state", help="Save final state to file")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch real-time epidemic data")
    fetch_parser.add_argument("--states", nargs="+", default=["Maharashtra", "Kerala", "Delhi"])
    fetch_parser.add_argument("--days", type=int, default=30)
    fetch_parser.add_argument("--output", help="Output JSON file")

    learn_parser = subparsers.add_parser("learn", help="Learn variant parameters from data")
    learn_parser.add_argument("--cases-file", required=True, help="CSV with daily cases")
    learn_parser.add_argument("--deaths-file", required=True, help="CSV with daily deaths")
    learn_parser.add_argument("--vaccination-file", help="CSV with vaccination data")
    learn_parser.add_argument("--population", type=int, default=1_000_000)
    learn_parser.add_argument("--output", help="Output JSON file")

    state_parser = subparsers.add_parser("state", help="Manage saved states")
    state_parser.add_argument("action", choices=["list", "save", "load"])
    state_parser.add_argument("--file", help="State file name")

    return parser


def run_simulation(args: argparse.Namespace) -> int:
    config = SimulationConfig(
        country=args.country,
        states=args.states,
        days=args.days,
        initial_infected=args.initial_infected,
        initial_variant=args.variant,
        interventions=args.interventions,
    )

    workflow = get_workflow()

    population = {}
    for state in config.states:
        population[state] = get_state_population(state)

    total_pop = sum(population.values())
    initial_infected_per_state = {
        s: int(config.initial_infected * population[s] / total_pop)
        for s in config.states
    }

    initial_state = EpidemicState(
        current_day=0,
        simulation_days=config.days,
        country=config.country,
        states=config.states,
        population=population,
        infected=initial_infected_per_state,
        exposed={s: v // 2 for s, v in initial_infected_per_state.items()},
        recovered=dict.fromkeys(config.states, 0),
        deceased=dict.fromkeys(config.states, 0),
        vaccinated={s: int(population[s] * 0.3) for s in config.states},
        active_variants=dict.fromkeys(config.states, config.initial_variant),
        variant_prevalence={s: {config.initial_variant: 1.0} for s in config.states},
        current_policies={s: [] for s in config.states},
        intervention_history=[],
        variant_shock=None,
        confidence_score=1.0,
        objective_value=0.0,
        objective_breakdown={},
        Rt_estimates=dict.fromkeys(config.states, VARIANT_PARAMS[config.initial_variant]["R0"]),
        healthcare_capacity={},
        contact_tracing_metrics={},
        metadata={"adaptation_loops": 0},
    )

    print(f"Starting simulation for {config.states} over {config.days} days...")
    print(f"Initial variant: {config.initial_variant}")
    print(f"Interventions: {config.interventions}")

    result = workflow.run(initial_state)

    print("\nSimulation complete!")
    print(f"Final day: {result['current_day']}")
    print(f"Total deaths: {sum(result['deceased'].values())}")
    print(f"Objective value: {result['objective_value']:.4f}")
    print(f"Confidence: {result['confidence_score']:.2f}")

    if result.get("variant_shock", {}).get("shock_detected"):
        print(f"⚠️ Variant shock detected: {result['variant_shock']}")

    recommendation = result["metadata"].get("final_recommendation", {})
    if recommendation:
        print(f"\nRecommendation: {recommendation.get('rationale', 'N/A')}")

    if args.output:
        output_data = {
            "config": config.model_dump(),
            "final_state": {k: v for k, v in result.items() if k != "metadata"},
            "recommendation": recommendation,
        }
        Path(args.output).write_text(json.dumps(output_data, indent=2, default=str))
        print(f"\nResults saved to {args.output}")

    if args.save_state:
        filepath = save_state(result, args.save_state)
        print(f"State saved to {filepath}")

    return 0


def fetch_data(args: argparse.Namespace) -> int:
    print(f"Fetching data for {args.states} (last {args.days} days)...")

    result = fetch_epidemic_data.invoke({
        "states": args.states,
        "days_back": args.days,
    })

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, default=str))
        print(f"Data saved to {args.output}")
    else:
        print(json.dumps(result, indent=2, default=str))

    return 0


def learn_variant(args: argparse.Namespace) -> int:
    import pandas as pd

    cases_df = pd.read_csv(args.cases_file)
    deaths_df = pd.read_csv(args.deaths_file)

    cases = cases_df.iloc[:, -1] if len(cases_df.columns) > 1 else cases_df.iloc[:, 0]
    deaths = deaths_df.iloc[:, -1] if len(deaths_df.columns) > 1 else deaths_df.iloc[:, 0]

    vaccination = None
    if args.vaccination_file:
        vax_df = pd.read_csv(args.vaccination_file)
        vaccination = vax_df.iloc[:, -1] if len(vax_df.columns) > 1 else vax_df.iloc[:, 0]

    learner = VariantParameterLearner()
    params = learner.learn_from_wave(cases, deaths, vaccination, args.population)

    result = {
        "R0": params.R0,
        "IFR": params.IFR,
        "immune_escape": params.immune_escape,
        "serial_interval": params.serial_interval,
        "matched_variant": learner.match_known_variant(params),
    }

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
        print(f"Learned parameters saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))

    return 0


def manage_state(args: argparse.Namespace) -> int:
    store = None
    try:
        from .persistence import get_state_store
        store = get_state_store()
    except ValueError:
        print("Error: PICKLE_HMAC_KEY not set in environment")
        return 1

    if args.action == "list":
        files = store.list_states()
        if files:
            for f in files:
                print(f)
        else:
            print("No saved states")
    elif args.action == "load" and args.file:
        try:
            state = load_state(args.file)
            print(json.dumps({k: str(v) for k, v in state.items()}, indent=2))
        except Exception as e:
            print(f"Error loading state: {e}")
            return 1
    return 0


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "run": run_simulation,
        "fetch": fetch_data,
        "learn": learn_variant,
        "state": manage_state,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

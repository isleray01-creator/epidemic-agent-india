import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from epidemic_agent.validation.backtester import run_full_backtest


def main():
    print("=" * 60)
    print("EPIDEMIC AGENT - FULL ACCURACY BACKTEST")
    print("=" * 60)
    print()

    print("Fetching real India COVID-19 data from data.incovid19.org...")
    print("Testing on: Delta Wave, Omicron Wave, First Wave")
    print("States: Maharashtra, Delhi, Karnataka")
    print()

    results = run_full_backtest()

    print()
    print("=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    for wave_name, wave_data in results["summary"].items():
        if wave_name == "overall":
            continue
        print(f"\n--- {wave_name} ---")
        print(f"  Variant: {wave_data['variant']}")
        print(f"  Period: {wave_data['period']}")
        print(f"  States: {wave_data['states_tested']}")
        print(f"  Avg MAE: {wave_data['avg_MAE']}")
        print(f"  Avg RMSE: {wave_data['avg_RMSE']}")
        print(f"  Avg R-squared: {wave_data['avg_R_squared']}")
        print(f"  Avg Correlation: {wave_data['avg_correlation']}")
        print(f"  Avg MAPE: {wave_data['avg_MAPE']}")

    overall = results["summary"]["overall"]
    print()
    print("=" * 60)
    print("OVERALL ACCURACY SUMMARY")
    print("=" * 60)
    print(f"  Total backtests: {overall['total_backtests']}")
    print(f"  Avg R-squared: {overall['avg_R_squared']}")
    print(f"  Avg Correlation: {overall['avg_correlation']}")
    print(f"  Avg MAPE: {overall['avg_MAPE']}")
    print(f"  Accuracy Rating: {overall['accuracy_rating']}")

    print()
    print("--- Per-State Results ---")
    for r in results["results"]:
        m = r.metrics
        print(f"\n  {r.state} ({r.variant}, {r.period}):")
        print(f"    Learned R0: {r.learned_R0:.2f} (actual: {r.actual_R0})")
        print(f"    Learned IFR: {r.learned_IFR:.4f} (actual: {r.actual_IFR})")
        print(f"    R-squared: {m.r_squared:.4f}")
        print(f"    Correlation: {m.correlation:.4f}")
        print(f"    MAPE: {m.mape:.1%}")
        print(f"    Peak timing error: {m.peak_timing_error} days")
        print(f"    Peak magnitude error: {m.peak_magnitude_error:.1%}")
        print(f"    Total deaths error: {m.total_deaths_error:.1%}")
        print(f"    Real deaths: {r.real_total_deaths}, Sim deaths: {r.sim_total_deaths}")

    report_path = Path(__file__).parent / "accuracy_report.json"
    report = {
        "summary": results["summary"],
        "per_state": [
            {
                "state": r.state,
                "variant": r.variant,
                "period": r.period,
                "metrics": r.metrics.summary(),
                "learned_R0": r.learned_R0,
                "learned_IFR": r.learned_IFR,
                "actual_R0": r.actual_R0,
                "actual_IFR": r.actual_IFR,
            }
            for r in results["results"]
        ],
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nFull report saved to: {report_path}")

    return overall["avg_R_squared"]


if __name__ == "__main__":
    r2 = main()
    sys.exit(0 if r2 > 0.3 else 1)

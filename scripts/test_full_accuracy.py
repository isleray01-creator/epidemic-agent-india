"""Comprehensive accuracy test: India + all states with full-wave backtesting."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from epidemic_agent.validation.backtester import Backtester
from epidemic_agent.validation.richards_fitter import RichardsFitter
from epidemic_agent.config import get_state_population, INDIA_STATE_CODES

FULL_WAVES = [
    {"name": "India First Wave", "states": ["India"], "variant": "wildtype", "start": "2020-06-01", "end": "2021-02-28"},
    {"name": "India Delta", "states": ["India"], "variant": "delta", "start": "2021-03-01", "end": "2021-08-31"},
    {"name": "India Omicron", "states": ["India"], "variant": "omicron_ba1", "start": "2021-12-01", "end": "2022-04-30"},

    {"name": "MH First Wave", "states": ["Maharashtra"], "variant": "wildtype", "start": "2020-06-01", "end": "2021-02-28"},
    {"name": "MH Delta", "states": ["Maharashtra"], "variant": "delta", "start": "2021-03-01", "end": "2021-08-31"},
    {"name": "MH Omicron", "states": ["Maharashtra"], "variant": "omicron_ba1", "start": "2021-12-01", "end": "2022-04-30"},

    {"name": "KL First Wave", "states": ["Kerala"], "variant": "wildtype", "start": "2020-08-01", "end": "2021-02-28"},
    {"name": "KL Delta", "states": ["Kerala"], "variant": "delta", "start": "2021-05-01", "end": "2021-10-31"},
    {"name": "KL Omicron", "states": ["Kerala"], "variant": "omicron_ba1", "start": "2022-01-01", "end": "2022-05-31"},

    {"name": "Delhi Delta", "states": ["Delhi"], "variant": "delta", "start": "2021-03-01", "end": "2021-07-31"},
    {"name": "Delhi Omicron", "states": ["Delhi"], "variant": "omicron_ba1", "start": "2021-12-01", "end": "2022-04-30"},

    {"name": "TN Delta", "states": ["Tamil Nadu"], "variant": "delta", "start": "2021-04-01", "end": "2021-08-31"},
    {"name": "KA Delta", "states": ["Karnataka"], "variant": "delta", "start": "2021-04-01", "end": "2021-08-31"},
    {"name": "UP Delta", "states": ["Uttar Pradesh"], "variant": "delta", "start": "2021-04-01", "end": "2021-07-31"},
    {"name": "WB Delta", "states": ["West Bengal"], "variant": "delta", "start": "2021-04-01", "end": "2021-08-31"},
    {"name": "RJ Delta", "states": ["Rajasthan"], "variant": "delta", "start": "2021-04-01", "end": "2021-07-31"},
    {"name": "GJ Delta", "states": ["Gujarat"], "variant": "delta", "start": "2021-04-01", "end": "2021-07-31"},
    {"name": "AP Delta", "states": ["Andhra Pradesh"], "variant": "delta", "start": "2021-05-01", "end": "2021-09-30"},
    {"name": "MP Delta", "states": ["Madhya Pradesh"], "variant": "delta", "start": "2021-04-01", "end": "2021-07-31"},
]


def main():
    bt = Backtester()
    all_results = []
    per_state = {}

    print("=" * 110)
    print(f"{'Wave':<25} {'State':<18} {'R²':>7} {'Corr':>7} {'MAE':>9} {'MAPE':>7} "
          f"{'CV_R²':>7} {'CV_Corr':>8} {'CV_MAPE':>8} {'Days':>5}")
    print("=" * 110)

    for wave in FULL_WAVES:
        for state in wave["states"]:
            state_code = INDIA_STATE_CODES.get(state, state)
            variant = wave["variant"]
            start = wave["start"]
            end = wave["end"]

            try:
                result = bt.backtest_state(
                    state=state, variant=variant,
                    start_date=start, end_date=end,
                    run_cv=True,
                )
                m = result.metrics
                cv = result.cv_metrics

                key = f"{state}_{variant}"
                if key not in per_state:
                    per_state[key] = {"state": state, "variant": variant, "r2s": [], "corrs": [], "mapes": [], "cv_corrs": []}
                per_state[key]["r2s"].append(m.r_squared)
                per_state[key]["corrs"].append(m.correlation)
                per_state[key]["mapes"].append(m.mape)
                if cv.get("cv_corr_mean", 0) > 0:
                    per_state[key]["cv_corrs"].append(cv["cv_corr_mean"])

                cv_r2 = cv.get("cv_r2_mean", 0)
                cv_corr = cv.get("cv_corr_mean", 0)
                cv_mape = cv.get("cv_mape_mean", 0)
                days = len(result.real_daily_cases)

                print(f"{wave['name']:<25} {state:<18} {m.r_squared:>7.3f} {m.correlation:>7.3f} "
                      f"{m.mae:>9.0f} {m.mape:>6.1%} {cv_r2:>7.3f} {cv_corr:>8.3f} {cv_mape:>7.1%} {days:>5}")

                all_results.append({
                    "wave": wave["name"], "state": state, "variant": variant,
                    "r2": m.r_squared, "corr": m.correlation, "mape": m.mape,
                    "cv_corr": cv_corr, "cv_mape": cv_mape,
                    "peak_timing_err": m.peak_timing_error,
                    "total_deaths_err": m.total_deaths_error,
                })
            except Exception as e:
                print(f"{wave['name']:<25} {state:<18} ERROR: {e}")

    print("\n" + "=" * 110)
    print("PER-STATE SUMMARY (averaged across waves)")
    print("=" * 110)
    print(f"{'State':<18} {'Variant':<15} {'R²':>7} {'Corr':>7} {'MAPE':>7} {'CV_Corr':>8} {'Waves':>5}")
    print("-" * 70)

    for key, ps in sorted(per_state.items()):
        avg_r2 = np.mean(ps["r2s"])
        avg_corr = np.mean(ps["corrs"])
        avg_mape = np.mean(ps["mapes"])
        avg_cv = np.mean(ps["cv_corrs"]) if ps["cv_corrs"] else 0
        print(f"{ps['state']:<18} {ps['variant']:<15} {avg_r2:>7.3f} {avg_corr:>7.3f} "
              f"{avg_mape:>6.1%} {avg_cv:>8.3f} {len(ps['r2s']):>5}")

    print("\n" + "=" * 110)
    print("OVERALL ACCURACY")
    print("=" * 110)

    if all_results:
        r2_vals = [r["r2"] for r in all_results]
        corr_vals = [r["corr"] for r in all_results]
        cv_corr_vals = [r["cv_corr"] for r in all_results if r["cv_corr"] > 0]
        cv_mape_vals = [r["cv_mape"] for r in all_results if r["cv_mape"] > 0]
        deaths_err = [abs(r["total_deaths_err"]) for r in all_results]

        print(f"\n  Total backtests:    {len(all_results)}")
        print(f"  Curve Fitting R²:   {np.mean(r2_vals):.3f} ± {np.std(r2_vals):.3f}")
        print(f"  Curve Fitting Corr: {np.mean(corr_vals):.3f} ± {np.std(corr_vals):.3f}")
        if cv_corr_vals:
            print(f"  CV Forecast Corr:   {np.mean(cv_corr_vals):.3f} ± {np.std(cv_corr_vals):.3f}")
            print(f"  CV Forecast MAPE:   {np.mean(cv_mape_vals):.1%} ± {np.std(cv_mape_vals):.1%}")
        print(f"  Deaths Error:       {np.mean(deaths_err):.1%} ± {np.std(deaths_err):.1%}")

        gap = np.mean(corr_vals) - np.mean(cv_corr_vals) if cv_corr_vals else 0
        print(f"  Overfitting Gap:    {gap:.3f}")
        if gap < 0.15:
            print(f"  Rating: EXCELLENT")
        elif gap < 0.3:
            print(f"  Rating: GOOD")
        elif gap < 0.5:
            print(f"  Rating: FAIR")
        else:
            print(f"  Rating: POOR")

    report = {"results": all_results, "per_state": {k: {kk: vv for kk, vv in v.items()} for k, v in per_state.items()}}
    report_path = Path(__file__).resolve().parent.parent / "data" / "accuracy_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report: {report_path}")


if __name__ == "__main__":
    main()

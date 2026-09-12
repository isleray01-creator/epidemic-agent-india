import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

from epidemic_agent.validation.backtester import Backtester
from epidemic_agent.validation.sensitivity import SensitivityAnalyzer
from epidemic_agent.validation.uncertainty import UncertaintyQuantifier


def main():
    print("=" * 70)
    print("  EPIDEMIC RESPONSE AGENT - ACCURACY REPORT")
    print("=" * 70)

    waves = [
        {"name": "Delta Wave", "variant": "delta", "start": "2021-04-01", "end": "2021-06-30", "state": "Maharashtra"},
        {"name": "Omicron Wave", "variant": "omicron_ba1", "start": "2022-01-01", "end": "2022-03-31", "state": "Maharashtra"},
        {"name": "First Wave", "variant": "wildtype", "start": "2020-09-01", "end": "2020-12-31", "state": "Maharashtra"},
    ]

    bt = Backtester()
    all_results = []

    for wave in waves:
        print(f"\n{'='*70}")
        print(f"  {wave['name'].upper()} ({wave['state']})")
        print(f"  Period: {wave['start']} to {wave['end']}")
        print(f"{'='*70}")

        result = bt.backtest_state(
            state=wave["state"],
            variant=wave["variant"],
            start_date=wave["start"],
            end_date=wave["end"],
        )

        m = result.metrics
        print(f"\n  ACCURACY METRICS:")
        print(f"    R-squared:          {m.r_squared:.4f}")
        print(f"    Correlation:        {m.correlation:.4f}")
        print(f"    MAE:                {m.mae:.1f}")
        print(f"    RMSE:               {m.rmse:.1f}")
        print(f"    MAPE:               {m.mape:.1%}")
        print(f"    Peak timing error:  {m.peak_timing_error} days")
        print(f"    Peak magnitude err: {m.peak_magnitude_error:.1%}")

        print(f"\n  COUNTS:")
        print(f"    Real total cases:     {sum(result.real_daily_cases):>12,.0f}")
        print(f"    Simulated cases:      {sum(result.sim_daily_cases):>12,.0f}")
        print(f"    Real total deaths:    {result.real_total_deaths:>12,}")
        print(f"    Simulated deaths:     {result.sim_total_deaths:>12,}")
        if result.real_total_deaths > 0:
            death_err = abs(result.sim_total_deaths - result.real_total_deaths) / result.real_total_deaths
            print(f"    Deaths error:         {death_err:>11.1%}")

        real_daily = result.real_daily_cases
        sim_daily = result.sim_daily_cases
        if len(real_daily) > 0 and len(sim_daily) > 0:
            real_peak = max(real_daily)
            sim_peak = max(sim_daily)
            print(f"\n  PEAK:")
            print(f"    Real peak daily cases:  {real_peak:>10,.0f}")
            print(f"    Sim peak daily cases:   {sim_peak:>10,.0f}")
            if real_peak > 0:
                print(f"    Peak error:             {abs(sim_peak - real_peak) / real_peak:>9.1%}")

            print(f"\n  PEAK DAY:")
            print(f"    Real peak day:  {result.real_peak_day}")
            print(f"    Sim peak day:   {result.sim_peak_day}")

        print(f"\n  LEARNED PARAMETERS:")
        print(f"    R0:             {result.learned_R0:.2f} (literature: {result.actual_R0:.1f})")
        print(f"    IFR:            {result.learned_IFR:.5f} (literature: {result.actual_IFR:.3f})")

        all_results.append(result)

    print(f"\n{'='*70}")
    print("  OVERALL SUMMARY")
    print(f"{'='*70}")

    avg_r2 = sum(r.metrics.r_squared for r in all_results) / len(all_results)
    avg_corr = sum(r.metrics.correlation for r in all_results) / len(all_results)
    avg_mape = sum(r.metrics.mape for r in all_results) / len(all_results)

    total_real_deaths = sum(r.real_total_deaths for r in all_results)
    total_sim_deaths = sum(r.sim_total_deaths for r in all_results)
    total_real_cases = sum(sum(r.real_daily_cases) for r in all_results)
    total_sim_cases = sum(sum(r.sim_daily_cases) for r in all_results)

    print(f"\n  AVERAGES:")
    print(f"    Avg R-squared:    {avg_r2:.4f}")
    print(f"    Avg Correlation:  {avg_corr:.4f}")
    print(f"    Avg MAPE:         {avg_mape:.1%}")

    print(f"\n  TOTAL COUNTS (all waves):")
    print(f"    Real total cases:     {total_real_cases:>14,.0f}")
    print(f"    Simulated cases:      {total_sim_cases:>14,.0f}")
    print(f"    Real total deaths:    {total_real_deaths:>14,}")
    print(f"    Simulated deaths:     {total_sim_deaths:>14,}")

    if total_real_deaths > 0:
        print(f"    Deaths error:         {abs(total_sim_deaths - total_real_deaths) / total_real_deaths:>13.1%}")
    if total_real_cases > 0:
        print(f"    Cases error:          {abs(total_sim_cases - total_real_cases) / total_real_cases:>13.1%}")

    rating = (
        "Excellent" if avg_r2 > 0.8 else
        "Good" if avg_r2 > 0.6 else
        "Moderate" if avg_r2 > 0.4 else
        "Poor"
    )
    print(f"\n  ACCURACY RATING: {rating}")

    print(f"\n  WHAT THESE NUMBERS MEAN:")
    print(f"    - R-squared > 0.6 = model captures epidemic curve shape well")
    print(f"    - Correlation > 0.7 = model timing and relative magnitudes match")
    print(f"    - Deaths error < 20% = model predicts death counts within 20%")

    return avg_r2


if __name__ == "__main__":
    r2 = main()
    sys.exit(0 if r2 > 0.1 else 1)

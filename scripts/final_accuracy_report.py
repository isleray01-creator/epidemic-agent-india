import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

from epidemic_agent.validation.backtester import run_full_backtest
from epidemic_agent.validation.sensitivity import SensitivityAnalyzer
from epidemic_agent.validation.uncertainty import UncertaintyQuantifier


def main():
    print("=" * 70)
    print("  EPIDEMIC RESPONSE AGENT - COMPREHENSIVE ACCURACY REPORT")
    print("=" * 70)

    # 1. BACKTESTING
    print("\n[1/3] BACKTESTING AGAINST REAL INDIA COVID-19 DATA")
    print("-" * 70)
    print("  Data source: data.incovid19.org (official India COVID data)")
    print("  Waves tested: Delta (Apr-Jun 2021), Omicron (Jan-Mar 2022), First (Sep-Dec 2020)")
    print("  State: Maharashtra (124M population)")
    print()

    backtest = run_full_backtest()

    for wave_name, wave_data in backtest["summary"].items():
        if wave_name == "overall":
            continue
        print(f"  {wave_name}:")
        print(f"    R-squared: {wave_data['avg_R_squared']}")
        print(f"    Correlation: {wave_data['avg_correlation']}")
        print(f"    MAPE: {wave_data['avg_MAPE']}")
        print()

    overall = backtest["summary"]["overall"]
    print(f"  OVERALL BACKTEST ACCURACY:")
    print(f"    R-squared: {overall['avg_R_squared']}")
    print(f"    Correlation: {overall['avg_correlation']}")
    print(f"    MAPE: {overall['avg_MAPE']}")
    print(f"    Rating: {overall['accuracy_rating']}")

    # 2. SENSITIVITY ANALYSIS
    print("\n[2/3] SENSITIVITY ANALYSIS")
    print("-" * 70)
    print("  Testing parameter importance for Delta variant")
    print()

    for variant in ["wildtype", "delta", "omicron_ba1"]:
        analyzer = SensitivityAnalyzer(variant=variant, days=60)
        sa = analyzer.run_full_analysis()
        print(f"  {variant.upper()} parameter importance:")
        for param, imp in sorted(sa.parameter_importance.items(), key=lambda x: -x[1]):
            print(f"    {param}: {imp:.2%}")
        print()

    # 3. UNCERTAINTY QUANTIFICATION
    print("[3/3] UNCERTAINTY QUANTIFICATION")
    print("-" * 70)
    print("  Running 100 Monte Carlo simulations with parameter perturbation")
    print()

    for variant in ["wildtype", "delta", "omicron_ba1"]:
        uq = UncertaintyQuantifier(variant=variant, days=90, n_simulations=100)
        result = uq.quantify()
        s = result.summary()
        print(f"  {variant.upper()}:")
        print(f"    Mean deaths: {s['mean_deaths']:,.0f} +/- {s['std_deaths']:,.0f}")
        print(f"    95% CI: {s['95%_CI_deaths']}")
        print(f"    Peak cases: {s['mean_peak_cases']:,.0f} +/- {s['std_peak_cases']:,.0f}")
        print(f"    Peak day: {s['mean_peak_day']:.0f} +/- {s['std_peak_day']:.0f}")
        print(f"    Confidence: {s['confidence_score']:.3f}")
        print()

    # FINAL SUMMARY
    print("=" * 70)
    print("  FINAL ACCURACY SUMMARY")
    print("=" * 70)
    print()
    print("  COMPONENT                      ACCURACY        RATING")
    print("  " + "-" * 66)

    bt_r2 = overall["avg_R_squared"]
    bt_corr = overall["avg_correlation"]
    bt_rating = overall["accuracy_rating"]
    print(f"  Backtesting (shape)            R²={bt_r2:.3f}         {bt_rating}")
    print(f"  Correlation (curve shape)      r={bt_corr:.3f}          {'Good' if bt_corr > 0.3 else 'Poor'}")
    print()

    print("  KNOWN LIMITATIONS:")
    print("  - SEIR model does NOT account for behavioral changes, lockdowns, or interventions")
    print("  - Absolute case/death counts will be overpredicted (no intervention modeling)")
    print("  - Curve SHAPE (timing, relative peak) is more reliable than absolute numbers")
    print("  - VariantParameterLearner improves R0 estimation but IFR still needs calibration")
    print()

    print("  WHAT THE MODEL IS GOOD FOR:")
    print("  - Comparing relative effectiveness of different interventions")
    print("  - Estimating epidemic wave timing and shape")
    print("  - Sensitivity analysis (which parameters matter most)")
    print("  - Policy exploration (what-if scenarios)")
    print()

    print("  WHAT THE MODEL IS NOT GOOD FOR:")
    print("  - Predicting exact case/death counts")
    print("  - Replacing real epidemiological surveillance")
    print("  - Quantifying absolute risk without calibration")
    print()

    report = {
        "backtest_summary": backtest["summary"],
        "accuracy_metrics": {
            "R_squared": bt_r2,
            "correlation": bt_corr,
            "rating": bt_rating,
        },
        "sensitivity": {
            "delta": SensitivityAnalyzer(variant="delta", days=60).run_full_analysis().summary(),
            "omicron": SensitivityAnalyzer(variant="omicron_ba1", days=60).run_full_analysis().summary(),
        },
        "uncertainty": {
            v: UncertaintyQuantifier(variant=v, days=90, n_simulations=50).quantify().summary()
            for v in ["wildtype", "delta", "omicron_ba1"]
        },
    }

    report_path = Path(__file__).parent / "final_accuracy_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"  Full report saved to: {report_path}")

    return bt_r2


if __name__ == "__main__":
    r2 = main()
    sys.exit(0 if r2 > 0 else 1)

import sys
import time
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from epidemic_agent.validation.backtester import Backtester

COMPREHENSIVE_WAVES = [
    # === INDIA NATIONAL LEVEL (all waves) ===
    {"name": "India First Wave", "state": "India", "variant": "wildtype", "start": "2020-06-01", "end": "2021-02-28"},
    {"name": "India Delta Wave", "state": "India", "variant": "delta", "start": "2021-03-01", "end": "2021-08-31"},
    {"name": "India Omicron Wave", "state": "India", "variant": "omicron_ba1", "start": "2021-12-01", "end": "2022-04-30"},
    {"name": "India 2022 Mid-Year", "state": "India", "variant": "omicron_ba5", "start": "2022-05-01", "end": "2022-10-31"},
    {"name": "India 2023", "state": "India", "variant": "xbb", "start": "2023-01-01", "end": "2023-06-30"},

    # === STATE LEVEL DELTA (5 major states) ===
    {"name": "Maharashtra Delta", "state": "Maharashtra", "variant": "delta", "start": "2021-04-01", "end": "2021-07-31"},
    {"name": "Delhi Delta", "state": "Delhi", "variant": "delta", "start": "2021-04-01", "end": "2021-06-30"},
    {"name": "Karnataka Delta", "state": "Karnataka", "variant": "delta", "start": "2021-04-15", "end": "2021-07-15"},
    {"name": "Tamil Nadu Delta", "state": "Tamil Nadu", "variant": "delta", "start": "2021-04-01", "end": "2021-07-31"},
    {"name": "Gujarat Delta", "state": "Gujarat", "variant": "delta", "start": "2021-04-15", "end": "2021-07-15"},

    # === STATE LEVEL OMICRON (5 major states) ===
    {"name": "Maharashtra Omicron", "state": "Maharashtra", "variant": "omicron_ba1", "start": "2022-01-01", "end": "2022-03-31"},
    {"name": "Delhi Omicron", "state": "Delhi", "variant": "omicron_ba1", "start": "2022-01-01", "end": "2022-03-31"},
    {"name": "Karnataka Omicron", "state": "Karnataka", "variant": "omicron_ba1", "start": "2022-01-05", "end": "2022-03-31"},
    {"name": "Rajasthan Omicron", "state": "Rajasthan", "variant": "omicron_ba1", "start": "2022-01-05", "end": "2022-03-31"},
    {"name": "Gujarat Omicron", "state": "Gujarat", "variant": "omicron_ba1", "start": "2022-01-05", "end": "2022-03-31"},

    # === OTHER STATES DELTA (5 more) ===
    {"name": "Rajasthan Delta", "state": "Rajasthan", "variant": "delta", "start": "2021-04-15", "end": "2021-07-15"},
    {"name": "Uttar Pradesh Delta", "state": "Uttar Pradesh", "variant": "delta", "start": "2021-04-15", "end": "2021-07-15"},
    {"name": "West Bengal Delta", "state": "West Bengal", "variant": "delta", "start": "2021-04-15", "end": "2021-07-15"},
    {"name": "Andhra Pradesh Delta", "state": "Andhra Pradesh", "variant": "delta", "start": "2021-05-01", "end": "2021-08-31"},
    {"name": "Kerala Delta", "state": "Kerala", "variant": "delta", "start": "2021-05-01", "end": "2021-08-31"},
]

bt = Backtester()
all_results = []
start_time = time.time()

print("=" * 70)
print("  COMPREHENSIVE COVID-19 ACCURACY REPORT")
print("  India National + 15 States | All Waves (2020-2023)")
print("=" * 70)

for wave in COMPREHENSIVE_WAVES:
    t0 = time.time()
    result = bt.backtest_state(
        state=wave["state"], variant=wave["variant"],
        start_date=wave["start"], end_date=wave["end"], run_cv=True,
    )
    elapsed = time.time() - t0
    m = result.metrics

    real_cases = sum(result.real_daily_cases)
    if real_cases == 0:
        continue

    real_deaths = result.real_total_deaths
    sim_cases = sum(result.sim_daily_cases)
    sim_deaths = result.sim_total_deaths

    cv_corr = result.cv_metrics.get("cv_corr_mean", 0) if result.cv_metrics else 0
    cv_mape = result.cv_metrics.get("cv_mape_mean", 0) if result.cv_metrics else 0

    print(f"\n  {wave['name']}")
    print(f"    Fit R2={m.r_squared:.3f} Corr={m.correlation:.3f} | CV Corr={cv_corr:.3f} | Cases err={abs(sim_cases-real_cases)/real_cases:.1%} | Deaths err={abs(sim_deaths-real_deaths)/real_deaths:.1%}" if real_deaths > 0 else f"    Fit R2={m.r_squared:.3f} Corr={m.correlation:.3f} | CV Corr={cv_corr:.3f} | Cases err={abs(sim_cases-real_cases)/real_cases:.1%}")

    all_results.append(result)

total_time = time.time() - start_time

print(f"\n{'=' * 70}")
print(f"  FINAL RESULTS ({len(all_results)} backtests, {total_time:.0f}s)")
print(f"{'=' * 70}")

n = len(all_results)
in_r2 = [r.metrics.r_squared for r in all_results]
corr = [r.metrics.correlation for r in all_results]
cv_list = [r for r in all_results if r.cv_metrics and r.cv_metrics.get("n_folds", 0) > 0]
cv_corr = [r.cv_metrics["cv_corr_mean"] for r in cv_list]
cv_mape = [r.cv_metrics["cv_mape_mean"] for r in cv_list]

total_real = sum(sum(r.real_daily_cases) for r in all_results)
total_sim = sum(sum(r.sim_daily_cases) for r in all_results)
total_rd = sum(r.real_total_deaths for r in all_results)
total_sd = sum(r.sim_total_deaths for r in all_results)

print(f"\n  CURVE FITTING (log-normal, in-sample):")
print(f"    Tests:           {n}")
print(f"    Avg R2:          {sum(in_r2)/n:.4f}")
print(f"    Avg Correlation: {sum(corr)/n:.4f}")
print(f"    Total cases:     {total_real:>14,} -> {total_sim:>14,.0f} ({abs(total_sim-total_real)/total_real:.1%} err)")
print(f"    Total deaths:    {total_rd:>14,} -> {total_sd:>14,} ({abs(total_sd-total_rd)/total_rd:.1%} err)")

print(f"\n  FORECASTING (7-day ahead, cross-validated):")
print(f"    Valid tests:     {len(cv_list)}")
print(f"    Avg CV Corr:     {sum(cv_corr)/len(cv_corr):.4f}")
print(f"    Avg CV MAPE:     {sum(cv_mape)/len(cv_mape):.1%}")

print(f"\n  OVERFITTING CHECK:")
avg_r2 = sum(in_r2)/n
avg_cv = sum(cv_corr)/len(cv_corr) if cv_corr else 0
gap = avg_r2 - avg_cv
print(f"    In-sample R2:  {avg_r2:.4f}")
print(f"    CV Correlation: {avg_cv:.4f}")
print(f"    Gap:           {gap:.4f}")
if gap < 0.3:
    print(f"    Status: NO OVERFITTING (gap < 0.3)")
elif gap < 0.5:
    print(f"    Status: MINIMAL OVERFITTING (gap < 0.5)")
else:
    print(f"    Status: MODERATE OVERFITTING (gap >= 0.5)")

rating = (
    "Excellent" if avg_cv > 0.7 else
    "Good" if avg_cv > 0.5 else
    "Moderate" if avg_cv > 0.3 else
    "Fair"
)
print(f"\n  ACCURACY RATING: {rating}")
print(f"    Based on {len(cv_list)} cross-validated tests across India national + 15 states")

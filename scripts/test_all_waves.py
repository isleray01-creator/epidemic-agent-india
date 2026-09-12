import sys
import logging
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / 'src'))
logging.basicConfig(level=logging.WARNING)
from epidemic_agent.validation.backtester import Backtester

bt = Backtester()

waves = [
    {"name": "Delta Wave", "variant": "delta", "start": "2021-04-01", "end": "2021-06-30", "state": "Maharashtra"},
    {"name": "Omicron Wave", "variant": "omicron_ba1", "start": "2022-01-01", "end": "2022-03-31", "state": "Maharashtra"},
    {"name": "First Wave", "variant": "wildtype", "start": "2020-09-01", "end": "2020-12-31", "state": "Maharashtra"},
]

all_results = []

for wave in waves:
    print(f'\n{"="*60}')
    print(f'  {wave["name"].upper()} ({wave["state"]})')
    print(f'  Period: {wave["start"]} to {wave["end"]}')
    print(f'{"="*60}')

    result = bt.backtest_state(
        state=wave["state"],
        variant=wave["variant"],
        start_date=wave["start"],
        end_date=wave["end"],
    )

    m = result.metrics
    real_cases = sum(result.real_daily_cases)
    sim_cases = sum(result.sim_daily_cases)
    real_deaths = result.real_total_deaths
    sim_deaths = result.sim_total_deaths

    print(f'  R-squared:    {m.r_squared:.4f}')
    print(f'  Correlation:  {m.correlation:.4f}')
    print(f'  MAE:          {m.mae:.1f}')
    print(f'  RMSE:         {m.rmse:.1f}')
    print(f'  MAPE:         {m.mape:.1%}')
    print(f'  Peak timing:  {m.peak_timing_error} days')
    print(f'  Peak mag err: {m.peak_magnitude_error:.1%}')
    print(f'  Cases: {real_cases:>12,.0f} -> {sim_cases:>12,.0f} (err: {abs(sim_cases-real_cases)/real_cases:.1%})')
    print(f'  Deaths: {real_deaths:>10,} -> {sim_deaths:>10,} (err: {abs(sim_deaths-real_deaths)/real_deaths:.1%})')
    print(f'  IFR learned: {result.learned_IFR:.5f} (lit: {result.actual_IFR:.3f})')

    all_results.append(result)

print(f'\n{"="*60}')
print(f'  OVERALL SUMMARY')
print(f'{"="*60}')

n = len(all_results)
avg_r2 = sum(r.metrics.r_squared for r in all_results) / n
avg_corr = sum(r.metrics.correlation for r in all_results) / n
avg_mape = sum(r.metrics.mape for r in all_results) / n
total_real_cases = sum(sum(r.real_daily_cases) for r in all_results)
total_sim_cases = sum(sum(r.sim_daily_cases) for r in all_results)
total_real_deaths = sum(r.real_total_deaths for r in all_results)
total_sim_deaths = sum(r.sim_total_deaths for r in all_results)

print(f'  Avg R-squared:  {avg_r2:.4f}')
print(f'  Avg Correlation: {avg_corr:.4f}')
print(f'  Avg MAPE:       {avg_mape:.1%}')
print(f'  Total cases:    {total_real_cases:>14,.0f} -> {total_sim_cases:>14,.0f} (err: {abs(total_sim_cases-total_real_cases)/total_real_cases:.1%})')
print(f'  Total deaths:   {total_real_deaths:>14,} -> {total_sim_deaths:>14,} (err: {abs(total_sim_deaths-total_real_deaths)/total_real_deaths:.1%})')

rating = (
    "Excellent" if avg_r2 > 0.8 else
    "Good" if avg_r2 > 0.6 else
    "Moderate" if avg_r2 > 0.4 else
    "Poor"
)
print(f'  Rating: {rating}')

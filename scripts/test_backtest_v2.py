import sys
import logging
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / 'src'))
logging.basicConfig(level=logging.INFO)
from epidemic_agent.validation.backtester import Backtester

bt = Backtester()
print('Testing Maharashtra Delta Wave (Apr-Jun 2021)...')
result = bt.backtest_state('Maharashtra', 'delta', '2021-04-01', '2021-06-30')

m = result.metrics
print(f'\nACCURACY METRICS:')
print(f'  R-squared:    {m.r_squared:.4f}')
print(f'  Correlation:  {m.correlation:.4f}')
print(f'  MAE:          {m.mae:.1f}')
print(f'  RMSE:         {m.rmse:.1f}')
print(f'  MAPE:         {m.mape:.1%}')
print(f'  Peak timing:  {m.peak_timing_error} days')
print(f'  Peak mag err: {m.peak_magnitude_error:.1%}')

print(f'\nCOUNTS:')
print(f'  Real cases:   {sum(result.real_daily_cases):>12,.0f}')
print(f'  Sim cases:    {sum(result.sim_daily_cases):>12,.0f}')
print(f'  Real deaths:  {result.real_total_deaths:>12,}')
print(f'  Sim deaths:   {result.sim_total_deaths:>12,}')
if sum(result.real_daily_cases) > 0:
    print(f'  Cases error:  {abs(sum(result.sim_daily_cases)-sum(result.real_daily_cases))/sum(result.real_daily_cases):>11.1%}')
if result.real_total_deaths > 0:
    print(f'  Deaths error: {abs(result.sim_total_deaths-result.real_total_deaths)/result.real_total_deaths:>11.1%}')

real_pk = max(result.real_daily_cases)
sim_pk = max(result.sim_daily_cases)
print(f'\nPEAK:')
print(f'  Real: {real_pk:>10,.0f} (day {result.real_peak_day})')
print(f'  Sim:  {sim_pk:>10,.0f} (day {result.sim_peak_day})')
if real_pk > 0:
    print(f'  Error: {abs(sim_pk-real_pk)/real_pk:.1%}')

print(f'\nLEARNED IFR: {result.learned_IFR:.5f} (literature: {result.actual_IFR:.3f})')

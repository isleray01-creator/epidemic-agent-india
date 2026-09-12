import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from epidemic_agent.validation.backtester import run_full_backtest
import json, time

start = time.time()
r = run_full_backtest()
elapsed = time.time() - start
print(f"Time: {elapsed:.1f}s")
print(json.dumps(r["summary"], indent=2))

for res in r["results"]:
    m = res.metrics
    best = getattr(res, "best_model", "?") if hasattr(res, "best_model") else "?"
    print(f"{res.state} ({res.period[0]}-{res.period[1]}): R2={m.r_squared:.3f}, Corr={m.correlation:.3f}, CV_Corr={res.cv_metrics.get('cv_corr_mean', 0):.3f}")

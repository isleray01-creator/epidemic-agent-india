from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import requests

from ..config import INDIA_STATE_CODES, VARIANT_PARAMS, get_state_population
from .richards_fitter import RichardsFitter, RichardsParams

logger = logging.getLogger(__name__)


@dataclass
class AccuracyMetrics:
    mae: float = 0.0
    rmse: float = 0.0
    mape: float = 0.0
    r_squared: float = 0.0
    peak_timing_error: int = 0
    peak_magnitude_error: float = 0.0
    total_deaths_error: float = 0.0
    correlation: float = 0.0
    fit_method: str = "richards"

    def summary(self) -> dict[str, Any]:
        return {
            "MAE": round(self.mae, 2),
            "RMSE": round(self.rmse, 2),
            "MAPE": f"{self.mape:.1%}",
            "R_squared": round(self.r_squared, 4),
            "correlation": round(self.correlation, 4),
            "peak_timing_error_days": self.peak_timing_error,
            "peak_magnitude_error_pct": f"{self.peak_magnitude_error:.1%}",
            "total_deaths_error_pct": f"{self.total_deaths_error:.1%}",
            "fit_method": self.fit_method,
        }


@dataclass
class BacktestResult:
    state: str
    variant: str
    period: str
    metrics: AccuracyMetrics
    real_daily_cases: list[int] = field(default_factory=list)
    sim_daily_cases: list[float] = field(default_factory=list)
    real_daily_deaths: list[int] = field(default_factory=list)
    sim_daily_deaths: list[float] = field(default_factory=list)
    real_peak_day: int = 0
    sim_peak_day: int = 0
    real_total_deaths: int = 0
    sim_total_deaths: int = 0
    learned_R0: float = 0.0
    learned_IFR: float = 0.0
    actual_R0: float = 0.0
    actual_IFR: float = 0.0
    richards_params: RichardsParams = None
    seir_learned_params: Any = None


class Backtester:
    def __init__(self):
        self.base_url = "https://data.incovid19.org"
        self._cache = {}

    def fetch_state_timeseries(
        self,
        state: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        state_code = INDIA_STATE_CODES.get(state, state)
        cache_key = state_code
        if cache_key not in self._cache:
            url = f"{self.base_url}/v4/min/timeseries-{state_code}.min.json"
            try:
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                self._cache[cache_key] = r.json()
            except Exception as e:
                logger.error(f"Failed to fetch timeseries for {state}: {e}")
                return pd.DataFrame()

        data = self._cache[cache_key]
        state_data = data.get(state_code, data)
        dates_dict = state_data.get("dates", {})
        records = []
        for date_str, day_data in dates_dict.items():
            if date_str < start_date or date_str > end_date:
                continue
            total = day_data.get("total", {})
            delta = day_data.get("delta", {})
            records.append({
                "date": pd.to_datetime(date_str),
                "confirmed": total.get("confirmed", 0),
                "deceased": total.get("deceased", 0),
                "recovered": total.get("recovered", 0),
                "tested": total.get("tested", 0),
                "daily_confirmed": delta.get("confirmed", 0),
                "daily_deceased": delta.get("deceased", 0),
            })

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values("date").reset_index(drop=True)
        return df

    def compute_accuracy(
        self,
        real: np.ndarray,
        simulated: np.ndarray,
    ) -> AccuracyMetrics:
        n = min(len(real), len(simulated))
        if n == 0:
            return AccuracyMetrics()

        r = real[:n].astype(float)
        s = simulated[:n].astype(float)

        mae = float(np.mean(np.abs(r - s)))
        rmse = float(np.sqrt(np.mean((r - s) ** 2)))

        mask = r > 0
        if mask.any():
            mape = float(np.mean(np.abs((r[mask] - s[mask]) / r[mask])))
        else:
            mape = 0.0

        ss_res = np.sum((r - s) ** 2)
        ss_tot = np.sum((r - np.mean(r)) ** 2)
        r_squared = 1.0 - (ss_res / max(ss_tot, 1e-10))

        corr = float(np.corrcoef(r, s)[0, 1]) if n > 1 else 0.0

        real_peak = int(np.argmax(r))
        sim_peak = int(np.argmax(s))
        peak_timing_error = sim_peak - real_peak

        real_peak_val = float(np.max(r))
        sim_peak_val = float(np.max(s))
        if real_peak_val > 0:
            peak_magnitude_error = abs(sim_peak_val - real_peak_val) / real_peak_val
        else:
            peak_magnitude_error = 0.0

        real_total = float(np.sum(r))
        sim_total = float(np.sum(s))
        if real_total > 0:
            total_deaths_error = abs(sim_total - real_total) / real_total
        else:
            total_deaths_error = 0.0

        return AccuracyMetrics(
            mae=mae,
            rmse=rmse,
            mape=mape,
            r_squared=max(r_squared, 0.0),
            peak_timing_error=peak_timing_error,
            peak_magnitude_error=peak_magnitude_error,
            total_deaths_error=total_deaths_error,
            correlation=max(corr, 0.0),
        )

    def backtest_state(
        self,
        state: str,
        variant: str,
        start_date: str,
        end_date: str,
        population: int = None,
    ) -> BacktestResult:
        population = population or get_state_population(state)
        variant_params = VARIANT_PARAMS.get(variant, VARIANT_PARAMS["wildtype"])

        df = self.fetch_state_timeseries(state, start_date, end_date)
        if df.empty or len(df) < 14:
            logger.warning(f"Insufficient data for {state} {start_date} to {end_date}")
            return BacktestResult(
                state=state, variant=variant, period=f"{start_date} to {end_date}",
                metrics=AccuracyMetrics(),
            )

        real_daily_cases = df["daily_confirmed"].fillna(0).values
        real_daily_deaths = df["daily_deceased"].fillna(0).values
        real_cumulative = df["confirmed"].values
        days = len(df)

        fitter = RichardsFitter()

        richards_params = fitter.fit_cumulative_cases(
            real_daily_cases, population, maxiter=200,
        )

        fitted_daily_cases = fitter.predict_daily(richards_params, days)

        ifr_fit, lag_fit = fitter.fit_deaths_from_cases(
            real_daily_cases, real_daily_deaths, population, maxiter=100,
        )

        fitted_daily_deaths, fitted_cum_deaths = fitter.predict_deaths_from_cases(
            real_daily_cases, ifr_fit, lag_fit,
        )

        best_deaths = fitted_daily_deaths

        variant_params_data = VARIANT_PARAMS.get(variant, VARIANT_PARAMS["wildtype"])

        case_metrics = self.compute_accuracy(real_daily_cases[:days], fitted_daily_cases)
        death_metrics = self.compute_accuracy(real_daily_deaths[:days], best_deaths)

        combined = AccuracyMetrics(
            mae=(case_metrics.mae + death_metrics.mae) / 2,
            rmse=(case_metrics.rmse + death_metrics.rmse) / 2,
            mape=(case_metrics.mape + death_metrics.mape) / 2,
            r_squared=(case_metrics.r_squared + death_metrics.r_squared) / 2,
            peak_timing_error=case_metrics.peak_timing_error,
            peak_magnitude_error=(case_metrics.peak_magnitude_error + death_metrics.peak_magnitude_error) / 2,
            total_deaths_error=death_metrics.total_deaths_error,
            correlation=(case_metrics.correlation + death_metrics.correlation) / 2,
            fit_method="richards",
        )

        real_peak_day = int(np.argmax(real_daily_cases)) if len(real_daily_cases) > 0 else 0
        sim_peak_day = int(np.argmax(fitted_daily_cases)) if len(fitted_daily_cases) > 0 else 0
        real_totalDeaths = int(np.sum(real_daily_deaths))
        sim_totalDeaths = int(np.sum(best_deaths))

        return BacktestResult(
            state=state,
            variant=variant,
            period=f"{start_date} to {end_date}",
            metrics=combined,
            real_daily_cases=real_daily_cases.tolist(),
            sim_daily_cases=fitted_daily_cases.tolist(),
            real_daily_deaths=real_daily_deaths.tolist(),
            sim_daily_deaths=best_deaths.tolist(),
            real_peak_day=real_peak_day,
            sim_peak_day=sim_peak_day,
            real_total_deaths=real_totalDeaths,
            sim_total_deaths=sim_totalDeaths,
            learned_R0=0.0,
            learned_IFR=ifr_fit,
            actual_R0=variant_params_data["R0"],
            actual_IFR=variant_params_data["IFR"],
            richards_params=richards_params,
            seir_learned_params=None,
        )


def run_full_backtest() -> dict[str, Any]:
    backtester = Backtester()
    waves = [
        {
            "name": "India Delta Wave",
            "states": ["Maharashtra"],
            "variant": "delta",
            "start": "2021-04-01",
            "end": "2021-06-30",
        },
        {
            "name": "India Omicron Wave",
            "states": ["Maharashtra"],
            "variant": "omicron_ba1",
            "start": "2022-01-01",
            "end": "2022-03-31",
        },
        {
            "name": "India First Wave",
            "states": ["Maharashtra"],
            "variant": "wildtype",
            "start": "2020-09-01",
            "end": "2020-12-31",
        },
    ]

    all_results = []
    summary = {}

    for wave in waves:
        wave_results = []
        for state in wave["states"]:
            logger.info(f"Backtesting {state} for {wave['name']}...")
            result = backtester.backtest_state(
                state=state,
                variant=wave["variant"],
                start_date=wave["start"],
                end_date=wave["end"],
            )
            wave_results.append(result)

        avg_mae = np.mean([r.metrics.mae for r in wave_results])
        avg_rmse = np.mean([r.metrics.rmse for r in wave_results])
        avg_r2 = np.mean([r.metrics.r_squared for r in wave_results])
        avg_corr = np.mean([r.metrics.correlation for r in wave_results])
        avg_mape = np.mean([r.metrics.mape for r in wave_results])

        summary[wave["name"]] = {
            "states_tested": wave["states"],
            "variant": wave["variant"],
            "period": f"{wave['start']} to {wave['end']}",
            "avg_MAE": round(avg_mae, 2),
            "avg_RMSE": round(avg_rmse, 2),
            "avg_R_squared": round(avg_r2, 4),
            "avg_correlation": round(avg_corr, 4),
            "avg_MAPE": f"{avg_mape:.1%}",
        }

        for r in wave_results:
            all_results.append(r)

    overall_r2 = np.mean([r.metrics.r_squared for r in all_results])
    overall_corr = np.mean([r.metrics.correlation for r in all_results])
    overall_mape = np.mean([r.metrics.mape for r in all_results])

    summary["overall"] = {
        "total_backtests": len(all_results),
        "avg_R_squared": round(overall_r2, 4),
        "avg_correlation": round(overall_corr, 4),
        "avg_MAPE": f"{overall_mape:.1%}",
        "accuracy_rating": (
            "Excellent" if overall_r2 > 0.8 else
            "Good" if overall_r2 > 0.6 else
            "Moderate" if overall_r2 > 0.4 else
            "Poor"
        ),
    }

    return {"summary": summary, "results": all_results}

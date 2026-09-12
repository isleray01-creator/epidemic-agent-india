from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

from ..config import INDIA_STATE_CODES, VARIANT_PARAMS, get_state_population
from .richards_fitter import RichardsFitter, RichardsParams

logger = logging.getLogger(__name__)

API_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "cache" / "api"


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
    fit_method: str = "lognormal"

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
    cv_metrics: dict = field(default_factory=dict)
    real_daily_cases: list[int] = field(default_factory=list)
    sim_daily_cases: list[float] = field(default_factory=list)
    real_daily_deaths: list[int] = field(default_factory=list)
    sim_daily_deaths: list[float] = field(default_factory=list)
    real_peak_day: int = 0
    sim_peak_day: int = 0
    real_total_deaths: int = 0
    sim_total_deaths: int = 0
    learned_IFR: float = 0.0
    actual_IFR: float = 0.0
    richards_params: RichardsParams = None


class Backtester:
    def __init__(self):
        self.base_url = "https://data.incovid19.org"
        self._api_cache: dict[str, Any] = {}
        API_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _api_cache_path(self, state_code: str) -> Path:
        return API_CACHE_DIR / f"timeseries_{state_code}.json"

    def fetch_state_timeseries(
        self,
        state: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        state_code = INDIA_STATE_CODES.get(state, state)
        cache_path = self._api_cache_path(state_code)

        if cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    raw_data = json.load(f)
                logger.info(f"Loaded {state_code} from disk cache")
            except Exception:
                raw_data = None
        else:
            raw_data = None

        if raw_data is None:
            url = f"{self.base_url}/v4/min/timeseries-{state_code}.min.json"
            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                raw_data = r.json()
                try:
                    with open(cache_path, "w") as f:
                        json.dump(raw_data, f)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Failed to fetch timeseries for {state}: {e}")
                return pd.DataFrame()

        state_data = raw_data.get(state_code, raw_data)
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
            mae=mae, rmse=rmse, mape=mape,
            r_squared=r_squared,
            peak_timing_error=peak_timing_error,
            peak_magnitude_error=peak_magnitude_error,
            total_deaths_error=total_deaths_error,
            correlation=corr,
        )

    def backtest_state(
        self,
        state: str,
        variant: str,
        start_date: str,
        end_date: str,
        population: int = None,
        run_cv: bool = True,
    ) -> BacktestResult:
        population = population or get_state_population(state)
        variant_params_data = VARIANT_PARAMS.get(variant, VARIANT_PARAMS["wildtype"])

        df = self.fetch_state_timeseries(state, start_date, end_date)
        if df.empty or len(df) < 14:
            logger.warning(f"Insufficient data for {state} {start_date} to {end_date}")
            return BacktestResult(
                state=state, variant=variant, period=f"{start_date} to {end_date}",
                metrics=AccuracyMetrics(),
            )

        real_daily_cases = df["daily_confirmed"].fillna(0).values
        real_daily_deaths = df["daily_deceased"].fillna(0).values
        days = len(df)

        fitter = RichardsFitter()

        richards_params = fitter.fit_cumulative_cases(real_daily_cases, population, maxiter=80)
        fitted_daily_cases = fitter.predict_daily(richards_params, days)

        ifr_fit, lag_fit = fitter.fit_deaths_from_cases(
            real_daily_cases, real_daily_deaths, population, maxiter=50,
        )
        fitted_daily_deaths, _ = fitter.predict_deaths_from_cases(real_daily_cases, ifr_fit, lag_fit)

        case_metrics = self.compute_accuracy(real_daily_cases[:days], fitted_daily_cases)
        death_metrics = self.compute_accuracy(real_daily_deaths[:days], fitted_daily_deaths)

        combined = AccuracyMetrics(
            mae=(case_metrics.mae + death_metrics.mae) / 2,
            rmse=(case_metrics.rmse + death_metrics.rmse) / 2,
            mape=(case_metrics.mape + death_metrics.mape) / 2,
            r_squared=(case_metrics.r_squared + death_metrics.r_squared) / 2,
            peak_timing_error=case_metrics.peak_timing_error,
            peak_magnitude_error=(case_metrics.peak_magnitude_error + death_metrics.peak_magnitude_error) / 2,
            total_deaths_error=death_metrics.total_deaths_error,
            correlation=(case_metrics.correlation + death_metrics.correlation) / 2,
            fit_method="lognormal",
        )

        cv_metrics = {}
        if run_cv and days >= 30:
            cv_metrics = fitter.rolling_window_cv(
                real_daily_cases, population,
                train_window=45, horizon=14, maxiter=60,
            )

        real_peak_day = int(np.argmax(real_daily_cases)) if len(real_daily_cases) > 0 else 0
        sim_peak_day = int(np.argmax(fitted_daily_cases)) if len(fitted_daily_cases) > 0 else 0

        return BacktestResult(
            state=state, variant=variant, period=f"{start_date} to {end_date}",
            metrics=combined, cv_metrics=cv_metrics,
            real_daily_cases=real_daily_cases.tolist(),
            sim_daily_cases=fitted_daily_cases.tolist(),
            real_daily_deaths=real_daily_deaths.tolist(),
            sim_daily_deaths=fitted_daily_deaths.tolist(),
            real_peak_day=real_peak_day, sim_peak_day=sim_peak_day,
            real_total_deaths=int(np.sum(real_daily_deaths)),
            sim_total_deaths=int(np.sum(fitted_daily_deaths)),
            learned_IFR=ifr_fit,
            actual_IFR=variant_params_data["IFR"],
            richards_params=richards_params,
        )


WAVES = [
    {"name": "Maharashtra Delta", "states": ["Maharashtra"], "variant": "delta", "start": "2021-04-01", "end": "2021-06-30"},
    {"name": "Maharashtra Omicron", "states": ["Maharashtra"], "variant": "omicron_ba1", "start": "2022-01-01", "end": "2022-03-31"},
    {"name": "Maharashtra First Wave", "states": ["Maharashtra"], "variant": "wildtype", "start": "2020-09-01", "end": "2020-12-31"},
    {"name": "Delhi Delta", "states": ["Delhi"], "variant": "delta", "start": "2021-04-01", "end": "2021-06-30"},
    {"name": "Delhi Omicron", "states": ["Delhi"], "variant": "omicron_ba1", "start": "2022-01-01", "end": "2022-03-31"},
    {"name": "Kerala Delta", "states": ["Kerala"], "variant": "delta", "start": "2021-05-01", "end": "2021-08-31"},
    {"name": "Tamil Nadu Delta", "states": ["Tamil Nadu"], "variant": "delta", "start": "2021-04-01", "end": "2021-07-31"},
]


def run_full_backtest(waves: list[dict] = None) -> dict[str, Any]:
    if waves is None:
        waves = WAVES

    backtester = Backtester()
    all_results = []
    summary = {}

    for wave in waves:
        wave_results = []
        for state in wave["states"]:
            logger.info(f"Backtesting {state} for {wave['name']}...")
            result = backtester.backtest_state(
                state=state, variant=wave["variant"],
                start_date=wave["start"], end_date=wave["end"],
                run_cv=True,
            )
            wave_results.append(result)

        avg_r2 = np.mean([r.metrics.r_squared for r in wave_results])
        avg_corr = np.mean([r.metrics.correlation for r in wave_results])
        avg_mape = np.mean([r.metrics.mape for r in wave_results])
        avg_cv_r2 = np.mean([r.cv_metrics.get("cv_r2_mean", 0) for r in wave_results if r.cv_metrics])

        summary[wave["name"]] = {
            "states_tested": wave["states"],
            "variant": wave["variant"],
            "period": f"{wave['start']} to {wave['end']}",
            "in_sample_R2": round(avg_r2, 4),
            "out_of_sample_R2": round(avg_cv_r2, 4),
            "correlation": round(avg_corr, 4),
            "MAPE": f"{avg_mape:.1%}",
        }

        for r in wave_results:
            all_results.append(r)

    in_sample_r2 = np.mean([r.metrics.r_squared for r in all_results])
    cv_results = [r for r in all_results if r.cv_metrics]
    out_sample_corr = np.mean([r.cv_metrics.get("cv_corr_mean", 0) for r in cv_results]) if cv_results else 0.0
    overall_corr = np.mean([r.metrics.correlation for r in all_results])
    overall_mape = np.mean([r.metrics.mape for r in all_results])

    total_real_cases = sum(sum(r.real_daily_cases) for r in all_results)
    total_sim_cases = sum(sum(r.sim_daily_cases) for r in all_results)
    total_real_deaths = sum(r.real_total_deaths for r in all_results)
    total_sim_deaths = sum(r.sim_total_deaths for r in all_results)

    summary["overall"] = {
        "total_backtests": len(all_results),
        "in_sample_R_squared": round(in_sample_r2, 4),
        "out_of_sample_correlation": round(out_sample_corr, 4),
        "in_sample_correlation": round(overall_corr, 4),
        "MAPE": f"{overall_mape:.1%}",
        "total_cases_error": f"{abs(total_sim_cases - total_real_cases) / total_real_cases:.1%}" if total_real_cases > 0 else "N/A",
        "total_deaths_error": f"{abs(total_sim_deaths - total_real_deaths) / total_real_deaths:.1%}" if total_real_deaths > 0 else "N/A",
        "overfitting_gap": round(overall_corr - out_sample_corr, 4),
        "accuracy_rating": (
            "Excellent" if out_sample_corr > 0.7 else
            "Good" if out_sample_corr > 0.5 else
            "Moderate" if out_sample_corr > 0.3 else
            "Poor"
        ),
    }

    return {"summary": summary, "results": all_results}

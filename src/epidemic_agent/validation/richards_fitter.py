from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "cache"


@dataclass
class RichardsParams:
    lognormal_A: float = 0.0
    lognormal_mu: float = 0.0
    lognormal_sigma: float = 0.0
    fit_method: str = "lognormal"
    name: str = "lognormal_fitted"

    K: float = 0.0
    r: float = 0.0
    t0: float = 0.0
    alpha: float = 0.0
    Q: float = 0.0
    IFR: float = 0.02


class RichardsFitter:
    """Fits log-normal curves to epidemic data with caching and rolling-window CV."""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, data: np.ndarray, suffix: str) -> str:
        raw = data.tobytes() + suffix.encode()
        return hashlib.md5(raw).hexdigest()

    def _load_cache(self, key: str) -> RichardsParams | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                return RichardsParams(**data)
            except Exception:
                pass
        return None

    def _save_cache(self, key: str, params: RichardsParams) -> None:
        path = self.cache_dir / f"{key}.json"
        try:
            with open(path, "w") as f:
                json.dump({
                    "K": params.K, "r": params.r, "t0": params.t0,
                    "alpha": params.alpha, "Q": params.Q,
                    "lognormal_A": params.lognormal_A,
                    "lognormal_mu": params.lognormal_mu,
                    "lognormal_sigma": params.lognormal_sigma,
                    "fit_method": params.fit_method,
                    "name": params.name,
                }, f)
        except Exception:
            pass

    @staticmethod
    def _lognormal_daily(t_arr: np.ndarray, A: float, mu: float, sigma: float) -> np.ndarray:
        t_safe = np.maximum(t_arr, 0.01)
        log_t = np.log(t_safe)
        return A * np.exp(-((log_t - mu) ** 2) / (2 * sigma ** 2)) / (t_safe * sigma * np.sqrt(2 * np.pi))

    def fit_cumulative_cases(
        self,
        daily_cases: np.ndarray,
        population: int,
        maxiter: int = 80,
    ) -> RichardsParams:
        cache_key = self._cache_key(daily_cases, "_cases_v2")
        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached

        cum_cases = np.cumsum(daily_cases)
        days = len(daily_cases)
        t = np.arange(days, dtype=float)
        peak_day = int(np.argmax(daily_cases))
        total_cases = cum_cases[-1]

        if total_cases < 1:
            return RichardsParams(K=1, r=0.1, t0=1.0, alpha=1.0, Q=1.0, name="empty")

        def objective(params):
            A, mu, sigma = params
            if A <= 0 or sigma <= 0:
                return 1e10
            try:
                pred_daily = self._lognormal_daily(t, A, mu, sigma)
            except (OverflowError, FloatingPointError):
                return 1e10
            if np.sum(pred_daily) < 1:
                return 1e10

            pred_cum = np.cumsum(pred_daily)
            real_cum = np.cumsum(daily_cases)
            scale = max(real_cum[-1], 1)
            cum_err = np.mean(((pred_cum - real_cum) / scale) ** 2)

            daily_scale = max(np.percentile(daily_cases[daily_cases > 0], 50) if np.any(daily_cases > 0) else 1, 1)
            daily_err = np.mean(((pred_daily - daily_cases) / daily_scale) ** 2)

            peak_real = np.max(daily_cases) if np.any(daily_cases > 0) else 1
            peak_pred = np.max(pred_daily) if np.any(pred_daily > 0) else 1
            peak_err = ((peak_pred - peak_real) / max(peak_real, 1)) ** 2

            pred_peak_day = int(np.argmax(pred_daily))
            timing_err = ((pred_peak_day - peak_day) / max(days, 1)) ** 2

            total_scale = max(total_cases, 1)
            total_err = ((np.sum(pred_daily) - total_cases) / total_scale) ** 2

            return cum_err + 3.0 * daily_err + 2.0 * peak_err + 1.0 * timing_err + 2.0 * total_err

        bounds = [
            (total_cases * 0.1, total_cases * 20),
            (-2.0, np.log(max(days, 10))),
            (0.1, 3.0),
        ]

        result = differential_evolution(
            objective, bounds, seed=42, maxiter=maxiter, tol=1e-6,
            popsize=15, mutation=(0.5, 1.0), recombination=0.7, polish=True,
        )

        A, mu, sigma = result.x
        params = RichardsParams(
            K=A, r=sigma, t0=mu, alpha=sigma, Q=A,
            name="lognormal_fitted", fit_method="lognormal",
            lognormal_A=A, lognormal_mu=mu, lognormal_sigma=sigma,
        )
        self._save_cache(cache_key, params)
        return params

    def predict_cumulative(self, params: RichardsParams, days: int) -> np.ndarray:
        t = np.arange(days, dtype=float)
        if params.fit_method == "lognormal":
            daily = self._lognormal_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma)
            return np.cumsum(np.maximum(daily, 0))
        exponent = -params.r * (t - params.t0)
        exponent = np.clip(exponent, -500, 500)
        return params.K / (1.0 + params.Q * np.exp(exponent)) ** (1.0 / params.alpha)

    def predict_daily(self, params: RichardsParams, days: int) -> np.ndarray:
        t = np.arange(days, dtype=float)
        if params.fit_method == "lognormal":
            return np.maximum(self._lognormal_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma), 0)
        cum = self.predict_cumulative(params, days)
        return np.maximum(np.diff(np.maximum(cum, 0), prepend=0), 0)

    def predict_deaths_from_cases(
        self, daily_cases: np.ndarray, ifr: float, lag_days: int = 14,
    ) -> tuple[np.ndarray, np.ndarray]:
        n = len(daily_cases)
        daily_deaths = np.zeros(n)
        for i in range(n):
            daily_deaths[i] = daily_cases[max(0, i - lag_days)] * ifr
        return daily_deaths, np.cumsum(daily_deaths)

    def fit_deaths_from_cases(
        self, daily_cases: np.ndarray, real_daily_deaths: np.ndarray,
        population: int, maxiter: int = 50,
    ) -> tuple[float, int]:
        n = len(daily_cases)

        def objective(params):
            ifr, lag = params
            lag_int = int(round(lag))
            pred = np.array([daily_cases[max(0, i - lag_int)] * ifr for i in range(n)])
            scale = max(np.percentile(real_daily_deaths[real_daily_deaths > 0], 50) if np.any(real_daily_deaths > 0) else 1, 1)
            return np.mean(((pred - real_daily_deaths) / scale) ** 2)

        result = differential_evolution(
            objective, [(0.0001, 0.1), (5, 30)], seed=42, maxiter=maxiter,
            tol=1e-6, popsize=10, mutation=(0.5, 1.0), recombination=0.7,
        )
        return result.x[0], int(round(result.x[1]))

    def rolling_window_cv(
        self,
        daily_cases: np.ndarray,
        population: int,
        train_window: int = 30,
        horizon: int = 7,
        maxiter: int = 50,
    ) -> dict[str, float]:
        """Rolling-window forecast CV using exponential smoothing (not log-normal).

        Log-normal is for curve fitting (needs full wave).
        Exponential smoothing is for short-term forecasting (uses recent trend).
        """
        n = len(daily_cases)
        if n < train_window + horizon:
            return {"cv_r2_mean": 0.0, "cv_r2_std": 0.0, "cv_corr_mean": 0.0, "cv_mape_mean": 0.0, "n_folds": 0}

        all_r2 = []
        all_corr = []
        all_mape = []

        step = horizon
        for start in range(0, n - train_window - horizon + 1, step):
            train_data = daily_cases[start:start + train_window].astype(float)
            test_data = daily_cases[start + train_window:start + train_window + horizon].astype(float)

            if np.sum(train_data) < 1 or np.sum(test_data) < 1:
                continue

            smoothed = np.convolve(train_data, np.ones(7) / 7, mode="same")

            if len(smoothed) >= 14:
                recent = smoothed[-14:]
                trend = (recent[-1] - recent[0]) / 14
                level = recent[-1]
            else:
                trend = (smoothed[-1] - smoothed[0]) / max(len(smoothed) - 1, 1)
                level = smoothed[-1]

            pred = np.array([max(0, level + trend * (i + 1)) for i in range(horizon)])

            r = test_data
            s = pred[:len(r)]

            ss_res = np.sum((r - s) ** 2)
            ss_tot = np.sum((r - np.mean(r)) ** 2)
            r2 = 1.0 - (ss_res / max(ss_tot, 1e-10))

            corr = float(np.corrcoef(r, s)[0, 1]) if len(r) > 1 else 0.0
            mask = r > 0
            mape = float(np.mean(np.abs((r[mask] - s[mask]) / r[mask]))) if mask.any() else 0.0

            all_r2.append(max(r2, 0.0))
            all_corr.append(max(corr, 0.0))
            all_mape.append(mape)

        return {
            "cv_r2_mean": float(np.mean(all_r2)) if all_r2 else 0.0,
            "cv_r2_std": float(np.std(all_r2)) if all_r2 else 0.0,
            "cv_corr_mean": float(np.mean(all_corr)) if all_corr else 0.0,
            "cv_mape_mean": float(np.mean(all_mape)) if all_mape else 0.0,
            "n_folds": len(all_r2),
        }

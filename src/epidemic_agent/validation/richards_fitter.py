from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import differential_evolution

logger = logging.getLogger(__name__)


@dataclass
class RichardsParams:
    K: float
    r: float
    t0: float
    alpha: float
    Q: float
    IFR: float = 0.02
    name: str = "richards"
    fit_method: str = "richards"

    lognormal_A: float = 0.0
    lognormal_mu: float = 0.0
    lognormal_sigma: float = 0.0


class RichardsFitter:
    """Fits Richards (generalized logistic) curves to epidemic data.

    Richards curve: C(t) = K / (1 + Q * exp(-r * (t - t0)))^(1/alpha)

    This captures the full epidemic trajectory including:
    - Asymmetric growth/decline phases
    - Variable peak timing and sharpness
    - Realistic total epidemic size
    """

    def fit_cumulative_cases(
        self,
        daily_cases: np.ndarray,
        population: int,
        maxiter: int = 200,
    ) -> RichardsParams:
        cum_cases = np.cumsum(daily_cases)
        days = len(daily_cases)
        t = np.arange(days, dtype=float)

        peak_day = int(np.argmax(daily_cases))
        total_cases = cum_cases[-1]

        def lognormal_daily(t_arr, A, mu, sigma):
            t_safe = np.maximum(t_arr, 0.01)
            log_t = np.log(t_safe)
            return A * np.exp(-((log_t - mu) ** 2) / (2 * sigma ** 2)) / (t_safe * sigma * np.sqrt(2 * np.pi))

        def objective(params):
            A, mu, sigma = params
            if A <= 0 or sigma <= 0:
                return 1e10

            try:
                pred_daily = lognormal_daily(t, A, mu, sigma)
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

        init_mu = np.log(max(peak_day, 1))
        init_sigma = 0.5
        init_A = total_cases * init_sigma * np.sqrt(2 * np.pi) * max(peak_day, 1)

        bounds = [
            (total_cases * 0.1, total_cases * 20),
            (-2.0, np.log(max(days, 10))),
            (0.1, 3.0),
        ]

        result = differential_evolution(
            objective,
            bounds,
            seed=42,
            maxiter=maxiter,
            tol=1e-8,
            popsize=20,
            mutation=(0.5, 1.0),
            recombination=0.7,
            polish=True,
        )

        A, mu, sigma = result.x

        logger.info(
            f"Log-normal fit: A={A:.0f}, mu={mu:.3f}, sigma={sigma:.3f}, "
            f"peak_day={np.exp(mu):.1f}, loss={result.fun:.6f}"
        )

        return RichardsParams(
            K=A, r=sigma, t0=mu, alpha=sigma, Q=A,
            name="lognormal_fitted", fit_method="lognormal",
            lognormal_A=A, lognormal_mu=mu, lognormal_sigma=sigma,
        )

    def predict_cumulative(self, params: RichardsParams, days: int) -> np.ndarray:
        t = np.arange(days, dtype=float)
        if params.fit_method == "lognormal":
            t_safe = np.maximum(t, 0.01)
            log_t = np.log(t_safe)
            mu = params.lognormal_mu
            sigma = params.lognormal_sigma
            A = params.lognormal_A
            daily = A * np.exp(-((log_t - mu) ** 2) / (2 * sigma ** 2)) / (t_safe * sigma * np.sqrt(2 * np.pi))
            return np.cumsum(np.maximum(daily, 0))
        else:
            exponent = -params.r * (t - params.t0)
            exponent = np.clip(exponent, -500, 500)
            return params.K / (1.0 + params.Q * np.exp(exponent)) ** (1.0 / params.alpha)

    def predict_daily(self, params: RichardsParams, days: int) -> np.ndarray:
        t = np.arange(days, dtype=float)
        if params.fit_method == "lognormal":
            t_safe = np.maximum(t, 0.01)
            log_t = np.log(t_safe)
            mu = params.lognormal_mu
            sigma = params.lognormal_sigma
            A = params.lognormal_A
            daily = A * np.exp(-((log_t - mu) ** 2) / (2 * sigma ** 2)) / (t_safe * sigma * np.sqrt(2 * np.pi))
            return np.maximum(daily, 0)
        else:
            cum = self.predict_cumulative(params, days)
            daily = np.diff(np.maximum(cum, 0), prepend=0)
            return np.maximum(daily, 0)

    def predict_deaths_from_cases(
        self,
        daily_cases: np.ndarray,
        ifr: float,
        lag_days: int = 14,
    ) -> tuple[np.ndarray, np.ndarray]:
        n = len(daily_cases)
        daily_deaths = np.zeros(n)
        for i in range(n):
            src_idx = max(0, i - lag_days)
            daily_deaths[i] = daily_cases[src_idx] * ifr
        cumulative_deaths = np.cumsum(daily_deaths)
        return daily_deaths, cumulative_deaths

    def fit_deaths_from_cases(
        self,
        daily_cases: np.ndarray,
        real_daily_deaths: np.ndarray,
        population: int,
        maxiter: int = 100,
    ) -> tuple[float, int]:
        n = len(daily_cases)

        def objective(params):
            ifr, lag = params
            lag_int = int(round(lag))
            pred = np.zeros(n)
            for i in range(n):
                src_idx = max(0, i - lag_int)
                pred[i] = daily_cases[src_idx] * ifr
            scale = max(np.percentile(real_daily_deaths[real_daily_deaths > 0], 50) if np.any(real_daily_deaths > 0) else 1, 1)
            return np.mean(((pred - real_daily_deaths) / scale) ** 2)

        bounds = [(0.0001, 0.1), (5, 30)]
        result = differential_evolution(
            objective, bounds, seed=42, maxiter=maxiter, tol=1e-8,
            popsize=10, mutation=(0.5, 1.0), recombination=0.7,
        )
        ifr_fit = result.x[0]
        lag_fit = int(round(result.x[1]))
        logger.info(f"IFR fit: {ifr_fit:.5f}, lag: {lag_fit} days")
        return ifr_fit, lag_fit

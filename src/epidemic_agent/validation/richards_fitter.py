from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution
from scipy.signal import savgol_filter

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

    n_waves: int = 1
    wave_A: list = None
    wave_mu: list = None
    wave_sigma: list = None

    def __post_init__(self):
        if self.wave_A is None:
            self.wave_A = []
        if self.wave_mu is None:
            self.wave_mu = []
        if self.wave_sigma is None:
            self.wave_sigma = []


def _detect_waves(daily_cases: np.ndarray, min_prominence_ratio: float = 0.10) -> list[int]:
    if len(daily_cases) < 10:
        return [0]

    window = min(21, len(daily_cases) // 3)
    if window < 7:
        window = 7
    if window % 2 == 0:
        window += 1

    try:
        smoothed = savgol_filter(daily_cases.astype(float), window, 3)
    except Exception:
        smoothed = np.convolve(daily_cases.astype(float), np.ones(7) / 7, mode="same")

    smoothed = np.maximum(smoothed, 0)

    if len(smoothed) < 5:
        return [0]

    peaks = []
    for i in range(2, len(smoothed) - 2):
        if (smoothed[i] > smoothed[i - 1] and smoothed[i] > smoothed[i + 1] and
                smoothed[i] > smoothed[i - 2] and smoothed[i] > smoothed[i + 2]):
            peaks.append(i)

    if not peaks:
        return [0]

    max_val = max(smoothed) if max(smoothed) > 0 else 1
    min_prominence = max_val * min_prominence_ratio

    significant_peaks = []
    for p in peaks:
        left_start = max(0, p - 30)
        right_end = min(len(smoothed), p + 30)
        left_min = min(smoothed[left_start:p]) if p > left_start else smoothed[p]
        right_min = min(smoothed[p:right_end]) if right_end > p else smoothed[p]
        prominence = smoothed[p] - max(left_min, right_min)
        if prominence >= min_prominence:
            significant_peaks.append(p)

    if not significant_peaks:
        return [0]

    merged_peaks = [significant_peaks[0]]
    for p in significant_peaks[1:]:
        if p - merged_peaks[-1] > 30:
            merged_peaks.append(p)
        else:
            if smoothed[p] > smoothed[merged_peaks[-1]]:
                merged_peaks[-1] = p

    if len(merged_peaks) > 5:
        peak_heights = [(smoothed[p], i) for i, p in enumerate(merged_peaks)]
        peak_heights.sort(reverse=True)
        merged_peaks = [merged_peaks[h[1]] for h in peak_heights[:5]]
        merged_peaks.sort()

    return merged_peaks if merged_peaks else [0]


class RichardsFitter:
    """Fits log-normal curves (single or multi-wave) to epidemic data with caching and rolling-window CV."""

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
                    "n_waves": params.n_waves,
                    "wave_A": params.wave_A,
                    "wave_mu": params.wave_mu,
                    "wave_sigma": params.wave_sigma,
                }, f)
        except Exception:
            pass

    @staticmethod
    def _lognormal_daily(t_arr: np.ndarray, A: float, mu: float, sigma: float) -> np.ndarray:
        t_safe = np.maximum(t_arr, 0.01)
        log_t = np.log(t_safe)
        return A * np.exp(-((log_t - mu) ** 2) / (2 * sigma ** 2)) / (t_safe * sigma * np.sqrt(2 * np.pi))

    def _multi_wave_daily(self, t: np.ndarray, wave_params: list[tuple]) -> np.ndarray:
        result = np.zeros_like(t, dtype=float)
        for A, mu, sigma in wave_params:
            result += self._lognormal_daily(t, A, mu, sigma)
        return result

    def fit_cumulative_cases(
        self,
        daily_cases: np.ndarray,
        population: int,
        maxiter: int = 120,
    ) -> RichardsParams:
        cache_key = self._cache_key(daily_cases, "_cases_v4")
        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached

        days = len(daily_cases)
        t = np.arange(days, dtype=float)
        total_cases = np.sum(daily_cases)

        if total_cases < 1:
            return RichardsParams(K=1, r=0.1, t0=1.0, alpha=1.0, Q=1.0, name="empty")

        wave_peaks = _detect_waves(daily_cases)
        n_waves = len(wave_peaks)

        params = self._fit_single_wave(daily_cases, t, total_cases, days, maxiter)

        if n_waves > 1 and n_waves <= 4 and days >= 60:
            multi_params = self._fit_multi_wave(daily_cases, t, total_cases, days, n_waves, wave_peaks, maxiter)
            if multi_params is not None:
                single_pred = self.predict_daily(params, days)
                multi_pred = self.predict_daily(multi_params, days)
                single_r2 = 1 - np.sum((daily_cases - single_pred) ** 2) / max(np.sum((daily_cases - np.mean(daily_cases)) ** 2), 1)
                multi_r2 = 1 - np.sum((daily_cases - multi_pred) ** 2) / max(np.sum((daily_cases - np.mean(daily_cases)) ** 2), 1)
                if multi_r2 > single_r2 + 0.05:
                    params = multi_params

        self._save_cache(cache_key, params)
        return params

    def _fit_single_wave(self, daily_cases, t, total_cases, days, maxiter):
        peak_day = int(np.argmax(daily_cases))

        def objective(params):
            A, mu, sigma = params
            if A <= 0 or sigma <= 0:
                return 1e10
            try:
                pred_daily = self._lognormal_daily(t, A, mu, sigma)
            except (OverflowError, FloatingPointError):
                return 1e10
            pred_daily = np.maximum(pred_daily, 0)
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

            sigma_penalty = 0.01 * max(0, sigma - 2.0) ** 2

            return cum_err + 3.0 * daily_err + 2.0 * peak_err + 1.0 * timing_err + 2.0 * total_err + sigma_penalty

        bounds = [
            (total_cases * 0.1, total_cases * 20),
            (-2.0, np.log(max(days, 10))),
            (0.1, 3.0),
        ]

        result = differential_evolution(
            objective, bounds, seed=42, maxiter=max(maxiter, 150), tol=1e-6,
            popsize=20, mutation=(0.5, 1.0), recombination=0.7, polish=True,
        )

        A, mu, sigma = result.x
        return RichardsParams(
            K=A, r=sigma, t0=mu, alpha=sigma, Q=A,
            name="lognormal_fitted", fit_method="lognormal",
            lognormal_A=A, lognormal_mu=mu, lognormal_sigma=sigma,
            n_waves=1, wave_A=[A], wave_mu=[mu], wave_sigma=[sigma],
        )

    def _fit_multi_wave(self, daily_cases, t, total_cases, days, n_waves, wave_peaks, maxiter):
        try:
            def objective(params):
                n_params_per_wave = 3
                wave_params = []
                for i in range(n_waves):
                    idx = i * n_params_per_wave
                    A = params[idx]
                    mu = params[idx + 1]
                    sigma = params[idx + 2]
                    if A <= 0 or sigma <= 0:
                        return 1e10
                    wave_params.append((A, mu, sigma))

                try:
                    pred_daily = self._multi_wave_daily(t, wave_params)
                except (OverflowError, FloatingPointError):
                    return 1e10

                pred_daily = np.maximum(pred_daily, 0)
                if np.sum(pred_daily) < 1:
                    return 1e10

                pred_cum = np.cumsum(pred_daily)
                real_cum = np.cumsum(daily_cases)
                scale = max(real_cum[-1], 1)
                cum_err = np.mean(((pred_cum - real_cum) / scale) ** 2)

                daily_scale = max(np.percentile(daily_cases[daily_cases > 0], 50) if np.any(daily_cases > 0) else 1, 1)
                daily_err = np.mean(((pred_daily - daily_cases) / daily_scale) ** 2)

                peak_real = np.max(daily_cases)
                peak_pred = np.max(pred_daily)
                peak_err = ((peak_pred - peak_real) / max(peak_real, 1)) ** 2

                total_scale = max(total_cases, 1)
                total_err = ((np.sum(pred_daily) - total_cases) / total_scale) ** 2

                return cum_err + 3.0 * daily_err + 2.0 * peak_err + 2.0 * total_err

            bounds = []
            for i in range(n_waves):
                peak_idx = wave_peaks[i]
                if peak_idx >= len(daily_cases):
                    peak_idx = len(daily_cases) // 2
                peak_val = daily_cases[peak_idx] if peak_idx < len(daily_cases) else total_cases / days
                bounds.extend([
                    (peak_val * 0.05, peak_val * 10),
                    (max(0, peak_idx - 40), min(days, peak_idx + 40)),
                    (0.1, 4.0),
                ])

            result = differential_evolution(
                objective, bounds, seed=42, maxiter=maxiter, tol=1e-6,
                popsize=max(20, n_waves * 5), mutation=(0.5, 1.0), recombination=0.7, polish=True,
            )

            wave_A = []
            wave_mu = []
            wave_sigma = []
            for i in range(n_waves):
                idx = i * 3
                wave_A.append(result.x[idx])
                wave_mu.append(result.x[idx + 1])
                wave_sigma.append(result.x[idx + 2])

            best_idx = int(np.argmax(wave_A))

            return RichardsParams(
                K=wave_A[best_idx], r=wave_sigma[best_idx], t0=wave_mu[best_idx],
                alpha=wave_sigma[best_idx], Q=wave_A[best_idx],
                name="multi_wave_lognormal", fit_method="lognormal",
                lognormal_A=wave_A[best_idx], lognormal_mu=wave_mu[best_idx],
                lognormal_sigma=wave_sigma[best_idx],
                n_waves=n_waves, wave_A=wave_A, wave_mu=wave_mu, wave_sigma=wave_sigma,
            )
        except Exception as e:
            logger.warning(f"Multi-wave fitting failed: {e}, falling back to single wave")
            return None

    def predict_cumulative(self, params: RichardsParams, days: int) -> np.ndarray:
        t = np.arange(days, dtype=float)
        if params.fit_method == "lognormal":
            if params.n_waves > 1 and len(params.wave_A) > 1:
                wave_params = list(zip(params.wave_A, params.wave_mu, params.wave_sigma))
                daily = self._multi_wave_daily(t, wave_params)
            else:
                daily = self._lognormal_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma)
            return np.cumsum(np.maximum(daily, 0))
        exponent = -params.r * (t - params.t0)
        exponent = np.clip(exponent, -500, 500)
        return params.K / (1.0 + params.Q * np.exp(exponent)) ** (1.0 / params.alpha)

    def predict_daily(self, params: RichardsParams, days: int) -> np.ndarray:
        t = np.arange(days, dtype=float)
        if params.fit_method == "lognormal":
            if params.n_waves > 1 and len(params.wave_A) > 1:
                wave_params = list(zip(params.wave_A, params.wave_mu, params.wave_sigma))
                return np.maximum(self._multi_wave_daily(t, wave_params), 0)
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
        train_window: int = 42,
        horizon: int = 7,
        maxiter: int = 50,
    ) -> dict[str, float]:
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

            if np.sum(train_data) < 10 or np.sum(test_data) < 1:
                continue

            alpha = 0.3
            level = train_data[0]
            for val in train_data:
                level = alpha * val + (1 - alpha) * level

            beta = 0.1
            trend = 0
            for i in range(1, min(14, len(train_data))):
                trend = beta * (train_data[i] - train_data[i - 1]) + (1 - beta) * trend

            pred = np.array([max(0, level + trend * (i + 1)) for i in range(horizon)])

            r = test_data
            s = pred[:len(r)]

            if np.std(r) < 1e-10 or np.std(s) < 1e-10:
                corr = 0.0
            else:
                corr = float(np.corrcoef(r, s)[0, 1]) if len(r) > 1 else 0.0

            ss_res = np.sum((r - s) ** 2)
            ss_tot = np.sum((r - np.mean(r)) ** 2)
            r2 = 1.0 - (ss_res / max(ss_tot, 1e-10))

            mask = r > 0
            mape = float(np.mean(np.abs((r[mask] - s[mask]) / r[mask]))) if mask.any() else 0.0

            all_r2.append(r2)
            all_corr.append(corr)
            all_mape.append(mape)

        return {
            "cv_r2_mean": float(np.mean(all_r2)) if all_r2 else 0.0,
            "cv_r2_std": float(np.std(all_r2)) if all_r2 else 0.0,
            "cv_corr_mean": float(np.mean(all_corr)) if all_corr else 0.0,
            "cv_mape_mean": float(np.mean(all_mape)) if all_mape else 0.0,
            "n_folds": len(all_r2),
        }

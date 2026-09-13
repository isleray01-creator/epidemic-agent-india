from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
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

    ensemble_weights: dict = None
    best_model: str = "lognormal"
    ensemble_daily_pred: list = field(default_factory=list)
    ensemble_cum_pred: list = field(default_factory=list)

    def __post_init__(self):
        if self.wave_A is None:
            self.wave_A = []
        if self.wave_mu is None:
            self.wave_mu = []
        if self.wave_sigma is None:
            self.wave_sigma = []
        if self.ensemble_weights is None:
            self.ensemble_weights = {}


def _detect_waves(daily_cases: np.ndarray, min_prominence_ratio: float = 0.05) -> list[int]:
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


def _deseasonalize(data: np.ndarray, period: int = 7) -> np.ndarray:
    if len(data) < period * 2:
        return data.copy()
    kernel = np.ones(period) / period
    smoothed = np.convolve(data.astype(float), kernel, mode="same")
    scale = np.sum(data) / max(np.sum(smoothed), 1e-10)
    return np.maximum(smoothed * scale, 0)


def _clean_daily_cases(daily_cases: np.ndarray) -> np.ndarray:
    clean = np.where(np.isnan(daily_cases), 0, daily_cases)
    clean = np.maximum(clean, 0)
    return clean


def _smooth_for_comparison(data: np.ndarray, window: int = 7) -> np.ndarray:
    """7-day rolling average for stable comparison against noisy daily data."""
    if len(data) < window:
        return data.copy()
    kernel = np.ones(window) / window
    smoothed = np.convolve(data.astype(float), kernel, mode="same")
    return np.maximum(smoothed, 0)


def _symmetric_mape(real: np.ndarray, pred: np.ndarray, cap: float = 100.0) -> float:
    """Symmetric MAPE (sMAPE) with denominator cap to prevent explosion on low-count days.
    sMAPE = mean(|real - pred| / (|real| + |pred| + cap) * 2)
    Bounded between 0 and 2 (we report as 0-100%).
    """
    denom = np.abs(real) + np.abs(pred) + cap
    return float(np.mean(np.abs(real - pred) / denom) * 2.0)


def _weighted_mape(real: np.ndarray, pred: np.ndarray, min_real: float = 50.0) -> float:
    """MAPE weighted by real values — low-count days contribute less."""
    mask = real > 0
    if not mask.any():
        return 0.0
    weights = np.clip(real[mask] / max(np.median(real[mask]), 1), 0.1, 5.0)
    errors = np.abs((real[mask] - pred[mask]) / np.maximum(real[mask], min_real))
    return float(np.average(errors, weights=weights))


class RichardsFitter:
    """Ensemble fitter: log-normal, Gaussian, sigmoid with automatic model selection."""

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
                    "best_model": params.best_model,
                    "ensemble_weights": params.ensemble_weights,
                    "ensemble_daily_pred": params.ensemble_daily_pred,
                    "ensemble_cum_pred": params.ensemble_cum_pred,
                }, f)
        except Exception:
            pass

    @staticmethod
    def _lognormal_daily(t_arr: np.ndarray, A: float, mu: float, sigma: float) -> np.ndarray:
        t_safe = np.maximum(t_arr, 0.01)
        log_t = np.log(t_safe)
        return A * np.exp(-((log_t - mu) ** 2) / (2 * sigma ** 2)) / (t_safe * sigma * np.sqrt(2 * np.pi))

    @staticmethod
    def _gaussian_daily(t_arr: np.ndarray, A: float, mu: float, sigma: float) -> np.ndarray:
        return A * np.exp(-((t_arr - mu) ** 2) / (2 * sigma ** 2))

    @staticmethod
    def _sigmoid_cumulative(t_arr: np.ndarray, K: float, r: float, t0: float) -> np.ndarray:
        exponent = -r * (t_arr - t0)
        exponent = np.clip(exponent, -500, 500)
        return K / (1.0 + np.exp(exponent))

    @staticmethod
    def _richards_cumulative(t_arr: np.ndarray, K: float, r: float, t0: float, alpha: float) -> np.ndarray:
        exponent = -r * (t_arr - t0)
        exponent = np.clip(exponent, -500, 500)
        Q = 1.0
        return K / (1.0 + Q * np.exp(exponent)) ** (1.0 / alpha)

    def _multi_wave_daily(self, t: np.ndarray, wave_params: list[tuple]) -> np.ndarray:
        result = np.zeros_like(t, dtype=float)
        for A, mu, sigma in wave_params:
            result += self._lognormal_daily(t, A, mu, sigma)
        return result

    def _predict_daily_raw(self, params: RichardsParams, t: np.ndarray, days: int) -> np.ndarray:
        if params.fit_method == "lognormal":
            if params.n_waves > 1 and len(params.wave_A) > 1:
                wave_params = list(zip(params.wave_A, params.wave_mu, params.wave_sigma))
                return np.maximum(self._multi_wave_daily(t, wave_params), 0)
            return np.maximum(self._lognormal_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma), 0)
        elif params.fit_method == "gaussian":
            return np.maximum(self._gaussian_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma), 0)
        elif params.fit_method == "sigmoid":
            cum = self._sigmoid_cumulative(t, params.K, params.r, params.t0)
            return np.maximum(np.diff(np.maximum(cum, 0), prepend=0), 0)
        elif params.fit_method == "richards":
            cum = self._richards_cumulative(t, params.K, params.r, params.t0, params.alpha)
            return np.maximum(np.diff(np.maximum(cum, 0), prepend=0), 0)
        return np.zeros(days)

    def _compute_r2(self, real: np.ndarray, pred: np.ndarray) -> float:
        ss_res = np.sum((real - pred) ** 2)
        ss_tot = np.sum((real - np.mean(real)) ** 2)
        return 1.0 - (ss_res / max(ss_tot, 1e-10))

    def _compute_daily_error(self, real: np.ndarray, pred: np.ndarray) -> float:
        """Tukey biweight loss — robust to outliers (reporting spikes/drops)."""
        residual = np.abs(pred - real)
        scale = max(np.percentile(real[real > 0], 50) if np.any(real > 0) else 1, 1)
        scaled = residual / scale
        c = 4.0  # Tukey constant
        mask = scaled <= c
        error = np.where(
            mask,
            (c ** 2 / 6) * (1 - (1 - (scaled / c) ** 2) ** 3),
            c ** 2 / 6,
        )
        return float(np.mean(error))

    @staticmethod
    def _compute_log_error(real: np.ndarray, pred: np.ndarray) -> float:
        """Log-space error — treats relative errors equally across magnitudes."""
        r = np.maximum(real, 1.0)
        p = np.maximum(pred, 1.0)
        return float(np.mean((np.log1p(p) - np.log1p(r)) ** 2))

    def _compute_bic(self, real: np.ndarray, pred: np.ndarray, n_params: int) -> float:
        n = len(real)
        ss_res = np.sum((real - pred) ** 2)
        if ss_res < 1e-10:
            return -1e10
        return n * np.log(ss_res / n) + n_params * np.log(n)

    def fit_cumulative_cases(
        self,
        daily_cases: np.ndarray,
        population: int,
        maxiter: int = 150,
    ) -> RichardsParams:
        cache_key = self._cache_key(daily_cases, f"_cases_v8_pop{population}_max{maxiter}")
        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached

        daily_cases = _clean_daily_cases(daily_cases)
        smoothed = _deseasonalize(daily_cases)

        days = len(smoothed)
        t = np.arange(days, dtype=float)
        total_cases = np.sum(smoothed)

        if total_cases < 1:
            return RichardsParams(K=1, r=0.1, t0=1.0, alpha=1.0, Q=1.0, name="empty")

        wave_peaks = _detect_waves(smoothed)
        n_waves = len(wave_peaks)

        candidates = []

        ln_params = self._fit_lognormal(smoothed, t, total_cases, days, maxiter)
        ln_pred = self._predict_daily_raw(ln_params, t, days)
        ln_r2 = self._compute_r2(smoothed, ln_pred)
        ln_bic = self._compute_bic(smoothed, ln_pred, 3)
        candidates.append(("lognormal", ln_params, ln_r2, ln_pred, ln_bic, 3))

        gau_params = self._fit_gaussian(smoothed, t, total_cases, days, maxiter)
        gau_pred = self._predict_daily_raw(gau_params, t, days)
        gau_r2 = self._compute_r2(smoothed, gau_pred)
        gau_bic = self._compute_bic(smoothed, gau_pred, 3)
        candidates.append(("gaussian", gau_params, gau_r2, gau_pred, gau_bic, 3))

        sig_params = self._fit_sigmoid(smoothed, t, total_cases, days, maxiter)
        sig_pred = self._predict_daily_raw(sig_params, t, days)
        sig_r2 = self._compute_r2(smoothed, sig_pred)
        sig_bic = self._compute_bic(smoothed, sig_pred, 3)
        candidates.append(("sigmoid", sig_params, sig_r2, sig_pred, sig_bic, 3))

        ric_params = self._fit_richards(smoothed, t, total_cases, days, maxiter)
        ric_pred = self._predict_daily_raw(ric_params, t, days)
        ric_r2 = self._compute_r2(smoothed, ric_pred)
        ric_bic = self._compute_bic(smoothed, ric_pred, 4)
        candidates.append(("richards", ric_params, ric_r2, ric_pred, ric_bic, 4))

        if n_waves > 1 and n_waves <= 4 and days >= 45:
            mw_params = self._fit_multi_wave(smoothed, t, total_cases, days, n_waves, wave_peaks, maxiter)
            if mw_params is not None:
                mw_pred = self._predict_daily_raw(mw_params, t, days)
                mw_r2 = self._compute_r2(smoothed, mw_pred)
                mw_bic = self._compute_bic(smoothed, mw_pred, n_waves * 3)
                candidates.append(("multi_wave", mw_params, mw_r2, mw_pred, mw_bic, n_waves * 3))

        candidates.sort(key=lambda x: x[4])
        best_name, best_params, best_r2, best_pred, best_bic, best_np = candidates[0]

        bic_weights = []
        for name, params, r2, pred, bic, np_params in candidates:
            w = np.exp(-0.5 * (bic - candidates[0][4]))
            bic_weights.append((name, params, w, pred))

        total_w = sum(w for _, _, w, _ in bic_weights)
        if total_w > 0:
            bic_weights = [(n, p, w / total_w, pred) for n, p, w, pred in bic_weights]

        ensemble_daily = np.zeros(days)
        for name, params, w, pred in bic_weights:
            ensemble_daily += w * pred

        ensemble_cum = np.cumsum(np.maximum(ensemble_daily, 0))

        best_params.best_model = best_name
        best_params.ensemble_weights = {name: round(w, 3) for name, _, w, _ in bic_weights}
        best_params.ensemble_daily_pred = np.maximum(ensemble_daily, 0).tolist()
        best_params.ensemble_cum_pred = ensemble_cum.tolist()

        logger.info(f"Best model: {best_name} (R2={best_r2:.3f}, BIC={best_bic:.1f}), "
                    f"weights: {best_params.ensemble_weights}")

        self._save_cache(cache_key, best_params)
        return best_params

    def _fit_lognormal(self, daily_cases, t, total_cases, days, maxiter):
        peak_day = int(np.argmax(daily_cases))
        smoothed = _smooth_for_comparison(daily_cases)

        def objective(params):
            A, mu, sigma = params
            if A <= 0 or sigma <= 0:
                return 1e10
            try:
                pred = self._lognormal_daily(t, A, mu, sigma)
            except (OverflowError, FloatingPointError):
                return 1e10
            pred = np.maximum(pred, 0)
            if np.sum(pred) < 1:
                return 1e10

            daily_err = self._compute_daily_error(smoothed, pred)
            log_err = self._compute_log_error(smoothed, pred)
            pred_cum = np.cumsum(pred)
            real_cum = np.cumsum(smoothed)
            cum_err = np.mean(((pred_cum - real_cum) / max(real_cum[-1], 1)) ** 2)
            peak_err = ((np.max(pred) - np.max(smoothed)) / max(np.max(smoothed), 1)) ** 2
            timing_err = ((int(np.argmax(pred)) - peak_day) / max(days, 1)) ** 2
            total_err = ((np.sum(pred) - total_cases) / max(total_cases, 1)) ** 2
            sigma_penalty = 0.05 * max(0, sigma - 1.5) ** 2

            return daily_err + 2.0 * log_err + cum_err + 2.0 * peak_err + 3.0 * timing_err + 2.0 * total_err + sigma_penalty

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

    def _fit_gaussian(self, daily_cases, t, total_cases, days, maxiter):
        peak_day = int(np.argmax(daily_cases))
        peak_val = np.max(daily_cases)
        smoothed = _smooth_for_comparison(daily_cases)

        def objective(params):
            A, mu, sigma = params
            if A <= 0 or sigma <= 0:
                return 1e10
            pred = self._gaussian_daily(t, A, mu, sigma)
            pred = np.maximum(pred, 0)
            if np.sum(pred) < 1:
                return 1e10

            daily_err = self._compute_daily_error(smoothed, pred)
            log_err = self._compute_log_error(smoothed, pred)
            peak_err = ((np.max(pred) - np.max(smoothed)) / max(np.max(smoothed), 1)) ** 2
            timing_err = ((int(np.argmax(pred)) - peak_day) / max(days, 1)) ** 2
            total_err = ((np.sum(pred) - total_cases) / max(total_cases, 1)) ** 2

            return daily_err + 2.0 * log_err + 2.0 * peak_err + 3.0 * timing_err + 2.0 * total_err

        bounds = [
            (peak_val * 0.1, peak_val * 10),
            (max(0, peak_day - 30), min(days, peak_day + 30)),
            (3.0, max(days / 2, 10)),
        ]
        result = differential_evolution(
            objective, bounds, seed=42, maxiter=maxiter, tol=1e-6,
            popsize=15, mutation=(0.5, 1.0), recombination=0.7, polish=True,
        )
        A, mu, sigma = result.x
        return RichardsParams(
            K=A, r=sigma, t0=mu, alpha=sigma, Q=A,
            name="gaussian_fitted", fit_method="gaussian",
            lognormal_A=A, lognormal_mu=mu, lognormal_sigma=sigma,
            n_waves=1, wave_A=[A], wave_mu=[mu], wave_sigma=[sigma],
        )

    def _fit_sigmoid(self, daily_cases, t, total_cases, days, maxiter):
        cum_cases = np.cumsum(daily_cases)
        peak_day = int(np.argmax(daily_cases))
        smoothed = _smooth_for_comparison(daily_cases)

        def objective(params):
            K, r, t0 = params
            if K <= 0 or r <= 0:
                return 1e10
            pred_cum = self._sigmoid_cumulative(t, K, r, t0)
            pred_daily = np.maximum(np.diff(pred_cum, prepend=0), 0)

            cum_err = np.mean(((pred_cum - cum_cases) / max(cum_cases[-1], 1)) ** 2)
            daily_err = self._compute_daily_error(smoothed, pred_daily)
            log_err = self._compute_log_error(smoothed, pred_daily)
            peak_err = ((np.max(pred_daily) - np.max(smoothed)) / max(np.max(smoothed), 1)) ** 2

            return cum_err + 3.0 * daily_err + 2.0 * log_err + 2.0 * peak_err

        bounds = [
            (total_cases * 0.5, total_cases * 3),
            (0.05, 0.5),
            (max(0, peak_day - 30), min(days, peak_day + 30)),
        ]
        result = differential_evolution(
            objective, bounds, seed=42, maxiter=maxiter, tol=1e-6,
            popsize=15, mutation=(0.5, 1.0), recombination=0.7, polish=True,
        )
        K, r, t0 = result.x
        return RichardsParams(
            K=K, r=r, t0=t0, alpha=1.0, Q=1.0,
            name="sigmoid_fitted", fit_method="sigmoid",
            lognormal_A=K, lognormal_mu=t0, lognormal_sigma=r,
            n_waves=1, wave_A=[K], wave_mu=[t0], wave_sigma=[r],
        )

    def _fit_richards(self, daily_cases, t, total_cases, days, maxiter):
        cum_cases = np.cumsum(daily_cases)
        peak_day = int(np.argmax(daily_cases))
        smoothed = _smooth_for_comparison(daily_cases)

        def objective(params):
            K, r, t0, alpha = params
            if K <= 0 or r <= 0 or alpha <= 0:
                return 1e10
            pred_cum = self._richards_cumulative(t, K, r, t0, alpha)
            pred_daily = np.maximum(np.diff(pred_cum, prepend=0), 0)

            cum_err = np.mean(((pred_cum - cum_cases) / max(cum_cases[-1], 1)) ** 2)
            daily_err = self._compute_daily_error(smoothed, pred_daily)
            log_err = self._compute_log_error(smoothed, pred_daily)
            peak_err = ((np.max(pred_daily) - np.max(smoothed)) / max(np.max(smoothed), 1)) ** 2
            timing_err = ((int(np.argmax(pred_daily)) - peak_day) / max(days, 1)) ** 2

            return cum_err + 3.0 * daily_err + 2.0 * log_err + 2.0 * peak_err + 3.0 * timing_err

        bounds = [
            (total_cases * 0.5, total_cases * 3),
            (0.05, 0.5),
            (max(0, peak_day - 30), min(days, peak_day + 30)),
            (0.3, 3.0),
        ]
        result = differential_evolution(
            objective, bounds, seed=42, maxiter=maxiter, tol=1e-6,
            popsize=15, mutation=(0.5, 1.0), recombination=0.7, polish=True,
        )
        K, r, t0, alpha = result.x
        return RichardsParams(
            K=K, r=r, t0=t0, alpha=alpha, Q=1.0,
            name="richards_fitted", fit_method="richards",
            lognormal_A=K, lognormal_mu=t0, lognormal_sigma=r,
            n_waves=1, wave_A=[K], wave_mu=[t0], wave_sigma=[r],
        )

    def _fit_multi_wave(self, daily_cases, t, total_cases, days, n_waves, wave_peaks, maxiter):
        try:
            smoothed = _smooth_for_comparison(daily_cases)

            def objective(params):
                wave_params = []
                for i in range(n_waves):
                    idx = i * 3
                    A = params[idx]
                    mu = params[idx + 1]
                    sigma = params[idx + 2]
                    if A <= 0 or sigma <= 0:
                        return 1e10
                    wave_params.append((A, mu, sigma))

                try:
                    pred = self._multi_wave_daily(t, wave_params)
                except (OverflowError, FloatingPointError):
                    return 1e10

                pred = np.maximum(pred, 0)
                if np.sum(pred) < 1:
                    return 1e10

                daily_err = self._compute_daily_error(smoothed, pred)
                log_err = self._compute_log_error(smoothed, pred)
                peak_err = ((np.max(pred) - np.max(smoothed)) / max(np.max(smoothed), 1)) ** 2
                total_err = ((np.sum(pred) - total_cases) / max(total_cases, 1)) ** 2

                return daily_err + 2.0 * log_err + 2.0 * peak_err + 2.0 * total_err

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
        if params.ensemble_cum_pred and len(params.ensemble_cum_pred) >= days:
            return np.array(params.ensemble_cum_pred[:days])

        t = np.arange(days, dtype=float)
        if params.fit_method == "lognormal":
            if params.n_waves > 1 and len(params.wave_A) > 1:
                wave_params = list(zip(params.wave_A, params.wave_mu, params.wave_sigma))
                daily = self._multi_wave_daily(t, wave_params)
            else:
                daily = self._lognormal_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma)
            return np.cumsum(np.maximum(daily, 0))
        elif params.fit_method == "gaussian":
            daily = self._gaussian_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma)
            return np.cumsum(np.maximum(daily, 0))
        elif params.fit_method == "sigmoid":
            return self._sigmoid_cumulative(t, params.K, params.r, params.t0)
        elif params.fit_method == "richards":
            return self._richards_cumulative(t, params.K, params.r, params.t0, params.alpha)
        return np.zeros(days)

    def predict_daily(self, params: RichardsParams, days: int) -> np.ndarray:
        if params.ensemble_daily_pred and len(params.ensemble_daily_pred) >= days:
            return np.array(params.ensemble_daily_pred[:days])

        t = np.arange(days, dtype=float)
        if params.fit_method == "lognormal":
            if params.n_waves > 1 and len(params.wave_A) > 1:
                wave_params = list(zip(params.wave_A, params.wave_mu, params.wave_sigma))
                return np.maximum(self._multi_wave_daily(t, wave_params), 0)
            return np.maximum(self._lognormal_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma), 0)
        elif params.fit_method == "gaussian":
            return np.maximum(self._gaussian_daily(t, params.lognormal_A, params.lognormal_mu, params.lognormal_sigma), 0)
        elif params.fit_method in ("sigmoid", "richards"):
            cum = self.predict_cumulative(params, days)
            return np.maximum(np.diff(np.maximum(cum, 0), prepend=0), 0)
        return np.zeros(days)

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
        horizon: int = 14,
        maxiter: int = 50,
    ) -> dict[str, float]:
        daily_cases = _clean_daily_cases(daily_cases)
        n = len(daily_cases)
        if n < train_window + horizon:
            return {"cv_r2_mean": 0.0, "cv_r2_std": 0.0, "cv_corr_mean": 0.0, "cv_mape_mean": 0.0, "n_folds": 0}

        all_r2 = []
        all_corr = []
        all_mape = []

        step = train_window + horizon
        for start in range(0, n - train_window - horizon + 1, step):
            train_data = daily_cases[start:start + train_window].astype(float)
            test_data = daily_cases[start + train_window:start + train_window + horizon].astype(float)

            if np.sum(train_data) < 10 or np.sum(test_data) < 1:
                continue

            try:
                params = self.fit_cumulative_cases(train_data, population, maxiter=min(maxiter, 80))
                pred_daily = self.predict_daily(params, train_window + horizon)
                pred = pred_daily[train_window:train_window + horizon]
            except Exception:
                last7 = train_data[-7:] if len(train_data) >= 7 else train_data
                pred = np.tile(last7, (horizon // 7 + 1))[:horizon]

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

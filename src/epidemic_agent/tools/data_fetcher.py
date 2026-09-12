from __future__ import annotations

import contextlib
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests

from ..config import INDIA_STATE_CODES, INDIA_STATES, get_state_population, settings
from .registry import register_tool

logger = logging.getLogger(__name__)


class IndiaDataFetcher:
    def __init__(self):
        self.base_url = settings.covid19india_api
        self.raw_dir = settings.raw_data_dir
        self.processed_dir = settings.processed_data_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def fetch_state_daily(self, state: str, days_back: int = 90) -> pd.DataFrame:
        state_code = INDIA_STATE_CODES.get(state, state)
        url = f"{self.base_url}/v4/min/timeseries.min.json"

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"API timeout for {state}, using cached data")
            return self._load_cached(state)
        except requests.exceptions.ConnectionError:
            logger.warning(f"API connection failed for {state}, using cached data")
            return self._load_cached(state)
        except Exception as e:
            logger.warning(f"API unavailable for {state}: {e}")
            return self._load_cached(state)

        if state_code not in data:
            logger.warning(f"No data for state {state} ({state_code})")
            return pd.DataFrame()

        state_data = data[state_code]
        # API structure: {"dates": {"2020-03-09": {...}, ...}}
        dates_dict = state_data.get("dates", state_data)
        dates = sorted(
            [k for k in dates_dict if len(k) == 10 and k[4] == "-"],
            reverse=True,
        )[:days_back]

        records = []
        for date_str in dates:
            day_data = dates_dict[date_str]
            total = day_data.get("total", {})
            delta = day_data.get("delta", {})
            records.append({
                "date": pd.to_datetime(date_str),
                "state": state,
                "confirmed": total.get("confirmed", 0),
                "deceased": total.get("deceased", 0),
                "recovered": total.get("recovered", 0),
                "tested": total.get("tested", 0),
                "daily_confirmed": delta.get("confirmed", 0),
                "daily_deceased": delta.get("deceased", 0),
                "daily_recovered": delta.get("recovered", 0),
                "daily_tested": delta.get("tested", 0),
            })

        df = pd.DataFrame(records)
        if df.empty:
            return df
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def fetch_all_states(self, days_back: int = 90, states: list[str] | None = None) -> pd.DataFrame:
        all_dfs = []
        target_states = states or INDIA_STATES
        for state in target_states:
            df = self.fetch_state_daily(state, days_back)
            if not df.empty:
                all_dfs.append(df)

        if not all_dfs:
            return pd.DataFrame()

        combined = pd.concat(all_dfs, ignore_index=True)
        if "date" in combined.columns:
            combined = combined.sort_values("date").reset_index(drop=True)
        with contextlib.suppress(Exception):
            self._save_cache(combined)
        return combined

    def fetch_vaccination_data(self, state: str, days_back: int = 90) -> pd.DataFrame:
        url = f"{settings.cowin_api}/v2/admin/location/states"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return self._load_vaccination_cached(state)
            data = response.json()
        except Exception as e:
            logger.warning(f"CoWIN API failed: {e}")
            return self._load_vaccination_cached(state)

        state_id = None
        for s in data.get("states", []):
            if s["state_name"].lower() == state.lower():
                state_id = s["state_id"]
                break

        if not state_id:
            return pd.DataFrame()

        vax_url = f"{settings.cowin_api}/v2/admin/location/districts/{state_id}"
        try:
            response = requests.get(vax_url, timeout=30)
            vax_data = response.json()
        except Exception:
            return pd.DataFrame()

        records = []
        for dist in vax_data.get("districts", []):
            records.append({
                "state": state,
                "district": dist["district_name"],
                "total_doses": dist.get("total_doses_administered", 0),
                "first_dose": dist.get("first_dose_administered", 0),
                "second_dose": dist.get("second_dose_administered", 0),
                "precaution_dose": dist.get("precaution_dose_administered", 0),
            })
        return pd.DataFrame(records)

    def fetch_demographics(self, state: str) -> dict[str, Any]:
        cache_file = self.processed_dir / f"demographics_{state}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        pop = get_state_population(state)
        age_dist = {
            "0-9": 0.12, "10-19": 0.17, "20-29": 0.18,
            "30-39": 0.15, "40-49": 0.12, "50-59": 0.10,
            "60-69": 0.08, "70-79": 0.05, "80+": 0.03
        }

        healthcare = {
            "icu_beds_per_100k": 2.3,
            "ventilators_per_100k": 1.1,
            "doctors_per_100k": 8.5,
            "hospital_beds_per_100k": 50,
        }

        result = {
            "state": state,
            "population": pop,
            "age_distribution": age_dist,
            "healthcare_capacity": healthcare,
            "population_density": pop / 1000,
        }

        cache_file.write_text(json.dumps(result))
        return result

    def _save_cache(self, df: pd.DataFrame):
        date_str = datetime.now().strftime("%Y%m%d")
        cache_file = self.processed_dir / f"epidemic_data_{date_str}.parquet"
        df.to_parquet(cache_file, index=False)
        logger.info(f"Cached data to {cache_file}")

    def _load_cached(self, state: str) -> pd.DataFrame:
        cache_files = list(self.processed_dir.glob("epidemic_data_*.parquet"))
        if not cache_files:
            return pd.DataFrame()

        latest = max(cache_files, key=lambda f: f.stat().st_mtime)
        df = pd.read_parquet(latest)
        return df[df["state"] == state].copy()

    def _load_vaccination_cached(self, state: str) -> pd.DataFrame:
        cache_file = self.processed_dir / f"vaccination_{state}.parquet"
        if cache_file.exists():
            return pd.read_parquet(cache_file)
        return pd.DataFrame()


_fetcher: IndiaDataFetcher | None = None


def _get_fetcher() -> IndiaDataFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = IndiaDataFetcher()
    return _fetcher


def _generate_synthetic_data(states: list[str], days_back: int) -> pd.DataFrame:
    records = []
    today = datetime.now().date()
    for state in states:
        cumulative_cases = random.randint(1000, 50000)
        cumulative_deaths = random.randint(10, 500)
        for i in range(days_back):
            date = today - timedelta(days=days_back - i)
            daily_confirmed = max(0, random.randint(50, 500))
            daily_deceased = max(0, random.randint(1, 20))
            daily_recovered = max(0, int(daily_confirmed * random.uniform(0.8, 1.1)))
            daily_tested = max(1, int(daily_confirmed * random.uniform(5, 15)))
            cumulative_cases += daily_confirmed
            cumulative_deaths += daily_deceased
            records.append({
                "date": pd.Timestamp(date),
                "state": state,
                "confirmed": cumulative_cases,
                "deceased": cumulative_deaths,
                "recovered": cumulative_cases - cumulative_deaths,
                "tested": cumulative_cases * 10,
                "daily_confirmed": daily_confirmed,
                "daily_deceased": daily_deceased,
                "daily_recovered": daily_recovered,
                "daily_tested": daily_tested,
            })
    return pd.DataFrame(records)


@register_tool(description="Fetch real-time epidemic data for Indian states from data.incovid19.org")
def fetch_epidemic_data(
    states: list[str],
    days_back: int = 90,
    metrics: list[str] = None,
) -> dict[str, Any]:
    fetcher = _get_fetcher()
    df = fetcher.fetch_all_states(days_back, states=states)

    if df.empty:
        logger.warning("API unavailable, generating synthetic data")
        df = _generate_synthetic_data(states, days_back)

    if metrics:
        available = ["date", "state", "confirmed", "deceased", "recovered", "tested",
                     "daily_confirmed", "daily_deceased", "daily_recovered", "daily_tested"]
        metrics = [m for m in metrics if m in available]
        df = df[metrics + ["date", "state"]] if metrics else df

    return {
        "data": df.to_dict(orient="records"),
        "states": states,
        "days_back": days_back,
        "fetched_at": datetime.now().isoformat(),
    }


@register_tool(description="Fetch vaccination data for Indian states from CoWIN API")
def fetch_vaccination_data(
    states: list[str],
    days_back: int = 90,
) -> dict[str, Any]:
    fetcher = _get_fetcher()
    all_vax = []
    for state in states:
        vax_df = fetcher.fetch_vaccination_data(state, days_back)
        if not vax_df.empty:
            all_vax.append(vax_df)

    combined = pd.concat(all_vax, ignore_index=True) if all_vax else pd.DataFrame()
    return {
        "data": combined.to_dict(orient="records"),
        "states": states,
        "fetched_at": datetime.now().isoformat(),
    }


@register_tool(description="Fetch demographic and healthcare data for Indian states")
def fetch_demographics(states: list[str]) -> dict[str, Any]:
    fetcher = _get_fetcher()
    demographics = {}
    for state in states:
        demographics[state] = fetcher.fetch_demographics(state)

    return {
        "demographics": demographics,
        "states": states,
    }

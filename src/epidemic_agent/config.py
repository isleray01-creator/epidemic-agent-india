from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    gemini_api_key: str | None = None

    pickle_hmac_key: str = Field(
        default="", description="HMAC key for trusted pickle verification"
    )

    covid19india_api: str = "https://api.covid19india.org"
    cowin_api: str = "https://cdn-api.co-vin.in/api"

    data_dir: Path = Path("data")
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    chroma_db_dir: Path = Path("chroma_db")

    default_population: int = 1_000_000
    default_simulation_days: int = 90


settings = Settings()


INDIA_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
]

INDIA_STATE_CODES = {
    "Andhra Pradesh": "AP",
    "Arunachal Pradesh": "AR",
    "Assam": "AS",
    "Bihar": "BR",
    "Chhattisgarh": "CT",
    "Goa": "GA",
    "Gujarat": "GJ",
    "Haryana": "HR",
    "Himachal Pradesh": "HP",
    "Jharkhand": "JH",
    "Karnataka": "KA",
    "Kerala": "KL",
    "Madhya Pradesh": "MP",
    "Maharashtra": "MH",
    "Manipur": "MN",
    "Meghalaya": "ML",
    "Mizoram": "MZ",
    "Nagaland": "NL",
    "Odisha": "OR",
    "Punjab": "PB",
    "Rajasthan": "RJ",
    "Sikkim": "SK",
    "Tamil Nadu": "TN",
    "Telangana": "TG",
    "Tripura": "TR",
    "Uttar Pradesh": "UP",
    "Uttarakhand": "UT",
    "West Bengal": "WB",
    "Andaman and Nicobar Islands": "AN",
    "Chandigarh": "CH",
    "Dadra and Nagar Haveli and Daman and Diu": "DN",
    "Delhi": "DL",
    "Jammu and Kashmir": "JK",
    "Ladakh": "LA",
    "Lakshadweep": "LD",
    "Puducherry": "PY",
}

OBJECTIVE_WEIGHTS = {
    "deaths": 0.45,
    "economic_cost": 0.30,
    "social_cost": 0.15,
    "healthcare_strain": 0.10,
}

CONTACT_TRACING_PARAMS = {
    "tracing_efficiency": 0.6,
    "isolation_compliance": 0.7,
    "delay_days": 2,
    "cost_per_trace_inr": 500,
}

SHOCK_THRESHOLD = 0.15
SHOCK_HIGH_SEVERITY = 0.30
MAX_ADAPTATION_LOOPS = 3
CONFIDENCE_THRESHOLD = 0.6
SIMULATION_DAYS_PER_STEP = 7

VARIANT_PARAMS: dict[str, dict[str, float]] = {
    "wildtype": {"R0": 2.5, "IFR": 0.005, "immune_escape": 0.0, "serial_interval": 5.2},
    "delta": {"R0": 5.0, "IFR": 0.015, "immune_escape": 0.2, "serial_interval": 4.5},
    "omicron_ba1": {"R0": 7.0, "IFR": 0.003, "immune_escape": 0.5, "serial_interval": 3.5},
    "omicron_ba2": {"R0": 8.5, "IFR": 0.002, "immune_escape": 0.6, "serial_interval": 3.2},
    "omicron_ba5": {"R0": 10.0, "IFR": 0.0015, "immune_escape": 0.7, "serial_interval": 3.0},
    "xbb": {"R0": 12.0, "IFR": 0.001, "immune_escape": 0.8, "serial_interval": 2.8},
}

DEFAULT_R0 = 2.5
DEFAULT_IFR = 0.005
DEFAULT_SERIAL_INTERVAL = 5.2
INCUBATION_PERIOD = 5.2
INFECTIOUS_PERIOD = 7.0

AGE_GROUPS = [
    "0-9", "10-19", "20-29", "30-39", "40-49",
    "50-59", "60-69", "70-79", "80+"
]

AGE_IFR_MULTIPLIER = {
    "0-9": 0.001, "10-19": 0.003, "20-29": 0.01,
    "30-39": 0.03, "40-49": 0.1, "50-59": 0.3,
    "60-69": 1.0, "70-79": 3.0, "80+": 8.0
}

COMORBIDITY_IFR_MULTIPLIER = 2.5


def get_variant_params(variant: str) -> dict[str, float]:
    return VARIANT_PARAMS.get(variant.lower(), VARIANT_PARAMS["wildtype"])


def get_state_population(state: str) -> int:
    populations = {
        "Maharashtra": 124_000_000,
        "Uttar Pradesh": 230_000_000,
        "Bihar": 125_000_000,
        "West Bengal": 99_000_000,
        "Madhya Pradesh": 85_000_000,
        "Tamil Nadu": 77_000_000,
        "Rajasthan": 81_000_000,
        "Karnataka": 67_000_000,
        "Gujarat": 64_000_000,
        "Andhra Pradesh": 53_000_000,
        "Odisha": 46_000_000,
        "Telangana": 39_000_000,
        "Kerala": 35_000_000,
        "Jharkhand": 39_000_000,
        "Assam": 35_000_000,
        "Punjab": 30_000_000,
        "Chhattisgarh": 30_000_000,
        "Haryana": 28_000_000,
        "Delhi": 32_000_000,
        "Jammu and Kashmir": 14_000_000,
        "Uttarakhand": 11_000_000,
        "Himachal Pradesh": 7_500_000,
        "Tripura": 4_200_000,
        "Meghalaya": 3_800_000,
        "Manipur": 3_200_000,
        "Nagaland": 2_300_000,
        "Goa": 1_600_000,
        "Arunachal Pradesh": 1_600_000,
        "Puducherry": 1_500_000,
        "Mizoram": 1_300_000,
        "Chandigarh": 1_200_000,
        "Sikkim": 700_000,
        "Dadra and Nagar Haveli and Daman and Diu": 600_000,
        "Andaman and Nicobar Islands": 400_000,
        "Ladakh": 300_000,
        "Lakshadweep": 70_000,
    }
    return populations.get(state, 1_000_000)

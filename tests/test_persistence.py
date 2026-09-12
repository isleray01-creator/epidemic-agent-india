import tempfile
from pathlib import Path

import pytest

from epidemic_agent.persistence import SecurityError, TrustedStateStore
from epidemic_agent.state import EpidemicState


class TestPersistence:
    def test_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TrustedStateStore(hmac_key="test_key_32_bytes_long_exactly!!", storage_dir=Path(tmpdir))

            test_state = EpidemicState(
                current_day=10,
                simulation_days=60,
                country="India",
                states=["Maharashtra"],
                population={"Maharashtra": 124_000_000},
                infected={"Maharashtra": 1000},
                exposed={"Maharashtra": 500},
                recovered={"Maharashtra": 100},
                deceased={"Maharashtra": 10},
                vaccinated={"Maharashtra": 37_200_000},
                active_variants={"Maharashtra": "wildtype"},
                variant_prevalence={"Maharashtra": {"wildtype": 1.0}},
                current_policies={"Maharashtra": ["contact_tracing"]},
                intervention_history=[],
                variant_shock=None,
                confidence_score=0.85,
                objective_value=0.12,
                objective_breakdown={
                    "deaths": 0.05,
                    "economic_cost": 0.04,
                    "social_cost": 0.02,
                    "healthcare_strain": 0.01,
                },
                Rt_estimates={"Maharashtra": 1.2},
                healthcare_capacity={},
                contact_tracing_metrics={},
                metadata={},
            )

            filepath = store.save(test_state, "test_state.pkl")
            assert filepath.exists()

            loaded = store.load("test_state.pkl")
            assert loaded["current_day"] == 10
            assert loaded["states"] == ["Maharashtra"]
            assert loaded["objective_value"] == 0.12

    def test_tampered_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TrustedStateStore(hmac_key="test_key_32_bytes_long_exactly!!", storage_dir=Path(tmpdir))

            test_state = {"test": "data"}
            store.save(test_state, "test.pkl")

            filepath = Path(tmpdir) / "test.pkl"
            raw = filepath.read_bytes()
            signature, data = raw.split(b"||", 1)
            tampered = signature + b"||" + b"tampered"
            filepath.write_bytes(tampered)

            with pytest.raises(SecurityError):
                store.load("test.pkl")

    def test_wrong_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = TrustedStateStore(hmac_key="key_one_32_bytes_long_exactly!!", storage_dir=Path(tmpdir))
            store2 = TrustedStateStore(hmac_key="key_two_32_bytes_long_exactly!!", storage_dir=Path(tmpdir))

            store1.save({"test": "data"}, "test.pkl")

            with pytest.raises(SecurityError):
                store2.load("test.pkl")

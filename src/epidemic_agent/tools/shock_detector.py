from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from ..config import SHOCK_HIGH_SEVERITY, SHOCK_THRESHOLD
from .registry import register_tool

logger = logging.getLogger(__name__)


@dataclass
class ShockResult:
    shock_detected: bool
    anomalies: dict[str, dict[str, Any]]
    severity: str
    recommended_action: str
    confidence: float


class VariantShockDetector:
    def __init__(self, threshold: float = SHOCK_THRESHOLD, high_severity: float = SHOCK_HIGH_SEVERITY):
        self.threshold = threshold
        self.high_severity = high_severity

    def detect(
        self,
        predicted: dict[str, Any],
        actual: dict[str, Any],
        metrics: list = None,
    ) -> ShockResult:
        metrics = metrics or ["cases", "deaths", "Rt", "test_positivity"]

        anomalies = {}
        max_deviation = 0.0

        for metric in metrics:
            if metric not in predicted or metric not in actual:
                continue

            pred_val = predicted[metric]
            act_val = actual[metric]

            if isinstance(pred_val, (list, tuple)):
                pred_val = pred_val[-1] if pred_val else 0
            if isinstance(act_val, (list, tuple)):
                act_val = act_val[-1] if act_val else 0

            if pred_val == 0:
                continue

            deviation = abs(act_val - pred_val) / max(abs(pred_val), 1)

            if deviation > self.threshold:
                severity = "high" if deviation > self.high_severity else "medium"
                anomalies[metric] = {
                    "predicted": pred_val,
                    "actual": act_val,
                    "deviation": deviation,
                    "severity": severity,
                }
                max_deviation = max(max_deviation, deviation)

        if anomalies:
            high_count = sum(1 for a in anomalies.values() if a["severity"] == "high")
            overall_severity = "high" if high_count > 0 else "medium"

            if any("Rt" in m or "cases" in m for m in anomalies):
                action = "re_evaluate_variant_parameters"
            elif "deaths" in anomalies:
                action = "increase_healthcare_capacity"
            else:
                action = "review_intervention_effectiveness"

            return ShockResult(
                shock_detected=True,
                anomalies=anomalies,
                severity=overall_severity,
                recommended_action=action,
                confidence=min(max_deviation * 2, 1.0),
            )

        return ShockResult(
            shock_detected=False,
            anomalies={},
            severity="none",
            recommended_action="continue_monitoring",
            confidence=1.0,
        )


@register_tool(description="Detect variant shock by comparing predicted vs actual epidemic metrics")
def detect_variant_shock(
    predicted: dict[str, Any],
    actual: dict[str, Any],
    threshold: float = SHOCK_THRESHOLD,
) -> dict[str, Any]:
    detector = VariantShockDetector(threshold=threshold)
    result = detector.detect(predicted, actual)
    return asdict(result)

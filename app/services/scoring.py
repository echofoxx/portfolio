from __future__ import annotations

from statistics import pstdev

DEFAULT_WEIGHTS = {
    "mission_criticality": 25,
    "strategic_alignment": 20,
    "operational_impact": 15,
    "urgency": 10,
    "risk_reduction": 10,
    "readiness_interoperability": 10,
    "feasibility": 5,
    "expected_value": 5,
}

LABELS = {
    "mission_criticality": "Mission criticality",
    "strategic_alignment": "Strategic alignment",
    "operational_impact": "Operational impact",
    "urgency": "Urgency and time sensitivity",
    "risk_reduction": "Risk reduction",
    "readiness_interoperability": "Readiness / interoperability",
    "feasibility": "Feasibility and resource confidence",
    "expected_value": "Expected value / ROI",
}


def calculate_weighted_score(scores: dict[str, float], weights: dict[str, float] | None = None) -> float:
    weights = weights or DEFAULT_WEIGHTS
    missing = set(weights) - set(scores)
    if missing:
        raise ValueError(f"Missing score criteria: {', '.join(sorted(missing))}")
    if round(sum(weights.values()), 6) != 100:
        raise ValueError("Scoring weights must total 100")
    for key, value in scores.items():
        if value < 0 or value > 5:
            raise ValueError(f"{key} must be between 0 and 5")
    return round(sum(scores[k] * weights[k] for k in weights) / 5.0, 2)


def score_variance(totals: list[float]) -> float:
    if len(totals) < 2:
        return 0.0
    return round(pstdev(totals), 2)

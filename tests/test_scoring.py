import pytest

from app.services.scoring import DEFAULT_WEIGHTS, calculate_weighted_score, score_variance


def test_weighted_score_reconciles_to_100():
    assert sum(DEFAULT_WEIGHTS.values()) == 100
    score = calculate_weighted_score({key: 5 for key in DEFAULT_WEIGHTS})
    assert score == 100.0


def test_weighted_score_expected_value():
    values = {key: 3 for key in DEFAULT_WEIGHTS}
    values["mission_criticality"] = 5
    assert calculate_weighted_score(values) == 70.0


def test_scoring_rejects_out_of_range_and_missing():
    with pytest.raises(ValueError):
        calculate_weighted_score({key: 6 for key in DEFAULT_WEIGHTS})
    with pytest.raises(ValueError):
        calculate_weighted_score({"mission_criticality": 5})


def test_variance_highlights_assessor_disagreement():
    assert score_variance([80]) == 0.0
    assert score_variance([50, 90]) == 20.0

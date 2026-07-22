from lifestats.scoring.domain.model import MIN_BASELINE_DAYS, Signal, component, weighted_score


def test_component_requires_personal_baseline() -> None:
    assert component(Signal(60, [50] * (MIN_BASELINE_DAYS - 1))) is None


def test_component_direction_and_clamping() -> None:
    assert component(Signal(200, [50] * 28)) == 100
    assert component(Signal(200, [50] * 28, inverse=True)) == 0


def test_weighted_score_renormalizes_missing_components() -> None:
    result = weighted_score(
        {"sleep": Signal(50, [50] * 28), "hrv": Signal(None, [50] * 28)},
        {"sleep": 0.5, "hrv": 0.5},
    )
    assert result.value == 50
    assert result.missing == ["hrv"]

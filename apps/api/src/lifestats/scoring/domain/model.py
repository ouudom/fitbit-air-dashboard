from dataclasses import dataclass
from statistics import median

MODEL_VERSION = "lifestats-daily-v1"
MIN_BASELINE_DAYS = 14


@dataclass(frozen=True)
class Signal:
    current: float | None
    history: list[float]
    inverse: bool = False


@dataclass(frozen=True)
class ScoreResult:
    value: float | None
    components: dict[str, float]
    missing: list[str]
    status: str


def component(signal: Signal) -> float | None:
    if signal.current is None or len(signal.history) < MIN_BASELINE_DAYS:
        return None
    center = median(signal.history)
    deviations = [abs(value - center) for value in signal.history]
    scale = max(1.4826 * median(deviations), abs(center) * 0.05, 1.0)
    z_score = (signal.current - center) / scale
    if signal.inverse:
        z_score *= -1
    return clamp(50 + 15 * z_score)


def weighted_score(
    signals: dict[str, Signal], weights: dict[str, float], *, invert_result: bool = False
) -> ScoreResult:
    components = {
        name: value for name, signal in signals.items() if (value := component(signal)) is not None
    }
    missing = [name for name in weights if name not in components]
    available_weight = sum(weights[name] for name in components)
    if not available_weight:
        return ScoreResult(None, components, missing, "unavailable")
    value = sum(components[name] * weights[name] for name in components) / available_weight
    if invert_result:
        value = 100 - value
    return ScoreResult(round(clamp(value), 1), components, missing, "available")


def weighted_components(
    components: dict[str, float | None], weights: dict[str, float]
) -> ScoreResult:
    available = {name: value for name, value in components.items() if value is not None}
    missing = [name for name in weights if name not in available]
    available_weight = sum(weights[name] for name in available)
    if not available_weight:
        return ScoreResult(None, {}, missing, "unavailable")
    value = sum(float(available[name]) * weights[name] for name in available) / available_weight
    return ScoreResult(
        round(clamp(value), 1),
        {name: float(value) for name, value in available.items()},
        missing,
        "available",
    )


def clamp(value: float) -> float:
    return max(0.0, min(100.0, value))

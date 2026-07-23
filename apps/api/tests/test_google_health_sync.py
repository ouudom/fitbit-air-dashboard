from src.modules.google_health.sync import scope_granted


def test_scope_granted_accepts_oauth_url_form() -> None:
    assert scope_granted(
        ["https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly"],
        "googlehealth.health_metrics_and_measurements.readonly",
    )


def test_scope_granted_rejects_different_scope() -> None:
    assert not scope_granted(
        ["https://www.googleapis.com/auth/googlehealth.sleep.readonly"],
        "googlehealth.ecg.readonly",
    )

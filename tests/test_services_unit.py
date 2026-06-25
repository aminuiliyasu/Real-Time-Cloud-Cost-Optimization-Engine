from app.services.costs.baseline import compute_metric_based_baseline
from app.services.simulations.engine import compute_trend_percent


def test_compute_metric_based_baseline_returns_reasonable_value():
    value = compute_metric_based_baseline(avg_cpu=10.0, avg_mem=20.0)
    assert value == 54.0


def test_compute_trend_percent_upward():
    direction, percent = compute_trend_percent(12.0, 8.0)
    assert direction == "up"
    assert percent == 50.0


def test_compute_trend_percent_insufficient_data():
    direction, percent = compute_trend_percent(None, 8.0)
    assert direction == "insufficient_data"
    assert percent == 0.0

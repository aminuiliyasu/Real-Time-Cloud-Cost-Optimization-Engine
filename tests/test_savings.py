from app.services.costs.savings import (
    estimate_migration_savings,
    estimate_rightsizing_savings,
    estimate_shutdown_savings,
)


def test_rightsizing_savings_scales_with_utilization():
    idle = estimate_rightsizing_savings(avg_cpu=2.0, avg_mem=10.0)
    busy = estimate_rightsizing_savings(avg_cpu=40.0, avg_mem=10.0)
    assert idle > 0
    assert busy > 0
    assert idle > busy


def test_shutdown_savings_is_fraction_of_baseline():
    value = estimate_shutdown_savings(avg_cpu=4.0, avg_mem=20.0)
    assert 10.0 < value < 80.0


def test_migration_savings_zero_when_cpu_high():
    assert estimate_migration_savings(avg_cpu=20.0) == 0.0

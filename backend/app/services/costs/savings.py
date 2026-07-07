from app.services.costs.baseline import compute_metric_based_baseline


def estimate_rightsizing_savings(avg_cpu: float, avg_mem: float | None = None) -> float:
    baseline = compute_metric_based_baseline(avg_cpu, avg_mem)
    headroom = max(0.0, (100.0 - avg_cpu) / 100.0)
    return round(baseline * headroom * 0.5, 2)


def estimate_shutdown_savings(avg_cpu: float, avg_mem: float | None = None) -> float:
    baseline = compute_metric_based_baseline(avg_cpu, avg_mem)
    # Assume nights + weekends (~14h/day off).
    return round(baseline * (14.0 / 24.0) * 0.85, 2)


def estimate_migration_savings(avg_cpu: float, avg_mem: float | None = None) -> float:
    baseline = compute_metric_based_baseline(avg_cpu, avg_mem)
    if avg_cpu >= 15.0:
        return 0.0
    headroom = (15.0 - avg_cpu) / 15.0
    return round(baseline * min(0.55, 0.2 + headroom * 0.35), 2)

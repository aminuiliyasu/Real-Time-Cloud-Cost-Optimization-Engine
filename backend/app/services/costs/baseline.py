def compute_metric_based_baseline(avg_cpu: float, avg_mem: float | None) -> float:
    """
    Simple cost heuristic:
    - base floor cost = 40
    - cpu contributes up to 60
    - memory contributes up to 40 (if present)
    """
    cpu_component = min(max(avg_cpu, 0.0), 100.0) * 0.6
    mem_component = (min(max(avg_mem or 0.0, 0.0), 100.0) * 0.4) if avg_mem is not None else 10.0
    return round(40.0 + cpu_component + mem_component, 2)

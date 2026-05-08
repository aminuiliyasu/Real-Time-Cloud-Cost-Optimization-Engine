def test_dashboard_kpis_contract(client, seeded_data):
    response = client.get("/dashboard/kpis")
    assert response.status_code == 200
    payload = response.json()
    expected_keys = {
        "total_resources",
        "total_recommendations",
        "open_recommendations",
        "approved_recommendations",
        "executed_recommendations",
        "total_estimated_monthly_savings",
        "realized_monthly_savings",
        "last_metric_at",
    }
    assert expected_keys.issubset(payload.keys())
    assert payload["total_resources"] == 1


def test_recommendation_lifecycle_and_audit_logs(client, seeded_data):
    recommendation_id = seeded_data["recommendation"].id
    headers_operator = {
        "X-API-Key": "change_me_strong_key",
        "X-Role": "operator",
        "Content-Type": "application/json",
    }
    headers_admin = {
        "X-API-Key": "change_me_strong_key",
        "X-Role": "admin",
        "Content-Type": "application/json",
    }

    approve = client.post(
        f"/recommendations/{recommendation_id}/approve",
        headers=headers_operator,
        json={"actor": "tester", "notes": "approve from test"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    execute = client.post(
        f"/recommendations/{recommendation_id}/execute",
        headers=headers_admin,
        json={"actor": "tester", "notes": "execute from test"},
    )
    assert execute.status_code == 200
    assert execute.json()["status"] == "executed"

    logs = client.get(f"/recommendations/{recommendation_id}/audit-logs")
    assert logs.status_code == 200
    assert len(logs.json()) == 2
    assert logs.json()[0]["action"] == "executed"
    assert logs.json()[1]["action"] == "approved"


def test_simulation_endpoint_persists_runs(client, seeded_data):
    recommendation_id = seeded_data["recommendation"].id
    simulate = client.post(
        f"/recommendations/{recommendation_id}/simulate",
        json={"reduction_percent": 25},
    )
    assert simulate.status_code == 200
    payload = simulate.json()
    assert payload["recommendation_id"] == recommendation_id
    assert "risk_level" in payload
    assert "trend_direction" in payload

    history = client.get(f"/recommendations/{recommendation_id}/simulations")
    assert history.status_code == 200
    assert len(history.json()) >= 1

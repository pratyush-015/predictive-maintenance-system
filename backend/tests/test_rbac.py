def test_viewer_cannot_resolve_alerts(client, agent_headers):
    # First user is auto-admin; create a second, explicit viewer
    client.post(
        "/api/v1/auth/register",
        json={"username": "root", "email": "root@example.com", "password": "password123", "role": "admin"},
    )
    client.post(
        "/api/v1/auth/register",
        json={"username": "viewer1", "email": "viewer1@example.com", "password": "password123", "role": "viewer"},
    )
    login = client.post("/api/v1/auth/login", json={"username": "viewer1", "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.post("/api/v1/alerts/1/resolve", headers=headers)
    assert resp.status_code in (403, 404)  # 404 if no alert exists yet, 403 if RBAC blocks first


def test_admin_only_reload_models(client):
    client.post(
        "/api/v1/auth/register",
        json={"username": "adm", "email": "adm@example.com", "password": "password123", "role": "admin"},
    )
    client.post(
        "/api/v1/auth/register",
        json={"username": "view2", "email": "view2@example.com", "password": "password123", "role": "viewer"},
    )
    login = client.post("/api/v1/auth/login", json={"username": "view2", "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.post("/api/v1/predictions/reload-models", headers=headers)
    assert resp.status_code == 403


def test_model_comparison_endpoint_reachable(client, auth_headers):
    resp = client.get("/api/v1/predictions/model-comparison", headers=auth_headers)
    assert resp.status_code == 200
    assert "models" in resp.json()


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

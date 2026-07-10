def test_register_and_login(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123", "role": "viewer"},
    )
    assert resp.status_code == 201
    body = resp.json()
    # First-ever user auto-promoted to admin regardless of requested role
    assert body["role"] == "admin"

    resp = client.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "password123", "role": "viewer"},
    )
    resp = client.post("/api/v1/auth/login", json={"username": "bob", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, auth_headers):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_second_user_gets_requested_role(client):
    client.post(
        "/api/v1/auth/register",
        json={"username": "first", "email": "first@example.com", "password": "password123", "role": "viewer"},
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "second", "email": "second@example.com", "password": "password123", "role": "operator"},
    )
    assert resp.json()["role"] == "operator"


def test_duplicate_username_rejected(client):
    payload = {"username": "dup", "email": "dup1@example.com", "password": "password123", "role": "viewer"}
    client.post("/api/v1/auth/register", json=payload)
    payload2 = {"username": "dup", "email": "dup2@example.com", "password": "password123", "role": "viewer"}
    resp = client.post("/api/v1/auth/register", json=payload2)
    assert resp.status_code == 400

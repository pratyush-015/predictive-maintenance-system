SAMPLE_METRIC = {
    "device_uid": "test-device-001",
    "hostname": "test-host",
    "os_info": "Linux Test",
    "device_type": "laptop",
    "cpu_percent": 25.0,
    "cpu_freq_mhz": 2800,
    "cpu_core_count": 8,
    "load_avg_1m": 1.2,
    "memory_percent": 45.0,
    "memory_used_mb": 7000,
    "memory_total_mb": 16000,
    "swap_percent": 2.0,
    "disk_percent": 50.0,
    "disk_used_gb": 250,
    "disk_total_gb": 500,
    "disk_read_mb_s": 1.0,
    "disk_write_mb_s": 0.5,
    "net_sent_mb_s": 0.3,
    "net_recv_mb_s": 0.6,
    "temperature_c": 50.0,
    "gpu_percent": 5.0,
    "gpu_memory_percent": 3.0,
    "battery_percent": 80,
    "battery_plugged": True,
    "uptime_seconds": 3600,
    "process_count": 150,
}


def test_ingest_requires_agent_key(client):
    resp = client.post("/api/v1/metrics", json=SAMPLE_METRIC)
    assert resp.status_code == 401


def test_ingest_metric_creates_device(client, agent_headers, auth_headers):
    resp = client.post("/api/v1/metrics", json=SAMPLE_METRIC, headers=agent_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ok"

    devices = client.get("/api/v1/devices", headers=auth_headers).json()
    assert len(devices) == 1
    assert devices[0]["device_uid"] == "test-device-001"


def test_ingest_triggers_cpu_alert(client, agent_headers, auth_headers):
    payload = dict(SAMPLE_METRIC, cpu_percent=97.0)
    resp = client.post("/api/v1/metrics", json=payload, headers=agent_headers)
    assert resp.status_code == 201
    assert resp.json()["alerts_created"] >= 1

    alerts = client.get("/api/v1/alerts", headers=auth_headers).json()
    assert any(a["category"] == "cpu_overload" for a in alerts)


def test_ingest_normal_reading_no_alert(client, agent_headers, auth_headers):
    client.post("/api/v1/metrics", json=SAMPLE_METRIC, headers=agent_headers)
    alerts = client.get("/api/v1/alerts", headers=auth_headers).json()
    assert len(alerts) == 0


def test_metrics_history_requires_auth(client, agent_headers):
    client.post("/api/v1/metrics", json=SAMPLE_METRIC, headers=agent_headers)
    resp = client.get("/api/v1/metrics/history")
    assert resp.status_code == 401


def test_metrics_history_returns_readings(client, agent_headers, auth_headers):
    for _ in range(3):
        client.post("/api/v1/metrics", json=SAMPLE_METRIC, headers=agent_headers)
    resp = client.get("/api/v1/metrics/history?device_uid=test-device-001", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_batch_ingest(client, agent_headers, auth_headers):
    resp = client.post(
        "/api/v1/metrics/batch",
        json={"readings": [SAMPLE_METRIC, SAMPLE_METRIC]},
        headers=agent_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["ingested"] == 2


def test_alert_resolve(client, agent_headers, auth_headers):
    payload = dict(SAMPLE_METRIC, disk_percent=95.0)
    client.post("/api/v1/metrics", json=payload, headers=agent_headers)
    alerts = client.get("/api/v1/alerts", headers=auth_headers).json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]

    resp = client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["resolved"] is True

# API Reference

Full interactive documentation (auto-generated from the FastAPI schema, with
request/response models and a "try it out" console) is always available at:

- **Swagger UI**: `{BACKEND_URL}/docs`
- **ReDoc**: `{BACKEND_URL}/redoc`
- **OpenAPI schema (JSON)**: `{BACKEND_URL}/openapi.json`

e.g. locally: http://localhost:8000/docs

## Summary

All endpoints below are under the `/api/v1` prefix. Endpoints marked
🔒 require a `Bearer` JWT (obtained from `/auth/login`); 🔑 require the
agent's `X-Agent-Key` header instead.

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create a user. First-ever user is auto-promoted to `admin`. |
| POST | `/auth/login` | Exchange username/password for access + refresh tokens. |
| POST | `/auth/refresh` | Exchange a refresh token for a new token pair. |
| GET | `/auth/me` 🔒 | Current user's profile. |
| GET | `/auth/users` 🔒 (admin) | List all users. |

### Metrics ingestion & query
| Method | Path | Description |
|---|---|---|
| POST | `/metrics` 🔑 | Ingest one reading. Triggers alerting + ML inference + WS broadcast. |
| POST | `/metrics/batch` 🔑 | Ingest multiple readings (agent offline-buffer flush). |
| GET | `/metrics/latest` 🔒 | Most recent reading, optionally filtered by `device_uid`. |
| GET | `/metrics/history` 🔒 | Recent readings (`limit`, up to 5000), oldest→newest. |

### Predictions
| Method | Path | Description |
|---|---|---|
| GET | `/predictions` 🔒 | Recent predictions; `anomalies_only=true` to filter. |
| GET | `/predictions/model-comparison` 🔒 | Accuracy/Precision/Recall/F1/ROC-AUC/latency for all 5 trained models. |
| POST | `/predictions/reload-models` 🔒 (admin/operator) | Hot-reload models from disk after retraining. |

### Alerts & Incidents
| Method | Path | Description |
|---|---|---|
| GET | `/alerts` 🔒 | Filter by `device_uid`, `unresolved_only`, `severity`. |
| POST | `/alerts/{id}/resolve` 🔒 (admin/operator) | Mark an alert resolved. |
| GET | `/incidents` 🔒 | Filter by `device_uid`, `status`. |

### Devices
| Method | Path | Description |
|---|---|---|
| GET | `/devices` 🔒 | All devices that have ever reported in, most recently seen first. |

### Live stream
| Protocol | Path | Description |
|---|---|---|
| WebSocket | `/ws/live?token=...` | Push channel: new `metric` (+ prediction + alert ids), `alerts`, and `batch_synced` events. |

### Meta (no auth, no `/api/v1` prefix)
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe + which ML models are currently loaded. |
| GET | `/` | Basic service info. |

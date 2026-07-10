# Architecture

## Data flow

```
┌─────────────┐   every 5s    ┌─────────────┐   REST/WS    ┌──────────────┐
│  Monitoring │ ─────────────▶│   FastAPI   │◀────────────▶│   React      │
│    Agent    │  POST /metrics│   Backend   │  live stream │  Dashboard   │
│  (psutil)   │               │             │              │              │
└─────────────┘               └──────┬──────┘              └──────────────┘
  buffers locally                    │
  if offline (SQLite)                │  writes reading, runs
                                      │  inference synchronously
                                      ▼
                          ┌───────────────────────┐
                          │  PostgreSQL / SQLite   │  metrics, predictions,
                          │  (system of record)    │  alerts, incidents, users
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌───────────────────────┐
                          │  ML Runtime            │  IsolationForest +
                          │  (scikit-learn +       │  RandomForest (live path)
                          │   TensorFlow, in-proc) │  + Autoencoder cross-check
                          └───────────────────────┘

                          ┌───────────────────────┐
                          │  InfluxDB (optional)   │  secondary high-res
                          │  disabled by default   │  time-series sink
                          └───────────────────────┘
```

Every metric ingestion request does four things synchronously, in order:
1. **Persist** the reading (`Metric` row).
2. **Rule-based alerting** — deterministic threshold checks (CPU/mem/disk/
   temp/battery) that work even before any ML model is trained.
3. **ML inference** — builds a feature vector from the reading plus recent
   rolling history, runs it through the loaded models, and stores a
   `Prediction` row. Failures here are caught and logged but never fail the
   ingestion request itself — monitoring must keep working even if a model
   is broken or missing.
4. **Broadcast** the new reading (and any resulting alerts) to connected
   dashboard clients over the `/api/v1/ws/live` WebSocket.

## Why the live path uses IsolationForest + RandomForest, not LSTM

All five models (`Isolation Forest`, `One-Class SVM`, `Random Forest`,
`LSTM`, `Autoencoder`) are trained and their metrics are shown side-by-side
on the **Model Comparison** page — that comparison is a first-class feature,
not just a training artifact.

For the synchronous, per-request `/metrics` inference path, though, the
backend deliberately serves from the classical models:
- They're 10-100x faster for single-sample inference (sub-millisecond vs.
  several ms for a TensorFlow forward pass), which matters when every
  ingestion request pays this cost inline.
- RandomForest's `predict_proba` + `feature_importances_` give both a
  multi-class issue label *and* cheap per-prediction explainability (see
  `app/ml_runtime/predictor.py`), which the dashboard's "top contributing
  signals" panel depends on.
- The Autoencoder is still consulted inline (it's a cheap single dense-net
  forward pass on one vector) as a secondary, fully-unsupervised cross-check
  — if its reconstruction error disagrees with the Random Forest's "normal"
  verdict, the prediction is escalated to `abnormal_behavior` at reduced
  confidence rather than silently trusting one model.
- The LSTM requires a sequence tensor, not a single vector, and would need
  either a live sequence buffer per device or an offline/batch scoring job.
  That's flagged here as the natural next step (see below) rather than
  bolted on under time pressure — a documented gap beats a fragile shortcut.

## Feature engineering duplication (`features.py` in two places)

`backend/app/ml_runtime/features.py` and `ml/feature_lib.py` intentionally
contain the same feature list and rolling-window logic, computed two
different ways (row-by-row on live SQLAlchemy history vs. vectorized pandas
over a static dataset). This is a pragmatic tradeoff: keeping training and
serving in the same repo but different processes without a shared package
avoids a packaging step for a project this size, at the cost of needing
discipline to keep them in sync. If this were served as a subject grown
into production teams, the fix is a `libs/telemetry_features` package
imported by both `backend/` and `ml/`.

## Extensibility — this is designed to grow

Given the ask to "employ more features later" and support other machines
beyond one laptop, several seams are already in place:

- **`Device` table** exists from day one, even though today there's exactly
  one laptop. Adding servers or IoT devices is just more rows, not a schema
  change — `device_type` is already a field, and `Metric`/`Prediction`/
  `Alert` are all foreign-keyed to `device_id`, not hardcoded to one host.
- **`Metric.extra` (JSON column)** is an escape hatch: a new sensor type
  (say, fan RPM, or a second GPU) can be added to a payload immediately via
  this field with zero migration, then promoted to a real typed column
  later once you know it's here to stay.
- **`ModelRegistry.reload()`** hot-swaps models from disk without an API
  restart (`POST /api/v1/predictions/reload-models`), so retraining on more
  data is a re-run of `ml/train_*.py` plus one API call, not a redeploy.
- **RBAC roles** (`admin` / `operator` / `viewer`) are already enforced at
  the route level via `require_role(...)`, ready for a real multi-user team
  rather than a single-laptop side project.
- **InfluxDB** is wired in (disabled by default) for the day raw
  high-resolution telemetry retention outgrows what you want sitting in
  Postgres.

## Suggested next milestones

1. **Sequence buffer for live LSTM scoring** — maintain the last N readings
   per device in-process (or in Redis for multi-worker deployments) so the
   LSTM can be added to the live prediction path, not just the offline
   comparison.
2. **Incident auto-correlation** — the `Incident` table and API exist, but
   nothing currently *creates* incidents from clusters of related alerts.
   A background job that groups alerts by device + time window + category
   is the natural next addition.
3. **SHAP-based explainability** — swap the importance × deviation
   approximation in `predictor.py` for `shap.TreeExplainer(rf)` once the
   added latency (a few ms) is acceptable for your traffic.
4. **Multi-tenant orgs** — if this grows beyond one team, add an
   `Organization` table above `Device`/`User` and scope queries by it.

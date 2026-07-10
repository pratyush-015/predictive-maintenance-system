# Pulse — AI-Powered AIOps Platform for Predictive Maintenance

Real-time monitoring and ML-driven predictive maintenance for your laptop
(or, from day one, any number of servers/IoT devices — see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)). A lightweight agent samples
CPU, memory, disk, network, temperature, GPU, battery, and processes every
5 seconds; a FastAPI backend stores it, runs it through five trained ML
models, raises alerts, and streams everything live to a React dashboard.

## What's actually in here

- **Agent** (`agent/`) — cross-platform Python collector using `psutil`,
  with automatic local buffering and sync if the backend is unreachable.
- **Backend** (`backend/`) — FastAPI + SQLAlchemy + Alembic, JWT auth with
  role-based access control, REST + WebSocket APIs, rule-based *and*
  ML-based alerting.
- **ML pipeline** (`ml/`) — trains and compares **Isolation Forest,
  One-Class SVM, Random Forest, LSTM, and an Autoencoder** on
  Accuracy/Precision/Recall/F1/ROC-AUC/inference-time, on a labeled
  synthetic telemetry dataset covering CPU overload, memory leaks, disk
  degradation, and general abnormal behavior.
- **Dashboard** (`frontend/`) — React 19 + TypeScript + Vite + Tailwind +
  Framer Motion. Live gauges, streaming charts, an ML prediction panel with
  lightweight explainability, alerts feed, incident timeline, model
  comparison view, dark/light mode.
- **Deployment** — Dockerfiles for backend/frontend, `docker-compose.yml`
  wiring Postgres (+ optional InfluxDB), Alembic migrations run
  automatically on boot, GitHub Actions CI.

## Quickstart

The fastest path to seeing your own laptop on the dashboard:

```bash
# 1. Train the ML models (one-time; ~2 minutes on a laptop CPU)
cd ml
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python generate_data.py && python train_baseline.py && python train_deep.py

# 2. Start the backend
cd ../backend
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
# -> http://localhost:8000/docs

# 3. Start the dashboard (new terminal)
cd ../frontend
npm install
cp .env.example .env
npm run dev
# -> http://localhost:5173  (register the first account — it becomes admin)

# 4. Start the agent (new terminal) — this is what feeds YOUR laptop's real data
cd ../agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Open `http://localhost:5173`, register, and your laptop should appear on
the Overview page within a few seconds.

For a one-command production-ish deployment via Docker, see
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, TailwindCSS v4, Framer Motion, Recharts, Zustand |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Databases | PostgreSQL (system of record), InfluxDB (optional, high-res raw telemetry) |
| ML | scikit-learn, TensorFlow/Keras, pandas, NumPy |
| Deployment | Docker, Docker Compose, Nginx, GitHub Actions |

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — data flow, design
  decisions (and their tradeoffs), extensibility points for adding more
  features/devices later
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Docker Compose and manual
  deployment, production hardening checklist
- [docs/API.md](docs/API.md) — endpoint reference (full interactive docs
  live at `/docs` on the running backend)
- [agent/README.md](agent/README.md) — agent configuration and
  background-service setup for Linux/macOS/Windows

## Project structure

```
aiops-platform/
├── agent/              # monitoring agent (psutil collector, offline buffer)
├── backend/            # FastAPI app, Alembic migrations, tests
│   └── app/
│       ├── api/routes/ # auth, metrics, predictions, alerts, devices, ws
│       ├── core/       # config, security (JWT/bcrypt), logging
│       ├── db/         # SQLAlchemy models + session
│       ├── ml_runtime/ # feature engineering + model loading/inference at serving time
│       ├── schemas/    # Pydantic request/response models
│       └── services/   # alerts, device lookup, InfluxDB, WebSocket manager
├── ml/                  # synthetic data generation + training scripts
│   └── models/          # trained artifacts (scaler, 5 models, metadata, comparison)
├── frontend/            # React dashboard
│   └── src/
│       ├── components/  # dashboard widgets, layout, ui primitives
│       ├── pages/       # Overview, Devices, Alerts, Incidents, Model Comparison
│       └── store/       # auth, theme, live dashboard data (WebSocket-driven)
├── docs/                 # architecture, deployment, API reference
└── docker-compose.yml
```

## Milestones (as built)

- ✅ **M1** — Collector + Backend + Database
- ✅ **M2** — Live Dashboard (WebSocket streaming, gauges, charts)
- ✅ **M3** — Baseline ML (Isolation Forest, One-Class SVM, Random Forest)
- ✅ **M4** — Deep Learning Prediction (LSTM, Autoencoder)
- ✅ **M5** — Explainable AI, alerts, deployment, documentation

## License

Built as an internship/portfolio project. Use and adapt freely.

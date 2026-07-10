# Deployment Guide

## Option A: Docker Compose (recommended — one command, production-ish)

Prerequisites: Docker + Docker Compose installed.

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `AGENT_API_KEY` — same command, different value
- `POSTGRES_PASSWORD` — a real password
- `PUBLIC_ORIGIN` — the URL you'll access the dashboard from (e.g. `http://your-server-ip` or your domain)

Then:
```bash
docker compose up -d --build
```

This starts Postgres, the backend (running Alembic migrations automatically
on boot), and the frontend served by nginx on port 80. Visit
`http://localhost` (or your server's address).

The ML models trained via `ml/train_baseline.py` / `ml/train_deep.py` are
mounted read-only from `../ml/models` into the backend container — retrain
and the backend picks them up after a container restart, or hit
`POST /api/v1/predictions/reload-models` (as an admin) to hot-reload without
restarting.

**Run the agent** on whatever machine you want to monitor (see
`agent/README.md`), pointing `AIOPS_BACKEND_URL` at wherever you exposed the
backend and `AIOPS_AGENT_API_KEY` at the same value you put in `.env`.

To include the optional InfluxDB service:
```bash
docker compose --profile influx up -d --build
```
and set `INFLUX_ENABLED=true` in `.env`.

### Updating
```bash
git pull
docker compose up -d --build
```
Migrations run automatically on backend startup — no manual DB step needed.

### Stopping / resetting
```bash
docker compose down          # stop, keep data
docker compose down -v       # stop and WIPE all data (Postgres + Influx volumes)
```

## Option B: Manual / native (best for local development)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
SQLite is used by default — zero setup. Swap `DATABASE_URL` in `.env` for a
Postgres URL and run `alembic upgrade head` if you want Postgres locally too.

**Train the ML models** (one-time, or whenever you want to retrain on more data):
```bash
cd ml
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python generate_data.py     # synthetic training data — swap for real collected data over time
python train_baseline.py    # Isolation Forest, One-Class SVM, Random Forest
python train_deep.py        # LSTM, Autoencoder
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env        # points at http://localhost:8000 by default
npm run dev
```
Visit `http://localhost:5173`.

**Agent** — see `agent/README.md`.

## Production hardening checklist

- [ ] Set a strong, unique `SECRET_KEY` and `AGENT_API_KEY` (never reuse the
      dev defaults from `.env.example`)
- [ ] Put the deployment behind HTTPS (a reverse proxy like Caddy or Traefik
      in front of the frontend's port 80 is the simplest path; or terminate
      TLS at a cloud load balancer)
- [ ] Set `CORS_ORIGINS` / `PUBLIC_ORIGIN` to your real domain, not `*`
- [ ] Back up the Postgres volume (`docker compose exec postgres pg_dump ...`)
- [ ] Review `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_MINUTES`
      in `backend/app/core/config.py` for your risk tolerance
- [ ] Consider running the backend with more `--workers` behind a real load
      balancer if monitoring many devices (each worker loads its own copy
      of the ML models into memory)
- [ ] Rotate `AGENT_API_KEY` periodically if agents run on machines outside
      your direct control

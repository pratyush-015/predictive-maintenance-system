# AIOps Monitoring Agent

Collects live system telemetry (CPU, RAM, disk, network, temperature, GPU,
battery, uptime, processes) every 5 seconds and streams it to the backend.
Buffers locally and syncs automatically if the backend is unreachable — you
can close your laptop lid, lose Wi-Fi, or restart the backend without losing
any readings.

## Quick start (any OS)

```bash
cd agent
python -m venv .venv

# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env        # edit AIOPS_BACKEND_URL / AIOPS_AGENT_API_KEY to match your backend
python main.py
```

You should see log lines confirming readings are being sent every 5 seconds.
Open the dashboard — your device should appear within a few seconds.

## Configuration

All settings are environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `AIOPS_BACKEND_URL` | `http://localhost:8000` | Backend base URL |
| `AIOPS_AGENT_API_KEY` | — | Must match the backend's `AGENT_API_KEY` |
| `AIOPS_DEVICE_TYPE` | `laptop` | `laptop` \| `server` \| `iot` |
| `AIOPS_COLLECT_INTERVAL` | `5` | Seconds between readings |
| `AIOPS_FLUSH_INTERVAL` | `15` | How often to retry flushing the offline buffer |
| `AIOPS_TOP_N_PROCESSES` | `5` | Processes reported per reading |

## Running it in the background

### Linux (systemd) — recommended
```bash
sudo cp aiops-agent.service /etc/systemd/system/
# edit the WorkingDirectory / ExecStart paths in the file first
sudo systemctl daemon-reload
sudo systemctl enable --now aiops-agent
journalctl -u aiops-agent -f   # tail logs
```

### macOS (launchd)
Create `~/Library/LaunchAgents/com.aiops.agent.plist` pointing `ProgramArguments`
at your venv's `python` and `main.py`, then:
```bash
launchctl load ~/Library/LaunchAgents/com.aiops.agent.plist
```

### Windows
Easiest: Task Scheduler → "Create Task" → Trigger "At log on" → Action
`C:\path\to\agent\.venv\Scripts\python.exe C:\path\to\agent\main.py`, "Start in"
set to the `agent` folder. For a true background service, wrap it with
[NSSM](https://nssm.cc/).

### Docker
Possible (`docker build -t aiops-agent . && docker run aiops-agent`) but only
recommended if you bind-mount the host's `/proc`, `/sys`, and root filesystem
— see the comment in `Dockerfile`. Running natively (above) is simpler and
gives more accurate readings for a laptop.

## How offline buffering works

Every reading is POSTed immediately. If that fails (backend down, no
network), the reading is written to a local SQLite file (`buffer.db`) instead
of being dropped. Every `AIOPS_FLUSH_INTERVAL` seconds, the agent retries
sending everything buffered via the batch endpoint, oldest first, and only
deletes entries the backend actually acknowledged. Safe to `Ctrl+C` and
restart any time — the buffer persists across restarts.

## Privacy note

The agent hashes a machine identifier (derived from the network MAC address)
into a `device_uid` rather than sending raw hardware identifiers, and caches
it in `.device_identity.json` so the ID is stable across restarts.

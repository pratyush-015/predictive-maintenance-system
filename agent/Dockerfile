# --- AIOps Monitoring Agent ---
#
# IMPORTANT: this container can only see the METRICS THE CONTAINER RUNTIME
# EXPOSES TO IT, not necessarily the true host. For monitoring the actual
# physical laptop (not a container), running the agent natively with
# `python main.py` (see agent/README.md) is strongly preferred and is what
# this project is built and tested against.
#
# This Dockerfile is provided for cases where you specifically want to run
# the agent inside a container against a host whose /proc, /sys, and root
# filesystem are bind-mounted in (see the commented example in
# docker-compose.yml). Even then, CPU/memory/disk readings will reflect the
# host correctly, but per-process detail and GPU/battery sensors are less
# reliable across the container boundary.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]

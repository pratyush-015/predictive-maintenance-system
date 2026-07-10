"""Agent configuration, loaded from environment variables / a local `.env`.

Keeping this as plain env vars (not a database or config service) is
deliberate: the agent must be able to start and buffer data even if it has
never talked to the backend yet.
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AgentConfig:
    backend_url: str = os.getenv("AIOPS_BACKEND_URL", "http://localhost:8000")
    api_key: str = os.getenv("AIOPS_AGENT_API_KEY", "dev-agent-key-change-me")
    device_type: str = os.getenv("AIOPS_DEVICE_TYPE", "laptop")
    collect_interval_seconds: float = float(os.getenv("AIOPS_COLLECT_INTERVAL", "5"))
    flush_interval_seconds: float = float(os.getenv("AIOPS_FLUSH_INTERVAL", "15"))
    top_n_processes: int = int(os.getenv("AIOPS_TOP_N_PROCESSES", "5"))
    buffer_db_path: str = os.getenv("AIOPS_BUFFER_DB", os.path.join(os.path.dirname(__file__), "buffer.db"))
    request_timeout_seconds: float = float(os.getenv("AIOPS_REQUEST_TIMEOUT", "5"))
    max_batch_size: int = int(os.getenv("AIOPS_MAX_BATCH_SIZE", "200"))
    log_level: str = os.getenv("AIOPS_LOG_LEVEL", "INFO")

    @property
    def ingest_url(self) -> str:
        return f"{self.backend_url.rstrip('/')}/api/v1/metrics"

    @property
    def batch_ingest_url(self) -> str:
        return f"{self.backend_url.rstrip('/')}/api/v1/metrics/batch"


config = AgentConfig()

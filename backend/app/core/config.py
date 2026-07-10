"""
Centralized configuration for the AIOps backend.

All values are overridable via environment variables or a `.env` file so the
same codebase runs unchanged across local dev (SQLite), Docker Compose
(Postgres + InfluxDB), and any future cloud deployment.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    PROJECT_NAME: str = "AIOps Predictive Maintenance Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # --- Security / Auth ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_super_secret_key_please_rotate"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]

    # --- Relational database (Postgres in prod, SQLite for zero-setup local dev) ---
    DATABASE_URL: str = "sqlite:///./aiops.db"

    # --- InfluxDB (optional high-resolution time-series store for raw metrics) ---
    INFLUX_ENABLED: bool = False
    INFLUX_URL: str = "http://localhost:8086"
    INFLUX_TOKEN: str = "dev-token"
    INFLUX_ORG: str = "aiops"
    INFLUX_BUCKET: str = "metrics"

    # --- ML ---
    ML_MODEL_DIR: str = "../ml/models"
    DEFAULT_ANOMALY_MODEL: str = "isolation_forest"  # which model serves /predict by default

    # --- Ingestion / Agent auth ---
    AGENT_API_KEY: str = "dev-agent-key-change-me"

    # --- Alerting thresholds (fallback rule-based alerts, independent of ML) ---
    CPU_ALERT_THRESHOLD: float = 90.0
    MEMORY_ALERT_THRESHOLD: float = 90.0
    DISK_ALERT_THRESHOLD: float = 90.0

    # --- WebSocket ---
    WS_BROADCAST_INTERVAL_SECONDS: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

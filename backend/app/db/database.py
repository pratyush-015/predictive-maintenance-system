"""Database engine/session management.

Works against SQLite (zero-config local dev) or PostgreSQL (docker-compose /
production) purely based on the `DATABASE_URL` env var — no code changes
needed when switching environments.
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist (used for first-run / SQLite dev).

    In Postgres/production, prefer Alembic migrations (`alembic upgrade head`).
    """
    from app.db import models  # noqa: F401  (ensures models are registered on Base)

    Base.metadata.create_all(bind=engine)

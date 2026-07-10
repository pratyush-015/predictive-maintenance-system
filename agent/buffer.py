"""Local durable buffer so the agent never loses readings if the backend is
unreachable (laptop offline, VPN down, backend restarting, etc). Readings are
appended here immediately after collection and only deleted once the backend
has acknowledged receiving them.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any


class LocalBuffer:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, timeout=10)

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def add(self, payload: dict[str, Any]) -> None:
        import time

        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO pending_readings (payload, created_at) VALUES (?, ?)",
                (json.dumps(payload), time.time()),
            )
            conn.commit()

    def peek_batch(self, limit: int) -> list[tuple[int, dict[str, Any]]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id, payload FROM pending_readings ORDER BY id ASC LIMIT ?", (limit,)
            ).fetchall()
        return [(row[0], json.loads(row[1])) for row in rows]

    def remove(self, ids: list[int]) -> None:
        if not ids:
            return
        with self._lock, self._connect() as conn:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(f"DELETE FROM pending_readings WHERE id IN ({placeholders})", ids)
            conn.commit()

    def count(self) -> int:
        with self._lock, self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM pending_readings").fetchone()[0]

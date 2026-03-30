from __future__ import annotations

import subprocess
import time
from typing import Final

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings


DB_WAIT_TIMEOUT_SECONDS: Final[int] = 60
DB_WAIT_INTERVAL_SECONDS: Final[int] = 2


def _run_alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def _create_engine():
    settings = get_settings()
    is_sqlite = settings.database_url.startswith("sqlite")
    return create_engine(
        settings.database_url,
        future=True,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )


def _wait_for_database() -> None:
    engine = _create_engine()
    deadline = time.monotonic() + DB_WAIT_TIMEOUT_SECONDS
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError as exc:
            last_error = exc
            time.sleep(DB_WAIT_INTERVAL_SECONDS)

    raise RuntimeError("Database did not become ready before bootstrap timeout.") from last_error


def main() -> None:
    _wait_for_database()
    _run_alembic("upgrade", "head")


if __name__ == "__main__":
    main()

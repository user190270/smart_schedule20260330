from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import subprocess
from threading import Lock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()
is_sqlite = settings.database_url.startswith("sqlite")
_migration_lock = Lock()
_migrations_applied = False

engine = create_engine(
    settings.database_url,
    echo=settings.sqlalchemy_echo,
    future=True,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    server_root = Path(__file__).resolve().parents[2]
    subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=server_root)


def init_db() -> None:
    global _migrations_applied

    if _migrations_applied:
        return

    with _migration_lock:
        if _migrations_applied:
            return
        run_migrations()
        _migrations_applied = True

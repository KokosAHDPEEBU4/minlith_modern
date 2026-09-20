"""Database engine — SQLite via SQLAlchemy with WAL mode."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

_DB_DIR = Path.home() / ".minlith"
_DB_PATH = _DB_DIR / "minlith.db"
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{_DB_PATH}"
        _engine = create_engine(url, echo=False, poolclass=NullPool, connect_args={"check_same_thread": False})
        # Enable WAL mode for better concurrency
        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        logger.info("Database connected: %s", _DB_PATH)
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db() -> None:
    """Create all tables if they don't exist."""
    from src.database.models import Base
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables created/verified")

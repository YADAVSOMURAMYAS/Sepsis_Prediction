"""SQLAlchemy engine + session factory — supports SQLite (dev) and PostgreSQL (prod)."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sepsisai.db")

# ── Engine — dialect-aware config ─────────────────────────────────────────────
_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # SQLite: single-thread safety flag required
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL (Cloud SQL via psycopg2):
    #   - pool_size      : persistent connections kept open
    #   - max_overflow   : burst connections above pool_size
    #   - pool_pre_ping  : validates connections before use (handles Cloud SQL idle timeouts)
    #   - pool_recycle   : drop & re-open connections older than 30 min
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency – yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

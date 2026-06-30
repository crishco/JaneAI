"""Database layer prepared for future SQLite integration."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for future ORM models."""


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _configure_sqlite(engine: Engine) -> None:
    """Enable foreign key support for SQLite connections."""

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
        if engine.dialect.name == "sqlite":
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


def init_database(settings: Settings) -> None:
    """Initialize the SQLAlchemy engine and session factory."""
    global _engine, _session_factory

    if _engine is not None:
        logger.debug("Database already initialized")
        return

    logger.info("Initializing database at %s", settings.database_url)
    _engine = create_engine(
        settings.database_url,
        echo=settings.database_echo,
        future=True,
        pool_pre_ping=True,
    )
    _configure_sqlite(_engine)
    _session_factory = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def create_tables() -> None:
    """Create all tables registered on the declarative base."""
    if _engine is None:
        raise RuntimeError("Database has not been initialized")

    Base.metadata.create_all(bind=_engine)
    logger.info("Database tables ensured")


def get_session_factory() -> sessionmaker[Session]:
    """Return the configured session factory."""
    if _session_factory is None:
        raise RuntimeError("Database has not been initialized")
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_database() -> None:
    """Dispose of the database engine."""
    global _engine, _session_factory

    if _engine is not None:
        _engine.dispose()
        logger.info("Database engine disposed")

    _engine = None
    _session_factory = None

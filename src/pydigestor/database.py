"""Database connection and session management."""

from collections.abc import Generator

from sqlmodel import Session, create_engine
from sqlalchemy import event

from pydigestor.config import settings

# Create database engine with SQLite-specific settings
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False  # Allow multi-threaded access

engine = create_engine(
    settings.database_url,
    echo=settings.enable_debug,  # Log SQL queries in debug mode
    connect_args=connect_args,
)


# Load sqlite-vec extension on connection (SQLite only)
@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """Load SQLite extensions on connection."""
    if settings.database_url.startswith("sqlite"):
        try:
            dbapi_conn.enable_load_extension(True)
            # Load sqlite-vec extension
            import sqlite_vec
            sqlite_vec.load(dbapi_conn)
            dbapi_conn.enable_load_extension(False)
        except Exception as e:
            # Log warning but don't fail - extension might not be needed yet
            import logging
            logging.warning(f"Could not load sqlite-vec extension: {e}")


def get_session() -> Generator[Session, None, None]:
    """
    Get a database session.

    Yields:
        Session: SQLModel database session

    Example:
        >>> with get_session() as session:
        ...     articles = session.query(Article).all()
    """
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """
    Initialize database tables.

    This is called by Alembic migrations, not needed in normal operation.
    """
    from pydigestor.models import Article, Signal, TriageDecision  # noqa: F401
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)

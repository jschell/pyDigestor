"""Database connection and session management."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from pydigestor.config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.enable_debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,  # Verify connections before using
)


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

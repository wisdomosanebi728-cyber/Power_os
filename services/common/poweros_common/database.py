from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


def get_engine(database_url: str, pool_size: int = 10, max_overflow: int = 20):
    """Create a configured SQLAlchemy engine."""
    return create_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
    )


def get_session_factory(engine):
    """Create a configured session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session(session_factory) -> Generator[Session, None, None]:
    """Context manager for safe transactional database sessions."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

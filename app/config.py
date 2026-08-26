"""Database configuration and session management."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Environment-based database selection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./visitarun.db",  # Default: SQLite local
)

# Create engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL or other URL
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency injection for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

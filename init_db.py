"""Initialize database (alternative to Alembic migration runner)."""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.config import DATABASE_URL, engine
from app.models import Base


def init_db():
    """Create all tables in the database."""
    print(f"Inicializando BD: {DATABASE_URL}")
    Base.metadata.create_all(engine)
    print("✓ Tablas creadas exitosamente.")


if __name__ == "__main__":
    init_db()

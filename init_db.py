"""Initialize database (alternative to Alembic migration runner)."""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.config import DATABASE_URL, SessionLocal, engine
from app.models import Base, Conserje
from app.security import hash_password


def init_db():
    """Create all tables in the database."""
    print(f"Inicializando BD: {DATABASE_URL}")
    Base.metadata.create_all(engine)
    print("✓ Tablas creadas exitosamente.")

    db = SessionLocal()
    try:
        conserje = db.query(Conserje).filter(Conserje.rut == "12345678").first()
        if conserje is None:
            db.add(
                Conserje(
                    nombre="Conserje de Prueba",
                    rut="12345678",
                    email="conserje@prueba.local",
                    password_hash=hash_password("password123"),
                    activo=True,
                )
            )
            db.commit()
            print("✓ Conserje inicial creado.")
        else:
            print("✓ El conserje inicial ya existe.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

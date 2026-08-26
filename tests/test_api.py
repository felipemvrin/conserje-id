"""Tests for API endpoints and security."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_db
from app.main import app
from app.models import Base, Conserje, Departamento, Residente
from app.security import hash_password

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override get_db dependency with test database."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def test_db():
    """Fixture for test database."""
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_conserje(test_db: Session):
    """Create a test conserje user."""
    conserje = Conserje(
        nombre="Test Conserje",
        rut="12345678",
        email="test@example.com",
        password_hash=hash_password("password123"),
        activo=True,
    )
    test_db.add(conserje)
    test_db.commit()
    test_db.refresh(conserje)
    return conserje


@pytest.fixture
def test_departamento(test_db: Session):
    """Create a test department."""
    depto = Departamento(
        numero="101",
        piso=1,
        descripcion="Test apartment",
        activo=True,
    )
    test_db.add(depto)
    test_db.commit()
    test_db.refresh(depto)
    return depto


@pytest.fixture
def test_residente(test_db: Session, test_departamento: Departamento):
    """Create a test resident."""
    residente = Residente(
        nombre_completo="Test Resident",
        run="87654321",
        departamento_id=test_departamento.id,
        activo=True,
    )
    test_db.add(residente)
    test_db.commit()
    test_db.refresh(residente)
    return residente


@pytest.fixture
def test_departamento_2(test_db: Session):
    """Create a second department for mismatch validations."""
    depto = Departamento(
        numero="102",
        piso=1,
        descripcion="Second test apartment",
        activo=True,
    )
    test_db.add(depto)
    test_db.commit()
    test_db.refresh(depto)
    return depto


@pytest.fixture
def auth_headers(test_conserje: Conserje):
    """Get authorization headers with a valid JWT token."""
    response = client.post(
        "/auth/login",
        json={"rut": test_conserje.rut, "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": "Bearer " + token}


class TestAuth:
    """Test authentication endpoints."""

    def test_login_success(self, test_conserje: Conserje):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={"rut": "12345678", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = client.post(
            "/auth/login",
            json={"rut": "invalid", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_missing_rut(self):
        """Test login with missing RUT."""
        response = client.post(
            "/auth/login",
            json={"password": "password123"},
        )
        assert response.status_code == 422  # Validation error


class TestVisitas:
    """Test visit endpoints."""

    def test_registrar_visita_sin_autenticacion(self):
        """Test registering visit without authentication."""
        response = client.post(
            "/visitas/",
            json={
                "run_visitante": "11111111",
                "nombre_visitante": "Juan Pérez",
                "fecha_nacimiento_visitante": "010190",
                "departamento_destino_id": 1,
                "residente_destino_id": 1,
                "motivo": "Visita personal",
            },
        )
        # Should fail without token
        assert response.status_code in (401, 403)

    def test_listar_visitas_sin_autenticacion(self):
        """Test listing visits without authentication."""
        response = client.get("/visitas/")
        # Should fail without token
        assert response.status_code in (401, 403)

    def test_registrar_visita_residente_departamento_mismatch(
        self,
        auth_headers: dict[str, str],
        test_residente: Residente,
        test_departamento_2: Departamento,
    ):
        """Reject visit when resident does not belong to selected department."""
        response = client.post(
            "/visitas/",
            headers=auth_headers,
            json={
                "run_visitante": "11111111",
                "nombre_visitante": "Juan Pérez",
                "fecha_nacimiento_visitante": "010190",
                "departamento_destino_id": test_departamento_2.id,
                "residente_destino_id": test_residente.id,
                "motivo": "Visita personal",
            },
        )
        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Resident does not belong to the specified department"
        )


class TestHome:
    """Test home endpoint."""

    def test_home_endpoint(self):
        """Test home page endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "VisitaRUN" in response.text


class TestNFC:
    """Test NFC endpoint validations."""

    def test_nfc_residente_departamento_mismatch(
        self,
        auth_headers: dict[str, str],
        test_residente: Residente,
        test_departamento_2: Departamento,
    ):
        """Reject NFC registration when resident and department mismatch."""
        response = client.post(
            "/lectura-nfc/leer-y-registrar",
            headers=auth_headers,
            json={
                "run_visitante": "11111111",
                "fecha_nacimiento": "010190",
                "fecha_vencimiento": "010230",
                "departamento_destino_id": test_departamento_2.id,
                "residente_destino_id": test_residente.id,
                "motivo": "Visita por NFC",
            },
        )
        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Resident does not belong to the specified department"
        )

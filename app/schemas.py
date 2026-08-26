"""Pydantic schemas for request/response validation."""
from datetime import datetime

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """User login credentials."""

    rut: str = Field(..., description="Conserje RUT (e.g., 12345678)")
    password: str = Field(..., description="Password")


class ConserjeResponse(BaseModel):
    """Conserje data (safe, without password)."""

    id: int
    nombre: str
    rut: str
    email: str
    activo: bool

    class Config:
        from_attributes = True


class RegistroVisitaRequest(BaseModel):
    """Register a visit from chip data."""

    run_visitante: str
    nombre_visitante: str
    fecha_nacimiento_visitante: str
    departamento_destino_id: int
    residente_destino_id: int
    motivo: str
    foto_visitante: bytes | None = None
    notas: str | None = None


class RegistrarSalidaRequest(BaseModel):
    """Mark visit as exited."""

    notas_salida: str | None = None


class VisitaResponse(BaseModel):
    """Visit record response."""

    id: int
    run_visitante: str
    nombre_visitante: str
    fecha_nacimiento_visitante: str
    departamento_destino_id: int
    residente_destino_id: int
    motivo: str
    timestamp_ingreso: datetime
    timestamp_salida: datetime | None = None
    notas: str | None = None
    creado_en: datetime

    class Config:
        from_attributes = True


class ListaVisitasResponse(BaseModel):
    """Paginated list of visits."""

    total: int
    limite: int
    offset: int
    visitas: list[VisitaResponse]


class DepartamentoResponse(BaseModel):
    """Building department response."""

    id: int
    numero: str
    piso: int
    descripcion: str | None = None
    activo: bool

    class Config:
        from_attributes = True


class ResidenteResponse(BaseModel):
    """Resident response."""

    id: int
    nombre_completo: str
    run: str
    telefono: str | None = None
    email: str | None = None
    departamento_id: int
    activo: bool

    class Config:
        from_attributes = True

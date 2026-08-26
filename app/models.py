"""SQLAlchemy models for VisitaRUN."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Relationship, mapped_column

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Conserje(Base):
    """Concierge/building staff user."""

    __tablename__ = "conserjes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    rut: Mapped[str] = mapped_column(String(12), unique=True)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    visitas: Mapped[list["Visita"]] = Relationship(back_populates="conserje_registrador")

    def __repr__(self) -> str:
        return f"<Conserje {self.nombre} ({self.rut})>"


class Departamento(Base):
    """Building department/unit."""

    __tablename__ = "departamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20))
    piso: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    residentes: Mapped[list["Residente"]] = Relationship(
        back_populates="departamento"
    )
    visitas: Mapped[list["Visita"]] = Relationship(back_populates="departamento")

    def __repr__(self) -> str:
        return f"<Departamento {self.numero} (piso {self.piso})>"


class Residente(Base):
    """Building resident."""

    __tablename__ = "residentes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_completo: Mapped[str] = mapped_column(String(150))
    run: Mapped[str] = mapped_column(String(12), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamentos.id"))
    departamento: Mapped["Departamento"] = Relationship(back_populates="residentes")
    visitas: Mapped[list["Visita"]] = Relationship(back_populates="residente_destino")

    def __repr__(self) -> str:
        return f"<Residente {self.nombre_completo} ({self.run})>"


class Visita(Base):
    """Visit record."""

    __tablename__ = "visitas"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_visitante: Mapped[str] = mapped_column(String(12))
    nombre_visitante: Mapped[str] = mapped_column(String(150))
    fecha_nacimiento_visitante: Mapped[str] = mapped_column(String(10))
    foto_visitante: Mapped[bytes | None] = mapped_column(nullable=True)
    motivo: Mapped[str] = mapped_column(String(255))
    timestamp_ingreso: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    timestamp_salida: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notas: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamentos.id"))
    residente_destino_id: Mapped[int] = mapped_column(ForeignKey("residentes.id"))
    conserje_registrador_id: Mapped[int] = mapped_column(ForeignKey("conserjes.id"))

    departamento: Mapped["Departamento"] = Relationship(back_populates="visitas")
    residente_destino: Mapped["Residente"] = Relationship(back_populates="visitas")
    conserje_registrador: Mapped["Conserje"] = Relationship(back_populates="visitas")

    def __repr__(self) -> str:
        return (
            f"<Visita {self.nombre_visitante} -> "
            f"Depto {self.departamento.numero} ({self.timestamp_ingreso})>"
        )

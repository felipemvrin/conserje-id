"""NFC chip reading integration routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import Conserje, Departamento, Residente, Visita
from app.schemas import RegistroVisitaRequest, VisitaResponse
from app.security import get_current_conserje
from reader_agent.service import (
    BACFailedException,
    CardNotDetectedException,
    InvalidCardException,
    ReaderNotDetectedException,
    leer_cedula,
)
from pydantic import BaseModel

router = APIRouter(prefix="/lectura-nfc", tags=["nfc"])


class LeerCedulaRequest(BaseModel):
    """Request to read and register a visit from NFC chip."""

    fecha_nacimiento: str  # DDMMYY format
    fecha_vencimiento: str  # DDMMYY format
    departamento_destino_id: int
    residente_destino_id: int
    motivo: str
    notas: str | None = None


class LeerCedulaResponse(BaseModel):
    """Response with both chip data and registered visit."""

    run: str
    nombre_completo: str
    fecha_nacimiento: str
    foto_disponible: bool
    visita_id: int
    timestamp_registro: str


@router.post("/leer-y-registrar", response_model=LeerCedulaResponse)
async def leer_cedula_y_registrar_visita(
    request: LeerCedulaRequest,
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
) -> LeerCedulaResponse:
    """
    Read NFC chip and automatically register visit.

    This combines chip reading, validation, and visit registration in one endpoint.
    Requires valid department and resident.
    """
    # Validate department and resident
    departamento = db.query(Departamento).filter(
        Departamento.id == request.departamento_destino_id
    ).first()
    if not departamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    residente = db.query(Residente).filter(
        Residente.id == request.residente_destino_id
    ).first()
    if not residente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    # Read chip
    try:
        datos_cedula = leer_cedula(
            run=residente.run,  # Use resident's RUN for chip reading
            fecha_nacimiento=request.fecha_nacimiento,
            fecha_vencimiento=request.fecha_vencimiento,
        )
    except ReaderNotDetectedException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NFC reader not detected. Check USB connection and drivers.",
        )
    except CardNotDetectedException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No card in reader. Place identity card on reader.",
        )
    except BACFailedException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="BAC authentication failed. Verify card data.",
        )
    except InvalidCardException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid card format (not ICAO 9303 compatible).",
        )

    # Register visit with chip data
    visita = Visita(
        run_visitante=datos_cedula.run,
        nombre_visitante=datos_cedula.nombre_completo,
        fecha_nacimiento_visitante=datos_cedula.fecha_nacimiento,
        departamento_id=request.departamento_destino_id,
        residente_destino_id=request.residente_destino_id,
        motivo=request.motivo,
        foto_visitante=datos_cedula.foto_bytes,
        conserje_registrador_id=conserje.id,
        notas=request.notas or "Registrado via lectura NFC",
    )

    db.add(visita)
    db.commit()
    db.refresh(visita)

    return LeerCedulaResponse(
        run=datos_cedula.run,
        nombre_completo=datos_cedula.nombre_completo,
        fecha_nacimiento=datos_cedula.fecha_nacimiento,
        foto_disponible=datos_cedula.foto_bytes is not None,
        visita_id=visita.id,
        timestamp_registro=visita.timestamp_ingreso.isoformat(),
    )

"""Visit registration and management routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import Conserje, Departamento, Residente, Visita
from app.schemas import (
    ListaVisitasResponse,
    RegistroVisitaRequest,
    RegistrarSalidaRequest,
    VisitaResponse,
)
from app.security import get_current_conserje

router = APIRouter(prefix="/visitas", tags=["visitas"])


@router.post("/", response_model=VisitaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_visita(
    request: RegistroVisitaRequest,
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
) -> VisitaResponse:
    """
    Register a new visit.

    Requires authentication. Data typically comes from NFC chip reading.
    """
    # Validate that department and resident exist
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
    if residente.departamento_id != departamento.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resident does not belong to the specified department",
        )

    # Create visit record
    visita = Visita(
        run_visitante=request.run_visitante,
        nombre_visitante=request.nombre_visitante,
        fecha_nacimiento_visitante=request.fecha_nacimiento_visitante,
        departamento_id=request.departamento_destino_id,
        residente_destino_id=request.residente_destino_id,
        motivo=request.motivo,
        foto_visitante=request.foto_visitante,
        conserje_registrador_id=conserje.id,
        notas=request.notas,
    )

    db.add(visita)
    db.commit()
    db.refresh(visita)

    return VisitaResponse.from_orm(visita)


@router.get("/", response_model=ListaVisitasResponse)
async def listar_visitas(
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
    limite: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    run: str | None = None,
    departamento_id: int | None = None,
) -> ListaVisitasResponse:
    """
    List visits with optional filters.

    Requires authentication.
    """
    query = db.query(Visita)

    if run:
        query = query.filter(Visita.run_visitante == run)
    if departamento_id:
        query = query.filter(Visita.departamento_id == departamento_id)

    total = query.count()
    visitas = query.offset(offset).limit(limite).all()

    return ListaVisitasResponse(
        total=total,
        limite=limite,
        offset=offset,
        visitas=[VisitaResponse.from_orm(v) for v in visitas],
    )


@router.post("/{visita_id}/salida", response_model=VisitaResponse)
async def registrar_salida(
    visita_id: int,
    request: RegistrarSalidaRequest,
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
) -> VisitaResponse:
    """
    Mark a visit as exited (register departure time).

    Requires authentication.
    """
    visita = db.query(Visita).filter(Visita.id == visita_id).first()
    if not visita:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    if visita.timestamp_salida is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visit already marked as exited",
        )

    # Import here to avoid circular dependency
    from datetime import datetime, timezone

    visita.timestamp_salida = datetime.now(timezone.utc)
    if request.notas_salida:
        visita.notas = (visita.notas or "") + f"\n[SALIDA] {request.notas_salida}"

    db.commit()
    db.refresh(visita)

    return VisitaResponse.from_orm(visita)

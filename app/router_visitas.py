"""Visit registration and management routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
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

router = APIRouter(tags=["visitas"])


async def _parse_registro_visita_input(request: Request) -> RegistroVisitaRequest:
    """Parse visit payload from JSON or form payload (HTMX compatibility)."""
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        raw_payload = await request.json()
    else:
        form_data = await request.form()
        raw_payload = dict(form_data)

    try:
        return RegistroVisitaRequest(**raw_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from None


def _to_visita_response(visita: Visita) -> VisitaResponse:
    """Map ORM entity to API schema field names."""
    return VisitaResponse(
        id=visita.id,
        run_visitante=visita.run_visitante,
        nombre_visitante=visita.nombre_visitante,
        fecha_nacimiento_visitante=visita.fecha_nacimiento_visitante,
        departamento_destino_id=visita.departamento_id,
        residente_destino_id=visita.residente_destino_id,
        motivo=visita.motivo,
        timestamp_ingreso=visita.timestamp_ingreso,
        timestamp_salida=visita.timestamp_salida,
        notas=visita.notas,
        creado_en=visita.creado_en,
    )


def _crear_visita(
    db: Session,
    conserje: Conserje,
    run_visitante: str,
    nombre_visitante: str,
    fecha_nacimiento_visitante: str,
    departamento_id: int,
    residente_id: int,
    motivo: str,
    notas: str | None = None,
    foto_visitante: bytes | None = None,
) -> Visita:
    """Helper to create visit record."""
    # Validate that department and resident exist
    departamento = db.query(Departamento).filter(
        Departamento.id == departamento_id
    ).first()
    if not departamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    residente = db.query(Residente).filter(
        Residente.id == residente_id
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
        run_visitante=run_visitante,
        nombre_visitante=nombre_visitante,
        fecha_nacimiento_visitante=fecha_nacimiento_visitante,
        departamento_id=departamento_id,
        residente_destino_id=residente_id,
        motivo=motivo,
        foto_visitante=foto_visitante,
        conserje_registrador_id=conserje.id,
        notas=notas,
    )

    db.add(visita)
    db.commit()
    db.refresh(visita)
    return visita


@router.post("/api/visitas/", response_model=VisitaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_visita(
    request: Request,
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
) -> VisitaResponse:
    """
    Register a new visit (JSON API).

    Requires authentication. Data typically comes from NFC chip reading.
    """
    payload = await _parse_registro_visita_input(request)

    visita = _crear_visita(
        db=db,
        conserje=conserje,
        run_visitante=payload.run_visitante,
        nombre_visitante=payload.nombre_visitante,
        fecha_nacimiento_visitante=payload.fecha_nacimiento_visitante,
        departamento_id=payload.departamento_destino_id,
        residente_id=payload.residente_destino_id,
        motivo=payload.motivo,
        notas=payload.notas,
        foto_visitante=payload.foto_visitante,
    )
    return _to_visita_response(visita)


@router.post("/visitas/", response_model=VisitaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_visita_legacy(
    request: Request,
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
) -> VisitaResponse:
    """Register a new visit (legacy endpoint for compatibility)."""
    payload = await _parse_registro_visita_input(request)

    visita = _crear_visita(
        db=db,
        conserje=conserje,
        run_visitante=payload.run_visitante,
        nombre_visitante=payload.nombre_visitante,
        fecha_nacimiento_visitante=payload.fecha_nacimiento_visitante,
        departamento_id=payload.departamento_destino_id,
        residente_id=payload.residente_destino_id,
        motivo=payload.motivo,
        notas=payload.notas,
        foto_visitante=payload.foto_visitante,
    )
    return _to_visita_response(visita)


@router.get("/api/visitas/", response_model=ListaVisitasResponse)
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
        visitas=[_to_visita_response(v) for v in visitas],
    )


@router.get("/visitas/", response_model=ListaVisitasResponse)
async def listar_visitas_legacy(
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
    limite: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    run: str | None = None,
    departamento_id: int | None = None,
) -> ListaVisitasResponse:
    """List visits with optional filters (legacy endpoint)."""
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
        visitas=[_to_visita_response(v) for v in visitas],
    )


@router.post("/api/visitas/{visita_id}/salida", response_model=VisitaResponse)
async def registrar_salida_api(
    visita_id: int,
    request: RegistrarSalidaRequest | None = Body(default=None),
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
) -> VisitaResponse:
    """
    Mark a visit as exited (register departure time) - API endpoint.

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

    visita.timestamp_salida = datetime.now(timezone.utc)
    notas_salida = request.notas_salida if request else None
    if notas_salida:
        visita.notas = (visita.notas or "") + f"\n[SALIDA] {notas_salida}"

    db.commit()
    db.refresh(visita)

    return _to_visita_response(visita)


@router.post("/visitas/{visita_id}/salida", response_model=VisitaResponse)
async def registrar_salida_legacy(
    visita_id: int,
    request: RegistrarSalidaRequest | None = Body(default=None),
    conserje: Conserje = Depends(get_current_conserje),
    db: Session = Depends(get_db),
) -> VisitaResponse:
    """Mark a visit as exited (legacy endpoint)."""
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

    visita.timestamp_salida = datetime.now(timezone.utc)
    notas_salida = request.notas_salida if request else None
    if notas_salida:
        visita.notas = (visita.notas or "") + f"\n[SALIDA] {notas_salida}"

    db.commit()
    db.refresh(visita)

    return _to_visita_response(visita)

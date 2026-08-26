"""Frontend routes for HTML/HTMX interface."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import Conserje, Departamento, Residente, Visita
from app.schemas import LoginRequest
from app.security import authenticate_conserje, create_access_token, get_current_conserje

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="app/templates")


def get_token_from_cookie(request: Request) -> str | None:
    """Extract JWT token from cookie."""
    return request.cookies.get("access_token")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Home page - redirect to login or dashboard."""
    token = get_token_from_cookie(request)
    if token:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Login page."""
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request, db: Session = Depends(get_db)
) -> Response:
    """Handle login form submission."""
    form_data = await request.form()
    rut = form_data.get("rut", "")
    password = form_data.get("password", "")

    conserje = authenticate_conserje(db, rut, password)
    if not conserje:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "RUT o contraseña incorrectos",
            },
            status_code=401,
        )

    # Create token and set cookie
    token = create_access_token(data={"sub": str(conserje.id)})
    if request.headers.get("HX-Request") == "true":
        response = Response(status_code=204)
        response.headers["HX-Redirect"] = "/dashboard"
    else:
        response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        "access_token",
        token,
        max_age=8 * 3600,  # 8 hours
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    conserje: Conserje = Depends(get_current_conserje),
) -> HTMLResponse:
    """Main dashboard after login."""
    token = get_token_from_cookie(request)
    if not token:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "conserje_nombre": conserje.nombre,
            "conserje_rut": conserje.rut,
        },
    )


@router.post("/logout")
async def logout(request: Request) -> Response:
    """Logout - clear session cookie."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/lectura-nfc-form", response_class=HTMLResponse)
async def lectura_nfc_form(
    request: Request,
    db: Session = Depends(get_db),
    conserje: Conserje = Depends(get_current_conserje),
) -> HTMLResponse:
    """NFC reading form."""
    departamentos = db.query(Departamento).filter(Departamento.activo == True).all()
    residentes = db.query(Residente).filter(Residente.activo == True).all()

    return templates.TemplateResponse(
        request,
        "lectura_nfc.html",
        {
            "request": request,
            "departamentos": departamentos,
            "residentes": residentes,
        },
    )


@router.get("/api/estadisticas-hoy", response_class=HTMLResponse)
async def estadisticas_hoy(
    db: Session = Depends(get_db),
    conserje: Conserje = Depends(get_current_conserje),
) -> str:
    """Get today's statistics."""
    today = datetime.now(timezone.utc).date()

    # Total visits today
    total_visitas = (
        db.query(Visita)
        .filter(Visita.creado_en >= datetime.combine(today, datetime.min.time()))
        .count()
    )

    # Visits with no exit (still inside)
    entrantes = (
        db.query(Visita)
        .filter(Visita.creado_en >= datetime.combine(today, datetime.min.time()))
        .filter(Visita.timestamp_salida == None)
        .count()
    )

    # Visits with exit
    salientes = total_visitas - entrantes

    return f"""
    <div class="stats">
        <div class="stat-box">
            <div class="stat-value">{total_visitas}</div>
            <div class="stat-label">Visitas hoy</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{entrantes}</div>
            <div class="stat-label">Entrantes</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{salientes}</div>
            <div class="stat-label">Salientes</div>
        </div>
    </div>
    """


@router.get("/historial", response_class=HTMLResponse)
async def historial(
    request: Request,
    db: Session = Depends(get_db),
    conserje: Conserje = Depends(get_current_conserje),
) -> HTMLResponse:
    """Today's visit history."""
    today = datetime.now(timezone.utc).date()

    visitas = (
        db.query(Visita)
        .filter(Visita.creado_en >= datetime.combine(today, datetime.min.time()))
        .order_by(Visita.timestamp_ingreso.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "historial.html",
        {
            "request": request,
            "visitas": visitas,
        },
    )


@router.get("/registro-manual-form", response_class=HTMLResponse)
async def registro_manual_form(
    request: Request,
    db: Session = Depends(get_db),
    conserje: Conserje = Depends(get_current_conserje),
) -> HTMLResponse:
    """Manual visit registration form."""
    departamentos = db.query(Departamento).filter(Departamento.activo == True).all()
    residentes = db.query(Residente).filter(Residente.activo == True).all()

    return templates.TemplateResponse(
        request,
        "registro_manual.html",
        {
            "request": request,
            "departamentos": departamentos,
            "residentes": residentes,
        },
    )


@router.get("/admin-panel", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    db: Session = Depends(get_db),
    conserje: Conserje = Depends(get_current_conserje),
) -> HTMLResponse:
    """Admin panel (simplified)."""
    departamentos = db.query(Departamento).all()
    residentes = db.query(Residente).all()

    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "request": request,
            "departamentos": departamentos,
            "residentes": residentes,
            "total_departamentos": len(departamentos),
            "total_residentes": len(residentes),
        },
    )

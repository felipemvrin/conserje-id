from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.router_auth import router as auth_router
from app.router_frontend import router as frontend_router
from app.router_nfc import router as nfc_router
from app.router_visitas import router as visitas_router

app = FastAPI(title="VisitaRUN", version="0.1.0")
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(frontend_router)
app.include_router(auth_router)
app.include_router(visitas_router)
app.include_router(nfc_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """API home page with basic info."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "app_name": "VisitaRUN",
            "version": "0.1.0",
        },
    )

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI(title="VisitaRUN", version="0.1.0")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Health page while feature routes are implemented in later phases."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": "VisitaRUN"},
    )

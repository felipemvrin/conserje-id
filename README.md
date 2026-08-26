# VisitaRUN

VisitaRUN es una aplicacion para conserjerias de edificios que usa un lector NFC ACS ACR122U para leer la cedula chilena y registrar visitas en segundos.

## Objetivo del repositorio

Este repositorio deja preparada la base de trabajo para:

- `reader_agent/`: integracion con hardware NFC (ACR122U, PC/SC, ICAO 9303).
- `app/`: backend FastAPI + vistas Jinja2/HTMX.
- `tests/`: pruebas con pytest.

## Requisitos de desarrollo (macOS 12 Monterey)

1. Python 3.11 o superior.
2. `uv` para gestionar entorno y dependencias.
3. Soporte PC/SC activo para el lector.

### 1) Instalar herramientas base

```bash
# Xcode Command Line Tools (si aun no estan instaladas)
xcode-select --install

# Homebrew (si no existe)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.11+
brew install python@3.11

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2) Instalar/validar driver CCID para ACR122U

macOS trae PC/SC, pero para ACR122U es recomendable instalar el driver oficial de ACS:

1. Descargar el paquete CCID/PCSC de ACS para macOS desde el sitio oficial de ACS.
2. Instalar el paquete y reiniciar sesion (o reiniciar el equipo).
3. Conectar el lector por USB.

Verificacion rapida del lector:

```bash
system_profiler SPUSBDataType | grep -i -E "acr122|acs"
```

Si el lector no aparece, revisar cable USB, puerto, y reinstalar el driver de ACS.

### 3) Instalar dependencias del proyecto

```bash
uv sync
```

Para incluir herramientas de desarrollo (`pytest`, `ruff`):

```bash
uv sync --group dev
```

Si quieres crear el conserje demo de desarrollo al inicializar la base de datos, habilítalo explícitamente:

```bash
VISITARUN_CREATE_DEMO_CONSERJE=true python init_db.py
```

## Ejecutar la aplicacion (base)

```bash
uv run uvicorn app.main:app --reload
```

Abrir en navegador:

- `http://127.0.0.1:8000/`

## Estructura inicial

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── templates/
│       └── index.html
├── reader_agent/
│   ├── __init__.py
│   └── service.py
├── tests/
│   └── __init__.py
├── .gitignore
├── pyproject.toml
└── README.md
```

## Notas

- Desarrollo local sin Docker Desktop.
- Base de datos y modelos se implementan en la Fase 2.
- Flujo BAC/PACE y lectura real del chip se implementan en la Fase 3.

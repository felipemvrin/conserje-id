# VisitaRUN

VisitaRUN es una aplicacion para conserjerias de edificios que usa un lector NFC ACS ACR122U para leer la cedula chilena y registrar visitas en segundos.

## Objetivo del proyecto

VisitaRUN permite registrar visitas en conserjerías mediante lectura NFC de la
cédula chilena o ingreso manual de datos. El repositorio contiene:

- `reader_agent/`: integración con hardware NFC (ACR122U, PC/SC, ICAO 9303).
- `app/`: backend FastAPI, API REST y vistas Jinja2/HTMX.
- `alembic/`: migraciones de base de datos.
- `tests/`: pruebas unitarias y de integración.

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

## Ejecutar la aplicacion (base)

Inicializar las tablas de la base de datos local:

```bash
python init_db.py
```

Para crear un conserje demo de desarrollo, habilítalo explícitamente:

```bash
VISITARUN_CREATE_DEMO_CONSERJE=true python init_db.py
```

Credenciales demo:

- RUT: `12345678`
- Contraseña: `password123`

Iniciar el servidor:

```bash
uv run uvicorn app.main:app --reload
```

Abrir en navegador:

- `http://127.0.0.1:8000/login`

## Configuración

La aplicación usa SQLite por defecto y crea el archivo `visitarun.db` en la
raíz del proyecto. La base de datos puede cambiarse mediante `DATABASE_URL`:

```bash
export DATABASE_URL="sqlite:///./visitarun.db"
```

En producción, define una clave JWT propia:

```bash
export JWT_SECRET_KEY="cambiar-por-una-clave-segura"
```

El valor predeterminado de `JWT_SECRET_KEY` solo sirve para desarrollo local.

## Pruebas

Ejecutar la suite completa:

```bash
python -m pytest -q
```

Las pruebas que requieren un lector NFC físico ACS ACR122U están omitidas en
entornos sin hardware.

## Estructura actual

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   ├── config.py
│   ├── router_auth.py
│   ├── router_visitas.py
│   ├── router_nfc.py
│   ├── router_frontend.py
│   └── templates/
├── reader_agent/
│   ├── bac.py
│   ├── chip_reader.py
│   └── service.py
├── alembic/
├── init_db.py
├── tests/
│   ├── test_api.py
│   └── test_reader.py
├── .gitignore
├── pyproject.toml
└── README.md
```

## Estado actual

- Fases 1 a 5 completadas: estructura, base de datos, lector NFC, API y
  frontend HTMX.
- Fase 6 en progreso: pruebas, validación de integración y preparación para
  despliegue.
- El login web usa JWT en una cookie `HttpOnly` con una duración de 8 horas.
- El frontend incluye dashboard, lectura NFC, registro manual, historial y
  panel administrativo.
- La integración con un lector NFC físico debe validarse en el equipo donde
  se conecte el ACS ACR122U.
- Desarrollo local sin Docker Desktop.

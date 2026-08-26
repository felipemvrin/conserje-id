# Fase 5: Frontend HTMX

## Descripción

Frontend completo para VisitaRUN implementado con **HTMX + Jinja2** desde FastAPI. Interfaz diseñada específicamente para conserjerías con flujo simplificado: autenticación → lectura NFC → historial → administración.

## Características Implementadas

### 1. Autenticación
- **Pantalla de Login** (`login.html`): 
  - Formulario simplificado (RUT + contraseña)
  - Validación HTML5 (RUT formato 8 dígitos)
  - Sesiones con JWT en cookies httpOnly (8 horas)
  - Mensajes de error en tiempo real

### 2. Dashboard Principal
- **Pantalla del Conserje** (`dashboard.html`):
  - Bienvenida personalizada con nombre y RUT del conserje
  - Estadísticas en tiempo real (visitas hoy, entrantes, salientes)
  - Acceso rápido a 4 funciones principales:
    1. Lectura NFC (interfaz dedicada)
    2. Registro manual (cuando no hay chip disponible)
    3. Historial del día (con filtros)
    4. Panel de administración

### 3. Lectura NFC
- **Pantalla Dedicada** (`lectura_nfc.html`):
  - Animación visual (ícono pulsante) indicando "esperando tarjeta"
  - Formulario pre-llenado con opciones:
    - Fecha de nacimiento/vencimiento (formato DDMMYY)
    - Selección de departamento destino
    - Selección de residente
    - Motivo de visita y notas adicionales
  - Integración con endpoint `/lectura-nfc/procesar`

### 4. Registro Manual
- **Formulario de Visita** (`registro_manual.html`):
  - Campos manuales cuando el chip no está disponible
  - Validación de datos (RUN, nombre, fecha de nacimiento)
  - Datos del visitante + destino de visita
  - Compatible con API JSON y form data HTMX

### 5. Historial de Visitas
- **Tabla Interactiva** (`historial.html`):
  - Lista de visitas del día actual
  - Columnas: hora ingreso, visitante, RUN, departamento, estado
  - Estados visuales (badge verde = "Dentro", rojo = "Salida")
  - Botón rápido para registrar salida
  - Sin página necesaria, carga dinámicamente

### 6. Panel de Administración
- **Vista Simplificada** (`admin.html`):
  - Contadores de departamentos y residentes
  - Tabla de departamentos (número, piso, descripción, estado)
  - Tabla de residentes (nombre, RUN, departamento, teléfono, estado)
  - Información de solo lectura (vista de datos registrados)

## Estructura de Archivos

```
app/
├── templates/
│   ├── base.html              # Plantilla base (HTMX + CSS global)
│   ├── login.html             # Pantalla de login
│   ├── dashboard.html         # Dashboard principal
│   ├── lectura_nfc.html       # Interfaz lectura NFC
│   ├── historial.html         # Historial de visitas
│   ├── registro_manual.html   # Registro manual
│   └── admin.html             # Panel de administración
├── router_frontend.py         # Rutas frontend (renderizado de plantillas)
├── security.py                # Actualizado para cookies + headers JWT
└── router_visitas.py          # Endpoints de visitas refactorizados
```

## Tecnologías

### Frontend
- **HTMX**: Interactividad sin JavaScript (AJAX simplificado)
- **Jinja2**: Renderizado de plantillas en servidor
- **CSS Puro**: Sin frameworks (minimalista, responsive)
- **FastAPI**: Servir plantillas y manejar sesiones

### Seguridad
- **JWT**: Tokens con expiración de 8 horas
- **Cookies httpOnly**: Previene acceso desde JavaScript
- **CSRF Protection**: Por defecto en HTMX
- **Password Hashing**: Bcrypt en base de datos

## Endpoints Frontend

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Redirige a login o dashboard según sesión |
| `/login` | GET | Pantalla de login |
| `/login` | POST | Procesa credenciales, crea cookie de sesión |
| `/dashboard` | GET | Dashboard principal (requiere autenticación) |
| `/logout` | POST | Limpia cookie de sesión |
| `/lectura-nfc-form` | GET | Carga formulario de lectura NFC |
| `/registro-manual-form` | GET | Carga formulario de registro manual |
| `/historial` | GET | Carga historial de visitas del día |
| `/admin-panel` | GET | Carga panel de administración |
| `/api/estadisticas-hoy` | GET | Estadísticas en tiempo real (HTMX) |

## Endpoints API (Refactorizados para HTMX)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/api/visitas/` | POST | Registrar visita (JSON) |
| `/api/visitas/` | GET | Listar visitas con filtros |
| `/api/visitas/{id}/salida` | POST | Registrar salida de visita |
| `/visitas/` | POST | Registrar visita (legacy) |
| `/visitas/` | GET | Listar visitas (legacy) |
| `/visitas/{id}/salida` | POST | Registrar salida (legacy) |

## Autenticación por Cookie

Después de login exitoso:
```
Set-Cookie: access_token=<JWT>; Max-Age=28800; HttpOnly; SameSite=Lax
```

El cookie se valida automáticamente en endpoints protegidos (fallback si no hay header Authorization).

## Diseño UI/UX

### Estilos Base
- **Paleta**: Gradiente violeta → púrpura (#667eea → #764ba2)
- **Tipografía**: System fonts (Apple/Segoe/Helvetica)
- **Responsive**: Mobile-first (viewport meta)
- **Componentes**: Botones, inputs, formularios, tablas, badges

### Animaciones
- **Pulse**: Ícono NFC pulsante (esperando tarjeta)
- **Loader Spinner**: Indicador de carga HTMX
- **Hover States**: Transiciones suaves en botones
- **Transitions**: Fade-in/out para cambios de contenido

## Próximos Pasos

1. **Pruebas E2E**: Validar flujos completos (login → visita → salida)
2. **Endpoint de Salida HTMX**: Actualizar historial sin recargar página
3. **Filtros Dinámicos**: Búsqueda de visitas por RUN o departamento
4. **Exportación**: Generar reportes diarios (PDF/CSV)
5. **Notificaciones**: Alertas cuando residente no está disponible

## Cómo Ejecutar

```bash
# Instalar dependencias (si es necesario)
pip install fastapi uvicorn jinja2 pyscard python-jose passlib pycryptodome

# Ejecutar servidor
uvicorn app.main:app --reload

# Acceder a interfaz
# - http://localhost:8000/login
# - Credenciales de prueba: RUT=12345678, pass=password123 (si existen en BD)
```

## Notas de Desarrollo

- Las plantillas heredan de `base.html` para consistencia de estilos
- HTMX maneja recargas de contenido sin página completa
- Modales se manejan con CSS display toggle + JavaScript mínimo
- Validación cliente (HTML5) + servidor (Pydantic)
- Sin build step ni compilación (archivos estáticos directos)

---

**Estado**: ✅ Fase 5 completa  
**Rama**: `feature/fase-5-frontend-htmx`  
**Próximo paso**: Merge a `main` y preparación de Fase 6 (pruebas/deployment)

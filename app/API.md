# API Backend (Fase 4)

## Descripción

Endpoints REST para registro de visitas, autenticación JWT y integración con lector NFC.

## Autenticación

Todos los endpoints (excepto `/auth/login` y `/`) requieren token JWT.

### Obtener Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"rut": "12345678", "password": "password123"}'
```

Respuesta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Usar Token en Requests

```bash
curl -X GET http://localhost:8000/visitas/ \
  -H "Authorization: Bearer <token>"
```

## Endpoints

### 1. Autenticación

#### `POST /auth/login`
Login de conserjes. No requiere autenticación.

**Request:**
```json
{
  "rut": "12345678",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

**Errors:**
- `401`: RUT o contraseña inválida

---

### 2. Registro de Visitas

#### `POST /visitas/`
Registrar visita manualmente. Requiere autenticación.

**Request:**
```json
{
  "run_visitante": "11111111",
  "nombre_visitante": "Juan Pérez",
  "fecha_nacimiento_visitante": "010190",
  "departamento_destino_id": 1,
  "residente_destino_id": 1,
  "motivo": "Visita familiar",
  "foto_visitante": null,
  "notas": "Visitante registrado"
}
```

**Response (201):**
```json
{
  "id": 1,
  "run_visitante": "11111111",
  "nombre_visitante": "Juan Pérez",
  "fecha_nacimiento_visitante": "010190",
  "departamento_destino_id": 1,
  "residente_destino_id": 1,
  "motivo": "Visita familiar",
  "timestamp_ingreso": "2026-08-25T22:30:00+00:00",
  "timestamp_salida": null,
  "notas": "Visitante registrado",
  "creado_en": "2026-08-25T22:30:00+00:00"
}
```

**Errors:**
- `404`: Departamento o residente no encontrado
- `401`: No autenticado

---

#### `GET /visitas/`
Listar visitas con filtros opcionales. Requiere autenticación.

**Query Parameters:**
- `limite` (default: 10, max: 100): Registros por página
- `offset` (default: 0): Número de registros a saltar
- `run` (opcional): Filtrar por RUN del visitante
- `departamento_id` (opcional): Filtrar por departamento

**Response (200):**
```json
{
  "total": 5,
  "limite": 10,
  "offset": 0,
  "visitas": [
    {
      "id": 1,
      "run_visitante": "11111111",
      ...
    }
  ]
}
```

---

#### `POST /visitas/{visita_id}/salida`
Registrar salida de visitante. Requiere autenticación.

**Request:**
```json
{
  "notas_salida": "Visitante se retira normalmente"
}
```

**Response (200):**
```json
{
  "id": 1,
  "run_visitante": "11111111",
  "timestamp_salida": "2026-08-25T23:00:00+00:00",
  "notas": "Visitante registrado\n[SALIDA] Visitante se retira normalmente",
  ...
}
```

**Errors:**
- `404`: Visita no encontrada
- `400`: Visita ya tiene salida registrada
- `401`: No autenticado

---

### 3. Lectura NFC Integrada

#### `POST /lectura-nfc/leer-y-registrar`
Lee cédula con NFC y registra visita automáticamente. Requiere autenticación y ACR122U.

**Request:**
```json
{
  "run_visitante": "12345678",
  "fecha_nacimiento": "010190",
  "fecha_vencimiento": "010230",
  "departamento_destino_id": 1,
  "residente_destino_id": 1,
  "motivo": "Visita verificada por chip",
  "notas": "Lectura exitosa"
}
```

**Response (200):**
```json
{
  "run": "12345678",
  "nombre_completo": "JUAN PÉREZ GARCÍA",
  "fecha_nacimiento": "010190",
  "foto_disponible": true,
  "visita_id": 1,
  "timestamp_registro": "2026-08-25T22:35:00+00:00"
}
```

**Errors:**
- `503`: Lector NFC no conectado
- `400`: Tarjeta no detectada o formato inválido
- `401`: Falló autenticación BAC (datos incorrectos)
- `404`: Departamento o residente no encontrado

---

## Testing

```bash
# Tests unitarios
pytest tests/test_api.py -v

# Ejecutar ejemplo de uso (requiere servidor corriendo)
python app/api_example.py
```

## Seguridad

- Contraseñas hasheadas con bcrypt
- JWT tokens con expiración (8 horas por defecto)
- Validación de estados (conserje activo, etc.)
- Rate limiting recomendado en producción

## Próximas fases

- Fase 5: Interfaz HTMX para frontend
- Integración con centros de datos (múltiples edificios)
- Autenticación MFA para conserjes
- Reportes y analytics

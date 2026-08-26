# Reader Agent (Fase 3)

## Descripción

Módulo `reader_agent/` que maneja la lectura física de cédulas chilenas usando lector NFC ACS ACR122U.

## Componentes

### 1. `bac.py` — BAC (Basic Access Control)

Implementa derivación de claves y handshake BAC según ICAO 9303:

- `BACKey`: Deriva material criptográfico desde RUN + fechas de nacimiento/vencimiento
- Calcula checksums MRZ (Machine Readable Zone)
- Establece sesión criptográfica con el chip

**Uso interno:**
```python
from reader_agent.bac import BACKey

bac = BACKey("12345678", "010190", "010230")
enc_key, mac_key = bac.derive_key_material()
session_keys = bac.establish_bac_session(b"\x00" * 8)
```

### 2. `chip_reader.py` — Lector PC/SC

Interfaz con lector ACR122U usando `pyscard`:

- `ACR122UReader`: Conecta al lector y ejecuta comandos ISO 7816
- Detecta disponibilidad del hardware
- Lee archivos del chip (DG1, DG2, etc.)

**Uso interno:**
```python
from reader_agent.chip_reader import ACR122UReader

reader = ACR122UReader()
if reader.detect_reader():
    if reader.connect():
        data = reader.read_file(b"\x01\x01")  # Read DG1
        reader.disconnect()
```

### 3. `service.py` — API Pública

Función principal que orquesta lectura de cédula:

```python
from reader_agent.service import leer_cedula, DatosCedula

try:
    datos: DatosCedula = leer_cedula(
        run="12345678",
        fecha_nacimiento="010190",
        fecha_vencimiento="010230"
    )
    print(f"Lectura exitosa: {datos.nombre_completo}")
except ReaderNotDetectedException:
    print("Lector no detectado")
except CardNotDetectedException:
    print("No hay tarjeta en el lector")
except BACFailedException:
    print("Autenticación BAC falló")
except InvalidCardException:
    print("Tarjeta no válida")
```

**Retorna `DatosCedula`:**
- `run: str` — Número de identidad
- `nombre_completo: str` — Nombre completo
- `fecha_nacimiento: str` — Fecha de nacimiento (DDMMYY)
- `foto_bytes: bytes | None` — Foto del chip si está disponible

## Manejo de Errores

Excepciones personalizadas en `service.py`:

- `ReaderNotDetectedException` — Lector USB no conectado
- `CardNotDetectedException` — No hay tarjeta en el lector
- `BACFailedException` — Falló handshake BAC (datos inválidos)
- `InvalidCardException` — Tarjeta no compatible (no ICAO 9303)

## Testing

Pruebas unitarias en `tests/test_reader.py`:

```bash
pytest tests/test_reader.py
```

Las pruebas que requieren hardware físico están marcadas con `@pytest.mark.skip`.

## Próximas fases

Fase 4 integrará `leer_cedula()` en endpoints FastAPI.

Fase 5 agregará interfaz HTMX para captura rápida de datos en conserjerías.

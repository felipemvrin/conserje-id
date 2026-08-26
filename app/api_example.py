"""Example: Using VisitaRUN API (Fase 4)"""
import requests

# Configuration
BASE_URL = "http://localhost:8000"
CONSERJE_RUT = "12345678"
CONSERJE_PASSWORD = "password123"

# ============================================================================
# 1. LOGIN - Get access token
# ============================================================================
print("1. Logging in...")
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "rut": CONSERJE_RUT,
        "password": CONSERJE_PASSWORD,
    },
)
assert response.status_code == 200
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✓ Got token: {token[:20]}...")

# ============================================================================
# 2. REGISTER VISIT MANUALLY (without NFC)
# ============================================================================
print("\n2. Registering manual visit...")
response = requests.post(
    f"{BASE_URL}/visitas/",
    headers=headers,
    json={
        "run_visitante": "11111111",
        "nombre_visitante": "Juan Pérez",
        "fecha_nacimiento_visitante": "010190",
        "departamento_destino_id": 1,
        "residente_destino_id": 1,
        "motivo": "Visita familiar",
        "notas": "Visitante conocido",
    },
)
if response.status_code in (200, 201):
    visita = response.json()
    visita_id = visita["id"]
    print(f"✓ Visit registered: ID {visita_id}")
else:
    print(f"Error ({response.status_code}): {response.json()}")

# ============================================================================
# 3. LIST VISITS
# ============================================================================
print("\n3. Listing visits...")
response = requests.get(
    f"{BASE_URL}/visitas/",
    headers=headers,
    params={"limite": 10, "offset": 0},
)
if response.status_code == 200:
    data = response.json()
    print(f"✓ Total visits: {data['total']}")
    for visita in data["visitas"]:
        print(
            f"  - {visita['nombre_visitante']} -> "
            f"Depto {visita['departamento_destino_id']} "
            f"({visita['timestamp_ingreso']})"
        )
else:
    print(f"Error ({response.status_code}): {response.json()}")

# ============================================================================
# 4. REGISTER VISIT EXIT
# ============================================================================
if "visita_id" in locals():
    print(f"\n4. Registering exit for visit {visita_id}...")
    response = requests.post(
        f"{BASE_URL}/visitas/{visita_id}/salida",
        headers=headers,
        json={"notas_salida": "Visitante se retira sin problemas"},
    )
    if response.status_code == 200:
        print("✓ Exit registered")
    else:
        print(f"Error ({response.status_code}): {response.json()}")

# ============================================================================
# 5. FILTERED LIST (by RUN)
# ============================================================================
print("\n5. Searching visits by RUN...")
response = requests.get(
    f"{BASE_URL}/visitas/",
    headers=headers,
    params={"run": "11111111"},
)
if response.status_code == 200:
    data = response.json()
    print(f"✓ Found {data['total']} visits for RUN 11111111")
else:
    print(f"Error ({response.status_code}): {response.json()}")

# ============================================================================
# 6. NFC CHIP READING (requires physical reader + card)
# ============================================================================
print("\n6. Reading NFC chip and registering visit...")
print("   (Requires ACR122U reader connected and card present)")
response = requests.post(
    f"{BASE_URL}/lectura-nfc/leer-y-registrar",
    headers=headers,
    json={
        "run_visitante": "11111111",
        "fecha_nacimiento": "010190",  # DDMMYY format
        "fecha_vencimiento": "010230",  # DDMMYY format
        "departamento_destino_id": 1,
        "residente_destino_id": 1,
        "motivo": "Visita verificada por chip",
        "notas": "Lectura exitosa desde NFC",
    },
)
if response.status_code == 200:
    data = response.json()
    print("✓ Chip read and visit registered:")
    print(f"  RUN: {data['run']}")
    print(f"  Name: {data['nombre_completo']}")
    print(f"  Visit ID: {data['visita_id']}")
elif response.status_code == 503:
    print("⚠ Reader not connected (expected in testing)")
elif response.status_code == 400:
    print("⚠ No card in reader or invalid card (expected in testing)")
else:
    print(f"Error ({response.status_code}): {response.json()}")

print("\n✓ API workflow example completed!")

import time
import random
import requests

# ============================================================
# CONFIGURACIÓN DEL SIMULADOR AquaBrain
# ============================================================
URL_API    = "http://127.0.0.1:8000/api/mediciones/"
USUARIO    = "iot_device"
PASSWORD   = "AquaSecret2026!"
INTERVALO  = 4   # segundos entre cada ciclo de lecturas

# UUID reales obtenidos desde la base de datos de Instalacion1
SENSORES = {
    "temperatura": {
        "id": "590d5414-2e4a-4525-a863-ae80715368a0",
        "min": 18.0,
        "max": 32.0,
        "unidad": "°C",
    },
    "humedad": {
        "id": "66128b04-7c15-407e-94da-52eb744aaddb",
        "min": 40.0,
        "max": 90.0,
        "unidad": "%",
    },
    "ph": {
        "id": "f4e111ad-6f9b-46a8-8bc5-d86913f691d5",
        "min": 5.5,
        "max": 8.0,
        "unidad": "pH",
    },
    "caudal": {
        "id": "d8af956e-de83-4b26-adff-68c277691086",
        "min": 0.5,
        "max": 5.0,
        "unidad": "L/min",
    },
}

# Iconos visuales para la consola
ICONOS = {
    "temperatura": "🌡️",
    "humedad":     "💧",
    "ph":          "🧪",
    "caudal":      "🌊",
}


def enviar_medicion(nombre_sensor: str, config: dict) -> None:
    """Genera y envía una medición simulada para el sensor indicado."""
    valor = round(random.uniform(config["min"], config["max"]), 2)
    icono = ICONOS.get(nombre_sensor, "📡")

    payload = {
        "sensor": config["id"],
        "valor": valor,
        "estado_conexion": True,
    }

    try:
        respuesta = requests.post(
            URL_API,
            json=payload,
            auth=(USUARIO, PASSWORD),
            timeout=5,
        )

        if respuesta.status_code == 201:
            print(f"  [OK] {icono}  {nombre_sensor:12} → {valor} {config['unidad']}")
        elif respuesta.status_code == 403:
            print(f"  [403] 🔴 {nombre_sensor}: Permisos denegados. Verifica usuario/contraseña.")
        elif respuesta.status_code == 400:
            print(f"  [400] 🟡 {nombre_sensor}: Error de validación → {respuesta.text[:120]}")
        else:
            print(f"  [???] ⚠️  {nombre_sensor}: Código {respuesta.status_code} → {respuesta.text[:80]}")

    except requests.exceptions.ConnectionError:
        print(f"  [RED] ⚠️  Sin conexión con el servidor Django. ¿Está corriendo en {URL_API}?")
    except requests.exceptions.Timeout:
        print(f"  [TMO] ⏱️  {nombre_sensor}: Tiempo de espera agotado.")


def iniciar_transmision() -> None:
    print("=" * 55)
    print("  🌱  AquaBrain — Simulador IoT  |  Instalacion1")
    print("=" * 55)
    print(f"  API    : {URL_API}")
    print(f"  Usuario: {USUARIO}")
    print(f"  Ciclo  : cada {INTERVALO} segundos por sensor")
    print("  Presiona Ctrl+C para detener.\n")

    ciclo = 1
    while True:
        print(f"── Ciclo #{ciclo} ─────────────────────────────────────")
        for nombre, config in SENSORES.items():
            enviar_medicion(nombre, config)
            time.sleep(0.5)   # pequeña pausa entre sensores del mismo ciclo
        ciclo += 1
        print()
        time.sleep(INTERVALO)


if __name__ == "__main__":
    try:
        iniciar_transmision()
    except KeyboardInterrupt:
        print("\n\n🛑  Transmisión detenida por el usuario. Hasta pronto.")

import time
import random
import requests

# --- Configuración del Dispositivo ---
URL_API = "http://127.0.0.1:8000/api/mediciones/"
USUARIO = "fbiHead"
PASSWORD = "admin" 
ID_SENSOR = "0f396b05cb0d47ec87066d8ea97c71dc"  # Aca ajuntar la ID sel sensor

def iniciar_transmision():
    print("🌱 Iniciando Simulador de Hardware AquaBrain...")
    print("Presiona Ctrl+C para detener la transmisión.\n")
    
    while True:
        # 1. Generar la medición simulada (ej. Temperatura entre 18.0 y 26.0 grados)
        valor_sensor = round(random.uniform(18.0, 26.0), 2)
        
        # 2. Empaquetar los datos en formato JSON
        payload = {
            "sensor": ID_SENSOR,
            "valor": valor_sensor,
            "estado_conexion": True
        }

        try:
            # 3. Enviar el paquete a la API usando HTTP Basic Auth
            respuesta = requests.post(
                URL_API, 
                json=payload, 
                auth=(USUARIO, PASSWORD) # La API validará si este usuario tiene permisos
            )
            
            # 4. Analizar la respuesta del servidor (DevSecOps)
            if respuesta.status_code == 201: # 201 significa "Created"
                print(f"[OK] 🟢 Medición enviada y guardada: {valor_sensor}°C")
            elif respuesta.status_code == 403:
                print("[BLOQUEO] 🔴 La API rechazó los datos (Error 403: Permisos denegados).")
            else:
                print(f"[ERROR] 🟡 Código inesperado: {respuesta.status_code} - {respuesta.text}")
                
        except requests.exceptions.ConnectionError:
            print("[ALERTA] ⚠️ No hay conexión. ¿Está encendido el servidor Django?")

        # 5. Esperar 4 segundos antes de la siguiente lectura para no saturar la red
        time.sleep(4)

if __name__ == "__main__":
    iniciar_transmision()
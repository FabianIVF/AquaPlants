"""
AquaBrain — Simulador IoT para AquaPlants
=========================================
Envía mediciones simuladas a la API REST de AquaPlants.

Características:
  * Descubre AUTOMÁTICAMENTE las instalaciones y sus sensores ACTIVOS vía API
    (ya no hay UUIDs escritos a mano). Si activas/desactivas sensores desde el
    dashboard, el simulador lo detecta en la siguiente re-sincronización.
  * Valores realistas por variable con "caminata aleatoria" (cambios suaves).
  * Anomalías ocasionales fuera de rango para probar las reglas de alerta.
  * Fallos de conexión simulados (estado_conexion = False).
  * Salida alineada con la estructura sugerida en la pauta (punto 5):
    id_sistema, id_dispositivo, id_sensor, tipo_variable, valor, unidad,
    timestamp, estado_conexion, alerta.

Uso:
  python simulador_iot.py                                  # local, todas las instalaciones
  python simulador_iot.py --url https://fabianvidal.pythonanywhere.com
  python simulador_iot.py --instalacion "Instalacion1" --intervalo 3
  python simulador_iot.py --anomalias 0.2 --fallos 0.05
  (En el instituto: python311\\python.exe simulador_iot.py ...)
"""
import argparse
import os
import random
import sys
import time

import requests

# Consola de Windows: forzar UTF-8 para que los emojis no rompan el script
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ============================================================
# PERFILES REALISTAS POR VARIABLE (hidroponía)
#   normal  : rango típico de operación
#   anomalo : rango fuera de lo normal (para disparar alertas)
#   paso    : variación máxima entre lecturas consecutivas
#   limite  : límites físicos absolutos (nunca se envía fuera de esto)
# ============================================================
PERFILES = {
    "temperatura_agua": {"normal": (18.0, 24.0),   "anomalo": (27.0, 32.0),     "paso": 0.3,  "limite": (0, 50),    "icono": "🌡️💧"},
    "temperatura_aire": {"normal": (18.0, 28.0),   "anomalo": (33.0, 40.0),     "paso": 0.5,  "limite": (0, 60),    "icono": "🌡️💨"},
    "temperatura":      {"normal": (18.0, 28.0),   "anomalo": (33.0, 40.0),     "paso": 0.5,  "limite": (0, 60),    "icono": "🌡️"},
    "humedad":          {"normal": (50.0, 80.0),   "anomalo": (20.0, 35.0),     "paso": 1.5,  "limite": (0, 100),   "icono": "💧"},
    "ph":               {"normal": (5.5, 6.5),     "anomalo": (7.5, 8.5),       "paso": 0.05, "limite": (0, 14),    "icono": "🧪"},
    "caudal":           {"normal": (1.5, 4.0),     "anomalo": (0.0, 0.4),       "paso": 0.2,  "limite": (0, 50),    "icono": "🌊"},
    "nivel_estanque":   {"normal": (40.0, 95.0),   "anomalo": (5.0, 15.0),      "paso": 0.8,  "limite": (0, 100),   "icono": "🪣"},
    "co2":              {"normal": (400.0, 1200.0),"anomalo": (1800.0, 2500.0), "paso": 25.0, "limite": (0, 5000),  "icono": "🫧"},
    "fotoperiodo":      {"normal": (12.0, 18.0),   "anomalo": (20.0, 24.0),     "paso": 0.25, "limite": (0, 24),    "icono": "☀️"},
}
PERFIL_GENERICO = {"normal": (0.0, 10.0), "anomalo": (50.0, 60.0), "paso": 0.5, "limite": (0, 1000), "icono": "📡"}


def leer_argumentos():
    p = argparse.ArgumentParser(description="Simulador IoT AquaBrain para AquaPlants")
    p.add_argument("--url", default=os.getenv("AQUA_URL", "http://127.0.0.1:8000"),
                   help="URL base del servidor (sin /api/). Ej: https://fabianvidal.pythonanywhere.com")
    p.add_argument("--usuario", default=os.getenv("AQUA_IOT_USER", "iot_device"))
    p.add_argument("--password", default=os.getenv("AQUA_IOT_PASSWORD", "AquaSecret2026!"))
    p.add_argument("--instalacion", default=None,
                   help="Nombre o UUID de una instalación. Si se omite, simula todas las activas.")
    p.add_argument("--intervalo", type=float, default=4.0, help="Segundos entre ciclos (def: 4)")
    p.add_argument("--anomalias", type=float, default=0.08,
                   help="Probabilidad (0-1) de enviar un valor anómalo (def: 0.08)")
    p.add_argument("--fallos", type=float, default=0.03,
                   help="Probabilidad (0-1) de simular fallo de conexión (def: 0.03)")
    p.add_argument("--resync", type=int, default=10,
                   help="Cada cuántos ciclos se vuelven a consultar los sensores (def: 10)")
    p.add_argument("--ciclos", type=int, default=0, help="Número de ciclos a ejecutar (0 = infinito)")
    return p.parse_args()


class SimuladorAquaBrain:
    def __init__(self, args):
        self.args = args
        self.base = args.url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (args.usuario, args.password)
        self.sensores = []     # lista de dicts devueltos por /api/sensores/
        self.ultimo = {}       # id_sensor -> último valor (para la caminata aleatoria)

    # ---------------------------------------------------------- API helpers
    def _get_todo(self, ruta, params=None):
        """GET que soporta respuestas paginadas o lista simple."""
        url, datos = f"{self.base}{ruta}", []
        while url:
            r = self.session.get(url, params=params, timeout=10)
            r.raise_for_status()
            js = r.json()
            if isinstance(js, dict) and "results" in js:
                datos.extend(js["results"])
                url, params = js.get("next"), None
            else:
                datos.extend(js)
                url = None
        return datos

    def sincronizar(self):
        """Descubre instalaciones activas y sus sensores activos."""
        instalaciones = [i for i in self._get_todo("/api/instalaciones/") if i.get("activa", True)]
        if self.args.instalacion:
            filtro = self.args.instalacion.lower()
            instalaciones = [i for i in instalaciones
                             if i["nombre"].lower() == filtro or str(i["id"]).lower() == filtro]
            if not instalaciones:
                raise SystemExit(f"❌ No se encontró una instalación activa llamada '{self.args.instalacion}'.")

        ids = {str(i["id"]) for i in instalaciones}
        sensores = self._get_todo("/api/sensores/", params={"activo": "true"})
        self.sensores = [s for s in sensores if str(s["instalacion"]) in ids]

        print(f"🔄 Sincronizado: {len(instalaciones)} instalación(es), {len(self.sensores)} sensor(es) activo(s)")
        for s in self.sensores:
            icono = PERFILES.get(s["tipo"], PERFIL_GENERICO)["icono"]
            print(f"   {icono}  {s.get('instalacion_nombre', ''):15} · {s['tipo']:16} [{s.get('unidad', '')}]")
        print()

    # ---------------------------------------------------------- generación
    def generar_valor(self, sensor):
        perfil = PERFILES.get(sensor["tipo"], PERFIL_GENERICO)
        lo, hi = perfil["normal"]
        lim_lo, lim_hi = perfil["limite"]

        if random.random() < self.args.anomalias:
            valor = random.uniform(*perfil["anomalo"])          # pico anómalo
        else:
            previo = self.ultimo.get(sensor["id"], random.uniform(lo, hi))
            valor = previo + random.uniform(-perfil["paso"], perfil["paso"])
            # Mantener la caminata dentro del rango normal (rebote suave)
            if valor < lo or valor > hi:
                valor = previo - (valor - previo)
            valor = min(max(valor, lo), hi)
            self.ultimo[sensor["id"]] = valor

        return round(min(max(valor, lim_lo), lim_hi), 2)

    # ---------------------------------------------------------- envío
    def enviar(self, sensor):
        perfil = PERFILES.get(sensor["tipo"], PERFIL_GENERICO)
        conectado = random.random() >= self.args.fallos
        valor = self.generar_valor(sensor) if conectado else 0.0

        payload = {"sensor": sensor["id"], "valor": valor, "estado_conexion": conectado}
        try:
            r = self.session.post(f"{self.base}/api/mediciones/", json=payload, timeout=10)
        except requests.exceptions.ConnectionError:
            print(f"  [RED] ⚠️  Sin conexión con {self.base}. ¿Está corriendo el servidor?")
            return
        except requests.exceptions.Timeout:
            print(f"  [TMO] ⏱️  {sensor['tipo']}: tiempo de espera agotado.")
            return

        if r.status_code == 201:
            d = r.json()
            estado = "🟢" if d.get("estado_conexion") else "🔴 FALLO"
            linea = (f"  [201] {perfil['icono']}  {d.get('tipo_variable', sensor['tipo']):16} "
                     f"{d.get('valor')} {d.get('unidad', '')}  {estado}")
            print(linea)
            alerta = d.get("alerta")
            if alerta:
                for a in (alerta if isinstance(alerta, list) else [alerta]):
                    print(f"        🚨 {a}")
        elif r.status_code in (401, 403):
            print(f"  [{r.status_code}] 🔴 Credenciales o permisos inválidos para '{self.args.usuario}'.")
        elif r.status_code == 400:
            print(f"  [400] 🟡 {sensor['tipo']}: {r.text[:150]}")
            # Posiblemente el sensor fue desactivado: forzar re-sincronización
            self.forzar_resync = True
        else:
            print(f"  [{r.status_code}] ⚠️  {sensor['tipo']}: {r.text[:100]}")

    # ---------------------------------------------------------- bucle
    def ejecutar(self):
        print("=" * 62)
        print("  🌱  AquaBrain — Simulador IoT  |  AquaPlants")
        print("=" * 62)
        print(f"  Servidor  : {self.base}")
        print(f"  Dispositivo: {self.args.usuario}")
        print(f"  Intervalo : {self.args.intervalo}s | Anomalías: {self.args.anomalias:.0%} | Fallos: {self.args.fallos:.0%}")
        print("  Presiona Ctrl+C para detener.\n")

        try:
            self.sincronizar()
        except requests.exceptions.HTTPError as e:
            raise SystemExit(f"❌ Error al consultar la API ({e}). Revisa usuario/contraseña.")
        except requests.exceptions.ConnectionError:
            raise SystemExit(f"❌ No se pudo conectar con {self.base}.")

        ciclo = 1
        while not self.args.ciclos or ciclo <= self.args.ciclos:
            self.forzar_resync = False
            print(f"── Ciclo #{ciclo}  {time.strftime('%H:%M:%S')} " + "─" * 36)
            if not self.sensores:
                print("  (sin sensores activos; activa alguno desde ✏️ Editar Instalación)")
            for s in self.sensores:
                self.enviar(s)
                time.sleep(0.2)
            print()

            if self.forzar_resync or ciclo % self.args.resync == 0:
                try:
                    self.sincronizar()
                except requests.exceptions.RequestException as e:
                    print(f"  ⚠️  No se pudo re-sincronizar: {e}\n")
            ciclo += 1
            time.sleep(self.args.intervalo)


if __name__ == "__main__":
    try:
        SimuladorAquaBrain(leer_argumentos()).ejecutar()
    except KeyboardInterrupt:
        print("\n\n🛑  Transmisión detenida por el usuario. Hasta pronto.")

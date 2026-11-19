"""
AquaBrain — Simulador IoT para AquaPlants
=========================================
Envía mediciones simuladas a la API REST de AquaPlants.

Características:
  * Descubre AUTOMÁTICAMENTE invernaderos, torres/instalaciones (incluidas las
    independientes sin invernadero), plantas activas y sus sensores activos vía API.
  * Se adapta en caliente si falta una torre, si creas nuevas plantas
    independientes/testigo o si desactivas un invernadero/torre/planta.
  * Valores realistas por variable con "caminata aleatoria" (cambios suaves).
  * Anomalías ocasionales fuera de rango para probar las reglas de alerta.
  * Fallos de conexión simulados (estado_conexion = False).

Uso:
  python simulador_iot.py                                  # local, todo lo activo
  python simulador_iot.py --url https://fabianvidal.pythonanywhere.com
  python simulador_iot.py --invernadero "Invernadero Norte"
  python simulador_iot.py --instalacion "Huerto1A" --intervalo 3
  python simulador_iot.py --planta "T1-A01"
  python simulador_iot.py --solo-plantas                   # solo sensores de plantas
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
# ============================================================
PERFILES = {
    "temperatura_agua": {
        "normal": (18.0, 24.0), "anomalo": (27.0, 32.0), "paso": 0.3, "limite": (0, 50), "icono": "🌡️💧",
    },
    "temperatura_aire": {
        "normal": (18.0, 28.0), "anomalo": (33.0, 40.0), "paso": 0.5, "limite": (0, 60), "icono": "🌡️💨",
    },
    "temperatura": {
        "normal": (18.0, 28.0), "anomalo": (33.0, 40.0), "paso": 0.5, "limite": (0, 60), "icono": "🌡️",
    },
    "humedad": {
        "normal": (50.0, 80.0), "anomalo": (20.0, 35.0), "paso": 1.5, "limite": (0, 100), "icono": "💧",
    },
    "ph": {
        "normal": (5.5, 6.5), "anomalo": (7.5, 8.5), "paso": 0.05, "limite": (0, 14), "icono": "🧪",
    },
    "caudal": {
        "normal": (1.5, 4.0), "anomalo": (0.0, 0.4), "paso": 0.2, "limite": (0, 50), "icono": "🌊",
    },
    "nivel_estanque": {
        "normal": (40.0, 95.0), "anomalo": (5.0, 15.0), "paso": 0.8, "limite": (0, 100), "icono": "🪣",
    },
    "co2": {
        "normal": (400.0, 1200.0), "anomalo": (1800.0, 2500.0), "paso": 25.0, "limite": (0, 5000), "icono": "🫧",
    },
    "fotoperiodo": {
        "normal": (12.0, 18.0), "anomalo": (20.0, 24.0), "paso": 0.25, "limite": (0, 24), "icono": "☀️",
    },
    "humedad_sustrato": {
        "normal": (55.0, 80.0), "anomalo": (20.0, 35.0), "paso": 1.2, "limite": (0, 100), "icono": "🪴",
    },
    "ph_sustrato": {
        "normal": (5.5, 6.5), "anomalo": (7.4, 8.4), "paso": 0.05, "limite": (0, 14), "icono": "🧪",
    },
    "temperatura_raiz": {
        "normal": (18.0, 24.0), "anomalo": (28.0, 33.0), "paso": 0.3, "limite": (0, 50), "icono": "🌡️",
    },
}
PERFIL_GENERICO = {"normal": (0.0, 10.0), "anomalo": (50.0, 60.0), "paso": 0.5, "limite": (0, 1000), "icono": "📡"}


def leer_argumentos():
    p = argparse.ArgumentParser(description="Simulador IoT AquaBrain para AquaPlants")
    p.add_argument("--url", default=os.getenv("AQUA_URL", "http://127.0.0.1:8000"),
                   help="URL base del servidor (sin /api/). Ej: https://fabianvidal.pythonanywhere.com")
    p.add_argument("--usuario", default=os.getenv("AQUA_IOT_USER", "iot_device"))
    p.add_argument("--password", default=os.getenv("AQUA_IOT_PASSWORD", "AquaSecret2026!"))
    p.add_argument("--invernadero", default=None,
                   help="Nombre o UUID de un invernadero. Filtra las torres que pertenecen a él.")
    p.add_argument("--instalacion", default=None,
                   help="Nombre o UUID de una torre/instalación. Si se omite, simula todas las activas.")
    p.add_argument("--planta", default=None,
                   help="Código o UUID de una planta específica con sensores propios.")
    p.add_argument("--solo-plantas", action="store_true",
                   help="Envía lecturas únicamente a sensores propios de plantas (plantas testigo/macetas).")
    p.add_argument("--solo-torres", action="store_true",
                   help="Envía lecturas únicamente a sensores generales de torre/instalación.")
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
        self.sensores = []
        self.instalaciones_map = {}
        self.ultimo = {}
        self.forzar_resync = False

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

    def _get_opcional(self, ruta, params=None):
        """GET tolerante a servidores antiguos o endpoints sin permiso de lectura."""
        try:
            return self._get_todo(ruta, params=params)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (403, 404):
                return None
            raise

    def sincronizar(self):
        """
        Descubre invernaderos, torres/instalaciones (incluidas las independientes),
        plantas activas y sensores activos, adaptándose si falta alguna torre o planta.
        """
        invernaderos = self._get_opcional("/api/invernaderos/")
        inv_activos_ids = None
        inv_map = {}
        if invernaderos is not None:
            inv_map = {str(inv["id"]): inv for inv in invernaderos}
            inv_activos_ids = {str(inv["id"]) for inv in invernaderos if inv.get("activa", True)}

        instalaciones_raw = self._get_todo("/api/instalaciones/")
        instalaciones = [i for i in instalaciones_raw if i.get("activa", True)]

        # Si el invernadero padre está desactivado, omitir sus torres (las independientes sin invernadero siguen)
        if inv_activos_ids is not None:
            instalaciones = [
                i for i in instalaciones
                if not i.get("invernadero") or str(i["invernadero"]) in inv_activos_ids
            ]

        if self.args.invernadero:
            filtro_inv = self.args.invernadero.lower()
            instalaciones = [
                i for i in instalaciones
                if (i.get("invernadero_nombre") or "").lower() == filtro_inv
                or str(i.get("invernadero") or "").lower() == filtro_inv
            ]

        if self.args.instalacion:
            filtro_inst = self.args.instalacion.lower()
            instalaciones = [
                i for i in instalaciones
                if i["nombre"].lower() == filtro_inst or str(i["id"]).lower() == filtro_inst
            ]

        self.instalaciones_map = {str(i["id"]): i for i in instalaciones}
        ids_inst = set(self.instalaciones_map.keys())

        plantas_raw = self._get_opcional("/api/plantas/", params={"activa": "true"})
        plantas_activas_ids = None
        if plantas_raw is not None:
            plantas_activas_ids = {
                str(p["id"]) for p in plantas_raw
                if p.get("activa", True) and str(p.get("instalacion")) in ids_inst
            }

        sensores_raw = self._get_todo("/api/sensores/", params={"activo": "true"})
        filtrados = []
        for s in sensores_raw:
            if str(s["instalacion"]) not in ids_inst:
                continue

            planta_id = s.get("planta")
            # Si hay plantas registradas, ignorar sensores de plantas desactivadas/inexistentes
            if planta_id is not None and plantas_activas_ids is not None:
                if str(planta_id) not in plantas_activas_ids:
                    continue

            if self.args.solo_plantas and not planta_id:
                continue
            if self.args.solo_torres and planta_id:
                continue
            if self.args.planta:
                f_planta = self.args.planta.lower()
                codigo = (s.get("planta_codigo") or "").lower()
                if codigo != f_planta and str(planta_id or "").lower() != f_planta:
                    continue

            filtrados.append(s)

        self.sensores = filtrados
        sensores_torre = sum(1 for s in self.sensores if not s.get("planta"))
        sensores_planta = sum(1 for s in self.sensores if s.get("planta"))
        independientes = sum(1 for i in instalaciones if not i.get("invernadero"))

        print(
            f"🔄 Sincronizado: {len(instalaciones)} torre(s) "
            f"({independientes} independiente(s)) · "
            f"{len(self.sensores)} sensor(es) activo(s) "
            f"[{sensores_torre} de torre, {sensores_planta} de planta]"
        )
        if not instalaciones:
            print("   ⚠️  No hay torres activas que coincidan con el filtro; esperando en línea...")
        elif not self.sensores:
            print("   ⚠️  Torres detectadas sin sensores activos aún; esperando configuración...")

        for s in self.sensores:
            icono = PERFILES.get(s["tipo"], PERFIL_GENERICO)["icono"]
            inst = self.instalaciones_map.get(str(s["instalacion"]), {})
            inv_id = str(inst.get("invernadero") or "")
            inv_nombre = inst.get("invernadero_nombre") or (
                inv_map[inv_id]["nombre"] if inv_id in inv_map else "Independiente"
            )
            destino = s.get("planta_codigo") or "Torre/Ambiental"
            print(f"   {icono}  {inv_nombre:16} · {s.get('instalacion_nombre', ''):14} · {destino:15} · {s['tipo']}")
        print()

    # ---------------------------------------------------------- generación
    def generar_valor(self, sensor):
        perfil = PERFILES.get(sensor["tipo"], PERFIL_GENERICO)
        lo, hi = perfil["normal"]
        lim_lo, lim_hi = perfil["limite"]

        if random.random() < self.args.anomalias:
            valor = random.uniform(*perfil["anomalo"])
        else:
            previo = self.ultimo.get(sensor["id"], random.uniform(lo, hi))
            valor = previo + random.uniform(-perfil["paso"], perfil["paso"])
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
            torre = sensor.get("instalacion_nombre") or ""
            planta = sensor.get("planta_codigo")
            etiqueta = f"{torre}/{planta}" if planta else f"{torre or 'Sistema'}"
            linea = (
                f"  [201] {perfil['icono']}  {etiqueta:22} · {d.get('tipo_variable', sensor['tipo']):16} "
                f"{d.get('valor')} {d.get('unidad', '')}  {estado}"
            )
            print(linea)
            alerta = d.get("alerta")
            if alerta:
                for a in (alerta if isinstance(alerta, list) else [alerta]):
                    print(f"        🚨 {a}")
        elif r.status_code in (401, 403):
            print(f"  [{r.status_code}] 🔴 Credenciales o permisos inválidos para '{self.args.usuario}'.")
        elif r.status_code in (400, 404):
            print(f"  [{r.status_code}] 🟡 {sensor['tipo']}: recurso inactivo o eliminado; re-sincronizando...")
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
        print(
            f"  Intervalo : {self.args.intervalo}s | "
            f"Anomalías: {self.args.anomalias:.0%} | Fallos: {self.args.fallos:.0%}"
        )
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
                print("  (sin sensores activos; esperando nuevas torres o plantas desde el dashboard...)")
                self.forzar_resync = True
            for s in self.sensores:
                self.enviar(s)
                if self.forzar_resync:
                    break
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

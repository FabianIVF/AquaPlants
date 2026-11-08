# AquaPlants — Plataforma IoT de Telemetría y Gestión Hidropónica

Sistema web integral desarrollado en **Django 5.x** y **Django REST Framework (DRF)** para el monitoreo en tiempo real, control de parámetros críticos y automatización de alertas en cultivos hidropónicos y acuapónicos.

* **Proyecto Académico:**  
Evaluación 3 - Unidad 3 — Proyecto Integrado.
* **Desarrollador / Autor:** 
Fabian Vidal y Pablo Cabezas.
* **Despliegue en la Nube:** 
https://fabianvidal.pythonanywhere.com/
* **Repositorio Oficial:** 
https://github.com/FabianIVF/AquaPlants

---

## 1. Arquitectura General y Decisiones de Diseño

El sistema está diseñado bajo una arquitectura modular desacoplada:

```text
               +--------------------------------------------------------+
               |                  AquaBrain IoT Simulador               |
               | (Lectura de 8 variables: pH, Temp Agua/Aire, CO2, etc.)|
               +---------------------------+----------------------------+
                                           | HTTP Basic Auth (iot_device)
                                           v
+-----------------------------------------------------------------------+
|                             API REST (DRF)                            |
|       /api/mediciones/  |  /api/sensores/  |  /api/instalaciones/     |
+----------------------------------+------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                    Lógica de Negocio y Seguridad                      |
|  - RBAC (Admin / Supervisor / IoT Device)                             |
|  - Generador de Alertas Rojas (Exceso) y Azules (Caída)               |
|  - Supresión de falsas alarmas por desconexión                        |
+----------------------------------+------------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v                                                   v
+------------------+                               +--------------------+
|  Dashboard Web   |                               | Persistencia Dual  |
| - Chart.js Live  |                               | - Local: MariaDB   |
| - CRUD Huertos   |                               | - Nube: SQLite3    |
| - Historial 100  |                               +--------------------+
+------------------+
```

### Características Técnicas Destacadas:
* **Identificadores Únicos Universales (UUIDv4):** Se aplican como Primary Key (`id`) a las entidades centrales de negocio (`Instalacion`, `Sensor`, `Medicion`) mediante `models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`. Esta decisión mitiga vulnerabilidades de enumeración horizontal (IDOR) e inferencia no autorizada de volumen de datos o tasa de actividad, mientras que las relaciones (`ForeignKey`) y tablas de auditoría/alertas preservan la integridad referencial estándar relacional.
* **Control Estricto de Hosts (`ALLOWED_HOSTS`):** Se lee y parsea dinámicamente desde el archivo de entorno `.env` como una lista delimitada por comas, respaldado por un fallback seguro restrictivo para entornos de desarrollo y pruebas (`127.0.0.1`, `localhost`, `testserver`, `.pythonanywhere.com`), evitando deliberadamente wildcards permisivos o peligrosos (`'*'`) para neutralizar ataques de manipulación o envenenamiento de cabecera HTTP Host (*Host Header Poisoning / Cache Poisoning*).
* **Persistencia Dual Conmutable:**
  - **Entorno Local (Desarrollo / Instituto):** MariaDB/MySQL mediante conector `pymysql` y cliente `HeidiSQL`.
  - **Entorno Nube (PythonAnywhere Free Tier):** Base de datos relacional `SQLite3`, optimizada para cuotas gratuitas sin soporte de MySQL externo (`DB_ENGINE=sqlite`).
* **Seguridad Basada en Roles (RBAC Estricto):**
  - **Administrador:** Acceso irrestricto; creación, edición y eliminación de instalaciones y reglas.
  - **Supervisor:** Solo lectura (`view_instalacion`, `view_medicion`). No puede alterar datos ni acceder a formularios de gestión (HTTP 403 Forbidden garantizado por decoradores y pruebas).
  - **Dispositivo IoT (`iot_device`):** Cuenta de servicio con permiso exclusivo de inserción (`add_medicion`) vía API REST.
* **Interfaz de Usuario de Nivel SaaS:** Libre de emojis, tipografía optimizada *Inter*, iconografía vectorial *Bootstrap Icons*, microinteracciones y paleta de colores contenida (`#34a37c` acento).

---

## 2. Variables de Entorno y Configuración (.env)

El proyecto utiliza variables de entorno mediante `python-dotenv` para desacoplar credenciales y configuraciones operativas. Crea un archivo `.env` en la raíz del proyecto tomando como referencia el archivo `.env.example`:

```ini
# Configuración General de Django
SECRET_KEY=django-insecure-+p#cpiotzzi(wd=zpz8&4-vf_2851+_&ma445x%+gln)!s2yi&
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,testserver,.pythonanywhere.com

# Motor de Base de Datos: 'mysql' (Local) o 'sqlite' (PythonAnywhere / Tests)
DB_ENGINE=mysql

# Credenciales de MariaDB / MySQL (Solo requeridas si DB_ENGINE=mysql)
DB_NAME=aquaplants_db
DB_USER=root
DB_PASSWORD=admin
DB_HOST=127.0.0.1
DB_PORT=3306
```

> [!NOTE]
> **Gestión Segura de `ALLOWED_HOSTS`:** Se parsea como una lista delimitada por comas (`[host.strip() for host in os.getenv("ALLOWED_HOSTS").split(",") if host.strip()]`). Si la variable no está configurada en `.env`, el backend aplica un fallback seguro restringido a desarrollo y pruebas (`127.0.0.1, localhost, testserver, .pythonanywhere.com`), evitando en todo momento comodines o wildcards inseguros (`'*'`) para mitigar vulnerabilidades de envenenamiento de cabecera HTTP Host (*Host Header Poisoning / Cache Poisoning*).

---

## 3. Instalación y Puesta en Marcha

### Opción A: Entorno Local con Python Portable (Laboratorios INACAP)
En los laboratorios donde existan restricciones de permisos o incompatibilidades de versión de Python, el proyecto incluye un entorno portable preinstalado en la carpeta `python311/`:

1. Clona el repositorio:
   ```bash
   git clone https://github.com/FabianIVF/AquaPlants.git
   cd AquaPlants
   ```
2. Asegúrate de tener MariaDB/MySQL levantado con la base de datos `aquaplants_db`.
3. Ejecuta las migraciones y roles:
   ```cmd
   python311\python.exe manage.py migrate
   python311\python.exe manage.py setup_roles
   ```
4. Inicia el servidor de desarrollo:
   ```cmd
   python311\python.exe manage.py runserver
   ```
5. Accede desde tu navegador a `http://127.0.0.1:8000/`.

---

### Opción B: Entorno Local con Virtualenv Estándar
1. Crea y activa tu entorno virtual:
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   # En Linux / macOS:
   source venv/bin/activate
   ```
2. Instala las dependencias:
   ```bash
   pip install django djangorestframework pymysql cryptography python-dotenv requests
   ```
3. Ejecuta migraciones y crea el superusuario:
   ```bash
   python manage.py migrate
   python manage.py setup_roles
   python manage.py createsuperuser
   python manage.py runserver
   ```

---

### Opción C: Despliegue en la Nube (PythonAnywhere)
1. En la consola **Bash** de PythonAnywhere:
   ```bash
   git clone https://github.com/FabianIVF/AquaPlants.git ~/WorkspaceAquaPlants
   cd ~/WorkspaceAquaPlants
   mkvirtualenv --python=/usr/bin/python3.10 aquaplants-venv
   pip install django djangorestframework cryptography python-dotenv requests
   ```
2. Configura el archivo `~/WorkspaceAquaPlants/.env` con:
   ```ini
   DEBUG=False
   DB_ENGINE=sqlite
   ALLOWED_HOSTS=.pythonanywhere.com
   ```
3. Ejecuta migraciones, roles y recolección de estáticos:
   ```bash
   python manage.py migrate
   python manage.py setup_roles
   python manage.py collectstatic --noinput
   ```
4. En el archivo WSGI de PythonAnywhere (`/var/www/fabianvidal_pythonanywhere_com_wsgi.py`), añade:
   ```python
   import os, sys
   path = '/home/fabianvidal/WorkspaceAquaPlants'
   if path not in sys.path:
       sys.path.append(path)
   os.environ['DJANGO_SETTINGS_MODULE'] = 'AquaPlants.settings'
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
5. En la pestaña **Web**, mapea los estáticos (`URL: /static/` $\rightarrow$ `Directory: /home/fabianvidal/WorkspaceAquaPlants/staticfiles`) y haz clic en **Reload**.

---

## 4. Ejecución del Simulador IoT (AquaBrain)

El script `simulador_iot.py` descubre automáticamente qué instalaciones y sensores se encuentran activos en la base de datos y comienza a emitir telemetría con variaciones biológicas creíbles, anomalías ocasionales y verificación de desconexiones:

```bash
# Simular contra el servidor local:
python simulador_iot.py

# Simular contra el servidor en la nube (PythonAnywhere):
python simulador_iot.py --url https://fabianvidal.pythonanywhere.com

# Simular un huerto específico con mayor tasa de anomalías para probar alertas:
python simulador_iot.py --instalacion "Huerto1A" --anomalias 0.3 --intervalo 2
```

---

## 5. Matriz de Trazabilidad Técnica (Criterio 3.1.6.12 - 10 pts)

Alineación completa entre requerimientos pedagógicos, componentes implementados y casos de prueba automatizados:

| ID Req. | Requerimiento de Negocio / HU | Archivo de Código | Ruta / Endpoint | Caso de Prueba (`tests.py`) | Resultado Obtenido vs Esperado |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **RF-01** | **Gestión CRUD de Instalaciones:** El administrador puede crear, listar, editar y dar de baja huertos. | `dashboard/views.py`<br>`dashboard/forms.py` | `/dashboard/`<br>`/dashboard/instalacion/crear/`<br>`.../<id>/editar/` | `test_admin_puede_acceder_crear_instalacion`<br>`test_instalacion_form_crea_sensores_seleccionados` | **Esperado:** 200 OK y persistencia.<br>**Obtenido:** 100% Coincidente. |
| **RF-02** | **Configuración Flexible de Sensores:** El usuario activa/desactiva las variables que desea vigilar por huerto. | `dashboard/forms.py`<br>`telemetria/models.py` | `/dashboard/instalacion/<id>/editar/` | `test_instalacion_form_crea_sensores_seleccionados`<br>`test_api_rechaza_lectura_de_sensor_desactivado` | **Esperado:** Sensor inactivo no emite ni alerta.<br>**Obtenido:** Cumple estrictamente. |
| **RF-03** | **Telemetría IoT en Tiempo Real:** Dashboard con gráficas Chart.js alimentadas por polling asíncrono. | `dashboard/views.py`<br>`dashboard/templates/.../detalle.html` | `/dashboard/instalacion/<id>/live/` | `test_iot_device_puede_enviar_medicion` | **Esperado:** Gráficas actualizan cada 5s.<br>**Obtenido:** Fluido y sin recarga. |
| **RF-04** | **Reglas de Alerta Bipolar (Rojas y Azules):** Disparo automático ante excesos (> máx) y caídas (< mín). | `telemetria/views.py`<br>`telemetria/models.py` | `/api/mediciones/`<br>`/dashboard/instalacion/<id>/regla/crear/` | `test_alerta_roja_generada_al_superar_maximo`<br>`test_alerta_azul_generada_al_caer_bajo_minimo` | **Esperado:** Generación de alerta en BD.<br>**Obtenido:** Alertas Rojas y Azules automáticas. |
| **RF-05** | **Mitigación de Falsas Alarmas:** Las desconexiones (`estado_conexion=False`) no deben disparar alertas. | `telemetria/views.py` | `/api/mediciones/` | `test_fallo_conexion_no_genera_alerta_falsa` | **Esperado:** Valor 0.00 guardado sin alerta.<br>**Obtenido:** Cero alertas espurias. |
| **RF-06** | **Seguridad RBAC y Principio de Mínimo Privilegio:** Supervisor solo ve; no edita ni borra. | `telemetria/management/commands/setup_roles.py`<br>`dashboard/views.py` | `/dashboard/instalacion/crear/` | `test_supervisor_no_puede_crear_instalacion`<br>`test_usuario_anonimo_redirigido_al_login` | **Esperado:** 403 Forbidden y 302 Login.<br>**Obtenido:** Cumplimiento total. |
| **RF-07** | **Validación de Integridad y Bordes:** Bloqueo de lecturas negativas, pH > 14 y humedad > 100%. | `telemetria/models.py`<br>`telemetria/serializers.py`<br>`dashboard/forms.py` | Model Validation & Form Clean | `test_modelo_valor_negativo_rechazado`<br>`test_humedad_porcentaje_mayor_a_100_rechazado`<br>`test_ph_fuera_de_escala_quimica_rechazado` | **Esperado:** ValidationError y Form Error.<br>**Obtenido:** Interceptado con éxito. |

---

## 6. Ejecución del Plan de Pruebas Automatizadas

Para validar la integridad de toda la solución técnica, ejecuta la suite de pruebas nativa:

```bash
python manage.py test telemetria -v 2
```

### Resumen del Reporte Oficial:
* **Total de Pruebas:** 21
* **Fallos (Failures):** 0
* **Errores (Errors):** 0
* **Tasa de Éxito:** **100% OK**
* **Detalle exhaustivo:** Consulta el archivo [InformePruebas.md](file:///F:/WorkspaceAquaPlants/InformePruebas.md).

---

## 7. Recomendaciones Técnicas y Trabajo Futuro (Criterio 3.1.6.13 - 5 pts)

1. **Migración a Broker MQTT (Bajo Consumo Energético):** Actualmente el simulador envía peticiones HTTP/REST (`POST`). En un entorno productivo con cientos de nodos a batería, se recomienda implementar un broker MQTT (como Mosquitto) y un worker de ingesta para optimizar el ancho de banda y el consumo de energía de los microcontroladores.
2. **WebSockets con Django Channels:** Reemplazar el polling HTTP actual de 5 segundos en el dashboard por conexiones WebSockets full-duplex, reduciendo la carga sobre el servidor web.
3. **Notificaciones Push Multicanal:** Extender el modelo `AlertaGenerada` mediante signals de Django para emitir notificaciones push móviles o webhooks de Telegram cuando se registre una Alerta Roja crítica.

---

## 8. Guía de Defensa Técnica ante Preguntas del Docente (Criterio 3.1.6.14 - 5 pts)

* **¿Por qué utilizaron UUIDs en vez del ID numérico clásico?**  
  *Respuesta:* Se implementaron identificadores UUIDv4 como Primary Key (`id`) en las entidades centrales del dominio (`Instalacion`, `Sensor`, `Medicion`) para mitigar vulnerabilidades de enumeración horizontal (IDOR) e impedir que actores maliciosos deduzcan el volumen de datos o la tasa de inserción de telemetría a través de la API REST o URLs del dashboard. Al mismo tiempo, las relaciones (`ForeignKey`) y los modelos de auditoría/alertas preservan la integridad referencial relacional estándar.
* **¿Cómo garantizan que un Supervisor no pueda crear huertos modificando el HTML?**  
  *Respuesta:* La seguridad no depende del front-end. En el backend, las vistas están protegidas con el decorador `@permission_required('telemetria.add_instalacion', raise_exception=True)`. Si un usuario sin dicho permiso fuerza una petición POST a la ruta, Django rechaza la solicitud de inmediato con un código HTTP 403 Forbidden.
* **¿Qué sucede si un sensor se desconecta físicamente en el huerto?**  
  *Respuesta:* El microcontrolador reporta `estado_conexion = False` y valor `0.00`. El backend almacena la medición para auditoría del hardware, pero suprime la evaluación de reglas para evitar que se dispare una falsa alerta de "pH críticamente bajo" o "Temperatura congelada".

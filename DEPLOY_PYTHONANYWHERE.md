# Guía de Despliegue en Producción — PythonAnywhere
## Plataforma de Telemetría y Gestión Hidropónica AquaPlants

Este documento describe de manera exhaustiva el procedimiento oficial para desplegar, configurar y mantener el sistema **AquaPlants** en los servidores cloud de **PythonAnywhere**. Todas las rutas, usuarios, repositorios y variables están alineados de forma estricta con el entorno productivo real del proyecto.

---

## 1. Ficha Técnica del Entorno Productivo

| Parámetro | Valor Oficial de Producción |
| :--- | :--- |
| **Usuario PythonAnywhere** | `fabianvidal` |
| **Dominio / URL Pública** | `https://fabianvidal.pythonanywhere.com` |
| **Directorio del Proyecto** | `/home/fabianvidal/WorkspaceAquaPlants` |
| **Repositorio Git Oficial** | `https://github.com/FabianIVF/AquaPlants.git` |
| **Versión de Python** | `Python 3.10` |
| **Ruta del Entorno Virtual** | `/home/fabianvidal/.virtualenvs/aquaplants-venv` |
| **Archivo de Configuración WSGI** | `/var/www/fabianvidal_pythonanywhere_com_wsgi.py` |
| **Motor de Base de Datos** | `SQLite3` (`DB_ENGINE=sqlite`) |
| **Directorio de Archivos Estáticos** | `/home/fabianvidal/WorkspaceAquaPlants/staticfiles` |
| **URL Mapeada de Estáticos** | `/static/` |

---

## 2. Requisitos Previos

1. Cuenta activa en [PythonAnywhere](https://www.pythonanywhere.com/) con el usuario `fabianvidal`.
2. Repositorio de código sincronizado y actualizado en GitHub (`FabianIVF/AquaPlants`).
3. Acceso a una consola **Bash** desde el dashboard de PythonAnywhere (`Consoles` > `Bash`).

---

## 3. Despliegue Inicial Paso a Paso

### Paso 1: Clonar el Repositorio Oficial
Abra una consola **Bash** en PythonAnywhere y clone el repositorio directamente en su directorio home:

```bash
cd /home/fabianvidal
git clone https://github.com/FabianIVF/AquaPlants.git WorkspaceAquaPlants
cd /home/fabianvidal/WorkspaceAquaPlants
```

> [!NOTE]
> Si la carpeta ya existe y desea una instalación limpia, asegúrese de respaldar cualquier dato previo antes de clonar.

---

### Paso 2: Crear y Activar el Entorno Virtual (Virtualenv)
PythonAnywhere incluye `virtualenvwrapper`. Cree el entorno especificando Python 3.10:

```bash
mkvirtualenv --python=/usr/bin/python3.10 aquaplants-venv
```

Para activarlo en sesiones futuras:
```bash
workon aquaplants-venv
```

La ruta canónica del entorno quedará establecida en:
```text
/home/fabianvidal/.virtualenvs/aquaplants-venv
```

---

### Paso 3: Instalación de Dependencias
Con el entorno virtual activado (`(aquaplants-venv)` visible en el prompt de la terminal), instale las dependencias del proyecto:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

O instale los paquetes nucleares de forma directa:
```bash
pip install django djangorestframework cryptography python-dotenv requests
```

---

### Paso 4: Configuración del Archivo de Entorno (`.env`)
En el directorio raíz del proyecto (`/home/fabianvidal/WorkspaceAquaPlants`), cree o edite el archivo `.env`:

```bash
nano /home/fabianvidal/WorkspaceAquaPlants/.env
```

Pegue exactamente la siguiente configuración de producción:

```ini
DEBUG=False
DB_ENGINE=sqlite
ALLOWED_HOSTS=.pythonanywhere.com
SECRET_KEY=tu-clave-secreta-de-produccion
```

> [!IMPORTANT]
> - `DEBUG=False`: Imprescindible para evitar filtración de trazas y datos sensibles en producción.
> - `DB_ENGINE=sqlite`: En la capa gratuita (Free Tier) de PythonAnywhere no se dispone de acceso a bases de datos externas o MySQL de alta concurrencia; `SQLite3` ofrece persistencia local óptima, segura e integrada.
> - `ALLOWED_HOSTS=.pythonanywhere.com`: Permite el acceso a través de `fabianvidal.pythonanywhere.com` y cualquier subdominio de la plataforma.
> - `SECRET_KEY`: Reemplace `tu-clave-secreta-de-produccion` por una cadena pseudoaleatoria de alta entropía (50+ caracteres).

---

### Paso 5: Migraciones, Roles RBAC y Recolección de Estáticos
Ejecute el ciclo de preparación de la base de datos y recursos estáticos:

```bash
cd /home/fabianvidal/WorkspaceAquaPlants
python manage.py migrate
python manage.py setup_roles
python manage.py collectstatic --noinput
```

Explicación técnica de cada comando:
* `python manage.py migrate`: Aplica las migraciones de Django y crea el esquema relacional en SQLite.
* `python manage.py setup_roles`: Crea los roles del modelo RBAC (`Administrador`, `Supervisor`, `Encargado de cultivo`) y aplica el Principio de Mínimo Privilegio.
* `python manage.py collectstatic --noinput`: Empaqueta todos los recursos de `dashboard` y `static/` en el directorio de producción `/home/fabianvidal/WorkspaceAquaPlants/staticfiles`.

---

### Paso 6: Configuración de Cuentas de Acceso

#### 1. Creación del Superusuario Administrador:
```bash
python manage.py createsuperuser
```
Siga las instrucciones en pantalla ingresando su nombre de usuario, correo y contraseña.

#### 2. Creación de la Cuenta de Servicio IoT (`iot_device`):
El simulador IoT y los microcontroladores físicos requieren una cuenta de servicio para autenticarse por HTTP Basic Auth y enviar telemetría a la API:

```bash
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='iot_device').exists() or User.objects.create_user('iot_device', password='AquaSecret2026!')"
```

---

## 4. Configuración del Servidor Web en PythonAnywhere

Diríjase a la pestaña **Web** del panel de control de PythonAnywhere:

### 4.1. Crear la Web App
Si aún no ha creado la aplicación web:
1. Haga clic en **"Add a new web app"**.
2. Seleccione su dominio asignado: `fabianvidal.pythonanywhere.com`.
3. Seleccione **"Manual configuration"** (NO seleccionar Django automático).
4. Elija la versión **Python 3.10**.

---

### 4.2. Secciones "Code" y "Virtualenv"
Configure los campos exactamente como sigue:

* **Source code:**
  ```text
  /home/fabianvidal/WorkspaceAquaPlants
  ```
* **Working directory:**
  ```text
  /home/fabianvidal/WorkspaceAquaPlants
  ```
* **Virtualenv:**
  ```text
  /home/fabianvidal/.virtualenvs/aquaplants-venv
  ```

---

### 4.3. Configuración del Archivo WSGI
En la sección **Code**, haga clic sobre el enlace del archivo WSGI:
`/var/www/fabianvidal_pythonanywhere_com_wsgi.py`

Borre todo el contenido existente y pegue el siguiente bloque de código exacto:

```python
import os, sys

path = '/home/fabianvidal/WorkspaceAquaPlants'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'AquaPlants.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Haga clic en **Save** (arriba a la derecha).

---

### 4.4. Mapeo de Archivos Estáticos (Static Files)
En la sección **Static files** de la pestaña **Web**, defina la siguiente regla de mapeo:

| URL | Directory |
| :--- | :--- |
| `/static/` | `/home/fabianvidal/WorkspaceAquaPlants/staticfiles` |

> [!WARNING]
> Verifique que la ruta del directorio apunte a `staticfiles` (con **s** al final), ya que allí es donde `collectstatic` deposita los archivos listos para producción.

---

### 4.5. Recargar la Aplicación Web
En la parte superior de la pestaña **Web**, presione el botón verde grande:
**"Reload fabianvidal.pythonanywhere.com"**

Una vez completada la recarga, visite:
`https://fabianvidal.pythonanywhere.com/`

---

## 5. Pruebas de Telemetría IoT en Producción

El proyecto incluye el simulador autónomo `simulador_iot.py` (AquaBrain). Para validar que la API en la nube recibe mediciones, actualiza el dashboard y evalúa reglas de alerta:

### Ejecución Básica:
Desde su equipo local (o desde otra consola Bash):
```bash
python simulador_iot.py --url https://fabianvidal.pythonanywhere.com
```

### Ejecución Avanzada con Inyección de Anomalías:
Para forzar la activación de Alertas Rojas (excesos) y Alertas Azules (caídas críticas) en el servidor de producción:
```bash
python simulador_iot.py --url https://fabianvidal.pythonanywhere.com --instalacion "Huerto1A" --anomalias 0.3 --intervalo 2
```

> [!TIP]
> Puede monitorear la llegada de telemetría en tiempo real ingresando con su usuario al dashboard web:
> `https://fabianvidal.pythonanywhere.com/dashboard/`

---

## 6. Procedimiento de Actualización Continua (Deploy / Update Workflow)

Cada vez que incorpore mejoras, correcciones o nuevas funcionalidades en el repositorio de GitHub, ejecute la siguiente secuencia en la consola Bash de PythonAnywhere:

```bash
# 1. Navegar al proyecto y activar el entorno
cd /home/fabianvidal/WorkspaceAquaPlants
workon aquaplants-venv

# 2. Descargar los últimos cambios
git pull

# 3. Aplicar migraciones y políticas RBAC
python manage.py migrate
python manage.py setup_roles

# 4. Recompilar archivos estáticos
python manage.py collectstatic --noinput

# 5. Reiniciar el servidor de producción
touch /var/www/fabianvidal_pythonanywhere_com_wsgi.py
```

> [!NOTE]
> Ejecutar `touch /var/www/fabianvidal_pythonanywhere_com_wsgi.py` equivale a presionar el botón **Reload** en la pestaña Web, permitiendo reiniciar el proceso WSGI directamente desde la terminal.

---

## 7. Diagnóstico y Monitoreo de Errores (Logs)

En caso de cualquier eventualidad (código HTTP 500, problemas de importación o errores de permisos), revise los archivos de registro ubicados en `/var/log/`:

* **Error log (Errores de Python y excepciones Django):**
  ```bash
  tail -n 100 /var/log/fabianvidal.pythonanywhere.com.error.log
  ```
* **Server log (Arranque y cierre del servidor uWSGI):**
  ```bash
  tail -n 100 /var/log/fabianvidal.pythonanywhere.com.server.log
  ```
* **Access log (Peticiones HTTP entrantes con código de respuesta):**
  ```bash
  tail -n 100 /var/log/fabianvidal.pythonanywhere.com.access.log
  ```

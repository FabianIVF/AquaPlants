# Guía Rápida de Despliegue en PythonAnywhere (100% Gratuito con SQLite)

Esta guía te permite desplegar **AquaPlants** en PythonAnywhere sin pagar suscripciones ni exceder el límite de 500 MB.

---

### Paso 1: Abrir la Consola Bash y Clonar el Proyecto

1. Entra a tu cuenta de [PythonAnywhere](https://www.pythonanywhere.com/).
2. Ve a la pestaña **Consoles** y abre una consola **Bash**.
3. Clona tu repositorio:
   ```bash
   git clone https://github.com/<tu_usuario_github>/WorkspaceAquaPlants.git
   cd WorkspaceAquaPlants
   ```

---

### Paso 2: Crear el Entorno Virtual e Instalar Dependencias

En la misma consola Bash:
```bash
mkvirtualenv --python=/usr/bin/python3.10 aquaplants-venv
pip install -r requirements.txt
```

---

### Paso 3: Configurar el archivo `.env` para SQLite

1. En la consola crea el archivo `.env`:
   ```bash
   nano .env
   ```
2. Pega lo siguiente:
   ```env
   DEBUG=False
   SECRET_KEY=clave-secreta-aquaplants-prod-2026
   DB_ENGINE=sqlite
   ```
   *(Guarda con `Ctrl + O`, presiona Enter y sal con `Ctrl + X`)*.

3. Aplica las migraciones (creará `db.sqlite3` en el proyecto):
   ```bash
   python manage.py migrate
   ```

4. Recolecta los archivos estáticos (CSS, iconos, JS):
   ```bash
   python manage.py collectstatic --noinput
   ```

5. Inicializa los roles y usuarios:
   ```bash
   python manage.py setup_roles
   python manage.py createsuperuser
   ```

6. Crea el usuario exclusivo para telemetría:
   ```bash
   python manage.py shell
   ```
   Dentro de Python ejecuta:
   ```python
   from django.contrib.auth.models import User, Permission
   u, _ = User.objects.get_or_create(username='iot_device')
   u.set_password('AquaSecret2026!')
   u.user_permissions.add(Permission.objects.get(codename='add_medicion'))
   u.save()
   exit()
   ```

---

### Paso 4: Configurar la pestaña "Web"

1. Ve a la pestaña **Web** en PythonAnywhere.
2. Haz clic en **Add a new web app** → **Manual configuration** → selecciona **Python 3.10**.
3. Configura las secciones:
   * **Virtualenv:** `/home/FabianVidal/.virtualenvs/aquaplants-venv`
   * **Source code:** `/home/FabianVidal/WorkspaceAquaPlants`
   * **Working directory:** ` `
   * **Static files:**
     * URL: `/static/`
     * Directory: `/home/FabianVidal/AquaPlants/staticfiles`
4. Edita el **WSGI configuration file** (enlace en la sección Code), borra su contenido y pega:
   ```python
   import os
   import sys

   path = '/home/FabianVidal/AquaPlants'
   if path not in sys.path:
       sys.path.append(path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'AquaPlants.settings'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
   *(Reemplaza `<tu_usuario>` por tu usuario exacto de PythonAnywhere y guarda)*.

---

### Paso 5: Recargar y Probar

1. Presiona el botón verde **"Reload <tu_usuario>.pythonanywhere.com"**.
2. Entra a: `https://<tu_usuario>.pythonanywhere.com/dashboard/`
3. ¡Tu CRUD web y telemetría ya están en la nube!

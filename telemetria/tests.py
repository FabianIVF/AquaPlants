import time
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock
from django.test import TestCase, Client
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from telemetria.models import Invernadero, Instalacion, Planta, Sensor, Medicion, ReglaAlerta, AlertaGenerada
from dashboard.analytics import resumen_planta, resumen_sensores
from dashboard.forms import ReglaAlertaForm, InstalacionForm
from simulador_iot import SimuladorAquaBrain


class ModelosTelemetriaTestCase(TestCase):
    """
    Criterios 3.1.2.3 y 3.1.5.9: Integridad de la base de datos y pruebas de borde.
    """
    def setUp(self):
        self.instalacion = Instalacion.objects.create(
            nombre="Huerto Experimental 1",
            ubicacion="Invernadero Norte",
            activa=True
        )
        self.sensor_ph = Sensor.objects.create(
            instalacion=self.instalacion,
            tipo="ph",
            modelo_hardware="Sonda Analógica V1.1",
            activo=True
        )

    def test_modelo_valor_negativo_rechazado(self):
        """Prueba de borde: Verifica que MinValueValidator(0.0) bloquee mediciones negativas."""
        medicion_invalida = Medicion(
            sensor=self.sensor_ph,
            valor=-1.50,
            estado_conexion=True
        )
        with self.assertRaises(ValidationError):
            medicion_invalida.full_clean()

    def test_eliminacion_en_cascada_instalacion(self):
        """Verifica integridad referencial: eliminar una instalación borra sus sensores."""
        inst_id = self.instalacion.id
        self.instalacion.delete()
        self.assertEqual(Sensor.objects.filter(instalacion_id=inst_id).count(), 0)

    def test_sensor_representacion_cadena_sin_emojis(self):
        """Verifica que la representación en texto del sensor sea limpia y técnica."""
        texto = str(self.sensor_ph)
        self.assertIn("Nivel de pH", texto)
        self.assertIn("Huerto Experimental 1", texto)


class SeguridadYPermisosRBACTestCase(TestCase):
    """
    Criterios 3.1.3.5 y 3.1.5.9: Patrones de seguridad y RBAC.
    """
    def setUp(self):
        # Crear grupos
        self.grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
        self.grupo_supervisor, _ = Group.objects.get_or_create(name='Supervisor')

        # Asignar permisos al grupo Supervisor (Principio de Mínimo Privilegio: Solo ver)
        ct_inst = ContentType.objects.get_for_model(Instalacion)
        ct_med = ContentType.objects.get_for_model(Medicion)
        perm_view_inst = Permission.objects.get(content_type=ct_inst, codename='view_instalacion')
        perm_view_med = Permission.objects.get(content_type=ct_med, codename='view_medicion')
        self.grupo_supervisor.permissions.set([perm_view_inst, perm_view_med])

        # Usuario Administrador
        self.admin_user = User.objects.create_user(username='admin_test', password='AdminPass2026!')
        perm_add_inst = Permission.objects.get(content_type=ct_inst, codename='add_instalacion')
        perm_change_inst = Permission.objects.get(content_type=ct_inst, codename='change_instalacion')
        perm_delete_inst = Permission.objects.get(content_type=ct_inst, codename='delete_instalacion')
        self.admin_user.user_permissions.set([perm_add_inst, perm_change_inst, perm_delete_inst, perm_view_inst])

        # Usuario Supervisor (sin permisos de modificación)
        self.supervisor_user = User.objects.create_user(username='supervisor_test', password='SuperPass2026!')
        self.supervisor_user.groups.add(self.grupo_supervisor)

        self.client = Client()

    def test_supervisor_no_puede_crear_instalacion(self):
        """Un supervisor debe recibir HTTP 403 Forbidden al intentar acceder al formulario de creación."""
        self.client.login(username='supervisor_test', password='SuperPass2026!')
        response = self.client.get('/dashboard/instalacion/crear/')
        self.assertEqual(response.status_code, 403)

    def test_admin_puede_acceder_crear_instalacion(self):
        """El administrador con permiso add_instalacion debe recibir HTTP 200 OK."""
        self.client.login(username='admin_test', password='AdminPass2026!')
        response = self.client.get('/dashboard/instalacion/crear/')
        self.assertEqual(response.status_code, 200)

    def test_usuario_anonimo_redirigido_al_login(self):
        """Cualquier ruta del dashboard sin sesión debe redirigir al login (HTTP 302)."""
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/login/', response.url)


class APITelemetriaSeguridadTestCase(APITestCase):
    """
    Criterios 3.1.3.5 y 3.1.5.9: Seguridad y consumo de API por dispositivos IoT.
    """
    def setUp(self):
        self.instalacion = Instalacion.objects.create(nombre="Huerto API", ubicacion="Módulo 2")
        self.sensor = Sensor.objects.create(
            instalacion=self.instalacion,
            tipo="temperatura_agua",
            modelo_hardware="DS18B20",
            activo=True
        )
        self.sensor_inactivo = Sensor.objects.create(
            instalacion=self.instalacion,
            tipo="co2",
            modelo_hardware="MH-Z19B",
            activo=False
        )

        # Usuario dedicado para el simulador/dispositivo IoT
        self.iot_user = User.objects.create_user(username='iot_device', password='AquaSecret2026!')
        ct_med = ContentType.objects.get_for_model(Medicion)
        perm_add_med = Permission.objects.get(content_type=ct_med, codename='add_medicion')
        self.iot_user.user_permissions.add(perm_add_med)

    def test_api_rechaza_peticion_anonima(self):
        """Peticiones POST a la API sin autenticación son bloqueadas (401 o 403)."""
        url = '/api/mediciones/'
        payload = {"sensor": str(self.sensor.id), "valor": "22.50", "estado_conexion": True}
        response = self.client.post(url, payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_iot_device_puede_enviar_medicion(self):
        """Dispositivo autenticado envía lectura válida y recibe HTTP 201 Created."""
        self.client.login(username='iot_device', password='AquaSecret2026!')
        url = '/api/mediciones/'
        payload = {"sensor": str(self.sensor.id), "valor": "21.30", "estado_conexion": True}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Medicion.objects.filter(sensor=self.sensor).count(), 1)

    def test_api_rechaza_lectura_de_sensor_desactivado(self):
        """No se aceptan mediciones para sensores marcados como inactivos (HTTP 400)."""
        self.client.login(username='iot_device', password='AquaSecret2026!')
        url = '/api/mediciones/'
        payload = {"sensor": str(self.sensor_inactivo.id), "valor": "800.00", "estado_conexion": True}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_rechaza_valor_negativo_en_payload(self):
        """La validación del Serializer bloquea números negativos con mensaje de error."""
        self.client.login(username='iot_device', password='AquaSecret2026!')
        url = '/api/mediciones/'
        payload = {"sensor": str(self.sensor.id), "valor": "-5.00", "estado_conexion": True}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReglasDeAlertaTestCase(APITestCase):
    """
    Criterios 3.1.1.1 y 3.1.5.9: Lógica automática de disparo de alertas (Roja y Azul).
    """
    def setUp(self):
        self.instalacion = Instalacion.objects.create(nombre="Huerto Alertas", ubicacion="Sector 1")
        self.sensor_temp = Sensor.objects.create(
            instalacion=self.instalacion,
            tipo="temperatura_agua",
            modelo_hardware="DS18B20",
            activo=True
        )
        self.regla = ReglaAlerta.objects.create(
            sensor=self.sensor_temp,
            limite_minimo=18.0,
            limite_maximo=24.0,
            activa=True
        )

        self.iot_user = User.objects.create_user(username='iot_device', password='AquaSecret2026!')
        ct_med = ContentType.objects.get_for_model(Medicion)
        self.iot_user.user_permissions.add(Permission.objects.get(content_type=ct_med, codename='add_medicion'))
        self.client.login(username='iot_device', password='AquaSecret2026!')

    def test_alerta_roja_generada_al_superar_maximo(self):
        """Lectura sobre límite máximo genera automáticamente AlertaGenerada (Roja)."""
        payload = {"sensor": str(self.sensor_temp.id), "valor": "28.50", "estado_conexion": True}
        response = self.client.post('/api/mediciones/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        alerta = AlertaGenerada.objects.filter(regla=self.regla).first()
        self.assertIsNotNone(alerta)
        self.assertIn("ALERTA ROJA", alerta.mensaje)
        self.assertIn("ALTO: 28.50°C", alerta.mensaje)

    def test_alerta_azul_generada_al_caer_bajo_minimo(self):
        """Lectura bajo límite mínimo genera automáticamente AlertaGenerada (Azul)."""
        payload = {"sensor": str(self.sensor_temp.id), "valor": "14.20", "estado_conexion": True}
        response = self.client.post('/api/mediciones/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        alerta = AlertaGenerada.objects.filter(regla=self.regla).first()
        self.assertIsNotNone(alerta)
        self.assertIn("ALERTA AZUL", alerta.mensaje)
        self.assertIn("BAJO: 14.20°C", alerta.mensaje)

    def test_sin_alerta_dentro_del_rango_optimo(self):
        """Lectura normal (18.0 a 24.0) NO genera alertas."""
        payload = {"sensor": str(self.sensor_temp.id), "valor": "21.00", "estado_conexion": True}
        response = self.client.post('/api/mediciones/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertaGenerada.objects.filter(regla=self.regla).count(), 0)

    def test_fallo_conexion_no_genera_alerta_falsa(self):
        """Lectura con estado_conexion=False no dispara alertas aunque su valor sea 0.0."""
        payload = {"sensor": str(self.sensor_temp.id), "valor": "0.00", "estado_conexion": False}
        response = self.client.post('/api/mediciones/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertaGenerada.objects.filter(regla=self.regla).count(), 0)


class FormulariosDashboardTestCase(TestCase):
    """
    Criterios 3.1.1.2 y 3.1.5.9: Validación estricta de formularios web.
    """
    def setUp(self):
        self.instalacion = Instalacion.objects.create(nombre="Huerto Forms", ubicacion="Sala 4")
        self.sensor_hum = Sensor.objects.create(
            instalacion=self.instalacion,
            tipo="humedad",
            modelo_hardware="DHT22",
            activo=True
        )
        self.sensor_ph = Sensor.objects.create(
            instalacion=self.instalacion,
            tipo="ph",
            modelo_hardware="Sonda Analógica V1.1",
            activo=True
        )

    def test_humedad_porcentaje_mayor_a_100_rechazado(self):
        """Humedad mayor a 100% debe ser rechazada por el formulario."""
        datos = {
            'sensor': str(self.sensor_hum.id),
            'limite_minimo': 20.0,
            'limite_maximo': 120.0,
            'activa': True
        }
        form = ReglaAlertaForm(data=datos, instalacion=self.instalacion)
        self.assertFalse(form.is_valid())
        self.assertIn('limite_maximo', form.errors)

    def test_ph_fuera_de_escala_quimica_rechazado(self):
        """pH mayor a 14.0 debe ser rechazado."""
        datos = {
            'sensor': str(self.sensor_ph.id),
            'limite_minimo': 5.5,
            'limite_maximo': 15.5,
            'activa': True
        }
        form = ReglaAlertaForm(data=datos, instalacion=self.instalacion)
        self.assertFalse(form.is_valid())
        self.assertIn('limite_maximo', form.errors)

    def test_minimo_mayor_que_maximo_rechazado(self):
        """Límite mínimo superior al máximo debe ser rechazado."""
        datos = {
            'sensor': str(self.sensor_ph.id),
            'limite_minimo': 8.0,
            'limite_maximo': 6.0,
            'activa': True
        }
        form = ReglaAlertaForm(data=datos, instalacion=self.instalacion)
        self.assertFalse(form.is_valid())
        self.assertIn('limite_minimo', form.errors)

    def test_instalacion_form_crea_sensores_seleccionados(self):
        """Verifica que el formulario active solo los sensores elegidos por el usuario."""
        datos = {
            'nombre': 'Huerto Selectivo',
            'ubicacion': 'Sector Este',
            'activa': True,
            'sensores_seleccionados': ['temperatura_agua', 'caudal']
        }
        form = InstalacionForm(data=datos)
        self.assertTrue(form.is_valid())
        nueva = form.save()
        activos = list(nueva.sensores.filter(activo=True).values_list('tipo', flat=True))
        self.assertIn('temperatura_agua', activos)
        self.assertIn('caudal', activos)
        self.assertEqual(len(activos), 2)


class SeguridadPunto6TestCase(TestCase):
    """
    Auditoría Técnica Punto 6 (Seguridad de la Sección 5.2):
    - Configuración segura de ALLOWED_HOSTS, DEBUG, SECRET_KEY y CORS.
    - Aprovisionamiento programático del dispositivo IoT y RBAC.
    """
    def test_settings_allowed_hosts_sin_comodin(self):
        """Verifica que ALLOWED_HOSTS no contenga el comodín '*' inseguro y tenga los hosts permitidos."""
        self.assertNotIn('*', settings.ALLOWED_HOSTS)
        self.assertIn('127.0.0.1', settings.ALLOWED_HOSTS)
        self.assertIn('localhost', settings.ALLOWED_HOSTS)
        self.assertIn('.pythonanywhere.com', settings.ALLOWED_HOSTS)

    def test_settings_cors_no_permite_todos_los_origenes_por_defecto(self):
        """Verifica que CORS_ALLOW_ALL_ORIGINS sea False y existan orígenes seguros configurados."""
        self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)
        self.assertTrue(hasattr(settings, 'CORS_ALLOWED_ORIGINS'))
        self.assertIn('https://fabianvidal.pythonanywhere.com', settings.CORS_ALLOWED_ORIGINS)

    def test_setup_roles_aprovisiona_dispositivo_iot(self):
        """El comando setup_roles debe crear/actualizar el usuario iot_device y asignarle permisos de telemetría."""
        out = StringIO()
        call_command('setup_roles', stdout=out)
        self.assertIn('Políticas de autorización aplicadas correctamente', out.getvalue())

        user_iot = User.objects.filter(username='iot_device').first()
        self.assertIsNotNone(user_iot)
        self.assertTrue(user_iot.has_perm('telemetria.add_medicion'))
        self.assertTrue(user_iot.has_perm('telemetria.view_sensor'))
        self.assertTrue(user_iot.has_perm('telemetria.view_instalacion'))
        self.assertTrue(user_iot.has_perm('telemetria.view_planta'))
        self.assertTrue(user_iot.has_perm('telemetria.view_invernadero'))
        self.assertTrue(user_iot.groups.filter(name='Dispositivo IoT').exists())

    def test_setup_roles_diferencia_admin_cultivador_supervisor(self):
        """
        Verifica la jerarquía RBAC completa generada por setup_roles:
        - Administrador (sin is_superuser): crea instalaciones y reglas (200).
        - Encargado de cultivo: crea reglas (200) pero NO instalaciones (403).
        - Supervisor: solo lectura, NO crea instalaciones ni reglas (403).
        """
        call_command('setup_roles', stdout=StringIO())
        instalacion = Instalacion.objects.create(nombre="Huerto RBAC", ubicacion="Sector Test")
        instalacion_ajena = Instalacion.objects.create(nombre="Huerto Ajeno", ubicacion="Sector X")

        admin_grupo = User.objects.create_user(username='admin_grupo', password='Pass1234!')
        admin_grupo.groups.add(Group.objects.get(name='Administrador'))

        cultivador = User.objects.create_user(username='cultivador_test', password='Pass1234!')
        cultivador.groups.add(Group.objects.get(name='Encargado de cultivo'))

        supervisor = User.objects.create_user(username='sup_rbac', password='Pass1234!')
        supervisor.groups.add(Group.objects.get(name='Supervisor'))

        instalacion.encargados.add(cultivador, supervisor)

        client = Client()

        # Administrador por grupo accede a instalaciones y reglas (propias y ajenas)
        client.login(username='admin_grupo', password='Pass1234!')
        self.assertEqual(client.get('/dashboard/instalacion/crear/').status_code, 200)
        self.assertEqual(client.get(f'/dashboard/instalacion/{instalacion.pk}/regla/crear/').status_code, 200)
        self.assertEqual(client.get(f'/dashboard/instalacion/{instalacion_ajena.pk}/').status_code, 200)

        # Encargado de cultivo gestiona reglas/plantas en SU instalación, pero NO huertos ni instalaciones ajenas
        client.login(username='cultivador_test', password='Pass1234!')
        self.assertEqual(client.get('/dashboard/instalacion/crear/').status_code, 403)
        self.assertEqual(client.get(f'/dashboard/instalacion/{instalacion.pk}/editar/').status_code, 403)
        self.assertEqual(client.get(f'/dashboard/instalacion/{instalacion.pk}/regla/crear/').status_code, 200)
        self.assertEqual(client.get(f'/dashboard/instalacion/{instalacion_ajena.pk}/').status_code, 403)

        # Supervisor es estrictamente solo lectura y solo en sus instalaciones
        client.login(username='sup_rbac', password='Pass1234!')
        self.assertEqual(client.get('/dashboard/instalacion/crear/').status_code, 403)
        self.assertEqual(client.get(f'/dashboard/instalacion/{instalacion.pk}/regla/crear/').status_code, 403)
        self.assertEqual(client.get(f'/dashboard/instalacion/{instalacion.pk}/').status_code, 200)
        self.assertEqual(client.get(f'/dashboard/instalacion/{instalacion_ajena.pk}/').status_code, 403)


class DashboardLiveTelemetriaTestCase(TestCase):
    """
    Verifica que SQLite sea el motor por defecto y que el endpoint en vivo
    del dashboard retorne siempre las 20 mediciones más recientes.
    """
    def setUp(self):
        self.client = Client()
        grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
        self.admin_user = User.objects.create_user(username='admin_live', password='Password123!')
        self.admin_user.groups.add(grupo_admin)
        self.instalacion = Instalacion.objects.create(nombre="Huerto Live", ubicacion="Lab 1")
        self.sensor = Sensor.objects.create(
            instalacion=self.instalacion,
            tipo="ph",
            modelo_hardware="Sonda pH Test",
            activo=True
        )

    def test_sqlite_es_motor_por_defecto(self):
        """Sin variables de entorno externas, SQLite debe ser la primera opción."""
        self.assertEqual(settings.DB_ENGINE, 'sqlite')
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')

    def test_api_telemetria_live_devuelve_ultimas_20_en_orden_cronologico(self):
        """Con más de 20 mediciones, /live/ debe devolver las 20 más recientes (no las 20 primeras)."""
        base = timezone.now() - timedelta(minutes=5)
        for i in range(1, 26):
            med = Medicion.objects.create(sensor=self.sensor, valor=float(i), estado_conexion=True)
            Medicion.objects.filter(pk=med.pk).update(timestamp=base + timedelta(seconds=i * 5))

        self.client.login(username='admin_live', password='Password123!')
        resp = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/live/')
        self.assertEqual(resp.status_code, 200)

        mediciones = resp.json()['sensores']['ph']['mediciones']
        self.assertEqual(len(mediciones), 20)
        valores = [m['valor'] for m in mediciones]
        self.assertEqual(valores[0], 6.0)
        self.assertEqual(valores[-1], 25.0)

    def test_panel_vivo_incluye_ultima_comunicacion(self):
        """La vista detalle en vivo debe incluir el indicador de última comunicación por sensor."""
        self.client.login(username='admin_live', password='Password123!')
        resp = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="ultima-ph"')
        self.assertContains(resp, 'Última com.:')

    def test_historial_muestra_ultima_comunicacion_y_filtra_por_sensor(self):
        """La vista historial muestra el último estado/hora por sensor y filtra correctamente por ?sensor=."""
        sensor_hum = Sensor.objects.create(
            instalacion=self.instalacion,
            tipo="humedad",
            modelo_hardware="DHT22 Test",
            activo=True
        )
        Medicion.objects.create(sensor=self.sensor, valor=6.25, estado_conexion=True)
        Medicion.objects.create(sensor=sensor_hum, valor=71.50, estado_conexion=True)

        self.client.login(username='admin_live', password='Password123!')
        resp_all = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/historial/')
        self.assertEqual(resp_all.status_code, 200)
        self.assertEqual(len(resp_all.context['estados_actuales']), 2)
        self.assertEqual(len(resp_all.context['historico']), 2)

        resp_ph = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/historial/?sensor=ph')
        self.assertEqual(resp_ph.status_code, 200)
        historico_ph = list(resp_ph.context['historico'])
        self.assertEqual(len(historico_ph), 1)
        self.assertEqual(historico_ph[0].sensor.tipo, 'ph')

    def test_carga_ingesta_y_consulta_sqlite_en_tiempo_acotado(self):
        """Prueba de carga (ES2/ES3): ingesta masiva de 300 lecturas y respuesta de /live/ e historial < 2s."""
        base = timezone.now() - timedelta(minutes=30)
        lote = [
            Medicion(sensor=self.sensor, valor=round(5.5 + (i % 10) * 0.1, 2), estado_conexion=True)
            for i in range(300)
        ]
        creadas = Medicion.objects.bulk_create(lote)
        for idx, med in enumerate(creadas):
            med.timestamp = base + timedelta(seconds=idx * 5)
        Medicion.objects.bulk_update(creadas, ['timestamp'])

        self.assertEqual(Medicion.objects.filter(sensor=self.sensor).count(), 300)

        self.client.login(username='admin_live', password='Password123!')
        inicio = time.perf_counter()
        resp_live = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/live/')
        resp_hist = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/historial/')
        duracion = time.perf_counter() - inicio

        self.assertEqual(resp_live.status_code, 200)
        self.assertEqual(len(resp_live.json()['sensores']['ph']['mediciones']), 20)
        self.assertEqual(resp_hist.status_code, 200)
        self.assertEqual(len(resp_hist.context['historico']), 100)
        self.assertLess(duracion, 2.0)


class UsuariosYAsignacionTestCase(TestCase):
    """
    Pruebas del CRUD web de usuarios y aislamiento por instalaciones asignadas.
    """
    def setUp(self):
        call_command('setup_roles', stdout=StringIO())
        self.inst_a = Instalacion.objects.create(nombre="Invernadero Alfa", ubicacion="Sector 1")
        self.inst_b = Instalacion.objects.create(nombre="Invernadero Beta", ubicacion="Sector 2")

        self.admin = User.objects.create_user(username='admin_web', password='Pass1234!')
        self.admin.groups.add(Group.objects.get(name='Administrador'))
        self.client = Client()

    def test_admin_puede_crear_usuario_y_asignar_instalaciones(self):
        """El administrador crea un Encargado de cultivo asignado solo a Invernadero Alfa."""
        self.client.login(username='admin_web', password='Pass1234!')
        resp = self.client.post('/dashboard/usuarios/crear/', {
            'username': 'cultivador_alfa',
            'first_name': 'Carlos',
            'last_name': 'Soto',
            'email': 'carlos@aquaplants.cl',
            'password': 'ClaveSegura123',
            'rol': 'Encargado de cultivo',
            'instalaciones': [str(self.inst_a.pk)],
            'is_active': True,
        })
        self.assertEqual(resp.status_code, 302)
        nuevo = User.objects.get(username='cultivador_alfa')
        self.assertTrue(nuevo.groups.filter(name='Encargado de cultivo').exists())
        self.assertIn(self.inst_a, nuevo.instalaciones_asignadas.all())
        self.assertNotIn(self.inst_b, nuevo.instalaciones_asignadas.all())

    def test_encargado_no_accede_a_crud_usuarios_ni_instalacion_ajena(self):
        """Encargado de cultivo recibe 403 en gestión de usuarios y en instalaciones no asignadas."""
        encargado = User.objects.create_user(username='enc_a', password='Pass1234!')
        encargado.groups.add(Group.objects.get(name='Encargado de cultivo'))
        self.inst_a.encargados.add(encargado)

        self.client.login(username='enc_a', password='Pass1234!')
        self.assertEqual(self.client.get('/dashboard/usuarios/').status_code, 403)
        self.assertEqual(self.client.get(f'/dashboard/instalacion/{self.inst_a.pk}/').status_code, 200)
        self.assertEqual(self.client.get(f'/dashboard/instalacion/{self.inst_b.pk}/').status_code, 403)


class PlantasYAnaliticaTestCase(TestCase):
    """
    Pruebas del CRUD de plantas por instalación, sensores propios,
    endpoint en vivo de planta y recomendaciones automáticas para el cultivador.
    """
    def setUp(self):
        call_command('setup_roles', stdout=StringIO())
        self.instalacion = Instalacion.objects.create(nombre="Torre Central", ubicacion="Nave 1")
        self.cultivador = User.objects.create_user(username='cult_plantas', password='Pass1234!')
        self.cultivador.groups.add(Group.objects.get(name='Encargado de cultivo'))
        self.instalacion.encargados.add(self.cultivador)
        self.client = Client()

    def test_crear_planta_genera_sensores_propios(self):
        """Registrar una planta desde la web crea sus sensores individuales vinculados."""
        self.client.login(username='cult_plantas', password='Pass1234!')
        resp = self.client.post(f'/dashboard/instalacion/{self.instalacion.pk}/plantas/crear/', {
            'codigo': 'T1-A01',
            'especie': 'lechuga_costina',
            'variedad': 'Romana',
            'posicion': 'Torre 1 · Nivel 1',
            'fecha_siembra': str(timezone.localdate() - timedelta(days=10)),
            'etapa': 'vegetativo',
            'activa': True,
            'notas': 'Buen desarrollo radicular',
            'sensores_planta': ['humedad_sustrato', 'ph_sustrato', 'temperatura_raiz'],
        })
        self.assertEqual(resp.status_code, 302)
        planta = Planta.objects.get(instalacion=self.instalacion, codigo='T1-A01')
        self.assertEqual(planta.dias_desde_siembra, 10)
        self.assertEqual(planta.sensores.filter(activo=True).count(), 3)

    def test_telemetria_live_planta_y_recomendaciones(self):
        """El endpoint /plantas/<id>/live/ retorna datos propios, estado crítico y recomendación simple."""
        planta = Planta.objects.create(
            instalacion=self.instalacion,
            codigo='T1-B02',
            especie='Albahaca',
            fecha_siembra=timezone.localdate() - timedelta(days=15),
            etapa='vegetativo',
        )
        sensor_ph = Sensor.objects.create(
            instalacion=self.instalacion,
            planta=planta,
            tipo='ph_sustrato',
            modelo_hardware='Sonda pH Sustrato',
            activo=True,
        )
        Medicion.objects.create(sensor=sensor_ph, valor=8.20, estado_conexion=True)

        resumen = resumen_sensores(planta.sensores.filter(activo=True))
        self.assertEqual(resumen['estado'], 'critico')
        self.assertEqual(resumen['porcentaje_en_rango'], 0)
        self.assertTrue(any('pH' in r for r in resumen['recomendaciones']))

        self.client.login(username='cult_plantas', password='Pass1234!')
        resp = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/plantas/{planta.pk}/live/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['resumen']['estado'], 'critico')
        self.assertEqual(data['sensores']['ph_sustrato']['mediciones'][0]['valor'], 8.2)

    def test_planta_sin_sensores_hereda_diagnostico_y_live_de_torre(self):
        """Una planta en torre compartida (sin sensores propios) hereda el estado y live de su instalación."""
        sensor_torre = Sensor.objects.create(
            instalacion=self.instalacion,
            planta=None,
            tipo='ph',
            modelo_hardware='Sonda pH Estanque',
            activo=True,
        )
        Medicion.objects.create(sensor=sensor_torre, valor=7.90, estado_conexion=True)

        planta = Planta.objects.create(
            instalacion=self.instalacion,
            codigo='T2-C01',
            especie='Lechuga',
            fecha_siembra=timezone.localdate() - timedelta(days=3),
            etapa='germinacion',
        )
        resumen = resumen_planta(planta)
        self.assertEqual(resumen['origen_datos'], 'compartidos')
        self.assertEqual(resumen['estado'], 'critico')
        self.assertTrue(any('germinación' in r.lower() for r in resumen['recomendaciones']))

        self.client.login(username='cult_plantas', password='Pass1234!')
        resp = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/plantas/{planta.pk}/live/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['resumen']['origen_datos'], 'compartidos')
        self.assertEqual(data['sensores']['ph']['mediciones'][0]['valor'], 7.9)

    def test_catalogo_plantas_calcula_dias_y_fecha_estimada_cosecha(self):
        """Cada especie compatible calcula sus días de cultivo, fecha de cosecha y aviso de madurez."""
        siembra_rucula = timezone.localdate() - timedelta(days=12)
        rucula = Planta.objects.create(
            instalacion=self.instalacion,
            codigo='T3-R01',
            especie='rucula',
            fecha_siembra=siembra_rucula,
            etapa='vegetativo',
        )
        self.assertEqual(rucula.especie_nombre, 'Rúcula')
        self.assertEqual(rucula.dias_ciclo, 30)
        self.assertEqual(rucula.dias_desde_siembra, 12)
        self.assertEqual(rucula.dias_para_cosecha, 18)
        self.assertEqual(rucula.progreso_cosecha, 40)
        self.assertEqual(rucula.fecha_estimada_cosecha, siembra_rucula + timedelta(days=30))
        self.assertFalse(rucula.lista_para_cosechar)

        tomate = Planta.objects.create(
            instalacion=self.instalacion,
            codigo='T3-T02',
            especie='tomate_cherry',
            fecha_siembra=timezone.localdate() - timedelta(days=82),
            etapa='floracion',
        )
        self.assertEqual(tomate.dias_para_cosecha, 0)
        self.assertTrue(tomate.lista_para_cosechar)
        res = resumen_planta(tomate)
        self.assertTrue(any('preparar cosecha' in r.lower() for r in res['recomendaciones']))

    def test_planta_trasplantada_en_etapa_avanzada_descuenta_dias_cosecha(self):
        """Crear una planta hoy en etapa avanzada descuenta los días previos estimados del ciclo total."""
        from dashboard.forms import PlantaForm

        hoy = timezone.localdate()
        form_tomate = PlantaForm(
            data={
                'codigo': 'TomateCherry',
                'especie': 'tomate_cherry',
                'variedad': 'Cherry Bloom',
                'posicion': '1',
                'fecha_siembra': hoy.isoformat(),
                'etapa': 'floracion',
                'activa': True,
            },
            instalacion=self.instalacion,
        )
        self.assertTrue(form_tomate.is_valid(), form_tomate.errors)
        tomate = form_tomate.save()

        # Tomate Cherry: ciclo 80d, floración = 60% -> 48 días previos, 32 restantes
        self.assertEqual(tomate.dias_previos, 48)
        self.assertEqual(tomate.dias_en_torre, 0)
        self.assertEqual(tomate.dias_desde_siembra, 48)
        self.assertEqual(tomate.dias_para_cosecha, 32)
        self.assertEqual(tomate.progreso_cosecha, 60)
        self.assertEqual(tomate.fecha_estimada_cosecha, hoy + timedelta(days=32))

        # Al avanzar 5 días en la torre, los días totales y el restante deben progresar
        tomate.fecha_siembra = hoy - timedelta(days=5)
        tomate.save()
        self.assertEqual(tomate.dias_en_torre, 5)
        self.assertEqual(tomate.dias_desde_siembra, 53)
        self.assertEqual(tomate.dias_para_cosecha, 27)

        # Verificar con otra especie (Lechuga Costina 45d en Vegetativo = 20% -> 9 días)
        form_lechuga = PlantaForm(
            data={
                'codigo': 'Lechuga-Veg',
                'especie': 'lechuga_costina',
                'fecha_siembra': hoy.isoformat(),
                'etapa': 'vegetativo',
                'activa': True,
            },
            instalacion=self.instalacion,
        )
        self.assertTrue(form_lechuga.is_valid(), form_lechuga.errors)
        lechuga = form_lechuga.save()
        self.assertEqual(lechuga.dias_previos, 9)
        self.assertEqual(lechuga.dias_desde_siembra, 9)
        self.assertEqual(lechuga.dias_para_cosecha, 36)

    def test_lista_plantas_ordena_por_severidad_criticas_primero(self):
        """Las plantas críticas y en atención deben aparecer antes que las óptimas en el listado."""
        p_opt = Planta.objects.create(instalacion=self.instalacion, codigo='P-OPT', especie='lechuga_costina')
        p_atn = Planta.objects.create(instalacion=self.instalacion, codigo='P-ATN', especie='rucula')
        p_crt = Planta.objects.create(instalacion=self.instalacion, codigo='P-CRT', especie='albahaca')

        s_opt = Sensor.objects.create(
            instalacion=self.instalacion, planta=p_opt, tipo='ph_sustrato', modelo_hardware='S1', activo=True
        )
        s_atn = Sensor.objects.create(
            instalacion=self.instalacion, planta=p_atn, tipo='ph_sustrato', modelo_hardware='S2', activo=True
        )
        s_crt = Sensor.objects.create(
            instalacion=self.instalacion, planta=p_crt, tipo='ph_sustrato', modelo_hardware='S3', activo=True
        )

        # 6.00 = Óptimo, 6.45 = Atención (cerca de 6.5), 8.20 = Crítico
        Medicion.objects.create(sensor=s_opt, valor=6.00, estado_conexion=True)
        Medicion.objects.create(sensor=s_atn, valor=6.45, estado_conexion=True)
        Medicion.objects.create(sensor=s_crt, valor=8.20, estado_conexion=True)

        self.client.login(username='cult_plantas', password='Pass1234!')
        resp = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/plantas/')
        self.assertEqual(resp.status_code, 200)

        orden = [f['planta'].codigo for f in resp.context['fichas']]
        self.assertEqual(orden, ['P-CRT', 'P-ATN', 'P-OPT'])

    def test_rangos_por_etapa_y_avisos_precosecha(self):
        """Los rangos y avisos de diagnóstico se adaptan según etapa y proximidad a cosecha."""
        sensor_hum = Sensor.objects.create(
            instalacion=self.instalacion, tipo='humedad', modelo_hardware='DHT22', activo=True
        )
        # 74% de humedad es óptimo en germinación (65-85%), pero crítico en floración (45-65%)
        Medicion.objects.create(sensor=sensor_hum, valor=74.0, estado_conexion=True)

        planta_germ = Planta.objects.create(
            instalacion=self.instalacion,
            codigo='GERM-01',
            especie='tomate_cherry',
            etapa='germinacion',
        )
        planta_flor = Planta.objects.create(
            instalacion=self.instalacion,
            codigo='FLOR-01',
            especie='tomate_cherry',
            etapa='floracion',
        )
        res_germ = resumen_planta(planta_germ)
        res_flor = resumen_planta(planta_flor)
        self.assertEqual(res_germ['estado'], 'optimo')
        self.assertEqual(res_flor['estado'], 'critico')
        self.assertTrue(any('floración' in r.lower() for r in res_flor['recomendaciones']))

        # Planta testigo en ventana pre-cosecha (4 días restantes, 74% humedad sustrato > 72%)
        hoy = timezone.localdate()
        testigo_pre = Planta.objects.create(
            instalacion=self.instalacion,
            codigo='PRE-01',
            especie='lechuga_costina',
            etapa='vegetativo',
            fecha_siembra=hoy - timedelta(days=41),
        )
        s_raiz = Sensor.objects.create(
            instalacion=self.instalacion,
            planta=testigo_pre,
            tipo='humedad_sustrato',
            modelo_hardware='Sonda Pre',
            activo=True,
        )
        Medicion.objects.create(sensor=s_raiz, valor=74.0, estado_conexion=True)
        res_pre = resumen_planta(testigo_pre)
        self.assertEqual(res_pre['origen_datos'], 'propios')
        self.assertTrue(res_pre['pre_cosecha'])
        self.assertEqual(res_pre['estado'], 'critico')
        self.assertTrue(any('pre-cosecha' in r.lower() for r in res_pre['recomendaciones']))

        # Vista detalle muestra el rango objetivo adaptado por etapa
        self.client.login(username='cult_plantas', password='Pass1234!')
        resp = self.client.get(f'/dashboard/instalacion/{self.instalacion.pk}/plantas/{planta_flor.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '45')
        self.assertContains(resp, '65')


class AlertasCentroTestCase(TestCase):
    """
    Pruebas del Centro de Alertas navegable, filtros, gestión de lectura y permisos por rol.
    """
    def setUp(self):
        call_command('setup_roles', stdout=StringIO())
        self.inst = Instalacion.objects.create(nombre="Huerto Alertas Centro", ubicacion="Sector A")
        self.sensor = Sensor.objects.create(
            instalacion=self.inst, tipo='ph', modelo_hardware='pH v1', activo=True
        )
        self.regla = ReglaAlerta.objects.create(
            sensor=self.sensor, limite_minimo=5.5, limite_maximo=6.8, activa=True
        )
        med1 = Medicion.objects.create(sensor=self.sensor, valor=8.10, estado_conexion=True)
        med2 = Medicion.objects.create(sensor=self.sensor, valor=4.20, estado_conexion=True)
        self.alerta_roja = AlertaGenerada.objects.create(
            regla=self.regla, medicion=med1, mensaje="¡ALERTA ROJA! pH ALTO: 8.10 pH", leida=False
        )
        self.alerta_azul = AlertaGenerada.objects.create(
            regla=self.regla, medicion=med2, mensaje="¡ALERTA AZUL! pH BAJO: 4.20 pH", leida=True
        )

        self.encargado = User.objects.create_user(username='enc_al', password='Pass1234!')
        self.encargado.groups.add(Group.objects.get(name='Encargado de cultivo'))
        self.supervisor = User.objects.create_user(username='sup_al', password='Pass1234!')
        self.supervisor.groups.add(Group.objects.get(name='Supervisor'))
        self.inst.encargados.add(self.encargado, self.supervisor)
        self.client = Client()

    def test_filtrar_alertas_por_estado_severidad_y_busqueda(self):
        """Los filtros ?estado=, ?severidad= y ?q= devuelven exactamente las alertas coincidentes."""
        self.client.login(username='enc_al', password='Pass1234!')

        resp_pend = self.client.get('/dashboard/alertas/?estado=pendientes')
        self.assertEqual(resp_pend.status_code, 200)
        self.assertEqual([a.pk for a in resp_pend.context['alertas']], [self.alerta_roja.pk])

        resp_azul = self.client.get('/dashboard/alertas/?severidad=azul')
        self.assertEqual(resp_azul.status_code, 200)
        self.assertEqual([a.pk for a in resp_azul.context['alertas']], [self.alerta_azul.pk])

        resp_q = self.client.get('/dashboard/alertas/?q=8.10')
        self.assertEqual(resp_q.status_code, 200)
        self.assertEqual([a.pk for a in resp_q.context['alertas']], [self.alerta_roja.pk])

    def test_encargado_marca_alerta_leida_y_supervisor_recibe_403(self):
        """Encargado gestiona alertas (toggle y marcar todas); Supervisor solo ve (403 al modificar)."""
        self.client.login(username='sup_al', password='Pass1234!')
        self.assertEqual(self.client.get('/dashboard/alertas/').status_code, 200)
        self.assertEqual(self.client.post(f'/dashboard/alertas/{self.alerta_roja.pk}/toggle/').status_code, 403)
        self.assertEqual(self.client.post('/dashboard/alertas/marcar-todas/').status_code, 403)

        self.client.login(username='enc_al', password='Pass1234!')
        resp = self.client.post(f'/dashboard/alertas/{self.alerta_roja.pk}/toggle/')
        self.assertEqual(resp.status_code, 302)
        self.alerta_roja.refresh_from_db()
        self.assertTrue(self.alerta_roja.leida)


class InvernaderosMonitorTestCase(TestCase):
    """
    Pruebas del módulo de Invernaderos, agrupación visual de torres en el Monitor y permisos.
    """
    def setUp(self):
        call_command('setup_roles', stdout=StringIO())
        self.admin = User.objects.create_user(username='admin_inv', password='Pass1234!')
        self.admin.groups.add(Group.objects.get(name='Administrador'))
        self.encargado = User.objects.create_user(username='enc_inv', password='Pass1234!')
        self.encargado.groups.add(Group.objects.get(name='Encargado de cultivo'))
        self.client = Client()

    def test_admin_crea_invernadero_y_agrupa_torres_en_monitor(self):
        """Admin crea un invernadero y una torre vinculada; el monitor los agrupa visualmente."""
        self.client.login(username='admin_inv', password='Pass1234!')
        resp_inv = self.client.post('/dashboard/invernadero/crear/', {
            'nombre': 'Invernadero Norte',
            'sector': 'Zona A',
            'descripcion': 'Nave principal',
            'activa': True,
        })
        self.assertEqual(resp_inv.status_code, 302)
        inv = Invernadero.objects.get(nombre='Invernadero Norte')

        # Preselección en GET ?invernadero=<id> y creación de torre vinculada
        resp_get = self.client.get(f'/dashboard/instalacion/crear/?invernadero={inv.pk}')
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(str(resp_get.context['form'].initial.get('invernadero')), str(inv.pk))

        Instalacion.objects.create(invernadero=inv, nombre='Torre N1', ubicacion='Fila 1')
        resp_mon = self.client.get('/dashboard/')
        self.assertEqual(resp_mon.status_code, 200)
        grupos = resp_mon.context['grupos_invernaderos']
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0]['invernadero'].nombre, 'Invernadero Norte')
        self.assertEqual(grupos[0]['num_torres'], 1)

    def test_encargado_solo_ve_su_invernadero_y_no_puede_crear_invernadero(self):
        """Encargado de cultivo recibe 403 al crear invernadero y solo ve el de sus torres."""
        inv_norte = Invernadero.objects.create(nombre='Invernadero Norte', sector='A')
        inv_sur = Invernadero.objects.create(nombre='Invernadero Sur', sector='B')
        torre_a = Instalacion.objects.create(invernadero=inv_norte, nombre='Torre A', ubicacion='F1')
        Instalacion.objects.create(invernadero=inv_sur, nombre='Torre B', ubicacion='F2')
        torre_a.encargados.add(self.encargado)

        self.client.login(username='enc_inv', password='Pass1234!')
        self.assertEqual(self.client.get('/dashboard/invernadero/crear/').status_code, 403)

        resp_mon = self.client.get('/dashboard/')
        self.assertEqual(resp_mon.status_code, 200)
        nombres_inv = [g['invernadero'].nombre for g in resp_mon.context['grupos_invernaderos']]
        self.assertEqual(nombres_inv, ['Invernadero Norte'])


class SimuladorAdaptativoTestCase(APITestCase):
    """
    Verifica que simulador_iot.py se adapte cuando faltan torres,
    hay torres independientes o existen plantas individuales activas/inactivas.
    """
    def _args_base(self, **overrides):
        base = {
            'url': 'http://127.0.0.1:8000',
            'usuario': 'iot_device',
            'password': 'secret',
            'invernadero': None,
            'instalacion': None,
            'planta': None,
            'solo_plantas': False,
            'solo_torres': False,
            'intervalo': 0.1,
            'anomalias': 0.0,
            'fallos': 0.0,
            'resync': 10,
            'ciclos': 1,
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_api_rechaza_lectura_de_planta_inactiva(self):
        """La API rechaza mediciones enviadas a un sensor cuya planta está inactiva (HTTP 400)."""
        call_command('setup_roles', stdout=StringIO())
        inst = Instalacion.objects.create(nombre='Torre Cosecha', ubicacion='Nave 1', activa=True)
        planta_inactiva = Planta.objects.create(
            instalacion=inst, codigo='P-COSECHADA', especie='rucula', activa=False
        )
        sensor = Sensor.objects.create(
            instalacion=inst, planta=planta_inactiva, tipo='ph_sustrato', modelo_hardware='S1', activo=True
        )
        self.client.login(username='iot_device', password='AquaSecret2026!')
        resp = self.client.post('/api/mediciones/', {
            'sensor': str(sensor.id), 'valor': '6.10', 'estado_conexion': True
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_simulador_filtra_torres_faltantes_y_plantas_independientes(self):
        """
        El simulador omite invernaderos inactivos y plantas inactivas,
        pero conserva torres independientes (sin invernadero) y plantas activas.
        """
        sim = SimuladorAquaBrain(self._args_base())
        datos_mock = {
            '/api/invernaderos/': [
                {'id': 'inv-1', 'nombre': 'Inv Activo', 'activa': True},
                {'id': 'inv-2', 'nombre': 'Inv Apagado', 'activa': False},
            ],
            '/api/instalaciones/': [
                {'id': 't-indep', 'nombre': 'Torre Libre', 'invernadero': None, 'activa': True},
                {'id': 't-apagada', 'nombre': 'Torre Inv 2', 'invernadero': 'inv-2', 'activa': True},
            ],
            '/api/plantas/': [
                {'id': 'p-activa', 'codigo': 'T-P1', 'instalacion': 't-indep', 'activa': True},
            ],
            '/api/sensores/': [
                {
                    'id': 's-torre', 'instalacion': 't-indep', 'instalacion_nombre': 'Torre Libre',
                    'planta': None, 'planta_codigo': None, 'tipo': 'ph', 'activo': True,
                },
                {
                    'id': 's-planta-ok', 'instalacion': 't-indep', 'instalacion_nombre': 'Torre Libre',
                    'planta': 'p-activa', 'planta_codigo': 'T-P1', 'tipo': 'humedad_sustrato', 'activo': True,
                },
                {
                    'id': 's-planta-off', 'instalacion': 't-indep', 'instalacion_nombre': 'Torre Libre',
                    'planta': 'p-inactiva', 'planta_codigo': 'T-OFF', 'tipo': 'ph_sustrato', 'activo': True,
                },
                {
                    'id': 's-inv-off', 'instalacion': 't-apagada', 'instalacion_nombre': 'Torre Inv 2',
                    'planta': None, 'planta_codigo': None, 'tipo': 'caudal', 'activo': True,
                },
            ],
        }
        sim._get_todo = lambda ruta, params=None: datos_mock[ruta]
        sim.sincronizar()
        self.assertEqual([s['id'] for s in sim.sensores], ['s-torre', 's-planta-ok'])

        # Si falta la torre solicitada por --instalacion, no cae con SystemExit: espera con 0 sensores
        sim_missing = SimuladorAquaBrain(self._args_base(instalacion='TorreQueNoExiste'))
        sim_missing._get_todo = lambda ruta, params=None: datos_mock[ruta]
        sim_missing.sincronizar()
        self.assertEqual(sim_missing.sensores, [])

        # Ante un 404 (torre o sensor borrado en vivo), activa forzar_resync
        resp_404 = Mock(status_code=404, text='Not found')
        sim.session.post = lambda *a, **kw: resp_404
        sim.forzar_resync = False
        sim.enviar(sim.sensores[0])
        self.assertTrue(sim.forzar_resync)

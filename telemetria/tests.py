from io import StringIO
from django.test import TestCase, Client
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status

from telemetria.models import Instalacion, Sensor, Medicion, ReglaAlerta, AlertaGenerada
from dashboard.forms import ReglaAlertaForm, InstalacionForm


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
        self.assertTrue(user_iot.groups.filter(name='Dispositivo IoT').exists())


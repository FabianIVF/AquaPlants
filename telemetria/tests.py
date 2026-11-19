import time
from datetime import timedelta
from io import StringIO
from django.test import TestCase, Client
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from telemetria.models import Instalacion, Planta, Sensor, Medicion, ReglaAlerta, AlertaGenerada
from dashboard.analytics import resumen_planta, resumen_sensores
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

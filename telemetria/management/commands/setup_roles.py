import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from telemetria.models import Invernadero, Instalacion, Planta, Sensor, Medicion, ReglaAlerta, AlertaGenerada


class Command(BaseCommand):  # Convierte este script en una herramienta de consola segura
    help = 'Configura los roles de seguridad, permisos RBAC y credenciales IoT para AquaPlants'

    def handle(self, *args, **kwargs):
        # 1. Definición de los grupos basados en el negocio
        roles = ['Administrador', 'Encargado de cultivo', 'Supervisor', 'Dispositivo IoT']

        for rol in roles:
            # get_or_create evita que el sistema falle si el rol ya existe (Idempotencia)
            grupo, creado = Group.objects.get_or_create(name=rol)
            if creado:
                self.stdout.write(self.style.SUCCESS(f'Rol creado: {rol}'))
            else:
                self.stdout.write(self.style.WARNING(f'El rol {rol} ya existía.'))

        # 2. Obtener las referencias de todos los modelos del dominio y usuarios en Django
        ct_invernadero = ContentType.objects.get_for_model(Invernadero)
        ct_instalacion = ContentType.objects.get_for_model(Instalacion)
        ct_planta = ContentType.objects.get_for_model(Planta)
        ct_sensor = ContentType.objects.get_for_model(Sensor)
        ct_medicion = ContentType.objects.get_for_model(Medicion)
        ct_regla = ContentType.objects.get_for_model(ReglaAlerta)
        ct_alerta = ContentType.objects.get_for_model(AlertaGenerada)
        ct_user = ContentType.objects.get_for_model(User)

        todos_modelos = [ct_invernadero, ct_instalacion, ct_planta, ct_sensor, ct_medicion, ct_regla, ct_alerta]

        # 3a. Administrador: Acceso total a instalaciones, plantas, sensores, mediciones, reglas, alertas y usuarios
        grupo_admin = Group.objects.get(name='Administrador')
        permisos_admin = list(Permission.objects.filter(content_type__in=todos_modelos)) + list(
            Permission.objects.filter(content_type=ct_user)
        )
        grupo_admin.permissions.set(permisos_admin)

        # 3b. Encargado de cultivo (Cultivador): Monitoreo completo + gestión de plantas y reglas/alertas,
        #     SIN permisos para crear, modificar ni eliminar instalaciones ni usuarios
        grupo_cultivador = Group.objects.get(name='Encargado de cultivo')
        permisos_vista_cultivador = Permission.objects.filter(
            content_type__in=todos_modelos,
            codename__startswith='view_'
        )
        permisos_plantas = Permission.objects.filter(content_type=ct_planta)
        permisos_reglas = Permission.objects.filter(content_type=ct_regla)
        perm_change_alerta = Permission.objects.filter(content_type=ct_alerta, codename='change_alertagenerada')
        grupo_cultivador.permissions.set(
            list(permisos_vista_cultivador)
            + list(permisos_plantas)
            + list(permisos_reglas)
            + list(perm_change_alerta)
        )

        # 3c. Supervisor: Principio de Mínimo Privilegio (Solo Lectura estricta)
        grupo_supervisor = Group.objects.get(name='Supervisor')
        permisos_lectura = Permission.objects.filter(
            content_type__in=todos_modelos,
            codename__startswith='view_'
        )
        grupo_supervisor.permissions.set(permisos_lectura)

        # 4. Aprovisionamiento programático del dispositivo IoT
        iot_username = os.getenv('AQUA_IOT_USER', 'iot_device')
        iot_password = os.getenv('AQUA_IOT_PASSWORD', 'AquaSecret2026!')

        iot_user, user_creado = User.objects.get_or_create(username=iot_username)
        iot_user.set_password(iot_password)
        iot_user.is_staff = False
        iot_user.is_superuser = False
        iot_user.save()

        # Permisos requeridos para reportar telemetría y consultar inventario de sensores/plantas
        perm_add_medicion = Permission.objects.get(content_type=ct_medicion, codename='add_medicion')
        perm_view_sensor = Permission.objects.get(content_type=ct_sensor, codename='view_sensor')
        perm_view_instalacion = Permission.objects.get(content_type=ct_instalacion, codename='view_instalacion')
        perm_view_planta = Permission.objects.get(content_type=ct_planta, codename='view_planta')

        permisos_iot = [perm_add_medicion, perm_view_sensor, perm_view_instalacion, perm_view_planta]
        iot_user.user_permissions.set(permisos_iot)

        grupo_iot = Group.objects.get(name='Dispositivo IoT')
        grupo_iot.permissions.set(permisos_iot)
        iot_user.groups.add(grupo_iot)

        if user_creado:
            self.stdout.write(self.style.SUCCESS(f'Usuario IoT aprovisionado: {iot_username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Usuario IoT actualizado: {iot_username}'))

        self.stdout.write(self.style.SUCCESS('Políticas de autorización aplicadas correctamente.'))

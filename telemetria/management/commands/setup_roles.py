import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from telemetria.models import Instalacion, Sensor, Medicion

class Command(BaseCommand):  # Convierte este script en una herramienta de consola segura
    help = 'Configura los roles de seguridad, permisos RBAC y credenciales IoT para AquaPlants'

    def handle(self, *args, **kwargs):
        # 1. Definición de los grupos basados en el negocio
        roles = ['Administrador', 'Supervisor', 'Encargado de cultivo', 'Dispositivo IoT']
        
        for rol in roles:
            # get_or_create evita que el sistema falle si el rol ya existe (Idempotencia)
            grupo, creado = Group.objects.get_or_create(name=rol)
            if creado:
                self.stdout.write(self.style.SUCCESS(f'Rol creado: {rol}'))
            else:
                self.stdout.write(self.style.WARNING(f'El rol {rol} ya existía.'))

        # 2. Obtener las referencias de los modelos en el sistema de permisos de Django
        content_type_instalacion = ContentType.objects.get_for_model(Instalacion)
        content_type_sensor = ContentType.objects.get_for_model(Sensor)
        content_type_medicion = ContentType.objects.get_for_model(Medicion)

        # 3. Asignación de permisos al Supervisor (Principio de Mínimo Privilegio: Solo Lectura)
        grupo_supervisor = Group.objects.get(name='Supervisor')
        permisos_lectura = Permission.objects.filter(
            content_type__in=[content_type_instalacion, content_type_medicion, content_type_sensor],
            codename__startswith='view_'  # Expresión que filtra solo los permisos de "ver"
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

        # Permisos requeridos para reportar telemetría y consultar inventario de sensores
        perm_add_medicion = Permission.objects.get(content_type=content_type_medicion, codename='add_medicion')
        perm_view_sensor = Permission.objects.get(content_type=content_type_sensor, codename='view_sensor')
        perm_view_instalacion = Permission.objects.get(content_type=content_type_instalacion, codename='view_instalacion')

        permisos_iot = [perm_add_medicion, perm_view_sensor, perm_view_instalacion]
        iot_user.user_permissions.set(permisos_iot)

        grupo_iot = Group.objects.get(name='Dispositivo IoT')
        grupo_iot.permissions.set(permisos_iot)
        iot_user.groups.add(grupo_iot)

        if user_creado:
            self.stdout.write(self.style.SUCCESS(f'Usuario IoT aprovisionado: {iot_username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Usuario IoT actualizado: {iot_username}'))

        self.stdout.write(self.style.SUCCESS('Políticas de autorización aplicadas correctamente.'))

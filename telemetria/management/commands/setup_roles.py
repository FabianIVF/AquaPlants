from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from telemetria.models import Instalacion, Sensor, Medicion

class Command(BaseCommand): #Convierte este script en una herramienta de consola segura
    help = 'Configura los roles de seguridad y permisos RBAC para AquaPlants'

    def handle(self, *args, **kwargs):
        # 1. Definición de los grupos basados en el negocio
        roles = ['Administrador', 'Supervisor', 'Encargado de cultivo']
        
        for rol in roles:
            # get_or_create evita que el sistema falle si el rol ya existe (Idempotencia)
            grupo, creado = Group.objects.get_or_create(name=rol)
            if creado:
                self.stdout.write(self.style.SUCCESS(f'Rol creado: {rol}'))
            else:
                self.stdout.write(self.style.WARNING(f'El rol {rol} ya existía.'))

        # 2. Obtener las referencias de los modelos en el sistema de permisos de Django
        content_type_instalacion = ContentType.objects.get_for_model(Instalacion)
        content_type_medicion = ContentType.objects.get_for_model(Medicion)

        # 3. Asignación de permisos al Supervisor (Principio de Mínimo Privilegio: Solo Lectura)
        grupo_supervisor = Group.objects.get(name='Supervisor')
        permisos_lectura = Permission.objects.filter(
            content_type__in=[content_type_instalacion, content_type_medicion],
            codename__startswith='view_' # Expresión que filtra solo los permisos de "ver"
        )
        grupo_supervisor.permissions.set(permisos_lectura)
        
        self.stdout.write(self.style.SUCCESS('Políticas de autorización aplicadas correctamente.'))
from django.contrib import admin
from .models import Instalacion, Sensor, Medicion, ReglaAlerta, AlertaGenerada


@admin.register(Instalacion) # Decorador para hacer publica la tabla dentro del panel
class InstalacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'activa', 'fecha_creacion') # list_display: define que columnas de la tabla se monstraran en la tabla visual
    search_fields = ('nombre', 'ubicacion') # Agregan barras de búsqueda

@admin.register(Sensor) # Decorador para hacer publica la tabla dentro del panel
class SensorAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'instalacion', 'modelo_hardware') # list_display: define que columnas de la tabla se monstraran en la tabla visual
    list_filter = ('tipo',) # Agrega filtros laterales

@admin.register(Medicion) # Decorador para hacer publica la tabla dentro del panel
class MedicionAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'valor', 'timestamp', 'estado_conexion') # list_display: define que columnas de la tabla se monstraran en la tabla visual
    list_filter = ('sensor__tipo', 'timestamp', 'estado_conexion')# Agrega filtros laterales

admin.site.register(ReglaAlerta)
admin.site.register(AlertaGenerada)
from django.contrib import admin
from .models import Invernadero, Instalacion, Planta, Sensor, Medicion, ReglaAlerta, AlertaGenerada


@admin.register(Invernadero)
class InvernaderoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sector', 'activa', 'fecha_creacion')
    search_fields = ('nombre', 'sector')


@admin.register(Instalacion)  # Decorador para hacer pública la tabla dentro del panel
class InstalacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'invernadero', 'ubicacion', 'activa', 'fecha_creacion')  # Columnas visibles
    list_filter = ('invernadero', 'activa')
    search_fields = ('nombre', 'ubicacion')  # Agregan barras de búsqueda


@admin.register(Planta)
class PlantaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'especie', 'instalacion', 'etapa', 'activa')
    list_filter = ('etapa', 'activa', 'instalacion')
    search_fields = ('codigo', 'especie', 'variedad')


@admin.register(Sensor)  # Decorador para hacer pública la tabla dentro del panel
class SensorAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'instalacion', 'planta', 'modelo_hardware', 'activo')  # Columnas visibles en admin
    list_filter = ('tipo', 'activo')  # Agrega filtros laterales


@admin.register(Medicion)  # Decorador para hacer pública la tabla dentro del panel
class MedicionAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'valor', 'timestamp', 'estado_conexion')  # Columnas visibles en admin
    list_filter = ('sensor__tipo', 'timestamp', 'estado_conexion')  # Agrega filtros laterales


admin.site.register(ReglaAlerta)
admin.site.register(AlertaGenerada)

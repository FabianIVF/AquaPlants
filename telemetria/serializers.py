from rest_framework import serializers
from .models import Instalacion, Sensor, Medicion

class InstalacionSerializer(serializers.ModelSerializer): #serializers.ModelSerializer: Hereda la clase
    class Meta:
        model = Instalacion
        fields = ['id', 'nombre', 'ubicacion', 'activa', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion']

class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['id', 'instalacion', 'tipo', 'modelo_hardware']
        read_only_fields = ['id']

class MedicionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicion
        # Definimos exactamente qué campos exponer
        fields = ['id', 'sensor', 'valor', 'timestamp', 'estado_conexion']
        
        # Campos de solo lectura por seguridad
        read_only_fields = ['id', 'timestamp']

    # Validación personalizada de seguridad a nivel de API
    def validate_valor(self, value):
        if value < 0:
            raise serializers.ValidationError("Una medición de sensor no puede tener un valor negativo. Posible manipulación de datos.")
        return value
from rest_framework import serializers
from .models import Instalacion, Sensor, Medicion


class InstalacionSerializer(serializers.ModelSerializer): #serializers.ModelSerializer: Hereda la clase
    class Meta:
        model = Instalacion
        fields = ['id', 'nombre', 'ubicacion', 'activa', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion']


class SensorSerializer(serializers.ModelSerializer):
    # Campos informativos de solo lectura (útiles para el simulador IoT)
    unidad = serializers.CharField(source='get_unidad', read_only=True)
    instalacion_nombre = serializers.CharField(source='instalacion.nombre', read_only=True)

    class Meta:
        model = Sensor
        fields = ['id', 'instalacion', 'instalacion_nombre', 'tipo', 'modelo_hardware', 'activo', 'unidad']
        read_only_fields = ['id']


class MedicionSerializer(serializers.ModelSerializer):
    """
    Estructura alineada con la pauta (punto 5 - datos simulados):
    id_sistema, id_dispositivo, id_sensor, tipo_variable, valor, unidad,
    timestamp, estado_conexion y alerta (esta última se agrega en la vista).
    El cliente solo envía: sensor, valor, estado_conexion.
    """
    id_sistema = serializers.UUIDField(source='sensor.instalacion_id', read_only=True)
    id_sensor = serializers.UUIDField(source='sensor_id', read_only=True)
    tipo_variable = serializers.CharField(source='sensor.tipo', read_only=True)
    unidad = serializers.CharField(source='sensor.get_unidad', read_only=True)
    id_dispositivo = serializers.SerializerMethodField()

    class Meta:
        model = Medicion
        # Definimos exactamente qué campos exponer
        fields = ['id', 'id_sistema', 'id_dispositivo', 'sensor', 'id_sensor',
                  'tipo_variable', 'valor', 'unidad', 'timestamp', 'estado_conexion']

        # Campos de solo lectura por seguridad
        read_only_fields = ['id', 'timestamp']

    def get_id_dispositivo(self, obj):
        # El dispositivo que reporta es la cuenta autenticada (ej. iot_device)
        request = self.context.get('request')
        return request.user.username if request and request.user.is_authenticated else None

    # Validación personalizada de seguridad a nivel de API
    def validate_valor(self, value):
        if value < 0:
            raise serializers.ValidationError("Una medición de sensor no puede tener un valor negativo. Posible manipulación de datos.")
        return value

    def validate_sensor(self, sensor):
        # No se aceptan lecturas de sensores desactivados en el dashboard
        if not sensor.activo:
            raise serializers.ValidationError("Este sensor está desactivado para esta instalación; la lectura fue rechazada.")
        return sensor

from django.db import models
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

# ============================================================
# CATÁLOGO MAESTRO DE SENSORES Y PARÁMETROS HIDROPÓNICOS
# ============================================================
SENSOR_CATALOGO = {
    'temperatura_agua': {
        'nombre': 'Temperatura del Agua / Solución',
        'unidad': '°C',
        'icono': '🌡️💧',
        'min_val': 0.0,
        'max_val': 50.0,
        'step': '0.1',
        'hardware_default': 'Sonda Sumergible DS18B20',
        'descripcion': 'Temperatura de la solución nutritiva en el estanque',
    },
    'temperatura_aire': {
        'nombre': 'Temperatura del Aire / Ambiente',
        'unidad': '°C',
        'icono': '🌡️💨',
        'min_val': 0.0,
        'max_val': 60.0,
        'step': '0.1',
        'hardware_default': 'Sensor Ambiental DHT22 / BME280',
        'descripcion': 'Temperatura ambiental del invernadero o cultivo',
    },
    'humedad': {
        'nombre': 'Humedad Ambiental',
        'unidad': '%',
        'icono': '💧',
        'min_val': 0.0,
        'max_val': 100.0,
        'step': '0.1',
        'hardware_default': 'Sensor de Humedad DHT22',
        'descripcion': 'Humedad relativa del aire (0% a 100%)',
    },
    'ph': {
        'nombre': 'Nivel de pH',
        'unidad': 'pH',
        'icono': '🧪',
        'min_val': 0.0,
        'max_val': 14.0,
        'step': '0.01',
        'hardware_default': 'Sonda pH Analógica V1.1',
        'descripcion': 'Acidez/alcalinidad de la solución nutritiva (0 a 14)',
    },
    'caudal': {
        'nombre': 'Caudal de Agua',
        'unidad': 'L/min',
        'icono': '🌊',
        'min_val': 0.0,
        'max_val': 50.0,
        'step': '0.1',
        'hardware_default': 'Flujómetro YF-S201',
        'descripcion': 'Flujo de agua a través del sistema de bombeo',
    },
    'nivel_estanque': {
        'nombre': 'Nivel del Estanque',
        'unidad': '%',
        'icono': '🪣',
        'min_val': 0.0,
        'max_val': 100.0,
        'step': '0.5',
        'hardware_default': 'Sensor Ultrasónico HC-SR04 / Nivel Líquido',
        'descripcion': 'Porcentaje de volumen de agua en el estanque (0% a 100%)',
    },
    'co2': {
        'nombre': 'Dióxido de Carbono (CO₂)',
        'unidad': 'ppm',
        'icono': '🫧',
        'min_val': 0.0,
        'max_val': 5000.0,
        'step': '1.0',
        'hardware_default': 'Sensor NDIR MH-Z19B',
        'descripcion': 'Concentración de CO2 en el aire (partes por millón)',
    },
    'fotoperiodo': {
        'nombre': 'Fotoperiodo (Luz)',
        'unidad': 'h/día',
        'icono': '☀️',
        'min_val': 0.0,
        'max_val': 24.0,
        'step': '0.5',
        'hardware_default': 'Sensor de Luz / Timer LDR-ESP32',
        'descripcion': 'Horas de iluminación recibidas al día (0 a 24 horas)',
    },
    'temperatura': {
        'nombre': 'Temperatura General (Legado)',
        'unidad': '°C',
        'icono': '🌡️',
        'min_val': 0.0,
        'max_val': 60.0,
        'step': '0.1',
        'hardware_default': 'DHT22 / DS18B20',
        'descripcion': 'Sensor legado de temperatura general',
    },
}


class Instalacion(models.Model):
    # Se reemplaza el ID secuencial clásico por un UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    ubicacion = models.CharField(max_length=200)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Sensor(models.Model):
    # Restricción estricta de tipos permitidos (personalizados para hidroponía)
    TIPO_CHOICES = [
        ('temperatura_agua', 'Temperatura Solución/Agua (°C)'),
        ('temperatura_aire', 'Temperatura Aire/Ambiente (°C)'),
        ('humedad', 'Humedad Relativa (%)'),
        ('ph', 'Nivel de pH (pH)'),
        ('caudal', 'Caudal de Agua (L/min)'),
        ('nivel_estanque', 'Nivel del Estanque (%)'),
        ('co2', 'Dióxido de Carbono - CO2 (ppm)'),
        ('fotoperiodo', 'Fotoperiodo (horas/día)'),
        ('temperatura', 'Temperatura General (Legado)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='sensores')
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    modelo_hardware = models.CharField(max_length=100)
    activo = models.BooleanField(default=True, help_text="Indica si el sensor está siendo monitoreado activamente")

    def __str__(self):
        return f"{self.get_icono()} {self.get_tipo_display()} - {self.instalacion.nombre}"

    @property
    def info_catalogo(self):
        return SENSOR_CATALOGO.get(self.tipo, {
            'nombre': self.get_tipo_display(),
            'unidad': '',
            'icono': '📡',
            'min_val': 0.0,
            'max_val': 1000.0,
            'step': '0.1',
            'hardware_default': self.modelo_hardware,
            'descripcion': '',
        })

    def get_unidad(self):
        return self.info_catalogo.get('unidad', '')

    def get_icono(self):
        return self.info_catalogo.get('icono', '📡')


class Medicion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='mediciones')
    
    # Validación a nivel de base de datos (valores positivos o cero)
    valor = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0.0)]
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    estado_conexion = models.BooleanField(default=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sensor', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.sensor.tipo}: {self.valor}{self.sensor.get_unidad()} a las {self.timestamp}"


class ReglaAlerta(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='reglas')
    limite_minimo = models.FloatField(null=True, blank=True, help_text="Avisa si baja de este valor")
    limite_maximo = models.FloatField(null=True, blank=True, help_text="Avisa si sube de este valor")
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"Regla para {self.sensor}"


class AlertaGenerada(models.Model):
    regla = models.ForeignKey(ReglaAlerta, on_delete=models.CASCADE)
    medicion = models.ForeignKey('Medicion', on_delete=models.CASCADE)
    mensaje = models.CharField(max_length=200)
    leida = models.BooleanField(default=False)
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.fecha_generacion.strftime('%H:%M:%S')}] {self.mensaje}"


# ============================================================
# GESTIÓN EXPLÍCITA DE SENSORES
# ============================================================
def asegurar_sensores_estandar(instalacion):
    """
    Función legada; ahora los sensores se configuran exclusivamente
    según la elección del usuario en el formulario del huerto.
    """
    pass

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
import uuid

# ============================================================
# CATÁLOGO MAESTRO DE SENSORES Y PARÁMETROS HIDROPÓNICOS
# ============================================================
SENSOR_CATALOGO = {
    'temperatura_agua': {
        'nombre': 'Temperatura del Agua / Solución',
        'unidad': '°C',
        'icono': '',
        'min_val': 0.0,
        'max_val': 50.0,
        'step': '0.1',
        'hardware_default': 'Sonda Sumergible DS18B20',
        'descripcion': 'Temperatura de la solución nutritiva en el estanque',
    },
    'temperatura_aire': {
        'nombre': 'Temperatura del Aire / Ambiente',
        'unidad': '°C',
        'icono': '',
        'min_val': 0.0,
        'max_val': 60.0,
        'step': '0.1',
        'hardware_default': 'Sensor Ambiental DHT22 / BME280',
        'descripcion': 'Temperatura ambiental del invernadero o cultivo',
    },
    'humedad': {
        'nombre': 'Humedad Ambiental',
        'unidad': '%',
        'icono': '',
        'min_val': 0.0,
        'max_val': 100.0,
        'step': '0.1',
        'hardware_default': 'Sensor de Humedad DHT22',
        'descripcion': 'Humedad relativa del aire (0% a 100%)',
    },
    'ph': {
        'nombre': 'Nivel de pH',
        'unidad': 'pH',
        'icono': '',
        'min_val': 0.0,
        'max_val': 14.0,
        'step': '0.01',
        'hardware_default': 'Sonda pH Analógica V1.1',
        'descripcion': 'Acidez/alcalinidad de la solución nutritiva (0 a 14)',
    },
    'caudal': {
        'nombre': 'Caudal de Agua',
        'unidad': 'L/min',
        'icono': '',
        'min_val': 0.0,
        'max_val': 50.0,
        'step': '0.1',
        'hardware_default': 'Flujómetro YF-S201',
        'descripcion': 'Flujo de agua a través del sistema de bombeo',
    },
    'nivel_estanque': {
        'nombre': 'Nivel del Estanque',
        'unidad': '%',
        'icono': '',
        'min_val': 0.0,
        'max_val': 100.0,
        'step': '0.5',
        'hardware_default': 'Sensor Ultrasónico HC-SR04 / Nivel Líquido',
        'descripcion': 'Porcentaje de volumen de agua en el estanque (0% a 100%)',
    },
    'co2': {
        'nombre': 'Dióxido de Carbono (CO₂)',
        'unidad': 'ppm',
        'icono': '',
        'min_val': 0.0,
        'max_val': 5000.0,
        'step': '1.0',
        'hardware_default': 'Sensor NDIR MH-Z19B',
        'descripcion': 'Concentración de CO2 en el aire (partes por millón)',
    },
    'fotoperiodo': {
        'nombre': 'Fotoperiodo (Luz)',
        'unidad': 'h/día',
        'icono': '',
        'min_val': 0.0,
        'max_val': 24.0,
        'step': '0.5',
        'hardware_default': 'Sensor de Luz / Timer LDR-ESP32',
        'descripcion': 'Horas de iluminación recibidas al día (0 a 24 horas)',
    },
    'humedad_sustrato': {
        'nombre': 'Humedad de Sustrato / Raíz',
        'unidad': '%',
        'icono': '',
        'min_val': 0.0,
        'max_val': 100.0,
        'step': '0.5',
        'hardware_default': 'Sensor Capacitivo Sustrato v1.2',
        'descripcion': 'Humedad retenida en la zona radicular de la planta (0% a 100%)',
    },
    'ph_sustrato': {
        'nombre': 'pH de Raíz / Sustrato',
        'unidad': 'pH',
        'icono': '',
        'min_val': 0.0,
        'max_val': 14.0,
        'step': '0.01',
        'hardware_default': 'Sonda pH Sustrato Micro',
        'descripcion': 'Acidez/alcalinidad medida directamente en la zona radicular (0 a 14)',
    },
    'temperatura_raiz': {
        'nombre': 'Temperatura de Raíz',
        'unidad': '°C',
        'icono': '',
        'min_val': 0.0,
        'max_val': 50.0,
        'step': '0.1',
        'hardware_default': 'Sonda DS18B20 Raíz',
        'descripcion': 'Temperatura en la zona de raíces de la planta',
    },
    'temperatura': {
        'nombre': 'Temperatura General (Legado)',
        'unidad': '°C',
        'icono': '',
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
    encargados = models.ManyToManyField(
        User,
        blank=True,
        related_name='instalaciones_asignadas',
        help_text="Usuarios (Encargados de cultivo / Supervisores) autorizados para esta instalación",
    )

    def __str__(self):
        return self.nombre


class Planta(models.Model):
    ETAPA_CHOICES = [
        ('germinacion', 'Germinación'),
        ('vegetativo', 'Crecimiento Vegetativo'),
        ('floracion', 'Floración / Desarrollo'),
        ('cosecha', 'Lista para Cosecha'),
    ]
    CICLO_DIAS_DEFAULT = 45

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='plantas')
    codigo = models.CharField(max_length=80)
    especie = models.CharField(max_length=100)
    variedad = models.CharField(max_length=100, blank=True)
    posicion = models.CharField(max_length=50, blank=True)
    fecha_siembra = models.DateField(default=timezone.localdate)
    etapa = models.CharField(max_length=20, choices=ETAPA_CHOICES, default='germinacion')
    activa = models.BooleanField(default=True)
    notas = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['posicion', 'codigo']
        unique_together = [('instalacion', 'codigo')]

    def __str__(self):
        return f"{self.codigo} ({self.especie}) - {self.instalacion.nombre}"

    @property
    def dias_desde_siembra(self):
        return max(0, (timezone.localdate() - self.fecha_siembra).days)

    @property
    def dias_para_cosecha(self):
        if self.etapa == 'cosecha':
            return 0
        return max(0, self.CICLO_DIAS_DEFAULT - self.dias_desde_siembra)


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
        ('humedad_sustrato', 'Humedad de Sustrato / Raíz (%)'),
        ('ph_sustrato', 'pH de Raíz / Sustrato (pH)'),
        ('temperatura_raiz', 'Temperatura de Raíz (°C)'),
        ('temperatura', 'Temperatura General (Legado)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='sensores')
    planta = models.ForeignKey(
        Planta,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='sensores',
        help_text="Si está asignado, el sensor mide específicamente a esta planta; si es nulo, es sensor ambiental.",
    )
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    modelo_hardware = models.CharField(max_length=100)
    activo = models.BooleanField(default=True, help_text="Indica si el sensor está siendo monitoreado activamente")

    def __str__(self):
        if self.planta_id:
            return f"{self.get_tipo_display()} - {self.planta.codigo} ({self.instalacion.nombre})"
        return f"{self.get_tipo_display()} - {self.instalacion.nombre}"

    @property
    def info_catalogo(self):
        return SENSOR_CATALOGO.get(self.tipo, {
            'nombre': self.get_tipo_display(),
            'unidad': '',
            'icono': '',
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

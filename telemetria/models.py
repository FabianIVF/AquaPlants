from django.db import models
from django.core.validators import MinValueValidator
import uuid

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
    # Restricción estricta de tipos permitidos
    TIPO_CHOICES = [
        ('temperatura', 'Temperatura'),
        ('humedad', 'Humedad'),
        ('ph', 'Nivel de pH'),
        ('caudal', 'Caudal de agua'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instalacion = models.ForeignKey(Instalacion, on_delete=models.CASCADE, related_name='sensores')
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES) # choices para limitar las opciones y proteger de inyecciones SQL
    modelo_hardware = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.tipo} - {self.instalacion.nombre}"

class Medicion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='mediciones')
    
    # Validación a nivel de base de datos
    valor = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0.0)] # Asegura que el valor minimo sea 0.0
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    estado_conexion = models.BooleanField(default=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sensor', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.sensor.tipo}: {self.valor} a las {self.timestamp}"

class ReglaAlerta(models.Model):
    # Conectamos la regla a un sensor específico
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='reglas')
    limite_minimo = models.FloatField(null=True, blank=True, help_text="Avisa si baja de este valor")
    limite_maximo = models.FloatField(null=True, blank=True, help_text="Avisa si sube de este valor")
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"Regla de alerta para el sensor: {self.sensor}"

class AlertaGenerada(models.Model):
    # Guardamos qué regla se rompió y con qué medición exacta
    regla = models.ForeignKey(ReglaAlerta, on_delete=models.CASCADE)
    medicion = models.ForeignKey('Medicion', on_delete=models.CASCADE)
    mensaje = models.CharField(max_length=200)
    leida = models.BooleanField(default=False) # Para que el usuario pueda marcarla como "vista"
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.fecha_generacion.strftime('%H:%M:%S')}] {self.mensaje}"
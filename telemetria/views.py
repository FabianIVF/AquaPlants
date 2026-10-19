from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from .models import Instalacion, Sensor, Medicion, ReglaAlerta, AlertaGenerada
from .serializers import InstalacionSerializer, SensorSerializer, MedicionSerializer


class InstalacionViewSet(viewsets.ModelViewSet):
    queryset = Instalacion.objects.all()
    serializer_class = InstalacionSerializer
    # Políticas de seguridad aplicadas a la ruta
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class SensorViewSet(viewsets.ModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class MedicionViewSet(viewsets.ModelViewSet):
    # Por defecto ordenamos las mediciones desde la más reciente
    queryset = Medicion.objects.all().order_by('-timestamp')
    serializer_class = MedicionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def perform_create(self, serializer):
        medicion_guardada = serializer.save()

        reglas = ReglaAlerta.objects.filter(sensor=medicion_guardada.sensor, activa=True)

        for regla in reglas:
            mensaje_alerta = None

            if regla.limite_maximo is not None and medicion_guardada.valor > regla.limite_maximo:
                mensaje_alerta = f"¡ALERTA ROJA! Temperatura ALTA: {medicion_guardada.valor}°C (Límite: {regla.limite_maximo}°C)"

            elif regla.limite_minimo is not None and medicion_guardada.valor < regla.limite_minimo:
                mensaje_alerta = f"¡ALERTA AZUL! Temperatura BAJA: {medicion_guardada.valor}°C (Límite: {regla.limite_minimo}°C)"

            if mensaje_alerta:
                AlertaGenerada.objects.create(
                    regla=regla,
                    medicion=medicion_guardada,
                    mensaje=mensaje_alerta
                )
        # ------------------------
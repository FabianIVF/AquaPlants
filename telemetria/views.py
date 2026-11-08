from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from .models import Instalacion, Sensor, Medicion, ReglaAlerta, AlertaGenerada
from .serializers import InstalacionSerializer, SensorSerializer, MedicionSerializer


class InstalacionViewSet(viewsets.ModelViewSet):
    queryset = Instalacion.objects.all()
    serializer_class = InstalacionSerializer
    # Políticas de seguridad aplicadas a la ruta
    permission_classes = [IsAuthenticated, DjangoModelPermissions]


class SensorViewSet(viewsets.ModelViewSet):
    serializer_class = SensorSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    queryset = Sensor.objects.select_related('instalacion').all()

    def get_queryset(self):
        """
        Filtros opcionales por query string (usados por el simulador IoT):
          ?instalacion=<uuid>   -> sensores de una instalación
          ?activo=true|false    -> solo sensores monitoreados / desactivados
        """
        qs = super().get_queryset()
        instalacion = self.request.query_params.get('instalacion')
        activo = self.request.query_params.get('activo')
        if instalacion:
            qs = qs.filter(instalacion_id=instalacion)
        if activo is not None:
            qs = qs.filter(activo=activo.lower() in ('true', '1', 'si'))
        return qs


class MedicionViewSet(viewsets.ModelViewSet):
    # Por defecto ordenamos las mediciones desde la más reciente
    queryset = Medicion.objects.select_related('sensor__instalacion').order_by('-timestamp')
    serializer_class = MedicionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def create(self, request, *args, **kwargs):
        """
        Igual que el create estándar, pero la respuesta incluye el campo
        'alerta' con las alertas generadas por esta medición (o null).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alertas = self.perform_create(serializer)
        data = dict(serializer.data)
        data['alerta'] = alertas[0] if len(alertas) == 1 else (alertas or None)
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        medicion_guardada = serializer.save()
        sensor = medicion_guardada.sensor

        # Si el dispositivo reporta fallo de conexión, el valor no es confiable:
        # se guarda para trazabilidad pero NO se evalúan reglas (evita falsas alertas)
        if not medicion_guardada.estado_conexion:
            return []

        reglas = ReglaAlerta.objects.filter(sensor=sensor, activa=True)

        unidad = sensor.get_unidad()
        # Las unidades con símbolo pegado (°C, %) no llevan espacio
        unidad_str = unidad if unidad.startswith(('°', '%')) else f" {unidad}"
        nombre_sensor = sensor.info_catalogo.get('nombre', sensor.get_tipo_display())

        alertas = []
        for regla in reglas:
            mensaje_alerta = None

            if regla.limite_maximo is not None and medicion_guardada.valor > regla.limite_maximo:
                mensaje_alerta = f"¡ALERTA ROJA! {nombre_sensor} ALTO: {medicion_guardada.valor}{unidad_str} (Límite: {regla.limite_maximo}{unidad_str})"

            elif regla.limite_minimo is not None and medicion_guardada.valor < regla.limite_minimo:
                mensaje_alerta = f"¡ALERTA AZUL! {nombre_sensor} BAJO: {medicion_guardada.valor}{unidad_str} (Límite: {regla.limite_minimo}{unidad_str})"

            if mensaje_alerta:
                AlertaGenerada.objects.create(
                    regla=regla,
                    medicion=medicion_guardada,
                    mensaje=mensaje_alerta[:200]
                )
                alertas.append(mensaje_alerta)
        return alertas

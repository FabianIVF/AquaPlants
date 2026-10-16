from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InstalacionViewSet, SensorViewSet, MedicionViewSet

# El enrutador automático de Django REST Framework
router = DefaultRouter()
router.register(r'instalaciones', InstalacionViewSet)
router.register(r'sensores', SensorViewSet)
router.register(r'mediciones', MedicionViewSet)

urlpatterns = [
    # Incluimos todas las rutas generadas automáticamente por el router
    path('', include(router.urls)),
]
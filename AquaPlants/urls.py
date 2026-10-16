from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Esta es la línea que falta para conectar tus rutas
    path('api/', include('telemetria.urls')),
    path('dashboard/', include('dashboard.urls')),
]
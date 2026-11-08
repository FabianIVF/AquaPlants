from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import logout
from django.shortcuts import redirect


def cerrar_sesion(request):
    """Cierra la sesión del usuario (acepta GET y POST en Django 4 y 5+) y redirige al login."""
    logout(request)
    return redirect('login')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('telemetria.urls')),
    path('dashboard/', include('dashboard.urls')),
    # Redirige la raíz "/" al dashboard automáticamente
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    # Logout propio del dashboard compatible con enlaces GET y formularios POST
    path('logout/', cerrar_sesion, name='logout'),
]

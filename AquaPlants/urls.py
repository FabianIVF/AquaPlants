from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('telemetria.urls')),
    path('dashboard/', include('dashboard.urls')),
    # Redirige la raíz "/" al dashboard automáticamente
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    # Logout propio del dashboard (soluciona el error de /admin/logout/)
    path('logout/', auth_views.LogoutView.as_view(next_page='/dashboard/login/'), name='logout'),
]

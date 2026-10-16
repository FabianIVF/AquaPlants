from django.urls import path
from . import views

urlpatterns = [
    # Agregamos la ruta del login al principio
    path('login/', views.user_login, name='login'),
    path('', views.inicio_dashboard, name='inicio_dashboard'),
    path('instalacion/<str:instalacion_id>/', views.detalle_instalacion, name='detalle_instalacion'),
]

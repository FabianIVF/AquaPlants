from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('', views.inicio_dashboard, name='inicio_dashboard'),
    
    # CRUD Instalaciones
    path('instalacion/crear/', views.crear_instalacion, name='crear_instalacion'),
    path('instalacion/<str:instalacion_id>/', views.detalle_instalacion, name='detalle_instalacion'),
    path('instalacion/<str:instalacion_id>/editar/', views.editar_instalacion, name='editar_instalacion'),
    path('instalacion/<str:instalacion_id>/eliminar/', views.eliminar_instalacion, name='eliminar_instalacion'),
    
    # CRUD Reglas de Alerta
    path('instalacion/<str:instalacion_id>/regla/crear/', views.crear_regla, name='crear_regla'),
    path('regla/<int:regla_id>/editar/', views.editar_regla, name='editar_regla'),
    path('regla/<int:regla_id>/eliminar/', views.eliminar_regla, name='eliminar_regla'),
    
    # API Live
    path('instalacion/<str:instalacion_id>/live/', views.api_telemetria_live, name='api_telemetria_live'),
    path('instalacion/<str:instalacion_id>/historial/', views.historial_instalacion, name='historial_instalacion'),
]

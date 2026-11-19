from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('', views.inicio_dashboard, name='inicio_dashboard'),

    # CRUD Usuarios y Asignación de Instalaciones (Solo Administrador)
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:user_id>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:user_id>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),

    # CRUD Instalaciones
    path('instalacion/crear/', views.crear_instalacion, name='crear_instalacion'),
    path('instalacion/<str:instalacion_id>/', views.detalle_instalacion, name='detalle_instalacion'),
    path('instalacion/<str:instalacion_id>/editar/', views.editar_instalacion, name='editar_instalacion'),
    path('instalacion/<str:instalacion_id>/eliminar/', views.eliminar_instalacion, name='eliminar_instalacion'),

    # Plantas por Instalación (CRUD + Telemetría en vivo individual)
    path('instalacion/<str:instalacion_id>/plantas/', views.lista_plantas, name='lista_plantas'),
    path('instalacion/<str:instalacion_id>/plantas/crear/', views.crear_planta, name='crear_planta'),
    path('instalacion/<str:instalacion_id>/plantas/<str:planta_id>/', views.detalle_planta, name='detalle_planta'),
    path(
        'instalacion/<str:instalacion_id>/plantas/<str:planta_id>/live/',
        views.api_planta_live,
        name='api_planta_live',
    ),
    path('instalacion/<str:instalacion_id>/plantas/<str:planta_id>/editar/', views.editar_planta, name='editar_planta'),
    path(
        'instalacion/<str:instalacion_id>/plantas/<str:planta_id>/eliminar/',
        views.eliminar_planta,
        name='eliminar_planta',
    ),

    # CRUD Reglas de Alerta
    path('instalacion/<str:instalacion_id>/regla/crear/', views.crear_regla, name='crear_regla'),
    path('regla/<int:regla_id>/editar/', views.editar_regla, name='editar_regla'),
    path('regla/<int:regla_id>/eliminar/', views.eliminar_regla, name='eliminar_regla'),

    # API Live e Historial
    path('instalacion/<str:instalacion_id>/live/', views.api_telemetria_live, name='api_telemetria_live'),
    path('instalacion/<str:instalacion_id>/historial/', views.historial_instalacion, name='historial_instalacion'),
]

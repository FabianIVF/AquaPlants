from telemetria.models import AlertaGenerada, Instalacion


def alertas_globales(request):
    """Expone el conteo de alertas sin leer autorizadas para el usuario en la barra de navegación."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'global_num_alertas': 0}

    if user.is_superuser or user.groups.filter(name='Administrador').exists():
        instalaciones = Instalacion.objects.all()
    else:
        instalaciones = user.instalaciones_asignadas.all()

    total = AlertaGenerada.objects.filter(
        regla__sensor__instalacion__in=instalaciones,
        leida=False,
    ).count()
    return {'global_num_alertas': total}

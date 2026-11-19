from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from telemetria.models import AlertaGenerada, Instalacion, Medicion, Planta, ReglaAlerta, Sensor
from .analytics import resumen_sensores
from .forms import InstalacionForm, PlantaForm, ReglaAlertaForm, UsuarioForm


# ============================================================
# HELPERS DE AUTORIZACIÓN Y ANALÍTICA COMPARTIDA
# ============================================================

def _es_admin(user):
    return user.is_superuser or user.groups.filter(name='Administrador').exists()


def _requiere_admin(user):
    if not (_es_admin(user) or user.has_perm('auth.view_user')):
        raise PermissionDenied


def _instalaciones_autorizadas(user):
    qs = Instalacion.objects.all().order_by('-fecha_creacion')
    if _es_admin(user):
        return qs
    return qs.filter(encargados=user)


def _obtener_instalacion_autorizada(user, instalacion_id):
    instalacion = get_object_or_404(Instalacion, pk=instalacion_id)
    if not _es_admin(user) and not instalacion.encargados.filter(pk=user.pk).exists():
        raise PermissionDenied
    return instalacion


def _construir_payload_live(sensores, nombre_objetivo):
    """Construye el JSON en vivo compartido por el panel de instalación y el de planta."""
    sensores_list = list(sensores)
    datos_sensores = {}
    for sensor in sensores_list:
        mediciones_qs = list(
            Medicion.objects
            .filter(sensor=sensor)
            .order_by('-timestamp')
            .values('valor', 'timestamp', 'estado_conexion')[:20]
        )
        mediciones_qs.reverse()

        datos_sensores[sensor.tipo] = {
            "id": str(sensor.id),
            "mediciones": [
                {
                    "valor": float(m["valor"]),
                    "timestamp": timezone.localtime(m["timestamp"]).strftime("%H:%M:%S"),
                    "timestamp_iso": timezone.localtime(m["timestamp"]).isoformat(),
                    "estado_conexion": m["estado_conexion"],
                }
                for m in mediciones_qs
            ],
        }

    alertas_qs = (
        AlertaGenerada.objects
        .filter(regla__sensor__in=sensores_list, leida=False)
        .order_by('-fecha_generacion')[:5]
        .values('mensaje', 'fecha_generacion', 'leida')
    )
    alertas = [
        {
            "mensaje": a["mensaje"],
            "hora": timezone.localtime(a["fecha_generacion"]).strftime("%H:%M:%S"),
            "leida": a["leida"],
        }
        for a in alertas_qs
    ]

    resumen = resumen_sensores(sensores_list)
    return {
        "instalacion": nombre_objetivo,
        "sensores": datos_sensores,
        "alertas": alertas,
        "num_alertas": len(alertas),
        "resumen": {
            "estado": resumen["estado"],
            "estado_label": resumen["estado_label"],
            "estado_css": resumen["estado_css"],
            "porcentaje_en_rango": resumen["porcentaje_en_rango"],
            "tendencia": resumen["tendencia"],
            "recomendaciones": resumen["recomendaciones"],
        },
    }


# ============================================================
# AUTENTICACIÓN E INICIO
# ============================================================

def user_login(request):
    if request.user.is_authenticated:
        return redirect('inicio_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.cleaned_data.get('username')
            contrasena = form.cleaned_data.get('password')
            user = authenticate(username=usuario, password=contrasena)
            if user is not None:
                login(request, user)
                return redirect('inicio_dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'dashboard/login.html', {'form': form})


@login_required(login_url='login')
def inicio_dashboard(request):
    instalaciones = list(_instalaciones_autorizadas(request.user))
    alertas_no_leidas = AlertaGenerada.objects.filter(
        regla__sensor__instalacion__in=instalaciones, leida=False
    ).order_by('-fecha_generacion')[:5]
    cantidad_alertas = AlertaGenerada.objects.filter(
        regla__sensor__instalacion__in=instalaciones, leida=False
    ).count()

    tarjetas = []
    total_plantas = 0
    plantas_en_riesgo = 0

    for inst in instalaciones:
        sensores_amb = inst.sensores.filter(activo=True, planta__isnull=True)
        resumen_amb = resumen_sensores(sensores_amb)
        plantas = list(inst.plantas.filter(activa=True))
        total_plantas += len(plantas)

        riesgo_inst = 0
        for p in plantas:
            res_p = resumen_sensores(p.sensores.filter(activo=True))
            if res_p['estado'] in ('atencion', 'critico'):
                riesgo_inst += 1
        plantas_en_riesgo += riesgo_inst

        alertas_inst = AlertaGenerada.objects.filter(
            regla__sensor__instalacion=inst, leida=False
        ).count()

        tarjetas.append({
            'instalacion': inst,
            'resumen': resumen_amb,
            'num_plantas': len(plantas),
            'plantas_riesgo': riesgo_inst,
            'num_alertas': alertas_inst,
        })

    contexto = {
        'instalaciones': instalaciones,
        'tarjetas': tarjetas,
        'total_instalaciones': len(instalaciones),
        'total_plantas': total_plantas,
        'plantas_en_riesgo': plantas_en_riesgo,
        'usuario': request.user,
        'es_admin': _es_admin(request.user),
        'alertas': alertas_no_leidas,
        'num_alertas': cantidad_alertas,
    }
    return render(request, 'dashboard/inicio.html', contexto)


@login_required(login_url='login')
def detalle_instalacion(request, instalacion_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    sensores = list(Sensor.objects.filter(instalacion=instalacion, activo=True, planta__isnull=True))
    reglas = ReglaAlerta.objects.filter(sensor__instalacion=instalacion).select_related('sensor', 'sensor__planta')
    resumen = resumen_sensores(sensores)
    plantas = list(instalacion.plantas.filter(activa=True)[:4])
    num_plantas = instalacion.plantas.count()

    contexto = {
        'instalacion': instalacion,
        'sensores': sensores,
        'reglas': reglas,
        'resumen': resumen,
        'plantas_destacadas': plantas,
        'num_plantas': num_plantas,
        'tab_activa': 'panel',
        'usuario': request.user,
    }
    return render(request, 'dashboard/detalle.html', contexto)


# ============================================================
# CRUD: INSTALACIONES (Protegido por permisos RBAC)
# ============================================================

@login_required(login_url='login')
@permission_required('telemetria.add_instalacion', raise_exception=True)
def crear_instalacion(request):
    if request.method == 'POST':
        form = InstalacionForm(request.POST)
        if form.is_valid():
            nueva = form.save()
            messages.success(request, f'Instalación "{nueva.nombre}" creada exitosamente y variables configuradas.')
            return redirect('inicio_dashboard')
    else:
        form = InstalacionForm()

    contexto = {
        'form': form,
        'titulo': 'Nueva Instalación de Cultivo',
        'descripcion': 'Registra un nuevo sistema o huerto vertical para comenzar a recibir telemetría.',
        'volver_url': reverse('inicio_dashboard'),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.change_instalacion', raise_exception=True)
def editar_instalacion(request, instalacion_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    if request.method == 'POST':
        form = InstalacionForm(request.POST, instance=instalacion)
        if form.is_valid():
            form.save()
            messages.success(request, f'Instalación "{instalacion.nombre}" actualizada con éxito.')
            return redirect('detalle_instalacion', instalacion_id=instalacion.pk)
    else:
        form = InstalacionForm(instance=instalacion)

    contexto = {
        'form': form,
        'instalacion': instalacion,
        'tab_activa': 'configuracion',
        'titulo': f'Configuración: {instalacion.nombre}',
        'descripcion': 'Actualiza los datos del sistema y selecciona qué sensores ambientales deseas vigilar.',
        'volver_url': reverse('detalle_instalacion', kwargs={'instalacion_id': instalacion.pk}),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.delete_instalacion', raise_exception=True)
def eliminar_instalacion(request, instalacion_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    if request.method == 'POST':
        nombre = instalacion.nombre
        instalacion.delete()
        messages.success(request, f'Instalación "{nombre}" eliminada correctamente.')
        return redirect('inicio_dashboard')

    contexto = {
        'elemento': f'la instalación "{instalacion.nombre}" y todos sus sensores y plantas vinculados',
        'volver_url': reverse('inicio_dashboard'),
    }
    return render(request, 'dashboard/confirmar_eliminar.html', contexto)


# ============================================================
# PLANTAS POR INSTALACIÓN (CRUD + Panel en vivo individual)
# ============================================================

@login_required(login_url='login')
def lista_plantas(request, instalacion_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    plantas = Planta.objects.filter(instalacion=instalacion)

    fichas = []
    for planta in plantas:
        sensores = planta.sensores.filter(activo=True)
        resumen = resumen_sensores(sensores)
        fichas.append({
            'planta': planta,
            'resumen': resumen,
            'num_sensores': sensores.count(),
        })

    contexto = {
        'instalacion': instalacion,
        'fichas': fichas,
        'tab_activa': 'plantas',
        'usuario': request.user,
    }
    return render(request, 'dashboard/plantas_lista.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.add_planta', raise_exception=True)
def crear_planta(request, instalacion_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    if request.method == 'POST':
        form = PlantaForm(request.POST, instalacion=instalacion)
        if form.is_valid():
            planta = form.save()
            messages.success(request, f'Planta "{planta.codigo}" registrada con sus sensores propios.')
            return redirect('lista_plantas', instalacion_id=instalacion.pk)
    else:
        form = PlantaForm(instalacion=instalacion)

    contexto = {
        'form': form,
        'instalacion': instalacion,
        'tab_activa': 'plantas',
        'titulo': f'Nueva Planta — {instalacion.nombre}',
        'descripcion': 'Registra una planta individual y selecciona los sensores dedicados para su monitoreo.',
        'volver_url': reverse('lista_plantas', kwargs={'instalacion_id': instalacion.pk}),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.change_planta', raise_exception=True)
def editar_planta(request, instalacion_id, planta_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    planta = get_object_or_404(Planta, pk=planta_id, instalacion=instalacion)
    if request.method == 'POST':
        form = PlantaForm(request.POST, instance=planta, instalacion=instalacion)
        if form.is_valid():
            form.save()
            messages.success(request, f'Planta "{planta.codigo}" actualizada correctamente.')
            return redirect('detalle_planta', instalacion_id=instalacion.pk, planta_id=planta.pk)
    else:
        form = PlantaForm(instance=planta, instalacion=instalacion)

    contexto = {
        'form': form,
        'instalacion': instalacion,
        'tab_activa': 'plantas',
        'titulo': f'Editar Planta: {planta.codigo}',
        'descripcion': 'Actualiza la etapa de crecimiento, posición o sensores propios de esta planta.',
        'volver_url': reverse('detalle_planta', kwargs={'instalacion_id': instalacion.pk, 'planta_id': planta.pk}),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.delete_planta', raise_exception=True)
def eliminar_planta(request, instalacion_id, planta_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    planta = get_object_or_404(Planta, pk=planta_id, instalacion=instalacion)
    if request.method == 'POST':
        codigo = planta.codigo
        planta.delete()
        messages.success(request, f'Planta "{codigo}" eliminada del monitoreo.')
        return redirect('lista_plantas', instalacion_id=instalacion.pk)

    contexto = {
        'elemento': f'la planta "{planta.codigo}" ({planta.especie}) y sus sensores vinculados',
        'volver_url': reverse('lista_plantas', kwargs={'instalacion_id': instalacion.pk}),
    }
    return render(request, 'dashboard/confirmar_eliminar.html', contexto)


@login_required(login_url='login')
def detalle_planta(request, instalacion_id, planta_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    planta = get_object_or_404(Planta, pk=planta_id, instalacion=instalacion)
    sensores = list(planta.sensores.filter(activo=True))
    resumen = resumen_sensores(sensores)
    reglas = ReglaAlerta.objects.filter(sensor__in=sensores).select_related('sensor')

    contexto = {
        'instalacion': instalacion,
        'planta': planta,
        'sensores': sensores,
        'resumen': resumen,
        'reglas': reglas,
        'tab_activa': 'plantas',
        'usuario': request.user,
    }
    return render(request, 'dashboard/planta_detalle.html', contexto)


@login_required(login_url='login')
def api_planta_live(request, instalacion_id, planta_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    planta = get_object_or_404(Planta, pk=planta_id, instalacion=instalacion)
    sensores = planta.sensores.filter(activo=True)
    return JsonResponse(_construir_payload_live(sensores, f"{instalacion.nombre} · {planta.codigo}"))


# ============================================================
# CRUD: REGLAS DE ALERTA (Protegido por permisos RBAC)
# ============================================================

@login_required(login_url='login')
@permission_required('telemetria.add_reglaalerta', raise_exception=True)
def crear_regla(request, instalacion_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    if request.method == 'POST':
        form = ReglaAlertaForm(request.POST, instalacion=instalacion)
        if form.is_valid():
            regla = form.save()
            messages.success(request, f'Regla de alerta creada para el sensor {regla.sensor.tipo}.')
            return redirect('detalle_instalacion', instalacion_id=instalacion.pk)
    else:
        form = ReglaAlertaForm(instalacion=instalacion)

    contexto = {
        'form': form,
        'instalacion': instalacion,
        'tab_activa': 'reglas',
        'titulo': f'Configurar Regla de Alerta — {instalacion.nombre}',
        'descripcion': 'Establece límites para disparo automático de alertas (Rojas para excesos, Azules para caídas).',
        'volver_url': reverse('detalle_instalacion', kwargs={'instalacion_id': instalacion.pk}),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.change_reglaalerta', raise_exception=True)
def editar_regla(request, regla_id):
    regla = get_object_or_404(ReglaAlerta, pk=regla_id)
    instalacion = _obtener_instalacion_autorizada(request.user, regla.sensor.instalacion_id)
    if request.method == 'POST':
        form = ReglaAlertaForm(request.POST, instance=regla, instalacion=instalacion)
        if form.is_valid():
            form.save()
            messages.success(request, f'Regla de alerta actualizada para {regla.sensor.tipo}.')
            return redirect('detalle_instalacion', instalacion_id=instalacion.pk)
    else:
        form = ReglaAlertaForm(instance=regla, instalacion=instalacion)

    contexto = {
        'form': form,
        'instalacion': instalacion,
        'tab_activa': 'reglas',
        'titulo': f'Editar Regla — {regla.sensor.tipo} ({instalacion.nombre})',
        'descripcion': 'Ajusta los umbrales de advertencia.',
        'volver_url': reverse('detalle_instalacion', kwargs={'instalacion_id': instalacion.pk}),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.delete_reglaalerta', raise_exception=True)
def eliminar_regla(request, regla_id):
    regla = get_object_or_404(ReglaAlerta, pk=regla_id)
    instalacion = _obtener_instalacion_autorizada(request.user, regla.sensor.instalacion_id)
    if request.method == 'POST':
        sensor_tipo = regla.sensor.tipo
        regla.delete()
        messages.success(request, f'Regla de alerta para {sensor_tipo} eliminada.')
        return redirect('detalle_instalacion', instalacion_id=instalacion.pk)

    contexto = {
        'elemento': f'la regla de alerta para el sensor {regla.sensor.tipo}',
        'volver_url': reverse('detalle_instalacion', kwargs={'instalacion_id': instalacion.pk}),
    }
    return render(request, 'dashboard/confirmar_eliminar.html', contexto)


# ============================================================
# API LIVE TELEMETRY E HISTORIAL DE INSTALACIÓN
# ============================================================

@login_required(login_url='login')
def api_telemetria_live(request, instalacion_id):
    """
    Endpoint JSON que devuelve las últimas 20 mediciones por sensor ambiental,
    diagnóstico en vivo y las últimas 5 alertas no leídas de la instalación.
    """
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    sensores = Sensor.objects.filter(instalacion=instalacion, activo=True, planta__isnull=True)
    return JsonResponse(_construir_payload_live(sensores, instalacion.nombre))


@login_required(login_url='login')
def historial_instalacion(request, instalacion_id):
    """
    Vista de estados actuales (última medición por sensor) e histórico
    completo de las últimas 100 mediciones con filtro por tipo de sensor.
    """
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    sensores = list(Sensor.objects.filter(instalacion=instalacion, activo=True).select_related('planta'))

    estados_actuales = []
    for sensor in sensores:
        ultima = Medicion.objects.filter(sensor=sensor).order_by('-timestamp').first()
        estados_actuales.append({
            'sensor': sensor,
            'ultima_medicion': ultima,
        })

    filtro_tipo = request.GET.get('sensor', '')
    mediciones_qs = Medicion.objects.filter(sensor__in=sensores).select_related('sensor', 'sensor__planta')
    if filtro_tipo:
        mediciones_qs = mediciones_qs.filter(sensor__tipo=filtro_tipo)
    historico = mediciones_qs.order_by('-timestamp')[:100]

    total_alertas = AlertaGenerada.objects.filter(regla__sensor__in=sensores).count()
    alertas_sin_leer = AlertaGenerada.objects.filter(regla__sensor__in=sensores, leida=False).count()
    tipos_sensor = sorted({s.tipo for s in sensores})

    contexto = {
        'instalacion': instalacion,
        'estados_actuales': estados_actuales,
        'historico': historico,
        'filtro_tipo': filtro_tipo,
        'tipos_sensor': tipos_sensor,
        'total_alertas': total_alertas,
        'alertas_sin_leer': alertas_sin_leer,
        'tab_activa': 'historial',
        'usuario': request.user,
    }
    return render(request, 'dashboard/historial.html', contexto)


# ============================================================
# CRUD: USUARIOS Y ASIGNACIÓN A INSTALACIONES (Solo Admin)
# ============================================================

@login_required(login_url='login')
def lista_usuarios(request):
    _requiere_admin(request.user)
    usuarios = User.objects.prefetch_related('groups', 'instalaciones_asignadas').order_by('username')

    filas = []
    for u in usuarios:
        rol = u.groups.first().name if u.groups.exists() else ('Superusuario' if u.is_superuser else 'Sin rol')
        filas.append({
            'obj': u,
            'rol': rol,
            'instalaciones': list(u.instalaciones_asignadas.all()),
        })

    return render(request, 'dashboard/usuarios_lista.html', {'filas': filas, 'es_admin': True})


@login_required(login_url='login')
def crear_usuario(request):
    _requiere_admin(request.user)
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            nuevo = form.save()
            messages.success(request, f'Usuario "{nuevo.username}" creado y asignado correctamente.')
            return redirect('lista_usuarios')
    else:
        form = UsuarioForm()

    contexto = {
        'form': form,
        'titulo': 'Nuevo Usuario',
        'descripcion': 'Crea una cuenta, asigna su rol de acceso y elige qué instalaciones podrá gestionar o ver.',
        'volver_url': reverse('lista_usuarios'),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
def editar_usuario(request, user_id):
    _requiere_admin(request.user)
    usuario_obj = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario "{usuario_obj.username}" actualizado con éxito.')
            return redirect('lista_usuarios')
    else:
        form = UsuarioForm(instance=usuario_obj)

    contexto = {
        'form': form,
        'titulo': f'Editar Usuario: {usuario_obj.username}',
        'descripcion': 'Modifica el rol, las instalaciones asignadas o restablece la contraseña del usuario.',
        'volver_url': reverse('lista_usuarios'),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
def eliminar_usuario(request, user_id):
    _requiere_admin(request.user)
    usuario_obj = get_object_or_404(User, pk=user_id)
    if usuario_obj.pk == request.user.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta mientras tienes la sesión abierta.')
        return redirect('lista_usuarios')

    if request.method == 'POST':
        nombre = usuario_obj.username
        usuario_obj.delete()
        messages.success(request, f'Usuario "{nombre}" eliminado correctamente.')
        return redirect('lista_usuarios')

    contexto = {
        'elemento': f'al usuario "{usuario_obj.username}"',
        'volver_url': reverse('lista_usuarios'),
    }
    return render(request, 'dashboard/confirmar_eliminar.html', contexto)

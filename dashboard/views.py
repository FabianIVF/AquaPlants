from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from telemetria.models import AlertaGenerada, Instalacion, Invernadero, Medicion, Planta, ReglaAlerta, Sensor
from .analytics import ESTADO_META, resumen_planta, resumen_sensores
from .forms import InstalacionForm, InvernaderoForm, PlantaForm, ReglaAlertaForm, UsuarioForm


# ============================================================
# HELPERS DE AUTORIZACIÓN Y ANALÍTICA COMPARTIDA
# ============================================================

def _es_admin(user):
    return user.is_superuser or user.groups.filter(name='Administrador').exists()


def _requiere_admin(user):
    if not (_es_admin(user) or user.has_perm('auth.view_user')):
        raise PermissionDenied


def _instalaciones_autorizadas(user):
    qs = Instalacion.objects.select_related('invernadero').all().order_by('-fecha_creacion')
    if _es_admin(user):
        return qs
    return qs.filter(encargados=user)


def _construir_tarjeta_instalacion(inst):
    sensores_amb = inst.sensores.filter(activo=True, planta__isnull=True)
    resumen_amb = resumen_sensores(sensores_amb)
    plantas = list(inst.plantas.filter(activa=True))

    riesgo_inst = 0
    for p in plantas:
        res_p = resumen_planta(p)
        if res_p['estado'] in ('atencion', 'critico'):
            riesgo_inst += 1

    alertas_inst = AlertaGenerada.objects.filter(
        regla__sensor__instalacion=inst, leida=False
    ).count()

    return {
        'instalacion': inst,
        'resumen': resumen_amb,
        'num_plantas': len(plantas),
        'plantas_riesgo': riesgo_inst,
        'num_alertas': alertas_inst,
    }


def _ordenar_tarjetas(tarjetas):
    prioridad = {'critico': 0, 'atencion': 1, 'optimo': 2, 'sin_datos': 3}
    tarjetas.sort(key=lambda t: (
        prioridad.get(t['resumen']['estado'], 9),
        -t['num_alertas'],
        t['instalacion'].nombre,
    ))
    return tarjetas


def _estado_agregado_grupo(tarjetas):
    niveles = {'sin_datos': 0, 'optimo': 1, 'atencion': 2, 'critico': 3}
    inverso = {0: 'sin_datos', 1: 'optimo', 2: 'atencion', 3: 'critico'}
    peor = 0
    for t in tarjetas:
        peor = max(peor, niveles.get(t['resumen']['estado'], 0))
        if t['plantas_riesgo'] > 0 and peor < 2:
            peor = 2
    estado = inverso[peor]
    label, css = ESTADO_META[estado]
    return estado, label, css


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
    cantidad_alertas = AlertaGenerada.objects.filter(
        regla__sensor__instalacion__in=instalaciones, leida=False
    ).count()

    tarjetas_todas = [_construir_tarjeta_instalacion(inst) for inst in instalaciones]
    total_plantas = sum(t['num_plantas'] for t in tarjetas_todas)
    plantas_en_riesgo = sum(t['plantas_riesgo'] for t in tarjetas_todas)

    por_invernadero = {}
    tarjetas_sin_invernadero = []
    for t in tarjetas_todas:
        inv_id = t['instalacion'].invernadero_id
        if inv_id:
            por_invernadero.setdefault(inv_id, []).append(t)
        else:
            tarjetas_sin_invernadero.append(t)
    _ordenar_tarjetas(tarjetas_sin_invernadero)

    if _es_admin(request.user):
        invernaderos_visibles = list(Invernadero.objects.all().order_by('nombre'))
    else:
        invernaderos_visibles = list(
            Invernadero.objects.filter(id__in=por_invernadero.keys()).order_by('nombre')
        )

    grupos_invernaderos = []
    for inv in invernaderos_visibles:
        tarjetas_inv = _ordenar_tarjetas(por_invernadero.get(inv.pk, []))
        estado, estado_label, estado_css = _estado_agregado_grupo(tarjetas_inv)
        grupos_invernaderos.append({
            'invernadero': inv,
            'tarjetas': tarjetas_inv,
            'num_torres': len(tarjetas_inv),
            'num_plantas': sum(t['num_plantas'] for t in tarjetas_inv),
            'plantas_riesgo': sum(t['plantas_riesgo'] for t in tarjetas_inv),
            'num_alertas': sum(t['num_alertas'] for t in tarjetas_inv),
            'estado': estado,
            'estado_label': estado_label,
            'estado_css': estado_css,
        })

    filtro_inv = request.GET.get('invernadero', '')
    grupos_filtrados = grupos_invernaderos
    sin_inv_filtrado = tarjetas_sin_invernadero
    if filtro_inv == 'sin_asignar':
        grupos_filtrados = []
    elif filtro_inv:
        grupos_filtrados = [g for g in grupos_invernaderos if str(g['invernadero'].pk) == filtro_inv]
        sin_inv_filtrado = []

    contexto = {
        'instalaciones': instalaciones,
        'tarjetas': tarjetas_todas,
        'grupos_invernaderos': grupos_filtrados,
        'tarjetas_sin_invernadero': sin_inv_filtrado,
        'invernaderos_filtro': invernaderos_visibles,
        'tiene_sin_asignar': len(tarjetas_sin_invernadero) > 0,
        'filtro_inv': filtro_inv,
        'total_invernaderos': len(invernaderos_visibles),
        'total_instalaciones': len(instalaciones),
        'total_plantas': total_plantas,
        'plantas_en_riesgo': plantas_en_riesgo,
        'usuario': request.user,
        'es_admin': _es_admin(request.user),
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
# CRUD: INVERNADEROS (Protegido por permisos RBAC)
# ============================================================

@login_required(login_url='login')
@permission_required('telemetria.add_invernadero', raise_exception=True)
def crear_invernadero(request):
    if request.method == 'POST':
        form = InvernaderoForm(request.POST)
        if form.is_valid():
            nuevo = form.save()
            messages.success(request, f'Invernadero "{nuevo.nombre}" creado correctamente.')
            return redirect('inicio_dashboard')
    else:
        form = InvernaderoForm()

    contexto = {
        'form': form,
        'titulo': 'Nuevo Invernadero',
        'descripcion': 'Registra una nave o invernadero para agrupar visualmente sus macetas verticales.',
        'volver_url': reverse('inicio_dashboard'),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.change_invernadero', raise_exception=True)
def editar_invernadero(request, invernadero_id):
    invernadero = get_object_or_404(Invernadero, pk=invernadero_id)
    if request.method == 'POST':
        form = InvernaderoForm(request.POST, instance=invernadero)
        if form.is_valid():
            form.save()
            messages.success(request, f'Invernadero "{invernadero.nombre}" actualizado.')
            return redirect('inicio_dashboard')
    else:
        form = InvernaderoForm(instance=invernadero)

    contexto = {
        'form': form,
        'titulo': f'Editar Invernadero: {invernadero.nombre}',
        'descripcion': 'Actualiza el nombre, sector o estado operativo del invernadero.',
        'volver_url': reverse('inicio_dashboard'),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.delete_invernadero', raise_exception=True)
def eliminar_invernadero(request, invernadero_id):
    invernadero = get_object_or_404(Invernadero, pk=invernadero_id)
    if request.method == 'POST':
        nombre = invernadero.nombre
        invernadero.delete()
        messages.success(
            request,
            f'Invernadero "{nombre}" eliminado. Sus torres pasaron a estar sin invernadero asignado.',
        )
        return redirect('inicio_dashboard')

    contexto = {
        'elemento': f'el invernadero "{invernadero.nombre}" (sus torres se conservarán independientes)',
        'volver_url': reverse('inicio_dashboard'),
    }
    return render(request, 'dashboard/confirmar_eliminar.html', contexto)


# ============================================================
# CRUD: INSTALACIONES / TORRES (Protegido por permisos RBAC)
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
        inv_pre = request.GET.get('invernadero')
        initial = {'invernadero': inv_pre} if inv_pre else None
        form = InstalacionForm(initial=initial)

    contexto = {
        'form': form,
        'titulo': 'Nueva Torre / Maceta Vertical',
        'descripcion': 'Registra una maceta o torre hidropónica y asígnala a un invernadero.',
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

    prioridad_estado = {'critico': 0, 'atencion': 1, 'optimo': 2, 'sin_datos': 3}
    fichas = []
    for planta in plantas:
        sensores_propios = planta.sensores.filter(activo=True)
        resumen = resumen_planta(planta)
        fichas.append({
            'planta': planta,
            'resumen': resumen,
            'num_sensores': sensores_propios.count(),
        })

    fichas.sort(key=lambda item: (
        prioridad_estado.get(item['resumen']['estado'], 9),
        item['resumen']['porcentaje_en_rango'] if item['resumen']['porcentaje_en_rango'] is not None else 101,
        item['planta'].dias_para_cosecha,
        item['planta'].codigo,
    ))

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


def _sensores_efectivos_planta(planta):
    """Retorna los sensores propios de la planta o, en su defecto, los compartidos de su instalación."""
    propios = list(planta.sensores.filter(activo=True))
    if propios:
        return propios
    return list(planta.instalacion.sensores.filter(activo=True, planta__isnull=True))


@login_required(login_url='login')
def detalle_planta(request, instalacion_id, planta_id):
    instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
    planta = get_object_or_404(Planta, pk=planta_id, instalacion=instalacion)
    sensores = _sensores_efectivos_planta(planta)
    resumen = resumen_planta(planta)
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
    sensores = _sensores_efectivos_planta(planta)
    payload = _construir_payload_live(sensores, f"{instalacion.nombre} · {planta.codigo}")
    res_p = resumen_planta(planta)
    payload['resumen'].update({
        'estado': res_p['estado'],
        'estado_label': res_p['estado_label'],
        'estado_css': res_p['estado_css'],
        'porcentaje_en_rango': res_p['porcentaje_en_rango'],
        'tendencia': res_p['tendencia'],
        'recomendaciones': res_p['recomendaciones'],
        'origen_datos': res_p['origen_datos'],
        'origen_label': res_p['origen_label'],
    })
    return JsonResponse(payload)


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


# ============================================================
# CENTRO DE ALERTAS (Navegable, filtrable y gestionable)
# ============================================================

@login_required(login_url='login')
def lista_alertas(request, instalacion_id=None):
    instalacion = None
    instalaciones_disponibles = list(_instalaciones_autorizadas(request.user))

    if instalacion_id:
        instalacion = _obtener_instalacion_autorizada(request.user, instalacion_id)
        base_qs = AlertaGenerada.objects.filter(regla__sensor__instalacion=instalacion)
    else:
        base_qs = AlertaGenerada.objects.filter(regla__sensor__instalacion__in=instalaciones_disponibles)

    base_qs = base_qs.select_related('regla__sensor__instalacion', 'regla__sensor__planta', 'medicion')

    total_pendientes = base_qs.filter(leida=False).count()
    total_rojas = base_qs.filter(mensaje__icontains='ROJA').count()
    total_azules = base_qs.filter(mensaje__icontains='AZUL').count()
    total_leidas = base_qs.filter(leida=True).count()

    filtro_estado = request.GET.get('estado', '')
    filtro_severidad = request.GET.get('severidad', '')
    filtro_inst = request.GET.get('instalacion', '')
    busqueda = request.GET.get('q', '').strip()

    alertas_qs = base_qs
    if filtro_estado == 'pendientes':
        alertas_qs = alertas_qs.filter(leida=False)
    elif filtro_estado == 'leidas':
        alertas_qs = alertas_qs.filter(leida=True)

    if filtro_severidad == 'roja':
        alertas_qs = alertas_qs.filter(mensaje__icontains='ROJA')
    elif filtro_severidad == 'azul':
        alertas_qs = alertas_qs.filter(mensaje__icontains='AZUL')

    if not instalacion and filtro_inst:
        alertas_qs = alertas_qs.filter(regla__sensor__instalacion_id=filtro_inst)

    if busqueda:
        alertas_qs = alertas_qs.filter(
            Q(mensaje__icontains=busqueda)
            | Q(regla__sensor__tipo__icontains=busqueda)
            | Q(regla__sensor__planta__codigo__icontains=busqueda)
            | Q(regla__sensor__instalacion__nombre__icontains=busqueda)
        )

    alertas = list(alertas_qs.order_by('leida', '-fecha_generacion')[:100])

    contexto = {
        'instalacion': instalacion,
        'instalaciones_disponibles': instalaciones_disponibles,
        'alertas': alertas,
        'total_pendientes': total_pendientes,
        'total_rojas': total_rojas,
        'total_azules': total_azules,
        'total_leidas': total_leidas,
        'filtro_estado': filtro_estado,
        'filtro_severidad': filtro_severidad,
        'filtro_inst': filtro_inst,
        'busqueda': busqueda,
        'tab_activa': 'alertas',
        'puede_gestionar': _es_admin(request.user) or request.user.has_perm('telemetria.change_alertagenerada'),
        'puede_eliminar': _es_admin(request.user) or request.user.has_perm('telemetria.delete_alertagenerada'),
    }
    return render(request, 'dashboard/alertas_lista.html', contexto)


@login_required(login_url='login')
@permission_required('telemetria.change_alertagenerada', raise_exception=True)
def toggle_alerta_leida(request, alerta_id):
    alerta = get_object_or_404(AlertaGenerada, pk=alerta_id)
    _obtener_instalacion_autorizada(request.user, alerta.regla.sensor.instalacion_id)
    if request.method == 'POST':
        alerta.leida = not alerta.leida
        alerta.save(update_fields=['leida'])
        estado_txt = 'leída' if alerta.leida else 'pendiente'
        messages.success(request, f'Alerta marcada como {estado_txt}.')
    return redirect(request.POST.get('next') or 'lista_alertas')


@login_required(login_url='login')
@permission_required('telemetria.change_alertagenerada', raise_exception=True)
def marcar_todas_alertas_leidas(request):
    if request.method == 'POST':
        instalacion_id = request.POST.get('instalacion_id')
        if instalacion_id:
            inst = _obtener_instalacion_autorizada(request.user, instalacion_id)
            qs = AlertaGenerada.objects.filter(regla__sensor__instalacion=inst, leida=False)
        else:
            instalaciones = _instalaciones_autorizadas(request.user)
            qs = AlertaGenerada.objects.filter(regla__sensor__instalacion__in=instalaciones, leida=False)
        cantidad = qs.update(leida=True)
        messages.success(request, f'{cantidad} alerta(s) marcadas como leídas.')
    return redirect(request.POST.get('next') or 'lista_alertas')


@login_required(login_url='login')
@permission_required('telemetria.delete_alertagenerada', raise_exception=True)
def eliminar_alerta(request, alerta_id):
    alerta = get_object_or_404(AlertaGenerada, pk=alerta_id)
    _obtener_instalacion_autorizada(request.user, alerta.regla.sensor.instalacion_id)
    if request.method == 'POST':
        alerta.delete()
        messages.success(request, 'Alerta eliminada del registro.')
    return redirect(request.POST.get('next') or 'lista_alertas')

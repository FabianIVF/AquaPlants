from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from telemetria.models import Instalacion, Sensor, Medicion, AlertaGenerada, ReglaAlerta
from .forms import InstalacionForm, ReglaAlertaForm


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
    instalaciones = Instalacion.objects.all().order_by('-fecha_creacion')
    alertas_no_leidas = AlertaGenerada.objects.filter(leida=False).order_by('-fecha_generacion')[:5]
    cantidad_alertas = alertas_no_leidas.count()

    contexto = {
        'instalaciones': instalaciones,
        'usuario': request.user,
        'alertas': alertas_no_leidas,
        'num_alertas': cantidad_alertas,
    }
    return render(request, 'dashboard/inicio.html', contexto)


@login_required(login_url='login')
def detalle_instalacion(request, instalacion_id):
    instalacion = get_object_or_404(Instalacion, pk=instalacion_id)
    sensores = Sensor.objects.filter(instalacion=instalacion)
    mediciones = Medicion.objects.filter(sensor__in=sensores).order_by('-timestamp')[:20]
    reglas = ReglaAlerta.objects.filter(sensor__in=sensores).select_related('sensor')
    
    contexto = {
        'instalacion': instalacion,
        'sensores': sensores,
        'mediciones': mediciones,
        'reglas': reglas,
        'usuario': request.user,
    }
    return render(request, 'dashboard/detalle.html', contexto)


# ============================================================
# CRUD: INSTALACIONES
# ============================================================

@login_required(login_url='login')
def crear_instalacion(request):
    if request.method == 'POST':
        form = InstalacionForm(request.POST)
        if form.is_valid():
            nueva = form.save()
            messages.success(request, f'Instalación "{nueva.nombre}" creada exitosamente.')
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
def editar_instalacion(request, instalacion_id):
    instalacion = get_object_or_404(Instalacion, pk=instalacion_id)
    if request.method == 'POST':
        form = InstalacionForm(request.POST, instance=instalacion)
        if form.is_valid():
            form.save()
            messages.success(request, f'Instalación "{instalacion.nombre}" actualizada con éxito.')
            return redirect('inicio_dashboard')
    else:
        form = InstalacionForm(instance=instalacion)

    contexto = {
        'form': form,
        'titulo': f'Editar Instalación: {instalacion.nombre}',
        'descripcion': 'Actualiza los datos del sistema o cambia su estado operativo.',
        'volver_url': reverse('inicio_dashboard'),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
def eliminar_instalacion(request, instalacion_id):
    instalacion = get_object_or_404(Instalacion, pk=instalacion_id)
    if request.method == 'POST':
        nombre = instalacion.nombre
        instalacion.delete()
        messages.success(request, f'Instalación "{nombre}" eliminada correctamente.')
        return redirect('inicio_dashboard')

    contexto = {
        'elemento': f'la instalación "{instalacion.nombre}" y todos sus sensores vinculados',
        'volver_url': reverse('inicio_dashboard'),
    }
    return render(request, 'dashboard/confirmar_eliminar.html', contexto)


# ============================================================
# CRUD: REGLAS DE ALERTA
# ============================================================

@login_required(login_url='login')
def crear_regla(request, instalacion_id):
    instalacion = get_object_or_404(Instalacion, pk=instalacion_id)
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
        'titulo': f'Configurar Regla de Alerta — {instalacion.nombre}',
        'descripcion': 'Establece límites para disparo automático de alertas (Rojas para excesos, Azules para caídas).',
        'volver_url': reverse('detalle_instalacion', kwargs={'instalacion_id': instalacion.pk}),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
def editar_regla(request, regla_id):
    regla = get_object_or_404(ReglaAlerta, pk=regla_id)
    instalacion = regla.sensor.instalacion
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
        'titulo': f'Editar Regla — {regla.sensor.tipo} ({instalacion.nombre})',
        'descripcion': 'Ajusta los umbrales de advertencia.',
        'volver_url': reverse('detalle_instalacion', kwargs={'instalacion_id': instalacion.pk}),
    }
    return render(request, 'dashboard/formulario.html', contexto)


@login_required(login_url='login')
def eliminar_regla(request, regla_id):
    regla = get_object_or_404(ReglaAlerta, pk=regla_id)
    instalacion_id = regla.sensor.instalacion.pk
    if request.method == 'POST':
        sensor_tipo = regla.sensor.tipo
        regla.delete()
        messages.success(request, f'Regla de alerta para {sensor_tipo} eliminada.')
        return redirect('detalle_instalacion', instalacion_id=instalacion_id)

    contexto = {
        'elemento': f'la regla de alerta para el sensor {regla.sensor.tipo}',
        'volver_url': reverse('detalle_instalacion', kwargs={'instalacion_id': instalacion_id}),
    }
    return render(request, 'dashboard/confirmar_eliminar.html', contexto)


# ============================================================
# API LIVE TELEMETRY
# ============================================================

@login_required(login_url='login')
def api_telemetria_live(request, instalacion_id):
    """
    Endpoint JSON que devuelve las últimas 20 mediciones por sensor
    y las últimas 5 alertas no leídas de la instalación.
    """
    instalacion = get_object_or_404(Instalacion, pk=instalacion_id)
    sensores = Sensor.objects.filter(instalacion=instalacion)

    datos_sensores = {}
    for sensor in sensores:
        mediciones_qs = (
            Medicion.objects
            .filter(sensor=sensor)
            .order_by('timestamp')
            .values('valor', 'timestamp', 'estado_conexion')
        )[:20]

        datos_sensores[sensor.tipo] = {
            "id": str(sensor.id),
            "mediciones": [
                {
                    "valor": float(m["valor"]),
                    "timestamp": m["timestamp"].strftime("%H:%M:%S"),
                    "estado_conexion": m["estado_conexion"],
                }
                for m in mediciones_qs
            ],
        }

    alertas_qs = (
        AlertaGenerada.objects
        .filter(regla__sensor__in=sensores, leida=False)
        .order_by('-fecha_generacion')[:5]
        .values('mensaje', 'fecha_generacion', 'leida')
    )

    alertas = [
        {
            "mensaje": a["mensaje"],
            "hora": a["fecha_generacion"].strftime("%H:%M:%S"),
            "leida": a["leida"],
        }
        for a in alertas_qs
    ]

    return JsonResponse({
        "instalacion": instalacion.nombre,
        "sensores": datos_sensores,
        "alertas": alertas,
        "num_alertas": len(alertas),
    })

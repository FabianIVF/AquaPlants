from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from telemetria.models import Instalacion, Sensor, Medicion, AlertaGenerada

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
    instalaciones_activas = Instalacion.objects.filter(activa=True)
    
    alertas_no_leidas = AlertaGenerada.objects.filter(leida=False).order_by('-fecha_generacion')[:5]
    
    cantidad_alertas = alertas_no_leidas.count()

    contexto = {
        'instalaciones': instalaciones_activas,
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
    
    contexto = {
        'instalacion': instalacion,
        'sensores': sensores,
        'mediciones': mediciones,
        'usuario': request.user
    }
    return render(request, 'dashboard/detalle.html', contexto)
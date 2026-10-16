from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from telemetria.models import Instalacion, Sensor, Medicion

# --- NUEVA VISTA DE LOGIN ---
def user_login(request):
    # Si el usuario ya inició sesión, lo mandamos directo al monitor
    if request.user.is_authenticated:
        return redirect('inicio_dashboard')

    if request.method == 'POST':
        # Instanciamos el formulario seguro de Django con los datos recibidos
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.cleaned_data.get('username')
            contrasena = form.cleaned_data.get('password')
            # authenticate verifica que las credenciales sean correctas en la base de datos
            user = authenticate(username=usuario, password=contrasena)
            if user is not None:
                login(request, user) # Crea la sesión segura (cookies)
                return redirect('inicio_dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'dashboard/login.html', {'form': form})

# --- ACTUALIZAMOS LOS DECORADORES DE TUS VISTAS EXISTENTES ---

# Cambiamos login_url='/admin/login/' por login_url='login'
@login_required(login_url='login')
def inicio_dashboard(request):
    instalaciones_activas = Instalacion.objects.filter(activa=True)
    contexto = {
        'instalaciones': instalaciones_activas,
        'usuario': request.user
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
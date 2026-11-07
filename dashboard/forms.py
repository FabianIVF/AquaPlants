from django import forms
from telemetria.models import Instalacion, ReglaAlerta, Sensor

class InstalacionForm(forms.ModelForm):
    class Meta:
        model = Instalacion
        fields = ['nombre', 'ubicacion', 'activa']
        labels = {
            'nombre': 'Nombre del Sistema / Instalación',
            'ubicacion': 'Ubicación física',
            'activa': 'Estado operativo (Activa)',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'placeholder': 'Ej. Huerto Vertical Torre A',
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'placeholder': 'Ej. Invernadero Central - Sector 2',
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class ReglaAlertaForm(forms.ModelForm):
    class Meta:
        model = ReglaAlerta
        fields = ['sensor', 'limite_minimo', 'limite_maximo', 'activa']
        labels = {
            'sensor': 'Sensor Asociado',
            'limite_minimo': 'Límite Mínimo (Alerta Azul si baja de este valor)',
            'limite_maximo': 'Límite Máximo (Alerta Roja si sube de este valor)',
            'activa': 'Regla Activa',
        }
        widgets = {
            'sensor': forms.Select(attrs={
                'class': 'form-select bg-dark text-light border-secondary',
            }),
            'limite_minimo': forms.NumberInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'step': '0.1',
                'placeholder': 'Ej. 18.0',
            }),
            'limite_maximo': forms.NumberInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'step': '0.1',
                'placeholder': 'Ej. 30.0',
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, instalacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        if instalacion:
            self.fields['sensor'].queryset = Sensor.objects.filter(instalacion=instalacion)

from django import forms
from telemetria.models import Instalacion, ReglaAlerta, Sensor, SENSOR_CATALOGO

# Opciones de sensores configurables para los huertos
OPCIONES_SENSORES_CHOICES = [
    ('temperatura_agua', '🌡️💧 Temperatura del Agua/Solución (°C)'),
    ('temperatura_aire', '🌡️💨 Temperatura del Aire/Ambiente (°C)'),
    ('humedad', '💧 Humedad Ambiental (%)'),
    ('ph', '🧪 Nivel de pH (pH)'),
    ('caudal', '🌊 Caudal de Agua (L/min)'),
    ('nivel_estanque', '🪣 Nivel del Estanque (%)'),
    ('co2', '🫧 Dióxido de Carbono (ppm)'),
    ('fotoperiodo', '☀️ Fotoperiodo (horas de luz/día)'),
]

SENSORES_RECOMENDADOS_DEFAULT = [
    'temperatura_agua',
    'temperatura_aire',
    'humedad',
    'ph',
    'caudal',
]


class InstalacionForm(forms.ModelForm):
    sensores_seleccionados = forms.MultipleChoiceField(
        choices=OPCIONES_SENSORES_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Variables / Sensores a Monitorear en este Huerto",
        help_text="Marca o desmarca los sensores según las necesidades operativas de esta instalación. Puedes modificarlos en cualquier momento."
    )

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
                'placeholder': 'Ej. Huerto Vertical Torre B',
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'placeholder': 'Ej. Invernadero Hidropónico - Sector 3',
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Si estamos editando, cargar los sensores que están actualmente activos
            activos = list(self.instance.sensores.filter(activo=True).values_list('tipo', flat=True))
            # Si tiene el sensor legado 'temperatura', asegurar que se reconozca
            if 'temperatura' in activos and 'temperatura_aire' not in activos:
                activos.append('temperatura_aire')
            self.fields['sensores_seleccionados'].initial = activos
        else:
            # En creación nueva, preseleccionar el kit estándar recomendado
            self.fields['sensores_seleccionados'].initial = SENSORES_RECOMENDADOS_DEFAULT

    def save(self, commit=True):
        instalacion = super().save(commit=commit)
        if commit:
            self.guardar_sensores(instalacion)
        return instalacion

    def guardar_sensores(self, instalacion):
        seleccionados = set(self.cleaned_data.get('sensores_seleccionados', []))
        sensores_actuales = {s.tipo: s for s in instalacion.sensores.all()}

        for tipo, meta in SENSOR_CATALOGO.items():
            if tipo == 'temperatura':
                continue
            if tipo in seleccionados:
                if tipo in sensores_actuales:
                    sensor = sensores_actuales[tipo]
                    if not sensor.activo:
                        sensor.activo = True
                        sensor.save(update_fields=['activo'])
                else:
                    Sensor.objects.create(
                        instalacion=instalacion,
                        tipo=tipo,
                        modelo_hardware=meta['hardware_default'],
                        activo=True
                    )
            else:
                # Si fue desmarcado, se pasa a inactivo sin eliminar historiales de medición
                if tipo in sensores_actuales:
                    sensor = sensores_actuales[tipo]
                    if sensor.activo:
                        sensor.activo = False
                        sensor.save(update_fields=['activo'])


class ReglaAlertaForm(forms.ModelForm):
    class Meta:
        model = ReglaAlerta
        fields = ['sensor', 'limite_minimo', 'limite_maximo', 'activa']
        labels = {
            'sensor': 'Sensor Asociado',
            'limite_minimo': 'Límite Mínimo (Alerta Azul si desciende bajo este valor)',
            'limite_maximo': 'Límite Máximo (Alerta Roja si sobrepasa este valor)',
            'activa': 'Regla Habilitada',
        }
        widgets = {
            'sensor': forms.Select(attrs={
                'class': 'form-select bg-dark text-light border-secondary',
            }),
            'limite_minimo': forms.NumberInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'step': '0.01',
                'placeholder': 'Ej. Valor mínimo',
            }),
            'limite_maximo': forms.NumberInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'step': '0.01',
                'placeholder': 'Ej. Valor máximo',
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, instalacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        if instalacion:
            # Solo permitir configurar reglas para sensores que estén activos en esta instalación
            self.fields['sensor'].queryset = Sensor.objects.filter(instalacion=instalacion, activo=True)
            self.fields['sensor'].label_from_instance = (
                lambda s: f"{s.get_icono()} {s.get_tipo_display()} [{s.get_unidad()}] — ({s.modelo_hardware})"
            )

    def clean(self):
        cleaned_data = super().clean()
        sensor = cleaned_data.get('sensor')
        minimo = cleaned_data.get('limite_minimo')
        maximo = cleaned_data.get('limite_maximo')

        if not sensor:
            return cleaned_data

        if minimo is None and maximo is None:
            raise forms.ValidationError("Debes establecer al menos un límite (Mínimo o Máximo) para activar la regla de alerta.")

        if minimo is not None and maximo is not None and minimo >= maximo:
            self.add_error(
                'limite_minimo',
                "El límite mínimo debe ser estrictamente inferior al límite máximo."
            )
            self.add_error(
                'limite_maximo',
                "El límite máximo debe ser estrictamente superior al límite mínimo."
            )

        tipo = sensor.tipo

        # 1. Validación estricta de Porcentaje: 0 a 100% (Humedad y Nivel del Estanque)
        if tipo in ['humedad', 'nivel_estanque']:
            for campo, valor, nombre_lim in [('limite_minimo', minimo, 'mínimo'), ('limite_maximo', maximo, 'máximo')]:
                if valor is not None:
                    if valor < 0.0 or valor > 100.0:
                        self.add_error(
                            campo,
                            f"Para {sensor.get_tipo_display()}, el valor {nombre_lim} debe estar en el rango de 0% a 100% (se ingresó {valor}%)."
                        )

        # 2. Validación estricta de pH: 0.0 a 14.0
        elif tipo == 'ph':
            for campo, valor, nombre_lim in [('limite_minimo', minimo, 'mínimo'), ('limite_maximo', maximo, 'máximo')]:
                if valor is not None:
                    if valor < 0.0 or valor > 14.0:
                        self.add_error(
                            campo,
                            f"El pH debe encontrarse dentro de la escala química de 0.0 a 14.0 (se ingresó {valor})."
                        )

        # 3. Validación estricta de Fotoperiodo: 0.0 a 24.0 horas al día
        elif tipo == 'fotoperiodo':
            for campo, valor, nombre_lim in [('limite_minimo', minimo, 'mínimo'), ('limite_maximo', maximo, 'máximo')]:
                if valor is not None:
                    if valor < 0.0 or valor > 24.0:
                        self.add_error(
                            campo,
                            f"El fotoperiodo representa horas de luz al día, por lo que debe estar entre 0.0 y 24.0 horas (se ingresó {valor} h)."
                        )

        # 4. Validación de Dióxido de Carbono: >= 0 ppm
        elif tipo == 'co2':
            for campo, valor, nombre_lim in [('limite_minimo', minimo, 'mínimo'), ('limite_maximo', maximo, 'máximo')]:
                if valor is not None:
                    if valor < 0.0:
                        self.add_error(
                            campo,
                            f"La concentración de CO₂ no puede ser negativa (se ingresó {valor} ppm)."
                        )

        # 5. Validación de Caudal: >= 0 L/min
        elif tipo == 'caudal':
            for campo, valor, nombre_lim in [('limite_minimo', minimo, 'mínimo'), ('limite_maximo', maximo, 'máximo')]:
                if valor is not None:
                    if valor < 0.0:
                        self.add_error(
                            campo,
                            f"El caudal de agua no puede ser negativo (se ingresó {valor} L/min)."
                        )

        # 6. Validación de Temperaturas (Solución y Aire): 0.0°C a 60.0°C (rango seguro de cultivo)
        elif tipo in ['temperatura_agua', 'temperatura_aire', 'temperatura']:
            for campo, valor, nombre_lim in [('limite_minimo', minimo, 'mínimo'), ('limite_maximo', maximo, 'máximo')]:
                if valor is not None:
                    if valor < 0.0 or valor > 60.0:
                        self.add_error(
                            campo,
                            f"Para {sensor.get_tipo_display()}, el valor {nombre_lim} debe estar en el rango operativo biológico de 0.0°C a 60.0°C."
                        )

        return cleaned_data

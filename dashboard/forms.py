from django import forms
from django.contrib.auth.models import Group, User
from telemetria.models import Invernadero, Instalacion, Planta, ReglaAlerta, Sensor, SENSOR_CATALOGO

# Opciones de sensores configurables para los huertos
OPCIONES_SENSORES_CHOICES = [
    ('temperatura_agua', 'Temperatura del Agua/Solución (°C)'),
    ('temperatura_aire', 'Temperatura del Aire/Ambiente (°C)'),
    ('humedad', 'Humedad Ambiental (%)'),
    ('ph', 'Nivel de pH (pH)'),
    ('caudal', 'Caudal de Agua (L/min)'),
    ('nivel_estanque', 'Nivel del Estanque (%)'),
    ('co2', 'Dióxido de Carbono (ppm)'),
    ('fotoperiodo', 'Fotoperiodo (horas de luz/día)'),
]

SENSORES_RECOMENDADOS_DEFAULT = [
    'temperatura_agua',
    'temperatura_aire',
    'humedad',
    'ph',
    'caudal',
]


class InvernaderoForm(forms.ModelForm):
    class Meta:
        model = Invernadero
        fields = ['nombre', 'sector', 'descripcion', 'activa']
        labels = {
            'nombre': 'Nombre del Invernadero',
            'sector': 'Sector / Nave física',
            'descripcion': 'Descripción del recinto',
            'activa': 'Invernadero operativo',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Invernadero Norte'}),
            'sector': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Zona A · Parcela 2'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class InstalacionForm(forms.ModelForm):
    sensores_seleccionados = forms.MultipleChoiceField(
        choices=OPCIONES_SENSORES_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Variables / Sensores a Monitorear en este Huerto",
        help_text=(
            "Marca o desmarca los sensores según las necesidades operativas de esta instalación. "
            "Puedes modificarlos en cualquier momento."
        )
    )

    class Meta:
        model = Instalacion
        fields = ['invernadero', 'nombre', 'ubicacion', 'activa']
        labels = {
            'invernadero': 'Invernadero al que pertenece',
            'nombre': 'Nombre de la Torre / Maceta Vertical',
            'ubicacion': 'Ubicación interna o fila',
            'activa': 'Estado operativo (Activa)',
        }
        widgets = {
            'invernadero': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'placeholder': 'Ej. Torre Vertical B1',
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'placeholder': 'Ej. Fila 2 · Pasillo Central',
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['invernadero'].required = False
        self.fields['invernadero'].empty_label = "--- Sin invernadero asignado (independiente) ---"
        if self.instance and self.instance.pk:
            # Si estamos editando, cargar los sensores ambientales actualmente activos
            activos = list(
                self.instance.sensores.filter(activo=True, planta__isnull=True).values_list('tipo', flat=True)
            )
            # Si tiene el sensor legado 'temperatura', asegurar que se reconozca
            if 'temperatura' in activos and 'temperatura_aire' not in activos:
                activos.append('temperatura_aire')
            self.fields['sensores_seleccionados'].initial = activos
        else:
            # En creación nueva, el usuario elige explícitamente cuáles sensores activar
            self.fields['sensores_seleccionados'].initial = []

    def save(self, commit=True):
        instalacion = super().save(commit=commit)
        if commit:
            self.guardar_sensores(instalacion)
        return instalacion

    def guardar_sensores(self, instalacion):
        seleccionados = set(self.cleaned_data.get('sensores_seleccionados', []))
        sensores_actuales = {
            s.tipo: s for s in instalacion.sensores.filter(planta__isnull=True)
        }

        # El sensor legado 'temperatura' se reemplaza por temperatura_aire/agua:
        # se desactiva (conservando su historial) para no duplicar lecturas.
        legado = sensores_actuales.get('temperatura')
        if legado and legado.activo:
            legado.activo = False
            legado.save(update_fields=['activo'])

        tipos_planta = {'humedad_sustrato', 'ph_sustrato', 'temperatura_raiz'}
        for tipo, meta in SENSOR_CATALOGO.items():
            if tipo == 'temperatura' or tipo in tipos_planta:
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
                        planta=None,
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
            # Sensores activos exclusivos de ESTA instalación
            base_qs = Sensor.objects.filter(instalacion=instalacion, activo=True)

            # Excluir sensores que ya tienen una regla configurada en este huerto
            reglas_existentes = ReglaAlerta.objects.filter(sensor__instalacion=instalacion)
            if self.instance and self.instance.pk:
                reglas_existentes = reglas_existentes.exclude(pk=self.instance.pk)
            sensores_con_regla = reglas_existentes.values_list('sensor_id', flat=True)

            self.fields['sensor'].queryset = base_qs.exclude(id__in=sensores_con_regla)
            self.fields['sensor'].empty_label = "--- Selecciona un sensor activo de este huerto ---"
            self.fields['sensor'].label_from_instance = (
                lambda s: (
                    f"[{s.planta.codigo}] {s.get_tipo_display()} — ({s.modelo_hardware})"
                    if s.planta_id
                    else f"[Ambiental] {s.get_tipo_display()} — ({s.modelo_hardware})"
                )
            )

    def clean(self):
        cleaned_data = super().clean()
        sensor = cleaned_data.get('sensor')
        minimo = cleaned_data.get('limite_minimo')
        maximo = cleaned_data.get('limite_maximo')

        if not sensor:
            return cleaned_data

        if minimo is None and maximo is None:
            raise forms.ValidationError(
                "Debes establecer al menos un límite (Mínimo o Máximo) para activar la regla de alerta."
            )

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

        # 1. Validación estricta de Porcentaje: 0 a 100%
        if tipo in ['humedad', 'nivel_estanque', 'humedad_sustrato']:
            for campo, valor, nombre_lim in [('limite_minimo', minimo, 'mínimo'), ('limite_maximo', maximo, 'máximo')]:
                if valor is not None:
                    if valor < 0.0 or valor > 100.0:
                        self.add_error(
                            campo,
                            f"Para {sensor.get_tipo_display()}, el valor {nombre_lim} debe estar "
                            f"en el rango de 0% a 100% (se ingresó {valor}%)."
                        )

        # 2. Validación estricta de pH: 0.0 a 14.0
        elif tipo in ['ph', 'ph_sustrato']:
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
                            f"El fotoperiodo representa horas de luz al día, por lo que debe estar "
                            f"entre 0.0 y 24.0 horas (se ingresó {valor} h)."
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

        # 6. Validación de Temperaturas (Solución, Aire y Raíz): 0.0°C a 60.0°C
        elif tipo in ['temperatura_agua', 'temperatura_aire', 'temperatura', 'temperatura_raiz']:
            for campo, valor, nombre_lim in [('limite_minimo', minimo, 'mínimo'), ('limite_maximo', maximo, 'máximo')]:
                if valor is not None:
                    if valor < 0.0 or valor > 60.0:
                        self.add_error(
                            campo,
                            f"Para {sensor.get_tipo_display()}, el valor {nombre_lim} debe estar "
                            "en el rango operativo biológico de 0.0°C a 60.0°C."
                        )

        return cleaned_data


OPCIONES_SENSORES_PLANTA = [
    ('humedad_sustrato', 'Humedad de Sustrato / Raíz (%)'),
    ('ph_sustrato', 'pH de Raíz / Sustrato (pH)'),
    ('temperatura_raiz', 'Temperatura de Raíz (°C)'),
]


class PlantaForm(forms.ModelForm):
    sensores_planta = forms.MultipleChoiceField(
        choices=OPCIONES_SENSORES_PLANTA,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Sensores Propios (Opcional — solo planta testigo o maceta aislada)",
        help_text=(
            "Marca sensores solo si esta planta tiene sondas propias. "
            "Si los dejas desmarcados, heredará automáticamente el monitoreo de su instalación/torre."
        ),
    )

    class Meta:
        model = Planta
        fields = ['codigo', 'especie', 'variedad', 'posicion', 'fecha_siembra', 'etapa', 'activa', 'notas']
        labels = {
            'codigo': 'Código o Nombre de la Planta',
            'especie': 'Especie compatible (ciclo estimado)',
            'variedad': 'Variedad',
            'posicion': 'Posición en torre / bancal',
            'fecha_siembra': 'Día en que se plantó',
            'etapa': 'Etapa de crecimiento',
            'activa': 'Planta activa en monitoreo',
            'notas': 'Notas agronómicas',
        }
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. T1-N2-01'}),
            'especie': forms.Select(attrs={'class': 'form-select'}),
            'variedad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Romana / Hidropónica'}),
            'posicion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Torre 1 · Nivel 2'}),
            'fecha_siembra': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'etapa': forms.Select(attrs={'class': 'form-select'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, instalacion=None, **kwargs):
        self.instalacion_target = instalacion
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            activos = list(self.instance.sensores.filter(activo=True).values_list('tipo', flat=True))
            self.fields['sensores_planta'].initial = activos
        else:
            self.fields['sensores_planta'].initial = []

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].strip()
        instalacion = self.instalacion_target or getattr(self.instance, 'instalacion', None)
        if instalacion:
            qs = Planta.objects.filter(instalacion=instalacion, codigo__iexact=codigo)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f'Ya existe una planta con el código "{codigo}" en esta instalación.')
        return codigo

    def save(self, commit=True):
        planta = super().save(commit=False)
        if self.instalacion_target and not planta.instalacion_id:
            planta.instalacion = self.instalacion_target
        if commit:
            planta.save()
            self._guardar_sensores_planta(planta)
        return planta

    def _guardar_sensores_planta(self, planta):
        seleccionados = set(self.cleaned_data.get('sensores_planta', []))
        actuales = {s.tipo: s for s in planta.sensores.all()}
        for tipo, _ in OPCIONES_SENSORES_PLANTA:
            meta = SENSOR_CATALOGO[tipo]
            if tipo in seleccionados:
                if tipo in actuales:
                    s = actuales[tipo]
                    if not s.activo:
                        s.activo = True
                        s.save(update_fields=['activo'])
                else:
                    Sensor.objects.create(
                        instalacion=planta.instalacion,
                        planta=planta,
                        tipo=tipo,
                        modelo_hardware=meta['hardware_default'],
                        activo=True,
                    )
            elif tipo in actuales and actuales[tipo].activo:
                s = actuales[tipo]
                s.activo = False
                s.save(update_fields=['activo'])


ROLES_WEB_CHOICES = [
    ('Encargado de cultivo', 'Encargado de cultivo (Gestiona plantas y reglas en sus instalaciones)'),
    ('Supervisor', 'Supervisor (Solo lectura en sus instalaciones asignadas)'),
    ('Administrador', 'Administrador (Acceso total al sistema y usuarios)'),
]


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        label='Contraseña',
        help_text='Obligatoria al crear un usuario. Al editar, déjala vacía para mantener la actual.',
    )
    rol = forms.ChoiceField(
        choices=ROLES_WEB_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Rol y Nivel de Permisos',
    )
    instalaciones = forms.ModelMultipleChoiceField(
        queryset=Instalacion.objects.all().order_by('nombre'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label='Instalaciones Asignadas',
        help_text='Selecciona a qué instalaciones tendrá acceso este usuario (Encargado / Supervisor).',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
            'is_active': 'Cuenta activa',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. juan.perez'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@aquaplants.cl'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            grupo = self.instance.groups.filter(
                name__in=['Administrador', 'Encargado de cultivo', 'Supervisor']
            ).first()
            if grupo:
                self.fields['rol'].initial = grupo.name
            elif self.instance.is_superuser:
                self.fields['rol'].initial = 'Administrador'
            self.fields['instalaciones'].initial = list(
                self.instance.instalaciones_asignadas.values_list('id', flat=True)
            )
        else:
            self.fields['password'].required = True

    def clean_password(self):
        pwd = self.cleaned_data.get('password', '')
        if not self.instance.pk and not pwd:
            raise forms.ValidationError('Debes ingresar una contraseña para el nuevo usuario.')
        if pwd and len(pwd) < 6:
            raise forms.ValidationError('La contraseña debe tener al menos 6 caracteres.')
        return pwd

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
            rol_nombre = self.cleaned_data['rol']
            grupo, _ = Group.objects.get_or_create(name=rol_nombre)
            user.groups.set([grupo])
            instalaciones = self.cleaned_data.get('instalaciones')
            if instalaciones is not None:
                user.instalaciones_asignadas.set(instalaciones)
        return user

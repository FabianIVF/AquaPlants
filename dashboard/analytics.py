"""
Módulo de analítica agronómica para AquaPlants.
Transforma mediciones crudas en indicadores comprensibles para el cultivador:
estado de salud, porcentaje en rango, tendencia y recomendaciones prácticas.
"""
from telemetria.models import Medicion, ReglaAlerta

RANGOS_IDEALES = {
    'temperatura_agua': (18.0, 24.0),
    'temperatura_aire': (18.0, 28.0),
    'temperatura': (18.0, 28.0),
    'humedad': (50.0, 80.0),
    'ph': (5.5, 6.5),
    'caudal': (1.5, 4.0),
    'nivel_estanque': (40.0, 95.0),
    'co2': (400.0, 1200.0),
    'fotoperiodo': (12.0, 18.0),
    'humedad_sustrato': (55.0, 80.0),
    'ph_sustrato': (5.5, 6.5),
    'temperatura_raiz': (18.0, 24.0),
}

# Ajustes agronómicos de rangos ideales según etapa fenológica del cultivo
RANGOS_POR_ETAPA = {
    'germinacion': {
        'humedad': (65.0, 85.0),
        'humedad_sustrato': (65.0, 85.0),
        'temperatura_aire': (20.0, 26.0),
        'temperatura_agua': (20.0, 24.0),
        'temperatura_raiz': (20.0, 24.0),
        'ph': (5.6, 6.5),
        'ph_sustrato': (5.6, 6.5),
    },
    'vegetativo': {
        'humedad': (55.0, 75.0),
        'humedad_sustrato': (55.0, 80.0),
        'temperatura_aire': (18.0, 27.0),
        'temperatura_agua': (18.0, 23.0),
        'temperatura_raiz': (18.0, 23.0),
        'ph': (5.5, 6.5),
        'ph_sustrato': (5.5, 6.5),
    },
    'floracion': {
        'humedad': (45.0, 65.0),
        'humedad_sustrato': (55.0, 75.0),
        'temperatura_aire': (19.0, 28.0),
        'temperatura_agua': (18.0, 22.0),
        'temperatura_raiz': (18.0, 22.0),
        'ph': (5.8, 6.5),
        'ph_sustrato': (5.8, 6.5),
    },
    'cosecha': {
        'humedad': (40.0, 60.0),
        'humedad_sustrato': (50.0, 70.0),
        'temperatura_aire': (18.0, 26.0),
        'temperatura_agua': (18.0, 22.0),
        'temperatura_raiz': (18.0, 22.0),
        'ph': (5.8, 6.5),
        'ph_sustrato': (5.8, 6.5),
    },
}

RECOMENDACIONES_ALTO = {
    'ph': 'pH elevado ({val}): aplicar reductor de pH (pH-) o revisar solución nutritiva.',
    'ph_sustrato': 'pH de raíz elevado ({val}): ajustar acidez del riego para mejorar absorción.',
    'temperatura_agua': 'Agua tibia ({val}°C): enfriar u oxigenar el estanque para evitar hongos radiculares.',
    'temperatura_aire': 'Temperatura ambiental alta ({val}°C): mejorar ventilación o sombreo.',
    'temperatura': 'Temperatura elevada ({val}°C): ventilar el invernadero.',
    'temperatura_raiz': 'Raíces con exceso de calor ({val}°C): revisar temperatura de solución y aislación.',
    'humedad': 'Humedad ambiental alta ({val}%): aumentar ventilación para prevenir moho.',
    'humedad_sustrato': 'Exceso de humedad en sustrato ({val}%): reducir frecuencia de riego.',
    'caudal': 'Caudal sobre lo habitual ({val} L/min): revisar presión de bomba.',
    'nivel_estanque': 'Estanque cerca de rebalse ({val}%): revisar válvula de llenado.',
    'co2': 'CO₂ elevado ({val} ppm): ventilar el recinto de cultivo.',
    'fotoperiodo': 'Exceso de horas de luz ({val} h): revisar temporizador de luminarias.',
}

RECOMENDACIONES_BAJO = {
    'ph': 'pH ácido ({val}): añadir solución alcalina (pH+) y homogeneizar estanque.',
    'ph_sustrato': 'Sustrato muy ácido ({val}): realizar lavado ligero con solución balanceada.',
    'temperatura_agua': 'Agua fría ({val}°C): verificar calefactor de estanque para no frenar raíces.',
    'temperatura_aire': 'Temperatura baja ({val}°C): cerrar cortinas o activar calefacción.',
    'temperatura': 'Temperatura baja ({val}°C): proteger el cultivo del frío.',
    'temperatura_raiz': 'Raíces frías ({val}°C): templar solución nutritiva.',
    'humedad': 'Ambiente seco ({val}%): activar nebulización o revisar humedad.',
    'humedad_sustrato': 'Sustrato seco ({val}%): verificar gotero o aumentar frecuencia de riego.',
    'caudal': 'Caudal bajo ({val} L/min): revisar bomba, filtro o posibles obstrucciones.',
    'nivel_estanque': 'Nivel de estanque bajo ({val}%): rellenar depósito con agua y nutrientes.',
    'co2': 'CO₂ bajo ({val} ppm): mejorar renovación de aire en el invernadero.',
    'fotoperiodo': 'Pocas horas de luz ({val} h): revisar encendido de lámparas de cultivo.',
}

ESTADO_META = {
    'optimo': ('Óptimo', 'status-ok'),
    'atencion': ('Atención', 'status-warn'),
    'critico': ('Crítico', 'status-err'),
    'sin_datos': ('Sin datos', 'status-off'),
}


def _rangos_para_cultivo(etapa=None, dias_para_cosecha=None):
    """Construye los rangos objetivos adaptados por etapa y cercanía de cosecha."""
    rangos = dict(RANGOS_IDEALES)
    especificos = set()
    if etapa and etapa in RANGOS_POR_ETAPA:
        for tipo, limites in RANGOS_POR_ETAPA[etapa].items():
            rangos[tipo] = limites
            especificos.add(tipo)
    # En ventana pre-cosecha (1-7 días), evitar exceso de humedad que favorezca hongos o pudrición
    if dias_para_cosecha is not None and dias_para_cosecha <= 7 and etapa != 'cosecha':
        hum_lo, hum_hi = rangos['humedad']
        rangos['humedad'] = (min(hum_lo, 45.0), min(hum_hi, 65.0))
        sub_lo, sub_hi = rangos['humedad_sustrato']
        rangos['humedad_sustrato'] = (min(sub_lo, 50.0), min(sub_hi, 72.0))
        especificos.update(('humedad', 'humedad_sustrato'))
    return rangos, especificos


def _obtener_limites(sensor, regla, rangos_base=None, tipos_etapa=None):
    catalogo = rangos_base if rangos_base is not None else RANGOS_IDEALES
    lo, hi = catalogo.get(sensor.tipo, (None, None))
    origen = 'etapa' if (tipos_etapa and sensor.tipo in tipos_etapa) else 'general'
    if regla and regla.activa:
        if regla.limite_minimo is not None:
            lo = regla.limite_minimo
            origen = 'regla'
        if regla.limite_maximo is not None:
            hi = regla.limite_maximo
            origen = 'regla'
    return lo, hi, origen


def _calcular_tendencia(valores_cronologicos):
    """Compara el promedio de las últimas 3 lecturas vs las 3 anteriores."""
    if len(valores_cronologicos) < 4:
        return 'estable'
    recientes = valores_cronologicos[-3:]
    anteriores = valores_cronologicos[-6:-3] or valores_cronologicos[:-3]
    diff = (sum(recientes) / len(recientes)) - (sum(anteriores) / len(anteriores))
    tolerancia = max(0.05, abs(sum(anteriores) / len(anteriores)) * 0.02)
    if diff > tolerancia:
        return 'sube'
    if diff < -tolerancia:
        return 'baja'
    return 'estable'


def _evaluar_valor(sensor, valor, conectado, lo, hi):
    if not conectado:
        return 'atencion', False, f'{sensor.get_tipo_display()} sin señal: revisar cableado o nodo IoT.'

    if hi is not None and valor > hi:
        tpl = RECOMENDACIONES_ALTO.get(sensor.tipo, '{tipo} sobre el máximo ({val}).')
        return 'critico', False, tpl.format(tipo=sensor.get_tipo_display(), val=valor)

    if lo is not None and valor < lo:
        tpl = RECOMENDACIONES_BAJO.get(sensor.tipo, '{tipo} bajo el mínimo ({val}).')
        return 'critico', False, tpl.format(tipo=sensor.get_tipo_display(), val=valor)

    # Margen preventivo (10% del ancho del rango)
    if lo is not None and hi is not None and hi > lo:
        margen = (hi - lo) * 0.10
        if valor >= hi - margen:
            return 'atencion', True, f'{sensor.get_tipo_display()} acercándose al límite superior ({valor}).'
        if valor <= lo + margen:
            return 'atencion', True, f'{sensor.get_tipo_display()} acercándose al límite inferior ({valor}).'

    return 'optimo', True, None


def resumen_sensores(sensores, limite_lecturas=30, etapa=None, dias_para_cosecha=None):
    """
    Calcula estado de salud, % en rango, tendencia y recomendaciones
    para un conjunto de sensores (de una planta o de una instalación).
    """
    sensores_list = list(sensores)
    rangos_objetivo, tipos_etapa = _rangos_para_cultivo(etapa, dias_para_cosecha)

    if not sensores_list:
        label, css = ESTADO_META['sin_datos']
        return {
            'estado': 'sin_datos',
            'estado_label': label,
            'estado_css': css,
            'porcentaje_en_rango': None,
            'tendencia': 'estable',
            'recomendaciones': ['Activa al menos un sensor para comenzar el diagnóstico automático.'],
            'sensores_detalle': [],
        }

    reglas_map = {
        r.sensor_id: r
        for r in ReglaAlerta.objects.filter(sensor__in=sensores_list, activa=True)
    }

    total_conectadas = 0
    total_en_rango = 0
    peor_nivel = 0  # 0=sin_datos, 1=optimo, 2=atencion, 3=critico
    niveles = {'sin_datos': 0, 'optimo': 1, 'atencion': 2, 'critico': 3}
    inverso = {0: 'sin_datos', 1: 'optimo', 2: 'atencion', 3: 'critico'}
    recomendaciones = []
    sensores_detalle = []
    tendencias = []

    for sensor in sensores_list:
        lecturas = list(
            Medicion.objects
            .filter(sensor=sensor)
            .order_by('-timestamp')
            .values('valor', 'estado_conexion', 'timestamp')[:limite_lecturas]
        )
        lo, hi, origen_rango = _obtener_limites(
            sensor,
            reglas_map.get(sensor.id),
            rangos_base=rangos_objetivo,
            tipos_etapa=tipos_etapa,
        )

        if not lecturas:
            sensores_detalle.append({
                'sensor': sensor,
                'valor': None,
                'estado': 'sin_datos',
                'tendencia': 'estable',
                'en_rango_pct': None,
                'rango_min': lo,
                'rango_max': hi,
                'rango_origen': origen_rango,
            })
            continue

        # Cronológico para tendencia
        lecturas_asc = list(reversed(lecturas))
        valores_conectados = [float(m['valor']) for m in lecturas_asc if m['estado_conexion']]
        tendencia = _calcular_tendencia(valores_conectados)
        tendencias.append(tendencia)

        en_rango_sensor = 0
        for val in valores_conectados:
            total_conectadas += 1
            dentro_lo = lo is None or val >= lo
            dentro_hi = hi is None or val <= hi
            if dentro_lo and dentro_hi:
                total_en_rango += 1
                en_rango_sensor += 1

        ultima = lecturas[0]
        val_actual = float(ultima['valor'])
        estado_s, _, rec = _evaluar_valor(sensor, val_actual, ultima['estado_conexion'], lo, hi)
        peor_nivel = max(peor_nivel, niveles[estado_s])
        if rec and rec not in recomendaciones:
            recomendaciones.append(rec)

        pct_s = round((en_rango_sensor / len(valores_conectados)) * 100) if valores_conectados else None
        sensores_detalle.append({
            'sensor': sensor,
            'valor': val_actual,
            'estado': estado_s,
            'estado_conexion': ultima['estado_conexion'],
            'timestamp': ultima['timestamp'],
            'tendencia': tendencia,
            'en_rango_pct': pct_s,
            'rango_min': lo,
            'rango_max': hi,
            'rango_origen': origen_rango,
        })

    estado_global = inverso[peor_nivel]
    label, css = ESTADO_META[estado_global]
    pct_global = round((total_en_rango / total_conectadas) * 100) if total_conectadas else None

    if not recomendaciones:
        if estado_global == 'sin_datos':
            recomendaciones = ['Esperando las primeras lecturas del simulador o nodo AquaBrain.']
        else:
            recomendaciones = ['Parámetros dentro del rango óptimo: mantener el plan actual de riego y nutrientes.']

    tendencia_global = 'estable'
    if tendencias.count('sube') > tendencias.count('baja') and tendencias.count('sube') > 0:
        tendencia_global = 'sube'
    elif tendencias.count('baja') > tendencias.count('sube') and tendencias.count('baja') > 0:
        tendencia_global = 'baja'

    return {
        'estado': estado_global,
        'estado_label': label,
        'estado_css': css,
        'porcentaje_en_rango': pct_global,
        'tendencia': tendencia_global,
        'recomendaciones': recomendaciones,
        'sensores_detalle': sensores_detalle,
    }


def _aviso_etapa_y_cosecha(planta, estado):
    """Genera un aviso agronómico específico según etapa fenológica y proximidad a cosecha."""
    restantes = planta.dias_para_cosecha
    if restantes == 0 and planta.etapa != 'cosecha':
        return (
            f'Ciclo estimado cumplido ({planta.dias_ciclo} días): revisar madurez de {planta.especie_nombre}, '
            'realizar lavado radicular y preparar cosecha.'
        )
    if 0 < restantes <= 7 and planta.etapa != 'cosecha':
        return (
            f'Pre-cosecha ({restantes} d restantes): reducir nutrientes (agua limpia), mantener humedad ≤ 65% '
            'y preparar corte.'
        )
    if planta.etapa == 'cosecha':
        if estado in ('atencion', 'critico'):
            return (
                'Etapa de cosecha con desvío ambiental: corregir humedad/temperatura pronto para no perder '
                'firmeza ni calidad.'
            )
        return (
            'Planta en etapa de cosecha con parámetros estables: recolectar en horas frescas y planificar limpieza.'
        )
    if planta.etapa == 'germinacion':
        if estado in ('atencion', 'critico'):
            return (
                'Etapa germinación: mayor sensibilidad radicular; estabilizar agua (20–24 °C), '
                'pH (5.6–6.5) y humedad (65–85%).'
            )
        return (
            f'Germinación / Arraigo ({restantes} d estimados a cosecha): mantener humedad alta (65–85%) '
            'y solución templada.'
        )
    if planta.etapa == 'floracion':
        return (
            f'Floración / Desarrollo ({restantes} d para cosecha): mantener humedad ≤ 65% contra hongos, '
            'agua fresca (18–22 °C) y pH 5.8–6.5.'
        )
    return (
        f'Crecimiento vegetativo ({restantes} d para cosecha): mantener pH 5.5–6.5 y riego continuo '
        'para impulsar follaje y raíces.'
    )


def resumen_planta(planta, limite_lecturas=30):
    """
    Calcula el diagnóstico de una planta con rangos adaptados a su etapa y cercanía de cosecha:
    - Si tiene sensores propios activos (planta testigo / maceta individual), usa sus propios sensores.
    - Si no tiene sensores propios, hereda automáticamente los sensores de su instalación/torre.
    """
    sensores_propios = list(planta.sensores.filter(activo=True))
    if sensores_propios:
        sensores = sensores_propios
        origen_datos = 'propios'
        origen_label = 'Planta testigo (sensores propios)'
    else:
        sensores = list(planta.instalacion.sensores.filter(activo=True, planta__isnull=True))
        origen_datos = 'compartidos'
        origen_label = 'Torre compartida (hereda sensores del sistema)'

    resumen = resumen_sensores(
        sensores,
        limite_lecturas=limite_lecturas,
        etapa=planta.etapa,
        dias_para_cosecha=planta.dias_para_cosecha,
    )
    resumen['origen_datos'] = origen_datos
    resumen['origen_label'] = origen_label
    resumen['pre_cosecha'] = planta.dias_para_cosecha <= 7

    aviso = _aviso_etapa_y_cosecha(planta, resumen['estado'])
    resumen['aviso_cosecha'] = aviso

    if resumen['estado'] == 'optimo':
        # Reemplaza el mensaje genérico por el aviso específico de etapa y cosecha
        resumen['recomendaciones'] = [aviso]
    elif aviso and aviso not in resumen['recomendaciones']:
        resumen['recomendaciones'].append(aviso)

    return resumen

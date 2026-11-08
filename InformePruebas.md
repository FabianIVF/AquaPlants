# Informe de Ejecución y Validación del Protocolo de Pruebas (Fase 4)
**Proyecto:** AquaPlants — Plataforma IoT de Telemetría Hidropónica  
**Asignatura / Evaluación:** ES3 — Implementación de la Solución de Software (INACAP)  
**Estudiantes:** Fabian Vidal y Pablo Cabezas  
**Fecha de Ejecución:** Noviembre 2026  
**Resultado Global:** `18/18 pruebas exitosas (100% OK)`

---

## 1. Alcance y Cobertura del Plan de Pruebas (Criterio 3.1.5.9 - 10 pts)

La suite de pruebas automatizadas fue desarrollada en `telemetria/tests.py` mediante el framework de pruebas de Django (`django.test.TestCase` y `rest_framework.test.APITestCase`). Cubre de forma exhaustiva casos de éxito, escenarios de borde, fallos forzados y políticas de seguridad RBAC:

| Módulo / Clase de Prueba | Escenarios Evaluados | Tipo de Prueba |
| :--- | :--- | :---: |
| **`ModelosTelemetriaTestCase`** | Validación de no negatividad (`MinValueValidator`), integridad referencial en cascada, formato limpio de presentación. | Borde / Integridad |
| **`SeguridadYPermisosRBACTestCase`** | Bloqueo al rol `Supervisor` (HTTP 403), acceso al rol `Administrador` (HTTP 200), redirección de usuario anónimo (HTTP 302). | Seguridad / RBAC |
| **`APITelemetriaSeguridadTestCase`** | Rechazo de peticiones anónimas a la API (HTTP 401/403), inserción válida por dispositivo `iot_device` (HTTP 201), rechazo a sensores desactivados (HTTP 400), validación en Serializer. | Seguridad API / IoT |
| **`ReglasDeAlertaTestCase`** | Disparo automático de Alerta Roja por exceso, disparo de Alerta Azul por caída, ausencia de alertas en rango óptimo, supresión de falsas alertas ante fallo de conexión. | Lógica de Negocio |
| **`FormulariosDashboardTestCase`** | Validación estricta de porcentajes (> 100% rechazado), escala química de pH (> 14 rechazado), coherencia de límites (mínimo $\ge$ máximo rechazado), persistencia selectiva de sensores. | Validación de Entrada |

---

## 2. Registro de Ejecución del Protocolo (Criterio 3.1.5.10 - 10 pts)

Comando ejecutado:
```bash
python manage.py test telemetria -v 2
```

### Salida Consignada del Protocolo:
```text
Creating test database for alias 'default' ('test_aquaplants_db')...
Found 18 test(s).
Operations to perform:
  Synchronize unmigrated apps: corsheaders, messages, rest_framework, staticfiles
  Apply all migrations: admin, auth, contenttypes, sessions, telemetria
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying sessions.0001_initial... OK
  Applying telemetria.0001_initial... OK
  Applying telemetria.0002_reglaalerta_alertagenerada... OK
  Applying telemetria.0003_sensor_activo_alter_sensor_tipo... OK

test_api_rechaza_lectura_de_sensor_desactivado ... ok
test_api_rechaza_peticion_anonima ... ok
test_api_rechaza_valor_negativo_en_payload ... ok
test_iot_device_puede_enviar_medicion ... ok
test_humedad_porcentaje_mayor_a_100_rechazado ... ok
test_instalacion_form_crea_sensores_seleccionados ... ok
test_minimo_mayor_que_maximo_rechazado ... ok
test_ph_fuera_de_escala_quimica_rechazado ... ok
test_eliminacion_en_cascada_instalacion ... ok
test_modelo_valor_negativo_rechazado ... ok
test_sensor_representacion_cadena_sin_emojis ... ok
test_alerta_azul_generada_al_caer_bajo_minimo ... ok
test_alerta_roja_generada_al_superar_maximo ... ok
test_fallo_conexion_no_genera_alerta_falsa ... ok
test_sin_alerta_dentro_del_rango_optimo ... ok
test_admin_puede_acceder_crear_instalacion ... ok
test_supervisor_no_puede_crear_instalacion ... ok
test_usuario_anonimo_redirigido_al_login ... ok

----------------------------------------------------------------------
Ran 18 tests in 8.862s

OK
Destroying test database for alias 'default' ('test_aquaplants_db')...
```

---

## 3. Validación de Resultados y Recomendaciones de Mejora (Criterio 3.1.5.11 - 10 pts)

### Análisis de Hallazgos
1. **Consistencia de Seguridad:** Se comprobó que un usuario no autenticado ni un Supervisor pueden alterar las instalaciones, cumpliendo estrictamente con el Principio de Mínimo Privilegio.
2. **Mitigación de Falsas Alarmas:** La lógica implementada en `MedicionViewSet.perform_create` comprobó su efectividad: si `estado_conexion = False` (dispositivo desconectado), la lectura de `0.00` se almacena con fines de auditoría pero **no gatilla alertas azules falsas**, evitando el pánico de los encargados agrícolas.
3. **Robustez de Entrada:** Tanto a nivel de base de datos (`MinValueValidator`) como en el Serializer REST y en los formularios web (`clean()`), las entradas anómalas (porcentajes $> 100\%$, pH $> 14.0$, números negativos) son interceptadas antes de persistir.

### Recomendaciones para Escalabilidad Futura (Criterio 3.1.6.13)
* **Desacople Asíncrono de Alertas:** Si la red de sensores crece a más de 100 huertos transmitiendo por segundo, delegar el cálculo de umbrales a una cola de tareas asíncronas con **Celery + Redis**.
* **Protocolo Ligero de Telemetría:** Reemplazar el envío periódico sobre HTTP/REST en los microcontroladores (ESP32) por un broker **MQTT**, dejando la API REST exclusivamente para gestión administrativa.
* **Alertas Multicanal:** Conectar las alertas generadas a un webhook de **Telegram o Correo SMTP** para notificar al agricultor sin necesidad de que tenga abierto el navegador.

from rest_framework.test import APITestCase
from rest_framework import status

class SeguridadAPITests(APITestCase):
    def test_rechazar_medicion_sin_autenticacion(self):
        # 1. Preparar el escenario del ataque
        url = '/api/mediciones/'
        payload_malicioso = {
            "valor": "999.99",
            "estado_conexion": True
        }

        # 2. Ejecutar la simulación (Petición POST sin credenciales)
        response = self.client.post(url, payload_malicioso, format='json')

        # 3. Afirmar (Assert) que las defensas actuaron correctamente
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

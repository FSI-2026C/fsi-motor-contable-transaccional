#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas de Integración QA — API REST HTTP del Motor Contable Transaccional
Verifica el flujo completo extremo a extremo (HTTP -> API -> Motor ACID -> SQLite).
"""

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

import app
from motor_contable import MotorContable


class TestApiIntegracionQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tmp.close()
        cls.orig_motor = app.motor
        app.motor = MotorContable(cls.tmp.name)

        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.FinanzasHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        app.motor = cls.orig_motor
        try:
            os.unlink(cls.tmp.name)
        except OSError:
            pass

    def _post(self, path, payload):
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_01_get_frontend_y_estado_sistema(self):
        with urllib.request.urlopen(f"{self.base_url}/index.html") as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("Motor Contable Transaccional", html)

        with urllib.request.urlopen(f"{self.base_url}/api/estado-sistema?periodo=2026-06") as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["ok"])
            self.assertEqual(len(data["asientos"]), 5)
            self.assertGreaterEqual(len(data["cuentas_pcge"]), 20)

    def test_02_post_asiento_valido_retorna_201(self):
        status, body = self._post(
            "/api/asientos",
            {
                "cuo": "CUO-API-01",
                "fecha": "2026-06-22",
                "libro_sunat": "14 · Registro de Ventas e Ingresos",
                "tipo_doc": "01 - Factura",
                "num_doc": "F001-00555",
                "ruc_tercero": "20604152631",
                "razon_social": "EMPRESA INTEGRACION QA S.A.C.",
                "glosa": "Por la venta de servicios verificada mediante prueba de integración QA",
                "lineas": [
                    {"cuenta": "1212", "debe": 590.00, "haber": 0.00},
                    {"cuenta": "4011", "debe": 0.00, "haber": 90.00},
                    {"cuenta": "7012", "debe": 0.00, "haber": 500.00},
                ],
            },
        )
        self.assertEqual(status, 201)
        self.assertTrue(body["ok"])

    def test_03_post_asiento_descuadrado_retorna_400(self):
        status, body = self._post(
            "/api/asientos",
            {
                "cuo": "CUO-API-ERR",
                "fecha": "2026-06-22",
                "libro_sunat": "05 · Libro Diario",
                "tipo_doc": "01 - Factura",
                "num_doc": "F001-00556",
                "ruc_tercero": "20604152631",
                "razon_social": "PRUEBA ERROR S.A.C.",
                "glosa": "Intento de registro descuadrado para prueba QA",
                "lineas": [
                    {"cuenta": "1212", "debe": 500.00, "haber": 0.00},
                    {"cuenta": "7012", "debe": 0.00, "haber": 400.00},
                ],
            },
        )
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        self.assertIn("Partida Doble", body["error"])

    def test_04_post_extorno_y_cierre_periodo_via_api(self):
        status, body = self._post(
            "/api/asientos/extornar",
            {"cuo": "CUO-API-01", "motivo": "Prueba QA de extorno vía API REST"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["extorno"]["cuo_extorno"], "EXT-CUO-API-01")

        # Cerrar período y comprobar bloqueo HTTP 400
        status_cierre, _ = self._post("/api/periodo/estado", {"periodo": "2026-06", "estado": "CERRADO"})
        self.assertEqual(status_cierre, 200)

        status_bloq, body_bloq = self._post(
            "/api/asientos",
            {
                "cuo": "CUO-API-BLQ",
                "fecha": "2026-06-25",
                "libro_sunat": "05 · Libro Diario",
                "tipo_doc": "00 - Otros",
                "num_doc": "OP-001",
                "ruc_tercero": "20604152631",
                "razon_social": "PRUEBA BLOQUEO S.A.C.",
                "glosa": "Debe ser bloqueado porque el período 2026-06 está cerrado",
                "lineas": [
                    {"cuenta": "1041", "debe": 100.00, "haber": 0.00},
                    {"cuenta": "1212", "debe": 0.00, "haber": 100.00},
                ],
            },
        )
        self.assertEqual(status_bloq, 400)
        self.assertIn("CERRADO", body_bloq["error"])

        # Reabrir período para dejar estado limpio
        self._post("/api/periodo/estado", {"periodo": "2026-06", "estado": "ABIERTO"})

    def test_05_descarga_ple_formato_5_1(self):
        with urllib.request.urlopen(f"{self.base_url}/api/exportar/ple?periodo=2026-06") as resp:
            self.assertEqual(resp.status, 200)
            disp = resp.headers.get("Content-Disposition", "")
            self.assertIn("LE2060184921120260600050100001111.txt", disp)
            content = resp.read().decode("utf-8")
            self.assertTrue(len(content.splitlines()) >= 19)


if __name__ == "__main__":
    unittest.main()

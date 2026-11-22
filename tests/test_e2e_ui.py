#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas E2E (End-to-End) en Navegador Real (Playwright + Chromium)
Ejecutadas automáticamente en GitHub Actions (.github/workflows/qa-e2e-navegador.yml).
Simula a un usuario contador real usando la interfaz web del Motor Contable Transaccional.
"""

import os
import sys
import tempfile
import threading
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

import app
from motor_contable import MotorContable


@unittest.skipUnless(PLAYWRIGHT_AVAILABLE, "Playwright no instalado en entorno local (se ejecuta en CI E2E)")
class TestE2ENavegadorQA(unittest.TestCase):
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

        cls.evidencias_dir = os.path.join(PROJECT_ROOT, "evidencias_e2e")
        os.makedirs(cls.evidencias_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        app.motor = cls.orig_motor
        try:
            os.unlink(cls.tmp.name)
        except OSError:
            pass

    def test_flujo_completo_usuario_contador_e2e(self):
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception:
                try:
                    browser = p.chromium.launch(headless=True, channel="chrome")
                except Exception as exc:
                    self.skipTest(f"Navegador Chromium/Chrome no disponible localmente: {exc}")
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            # 1. Cargar Libro Diario (Formato 5.1)
            page.goto(f"{self.base_url}/index.html", wait_until="networkidle")
            page.wait_for_selector("#kpi-debe")
            self.assertEqual(page.locator("#kpi-debe").inner_text().strip(), "S/ 11,080.00")
            self.assertEqual(page.locator("#kpi-diff").inner_text().strip(), "S/ 0.00")
            page.screenshot(path=os.path.join(self.evidencias_dir, "01_libro_diario_inicial.png"))

            # 2. Navegar a Registrar Asiento y aplicar plantilla de Compra + Destino Almacén
            page.click("#tab-2")
            page.select_option("#tpl-select", "compra_mercaderia")
            page.fill("#calc-monto", "2360.00")
            page.click("button:has-text('Calcular IGV (18%)')")
            self.assertIn("[OK] Partida doble", page.locator("#v-r1").inner_text())
            page.screenshot(path=os.path.join(self.evidencias_dir, "02_registro_asiento_sunat.png"))

            # 3. Grabar el asiento y validar actualización del Libro Diario
            page.click("#btn-grabar-asiento")
            page.wait_for_selector("text=CUO-0006")
            self.assertEqual(page.locator("#kpi-count").inner_text().strip(), "6 asientos")
            self.assertEqual(page.locator("#kpi-diff").inner_text().strip(), "S/ 0.00")

            # 4. Ejecutar Extorno desde la interfaz y confirmar el modal
            page.locator("tr:has-text('CUO-0006') button:has-text('Extornar')").first.click()
            page.wait_for_selector("#modal-extorno.open")
            page.fill("#extorno-motivo", "Extorno automatizado en prueba E2E Playwright")
            page.click("button:has-text('Confirmar extorno')")
            page.wait_for_selector("text=EXT-CUO-0006")
            page.screenshot(path=os.path.join(self.evidencias_dir, "03_diario_con_extorno.png"))

            # 5. Revisar pestaña Auditoría y Período
            page.click("#tab-4")
            page.wait_for_selector("text=EXTORNO_ASIENTO")
            page.screenshot(path=os.path.join(self.evidencias_dir, "04_auditoria_transaccional.png"))

            browser.close()


if __name__ == "__main__":
    unittest.main()

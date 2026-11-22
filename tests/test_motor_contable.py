#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas Unitarias Automatizadas — Motor Contable Transaccional (SUNAT Formato 5.1)
Ejecutar con: python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from motor_contable import ErrorValidacionContable, MotorContable


class TestMotorContableSUNAT(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.motor = MotorContable(self.tmp.name)

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def _asiento_venta_valido(self, cuo="CUO-0099"):
        return {
            "cuo": cuo,
            "fecha": "2026-06-20",
            "libro_sunat": "14 · Registro de Ventas e Ingresos",
            "tipo_doc": "01 - Factura",
            "num_doc": "F001-00999",
            "ruc_tercero": "20604152631",
            "razon_social": "CLIENTE PRUEBA S.A.C.",
            "glosa": "Por la venta de mercaderías gravadas con IGV según Factura F001-00999",
            "lineas": [
                {"cuenta": "1212", "debe": 1180.00, "haber": 0.00},
                {"cuenta": "4011", "debe": 0.00, "haber": 180.00},
                {"cuenta": "7012", "debe": 0.00, "haber": 1000.00},
            ],
        }

    def test_01_registro_asiento_valido_y_partida_doble(self):
        res = self.motor.registrar_asiento(self._asiento_venta_valido())
        self.assertEqual(res["cuo"], "CUO-0099")
        self.assertEqual(res["total"], 1180.00)

        asientos = self.motor.listar_asientos()
        self.assertTrue(any(a["cuo"] == "CUO-0099" for a in asientos))

    def test_02_rechaza_asiento_descuadrado(self):
        asiento = self._asiento_venta_valido("CUO-DESC")
        asiento["lineas"][2]["haber"] = 900.00  # Debe 1180 vs Haber 1080
        with self.assertRaises(ErrorValidacionContable) as ctx:
            self.motor.registrar_asiento(asiento)
        self.assertIn("Partida Doble", str(ctx.exception))

    def test_03_rechaza_ruc_invalido(self):
        asiento = self._asiento_venta_valido("CUO-RUC")
        asiento["ruc_tercero"] = "12345"  # Menos de 11 dígitos
        with self.assertRaises(ErrorValidacionContable) as ctx:
            self.motor.registrar_asiento(asiento)
        self.assertIn("11 dígitos", str(ctx.exception))

    def test_04_rechaza_cuenta_pcge_inexistente(self):
        asiento = self._asiento_venta_valido("CUO-CTA")
        asiento["lineas"][0]["cuenta"] = "9999"
        with self.assertRaises(ErrorValidacionContable) as ctx:
            self.motor.registrar_asiento(asiento)
        self.assertIn("no existe", str(ctx.exception))

    def test_05_extorno_invierte_debe_y_haber_y_audita(self):
        self.motor.registrar_asiento(self._asiento_venta_valido("CUO-0100"))
        ext = self.motor.extornar_asiento("CUO-0100", motivo="Error de emisión")
        self.assertEqual(ext["cuo_extorno"], "EXT-CUO-0100")

        asientos = {a["cuo"]: a for a in self.motor.listar_asientos()}
        self.assertEqual(asientos["CUO-0100"]["estado"], "EXTORNADO")
        self.assertEqual(asientos["EXT-CUO-0100"]["estado"], "EXTORNO")

        # Verificar inversión exacta Debe <-> Haber
        orig_l0 = asientos["CUO-0100"]["lineas"][0]
        ext_l0 = asientos["EXT-CUO-0100"]["lineas"][0]
        self.assertEqual(orig_l0["debe"], ext_l0["haber"])
        self.assertEqual(orig_l0["haber"], ext_l0["debe"])

        # Verificar registro en auditoría
        auditoria = self.motor.obtener_auditoria()
        self.assertTrue(any(ev["accion"] == "EXTORNO_ASIENTO" and ev["cuo_afectado"] == "EXT-CUO-0100" for ev in auditoria))

    def test_06_rechaza_doble_extorno(self):
        self.motor.extornar_asiento("CUO-0001", motivo="Prueba extorno")
        with self.assertRaises(ErrorValidacionContable):
            self.motor.extornar_asiento("CUO-0001", motivo="Segundo intento")

    def test_07_cierre_periodo_bloquea_nuevos_registros(self):
        self.motor.cambiar_estado_periodo("2026-06", "CERRADO")
        with self.assertRaises(ErrorValidacionContable) as ctx:
            self.motor.registrar_asiento(self._asiento_venta_valido("CUO-CERRADO"))
        self.assertIn("CERRADO", str(ctx.exception))

        # Reabrir permite registrar nuevamente
        self.motor.cambiar_estado_periodo("2026-06", "ABIERTO")
        res = self.motor.registrar_asiento(self._asiento_venta_valido("CUO-REABIERTO"))
        self.assertEqual(res["cuo"], "CUO-REABIERTO")

    def test_08_generacion_ple_5_1_formato_sunat(self):
        nombre, contenido = self.motor.generar_ple_5_1(ruc_empresa="20601849211", periodo="2026-06")
        self.assertEqual(nombre, "LE2060184921120260600050100001111.txt")
        lineas = contenido.splitlines()
        self.assertGreaterEqual(len(lineas), 19)
        # Cada línea del PLE 5.1 debe terminar en pipe '|' y contener 21 campos
        for l in lineas:
            self.assertTrue(l.endswith("|"))
            self.assertEqual(len(l.split("|")) - 1, 21)

    def test_09_mayor_mantiene_cuadre_global(self):
        mayor = self.motor.obtener_libro_mayor()
        total_debe = round(sum(c["total_debe"] for c in mayor), 2)
        total_haber = round(sum(c["total_haber"] for c in mayor), 2)
        self.assertGreater(total_debe, 0)
        self.assertEqual(total_debe, total_haber)


if __name__ == "__main__":
    unittest.main()

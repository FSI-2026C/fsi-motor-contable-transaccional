#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas Avanzadas QA — Casos Borde SUNAT, Atomicidad ACID y Rendimiento Transaccional
Cubre escenarios críticos de estrés, precisión decimal, inmutabilidad y rollback.
"""

import os
import sqlite3
import sys
import tempfile
import time
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from motor_contable import ErrorValidacionContable, MotorContable


class TestCasosBordeYRendimientoQA(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.motor = MotorContable(self.tmp.name)

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_01_rechaza_linea_con_debe_y_haber_simultaneos(self):
        with self.assertRaises(ErrorValidacionContable):
            self.motor.registrar_asiento({
                "cuo": "CUO-EDGE-01",
                "fecha": "2026-06-18",
                "libro_sunat": "05 · Libro Diario",
                "tipo_doc": "00 - Otros",
                "num_doc": "OP-0010",
                "ruc_tercero": "20601849211",
                "razon_social": "EMPRESA TEST S.A.C.",
                "glosa": "Línea inválida con cargo y abono simultáneo",
                "lineas": [
                    {"cuenta": "1041", "debe": 100.00, "haber": 50.00},
                    {"cuenta": "1212", "debe": 0.00, "haber": 50.00},
                ],
            })

    def test_02_rechaza_importes_negativos_o_cero(self):
        with self.assertRaises(ErrorValidacionContable):
            self.motor.registrar_asiento({
                "cuo": "CUO-EDGE-02",
                "fecha": "2026-06-18",
                "libro_sunat": "05 · Libro Diario",
                "tipo_doc": "00 - Otros",
                "num_doc": "OP-0011",
                "ruc_tercero": "20601849211",
                "razon_social": "EMPRESA TEST S.A.C.",
                "glosa": "Prueba de validación de importes negativos",
                "lineas": [
                    {"cuenta": "1041", "debe": -100.00, "haber": 0.00},
                    {"cuenta": "1212", "debe": 0.00, "haber": -100.00},
                ],
            })

    def test_03_rechaza_cuo_duplicado_preservando_integridad(self):
        with self.assertRaises(ErrorValidacionContable) as ctx:
            self.motor.registrar_asiento({
                "cuo": "CUO-0001",  # Ya existe en la semilla
                "fecha": "2026-06-18",
                "libro_sunat": "14 · Registro de Ventas e Ingresos",
                "tipo_doc": "01 - Factura",
                "num_doc": "F001-09999",
                "ruc_tercero": "20601849211",
                "razon_social": "CLIENTE DUPLICADO S.A.C.",
                "glosa": "Intento de insertar CUO duplicado para probar unicidad",
                "lineas": [
                    {"cuenta": "1212", "debe": 118.00, "haber": 0.00},
                    {"cuenta": "4011", "debe": 0.00, "haber": 18.00},
                    {"cuenta": "7012", "debe": 0.00, "haber": 100.00},
                ],
            })
        self.assertIn("Ya existe", str(ctx.exception))

    def test_04_rechaza_glosa_corta_y_fecha_invalida(self):
        with self.assertRaises(ErrorValidacionContable):
            self.motor.registrar_asiento({
                "cuo": "CUO-EDGE-04",
                "fecha": "20-06-2026",  # Formato inválido
                "libro_sunat": "05 · Libro Diario",
                "tipo_doc": "00 - Otros",
                "num_doc": "OP-0012",
                "ruc_tercero": "20601849211",
                "razon_social": "TEST S.A.C.",
                "glosa": "Glosa válida de prueba contable",
                "lineas": [
                    {"cuenta": "1041", "debe": 50.00, "haber": 0.00},
                    {"cuenta": "1212", "debe": 0.00, "haber": 50.00},
                ],
            })

        with self.assertRaises(ErrorValidacionContable):
            self.motor.registrar_asiento({
                "cuo": "CUO-EDGE-05",
                "fecha": "2026-06-20",
                "libro_sunat": "05 · Libro Diario",
                "tipo_doc": "00 - Otros",
                "num_doc": "OP-0013",
                "ruc_tercero": "20601849211",
                "razon_social": "TEST S.A.C.",
                "glosa": "Corta",  # Menos de 8 caracteres
                "lineas": [
                    {"cuenta": "1041", "debe": 50.00, "haber": 0.00},
                    {"cuenta": "1212", "debe": 0.00, "haber": 50.00},
                ],
            })

    def test_05_precision_decimal_centimos_igv_18(self):
        """Verifica que importes con decimales complejos cuadren al centavo sin errores de punto flotante."""
        total = 1538.47
        base = round(total / 1.18, 2)
        igv = round(total - base, 2)
        res = self.motor.registrar_asiento({
            "cuo": "CUO-DEC-01",
            "fecha": "2026-06-21",
            "libro_sunat": "14 · Registro de Ventas e Ingresos",
            "tipo_doc": "01 - Factura",
            "num_doc": "F001-01538",
            "ruc_tercero": "20604152631",
            "razon_social": "PRECISIÓN DECIMAL S.A.C.",
            "glosa": "Venta con decimales complejos para validar precisión contable",
            "lineas": [
                {"cuenta": "1212", "debe": total, "haber": 0.00},
                {"cuenta": "4011", "debe": 0.00, "haber": igv},
                {"cuenta": "7012", "debe": 0.00, "haber": base},
            ],
        })
        self.assertEqual(res["total"], total)

    def test_06_atomicidad_acid_rollback_en_bd(self):
        """Verifica que si falla una validación a mitad del proceso no queda cabecera huérfana en SQLite."""
        antes = len(self.motor.listar_asientos())
        with self.assertRaises(ErrorValidacionContable):
            self.motor.registrar_asiento({
                "cuo": "CUO-ROLLBACK",
                "fecha": "2026-06-22",
                "libro_sunat": "05 · Libro Diario",
                "tipo_doc": "00 - Otros",
                "num_doc": "OP-9999",
                "ruc_tercero": "20604152631",
                "razon_social": "PRUEBA ACID S.A.C.",
                "glosa": "Prueba de rollback atómico ante cuenta inválida en segunda línea",
                "lineas": [
                    {"cuenta": "1041", "debe": 500.00, "haber": 0.00},
                    {"cuenta": "8888", "debe": 0.00, "haber": 500.00},  # Cuenta inexistente
                ],
            })
        despues = len(self.motor.listar_asientos())
        self.assertEqual(antes, despues)

        conn = sqlite3.connect(self.tmp.name)
        huerfano = conn.execute("SELECT COUNT(*) FROM asientos_cabecera WHERE cuo = 'CUO-ROLLBACK'").fetchone()[0]
        conn.close()
        self.assertEqual(huerfano, 0)

    def test_07_carga_transaccional_150_asientos_y_cuadre_ple(self):
        """Prueba de estrés QA: inserta 150 asientos consecutivos, verifica tiempo, cuadre y PLE masivo."""
        inicio = time.perf_counter()
        for i in range(1, 151):
            total = round(118.00 + i * 1.18, 2)
            base = round(total / 1.18, 2)
            igv = round(total - base, 2)
            self.motor.registrar_asiento({
                "cuo": f"CUO-LOAD-{i:04d}",
                "fecha": "2026-06-25",
                "libro_sunat": "14 · Registro de Ventas e Ingresos",
                "tipo_doc": "01 - Factura",
                "num_doc": f"F001-{i:05d}",
                "ruc_tercero": "20604152631",
                "razon_social": f"CLIENTE CARGA {i} S.A.C.",
                "glosa": f"Operación de prueba de carga transaccional lote #{i}",
                "lineas": [
                    {"cuenta": "1212", "debe": total, "haber": 0.00},
                    {"cuenta": "4011", "debe": 0.00, "haber": igv},
                    {"cuenta": "7012", "debe": 0.00, "haber": base},
                ],
            }, usuario="qa_stress")
        duracion = time.perf_counter() - inicio

        # Debe completar 150 transacciones ACID SQLite en menos de 10 segundos
        self.assertLess(duracion, 10.0, f"Carga demasiado lenta: {duracion:.2f}s")

        # Cuadre global del Libro Mayor tras 155 asientos (5 semilla + 150 carga)
        mayor = self.motor.obtener_libro_mayor()
        sum_debe = round(sum(c["total_debe"] for c in mayor), 2)
        sum_haber = round(sum(c["total_haber"] for c in mayor), 2)
        self.assertEqual(sum_debe, sum_haber)

        # Validación de exportación PLE 5.1 masiva (19 + 450 = 469 líneas)
        _, contenido = self.motor.generar_ple_5_1(periodo="2026-06", usuario="qa_stress")
        self.assertEqual(len(contenido.splitlines()), 19 + 150 * 3)


if __name__ == "__main__":
    unittest.main()

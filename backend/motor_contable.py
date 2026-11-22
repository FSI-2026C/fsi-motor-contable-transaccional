#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOTOR CONTABLE TRANSACCIONAL (SUNAT FORMATO 5.1 / PCGE)
Implementa:
- Persistencia relacional normalizada en SQLite con transacciones ACID (COMMIT / ROLLBACK).
- Validación estricta de reglas contables y tributarias SUNAT.
- Inmutabilidad contable mediante Extorno / Contra-asiento automático.
- Cierre y reapertura de períodos contables.
- Generación del archivo oficial PLE Formato 5.1 (.txt delimitado por pipes '|').
"""

import os
import re
import sqlite3
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "database", "schema.sql")

CATALOGO_PCGE_BASE = [
    ("1011", "Elemento 1 - Activo Disponible", "Caja Moneda Nacional"),
    ("1041", "Elemento 1 - Activo Disponible", "Cuentas corrientes operativas (Banco BCP MN)"),
    ("1212", "Elemento 1 - Activo Exigible", "Facturas, boletas y otros comprobantes por cobrar - Emitidas"),
    ("2011", "Elemento 2 - Activo Realizable", "Mercaderías al costo"),
    ("3351", "Elemento 3 - Activo Inmovilizado", "Muebles, enseres y equipos diversos"),
    ("3913", "Elemento 3 - Activo Inmovilizado", "Depreciación acumulada inmuebles, maquinaria y equipo"),
    ("4011", "Elemento 4 - Pasivo Tributario", "Gobierno Nacional - IGV Cuenta Propia (18%)"),
    ("4031", "Elemento 4 - Pasivo Tributario", "Instituciones públicas - EsSalud (9%) y ONP (13%)"),
    ("4111", "Elemento 4 - Pasivo Laboral", "Remuneraciones por pagar - Sueldos netos"),
    ("4212", "Elemento 4 - Pasivo Comercial", "Facturas, boletas y otros comprobantes por pagar - Emitidas"),
    ("5011", "Elemento 5 - Patrimonio", "Capital social - Acciones y participaciones"),
    ("6011", "Elemento 6 - Gastos por Naturaleza", "Compras de mercaderías"),
    ("6111", "Elemento 6 - Variación de Existencias", "Variación de existencias - Mercaderías"),
    ("6211", "Elemento 6 - Gastos de Personal", "Remuneraciones - Sueldos y salarios"),
    ("6271", "Elemento 6 - Gastos de Personal", "Régimen de prestaciones de salud - EsSalud (9%)"),
    ("6361", "Elemento 6 - Gastos de Servicios", "Servicios básicos - Energía eléctrica, agua e internet"),
    ("6814", "Elemento 6 - Valuación y Deterioro", "Depreciación de inmuebles, maquinaria y equipo"),
    ("6912", "Elemento 6 - Costo de Ventas", "Costo de ventas - Mercaderías venta local"),
    ("7012", "Elemento 7 - Ingresos", "Mercaderías - Venta local"),
    ("7911", "Elemento 7 - Cargas Imputables", "Cargas imputables a cuentas de costos y gastos"),
    ("9411", "Elemento 9 - Contabilidad Analítica", "Gastos de administración"),
    ("9511", "Elemento 9 - Contabilidad Analítica", "Gastos de ventas"),
]

ASIENTOS_SEMILLA = [
    {
        "cuo": "CUO-0001",
        "fecha": "2026-06-05",
        "libro_sunat": "14 · Registro de Ventas e Ingresos",
        "tipo_doc": "01 - Factura",
        "num_doc": "F001-00120",
        "ruc_tercero": "20601849211",
        "razon_social": "COMERCIAL ANDINA S.A.C.",
        "glosa": "Por la venta de mercaderías al crédito según Factura Electrónica F001-00120",
        "lineas": [
            {"cuenta": "1212", "debe": 1180.00, "haber": 0.00},
            {"cuenta": "4011", "debe": 0.00, "haber": 180.00},
            {"cuenta": "7012", "debe": 0.00, "haber": 1000.00},
        ],
    },
    {
        "cuo": "CUO-0002",
        "fecha": "2026-06-05",
        "libro_sunat": "01 · Libro Caja y Bancos",
        "tipo_doc": "00 - Otros",
        "num_doc": "OP-994120",
        "ruc_tercero": "20601849211",
        "razon_social": "COMERCIAL ANDINA S.A.C.",
        "glosa": "Por el cobro de la Factura F001-00120 mediante transferencia en Cta. Cte. BCP",
        "lineas": [
            {"cuenta": "1041", "debe": 1180.00, "haber": 0.00},
            {"cuenta": "1212", "debe": 0.00, "haber": 1180.00},
        ],
    },
    {
        "cuo": "CUO-0003",
        "fecha": "2026-06-10",
        "libro_sunat": "08 · Registro de Compras",
        "tipo_doc": "01 - Factura",
        "num_doc": "F002-00450",
        "ruc_tercero": "20519283741",
        "razon_social": "DISTRIBUIDORA NACIONAL S.A.C.",
        "glosa": "Por la compra de mercaderías según Factura F002-00450 y destino a almacén",
        "lineas": [
            {"cuenta": "6011", "debe": 2000.00, "haber": 0.00},
            {"cuenta": "4011", "debe": 360.00, "haber": 0.00},
            {"cuenta": "4212", "debe": 0.00, "haber": 2360.00},
            {"cuenta": "2011", "debe": 2000.00, "haber": 0.00},
            {"cuenta": "6111", "debe": 0.00, "haber": 2000.00},
        ],
    },
    {
        "cuo": "CUO-0004",
        "fecha": "2026-06-15",
        "libro_sunat": "08 · Registro de Compras",
        "tipo_doc": "01 - Factura",
        "num_doc": "F010-00890",
        "ruc_tercero": "20100070970",
        "razon_social": "EMPRESA DE SERVICIOS ELÉCTRICOS S.A.",
        "glosa": "Por el recibo de energía eléctrica del mes y destino a gastos administrativos",
        "lineas": [
            {"cuenta": "6361", "debe": 500.00, "haber": 0.00},
            {"cuenta": "4011", "debe": 90.00, "haber": 0.00},
            {"cuenta": "4212", "debe": 0.00, "haber": 590.00},
            {"cuenta": "9411", "debe": 500.00, "haber": 0.00},
            {"cuenta": "7911", "debe": 0.00, "haber": 500.00},
        ],
    },
    {
        "cuo": "CUO-0005",
        "fecha": "2026-06-30",
        "libro_sunat": "05 · Libro Diario",
        "tipo_doc": "00 - Otros",
        "num_doc": "PLN-2026-06",
        "ruc_tercero": "20601849211",
        "razon_social": "PLANILLA MENSUAL DE TRABAJADORES",
        "glosa": "Por la provisión de planilla de sueldos, ONP (13%) y EsSalud (9%) del mes",
        "lineas": [
            {"cuenta": "6211", "debe": 3000.00, "haber": 0.00},
            {"cuenta": "6271", "debe": 270.00, "haber": 0.00},
            {"cuenta": "4031", "debe": 0.00, "haber": 660.00},
            {"cuenta": "4111", "debe": 0.00, "haber": 2610.00},
        ],
    },
]


class ErrorValidacionContable(ValueError):
    """Excepción lanzada cuando un asiento infringe una regla normativa SUNAT o contable."""


class MotorContable:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.inicializar_base_datos()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def inicializar_base_datos(self, cargar_semilla: bool = True):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        conn = self._connect()
        try:
            conn.executescript(schema_sql)
            cur = conn.cursor()

            # Sembrar período base
            cur.execute(
                "INSERT OR IGNORE INTO periodos_contables (periodo, estado) VALUES (?, 'ABIERTO')",
                ("2026-06",),
            )

            # Sembrar catálogo oficial PCGE
            cur.executemany(
                "INSERT OR IGNORE INTO cuentas_pcge (codigo, clase, denominacion) VALUES (?, ?, ?)",
                CATALOGO_PCGE_BASE,
            )
            conn.commit()
        finally:
            conn.close()

        if cargar_semilla and len(self.listar_asientos()) == 0:
            for asiento in ASIENTOS_SEMILLA:
                self.registrar_asiento(asiento, usuario="sistema_inicial")

    def reiniciar_datos(self):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM asientos_detalle")
            conn.execute("DELETE FROM asientos_cabecera")
            conn.execute("DELETE FROM auditoria_transacciones")
            conn.execute("DELETE FROM periodos_contables")
            conn.execute(
                "INSERT INTO periodos_contables (periodo, estado) VALUES ('2026-06', 'ABIERTO')"
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        for asiento in ASIENTOS_SEMILLA:
            self.registrar_asiento(asiento, usuario="sistema_inicial")

    def _validar_asiento(self, conn: sqlite3.Connection, data: dict):
        cuo = str(data.get("cuo", "")).strip()
        fecha = str(data.get("fecha", "")).strip()
        libro = str(data.get("libro_sunat", "")).strip()
        tipo_doc = str(data.get("tipo_doc", "")).strip()
        num_doc = str(data.get("num_doc", "")).strip()
        ruc = str(data.get("ruc_tercero", "")).strip()
        glosa = str(data.get("glosa", "")).strip()
        lineas = data.get("lineas", [])

        if not cuo:
            raise ErrorValidacionContable("El Código Único de Operación (CUO) es obligatorio.")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
            raise ErrorValidacionContable("La fecha de operación debe tener formato YYYY-MM-DD.")
        if not libro or not tipo_doc or len(num_doc) < 4:
            raise ErrorValidacionContable("Libro auxiliar, tipo y número de comprobante son obligatorios (SUNAT).")
        if len(glosa) < 8:
            raise ErrorValidacionContable("La glosa descriptiva debe contener al menos 8 caracteres.")
        if not re.match(r"^\d{11}$", ruc):
            raise ErrorValidacionContable("El RUC del tercero debe tener exactamente 11 dígitos numéricos.")

        periodo = fecha[:7]
        cur = conn.cursor()
        cur.execute("SELECT estado FROM periodos_contables WHERE periodo = ?", (periodo,))
        row_per = cur.fetchone()
        if row_per and row_per["estado"] == "CERRADO":
            raise ErrorValidacionContable(
                f"El período contable {periodo} se encuentra CERRADO. No se permiten nuevos registros."
            )

        if not isinstance(lineas, list) or len(lineas) < 2:
            raise ErrorValidacionContable("Un asiento contable requiere como mínimo 2 líneas (Cargo y Abono).")

        total_debe = 0.0
        total_haber = 0.0
        tiene_cargo = False
        tiene_abono = False

        cuentas_validas = {
            r["codigo"] for r in cur.execute("SELECT codigo FROM cuentas_pcge").fetchall()
        }

        for idx, linea in enumerate(lineas, start=1):
            cta = str(linea.get("cuenta", "")).strip()
            debe = round(float(linea.get("debe", 0) or 0), 2)
            haber = round(float(linea.get("haber", 0) or 0), 2)

            if cta not in cuentas_validas:
                raise ErrorValidacionContable(f"Línea {idx}: La cuenta PCGE '{cta}' no existe en el catálogo.")
            if debe < 0 or haber < 0:
                raise ErrorValidacionContable(f"Línea {idx}: Los importes de Debe y Haber no pueden ser negativos.")
            if debe > 0 and haber > 0:
                raise ErrorValidacionContable(f"Línea {idx}: Una misma línea no puede tener importe en Debe y Haber a la vez.")
            if debe == 0 and haber == 0:
                raise ErrorValidacionContable(f"Línea {idx}: Debe ingresar un importe mayor a 0.00 en Debe o Haber.")

            if debe > 0:
                tiene_cargo = True
            if haber > 0:
                tiene_abono = True

            total_debe = round(total_debe + debe, 2)
            total_haber = round(total_haber + haber, 2)

        if not (tiene_cargo and tiene_abono):
            raise ErrorValidacionContable("El asiento debe contener al menos una cuenta deudora (Debe) y una acreedora (Haber).")

        if total_debe <= 0 or total_debe != total_haber:
            raise ErrorValidacionContable(
                f"Principio de Partida Doble incumplido: Total Debe (S/ {total_debe:.2f}) ≠ Total Haber (S/ {total_haber:.2f})."
            )

        return {
            "cuo": cuo,
            "periodo": periodo,
            "fecha": fecha,
            "libro_sunat": libro,
            "tipo_doc": tipo_doc,
            "num_doc": num_doc.upper(),
            "ruc_tercero": ruc,
            "razon_social": str(data.get("razon_social", "")).strip().upper(),
            "glosa": glosa,
            "total": total_debe,
            "lineas": [
                {
                    "cuenta": str(linea["cuenta"]).strip(),
                    "debe": round(float(linea.get("debe", 0) or 0), 2),
                    "haber": round(float(linea.get("haber", 0) or 0), 2),
                }
                for linea in lineas
            ],
        }

    def registrar_asiento(self, data: dict, usuario: str = "contador") -> dict:
        """Registra un asiento contable dentro de una transacción ACID (BEGIN / COMMIT / ROLLBACK)."""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            asiento = self._validar_asiento(conn, data)
            cur = conn.cursor()

            # Garantizar existencia del período si es un mes nuevo
            cur.execute(
                "INSERT OR IGNORE INTO periodos_contables (periodo, estado) VALUES (?, 'ABIERTO')",
                (asiento["periodo"],),
            )

            # Verificar que no exista un CUO duplicado
            cur.execute("SELECT cuo FROM asientos_cabecera WHERE cuo = ?", (asiento["cuo"],))
            if cur.fetchone():
                raise ErrorValidacionContable(f"Ya existe un asiento registrado con el código {asiento['cuo']}.")

            cur.execute(
                """
                INSERT INTO asientos_cabecera
                (cuo, periodo, fecha, libro_sunat, tipo_doc, num_doc, ruc_tercero, razon_social, glosa, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'REGISTRADO')
                """,
                (
                    asiento["cuo"],
                    asiento["periodo"],
                    asiento["fecha"],
                    asiento["libro_sunat"],
                    asiento["tipo_doc"],
                    asiento["num_doc"],
                    asiento["ruc_tercero"],
                    asiento["razon_social"],
                    asiento["glosa"],
                ),
            )

            for idx, linea in enumerate(asiento["lineas"], start=1):
                cur.execute(
                    """
                    INSERT INTO asientos_detalle (cuo, item, cuenta_pcge, debe, haber)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (asiento["cuo"], idx, linea["cuenta"], linea["debe"], linea["haber"]),
                )

            cur.execute(
                """
                INSERT INTO auditoria_transacciones (usuario, accion, cuo_afectado, detalle)
                VALUES (?, 'REGISTRO_ASIENTO', ?, ?)
                """,
                (
                    usuario,
                    asiento["cuo"],
                    f"Registro de asiento ({asiento['libro_sunat']}) por S/ {asiento['total']:.2f} - Doc. {asiento['num_doc']}",
                ),
            )

            conn.commit()
            return asiento
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def extornar_asiento(self, cuo_original: str, motivo: str = "", usuario: str = "contador") -> dict:
        """
        Inmutabilidad SUNAT: En lugar de borrar un asiento contabilizado,
        genera un contra-asiento invirtiendo Debe <-> Haber en una transacción ACID.
        """
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.cursor()

            cur.execute("SELECT * FROM asientos_cabecera WHERE cuo = ?", (cuo_original,))
            orig = cur.fetchone()
            if not orig:
                raise ErrorValidacionContable(f"No se encontró el asiento {cuo_original}.")
            if orig["estado"] != "REGISTRADO":
                raise ErrorValidacionContable(
                    f"El asiento {cuo_original} no puede extornarse porque su estado actual es {orig['estado']}."
                )

            cur.execute("SELECT estado FROM periodos_contables WHERE periodo = ?", (orig["periodo"],))
            row_per = cur.fetchone()
            if row_per and row_per["estado"] == "CERRADO":
                raise ErrorValidacionContable(
                    f"El período {orig['periodo']} está CERRADO. No se pueden generar extornos."
                )

            cur.execute(
                "SELECT cuenta_pcge, debe, haber FROM asientos_detalle WHERE cuo = ? ORDER BY item ASC",
                (cuo_original,),
            )
            detalles_orig = cur.fetchall()

            cuo_extorno = f"EXT-{cuo_original}"
            glosa_ext = f"EXTORNO DE {cuo_original}: {motivo.strip() or orig['glosa']}"

            # Marcar original como EXTORNADO
            cur.execute("UPDATE asientos_cabecera SET estado = 'EXTORNADO' WHERE cuo = ?", (cuo_original,))

            # Insertar contra-asiento de extorno
            cur.execute(
                """
                INSERT INTO asientos_cabecera
                (cuo, periodo, fecha, libro_sunat, tipo_doc, num_doc, ruc_tercero, razon_social, glosa, estado, cuo_referencia)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'EXTORNO', ?)
                """,
                (
                    cuo_extorno,
                    orig["periodo"],
                    orig["fecha"],
                    orig["libro_sunat"],
                    orig["tipo_doc"],
                    orig["num_doc"],
                    orig["ruc_tercero"],
                    orig["razon_social"],
                    glosa_ext,
                    cuo_original,
                ),
            )

            total_ext = 0.0
            for idx, d in enumerate(detalles_orig, start=1):
                nuevo_debe = round(float(d["haber"]), 2)
                nuevo_haber = round(float(d["debe"]), 2)
                total_ext = round(total_ext + nuevo_debe, 2)
                cur.execute(
                    """
                    INSERT INTO asientos_detalle (cuo, item, cuenta_pcge, debe, haber)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (cuo_extorno, idx, d["cuenta_pcge"], nuevo_debe, nuevo_haber),
                )

            cur.execute(
                """
                INSERT INTO auditoria_transacciones (usuario, accion, cuo_afectado, detalle)
                VALUES (?, 'EXTORNO_ASIENTO', ?, ?)
                """,
                (
                    usuario,
                    cuo_extorno,
                    f"Contra-asiento automático que extorna {cuo_original} por S/ {total_ext:.2f} (Inmutabilidad SUNAT)",
                ),
            )

            conn.commit()
            return {"cuo_original": cuo_original, "cuo_extorno": cuo_extorno, "importe": total_ext}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def cambiar_estado_periodo(self, periodo: str, nuevo_estado: str, usuario: str = "contador") -> dict:
        if nuevo_estado not in ("ABIERTO", "CERRADO"):
            raise ErrorValidacionContable("Estado de período inválido.")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO periodos_contables (periodo, estado) VALUES (?, 'ABIERTO')",
                (periodo,),
            )

            if nuevo_estado == "CERRADO":
                # Verificar que el libro del período esté 100% cuadrado antes de cerrar
                cur.execute(
                    """
                    SELECT ROUND(COALESCE(SUM(d.debe), 0), 2) AS sum_d,
                           ROUND(COALESCE(SUM(d.haber), 0), 2) AS sum_h
                    FROM asientos_detalle d
                    JOIN asientos_cabecera c ON c.cuo = d.cuo
                    WHERE c.periodo = ?
                    """,
                    (periodo,),
                )
                row = cur.fetchone()
                if row["sum_d"] != row["sum_h"]:
                    raise ErrorValidacionContable(
                        f"No se puede cerrar el período {periodo}: existe descuadre en el Libro Diario."
                    )
                fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute(
                    "UPDATE periodos_contables SET estado = 'CERRADO', fecha_cierre = ?, usuario_cierre = ? WHERE periodo = ?",
                    (fecha_cierre, usuario, periodo),
                )
                accion = "CIERRE_PERIODO"
                detalle = f"Cierre contable del período {periodo} (Total cuadrado: S/ {row['sum_d']:.2f})"
            else:
                cur.execute(
                    "UPDATE periodos_contables SET estado = 'ABIERTO', fecha_cierre = NULL, usuario_cierre = NULL WHERE periodo = ?",
                    (periodo,),
                )
                accion = "REAPERTURA_PERIODO"
                detalle = f"Reapertura administrativa del período {periodo}"

            cur.execute(
                "INSERT INTO auditoria_transacciones (usuario, accion, cuo_afectado, detalle) VALUES (?, ?, ?, ?)",
                (usuario, accion, periodo, detalle),
            )
            conn.commit()
            return {"periodo": periodo, "estado": nuevo_estado}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def listar_asientos(self, periodo: str = None) -> list:
        conn = self._connect()
        try:
            cur = conn.cursor()
            if periodo:
                cur.execute(
                    "SELECT * FROM asientos_cabecera WHERE periodo = ? ORDER BY fecha ASC, creado_en ASC, cuo ASC",
                    (periodo,),
                )
            else:
                cur.execute("SELECT * FROM asientos_cabecera ORDER BY fecha ASC, creado_en ASC, cuo ASC")
            cabeceras = cur.fetchall()

            resultado = []
            for c in cabeceras:
                item = dict(c)
                cur.execute(
                    """
                    SELECT d.item, d.cuenta_pcge AS cuenta, p.denominacion, d.debe, d.haber
                    FROM asientos_detalle d
                    JOIN cuentas_pcge p ON p.codigo = d.cuenta_pcge
                    WHERE d.cuo = ?
                    ORDER BY d.item ASC
                    """,
                    (c["cuo"],),
                )
                item["lineas"] = [dict(r) for r in cur.fetchall()]
                resultado.append(item)
            return resultado
        finally:
            conn.close()

    def obtener_libro_mayor(self, periodo: str = None) -> list:
        conn = self._connect()
        try:
            cur = conn.cursor()
            query = """
                SELECT p.codigo,
                       p.clase,
                       p.denominacion,
                       ROUND(SUM(d.debe), 2) AS total_debe,
                       ROUND(SUM(d.haber), 2) AS total_haber
                FROM asientos_detalle d
                JOIN cuentas_pcge p ON p.codigo = d.cuenta_pcge
                JOIN asientos_cabecera c ON c.cuo = d.cuo
            """
            params = ()
            if periodo:
                query += " WHERE c.periodo = ?"
                params = (periodo,)
            query += " GROUP BY p.codigo, p.clase, p.denominacion ORDER BY p.codigo ASC"
            cur.execute(query, params)
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                saldo = round(d["total_debe"] - d["total_haber"], 2)
                d["saldo"] = abs(saldo)
                d["naturaleza"] = "Deudor" if saldo > 0 else ("Acreedor" if saldo < 0 else "Saldada")
                rows.append(d)
            return rows
        finally:
            conn.close()

    def obtener_periodos(self) -> list:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM periodos_contables ORDER BY periodo DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def obtener_cuentas_pcge(self) -> list:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM cuentas_pcge ORDER BY codigo ASC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def obtener_auditoria(self, limite: int = 50) -> list:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM auditoria_transacciones ORDER BY id DESC LIMIT ?",
                (limite,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def generar_ple_5_1(self, ruc_empresa: str = "20601849211", periodo: str = "2026-06", usuario: str = "contador") -> tuple:
        """
        Genera el archivo oficial de texto PLE SUNAT Formato 5.1 (Libro Diario)
        Nombre estándar: LE[RUC][AAAAMM]00050100001111.txt
        Campos separados por pipe '|' según estructura oficial SUNAT.
        """
        asientos = self.listar_asientos(periodo=periodo)
        periodo_ple = periodo.replace("-", "") + "00"
        lineas_txt = []

        for a in asientos:
            fecha_ddmmyyyy = "/".join(reversed(a["fecha"].split("-")))
            cod_tipo_doc = a["tipo_doc"].split(" ")[0].strip() if a["tipo_doc"] else "00"
            if "-" in a["num_doc"]:
                serie, numero = a["num_doc"].split("-", 1)
            else:
                serie, numero = "0000", a["num_doc"]

            for idx, linea in enumerate(a["lineas"], start=1):
                correlativo = f"M{idx:04d}"
                # Estructura oficial simplificada 21 campos Formato 5.1 PLE SUNAT
                campos = [
                    periodo_ple,                   # 1. Período (AAAAMM00)
                    a["cuo"],                      # 2. Código Único de Operación (CUO)
                    correlativo,                   # 3. Número correlativo del asiento (M0001)
                    linea["cuenta"],               # 4. Código de cuenta contable PCGE
                    "",                            # 5. Código de unidad de operación
                    "",                            # 6. Código de centro de costo
                    "PEN",                         # 7. Tipo de moneda de origen
                    "6",                           # 8. Tipo doc identidad emisor (6 = RUC)
                    a["ruc_tercero"],              # 9. Número de RUC emisor
                    cod_tipo_doc,                  # 10. Tipo de comprobante de pago (Tabla 10)
                    serie,                         # 11. Número de serie del comprobante
                    numero,                        # 12. Número del comprobante
                    fecha_ddmmyyyy,                # 13. Fecha contable
                    "",                            # 14. Fecha de vencimiento
                    fecha_ddmmyyyy,                # 15. Fecha de operación o emisión
                    a["glosa"].replace("|", " "),  # 16. Glosa o descripción de la operación
                    "",                            # 17. Glosa referencial
                    f"{linea['debe']:.2f}",        # 18. Movimientos del Debe
                    f"{linea['haber']:.2f}",       # 19. Movimientos del Haber
                    "",                            # 20. Dato estructurado (Libro Auxiliar)
                    "1",                           # 21. Estado de la operación (1 = vigente)
                ]
                lineas_txt.append("|".join(campos) + "|")

        nombre_archivo = f"LE{ruc_empresa}{periodo_ple}050100001111.txt"
        contenido = "\r\n".join(lineas_txt)

        # Registrar exportación en auditoría
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO auditoria_transacciones (usuario, accion, cuo_afectado, detalle) VALUES (?, 'EXPORTACION_PLE', ?, ?)",
                (usuario, periodo, f"Generación de archivo PLE SUNAT 5.1: {nombre_archivo} ({len(lineas_txt)} registros)"),
            )
            conn.commit()
        finally:
            conn.close()

        return nombre_archivo, contenido

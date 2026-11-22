#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERVIDOR WEB Y API REST — MOTOR CONTABLE TRANSACCIONAL (SUNAT FORMATO 5.1)
Usa únicamente librería estándar de Python + SQLite (sin dependencias externas).
"""

import json
import os
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from motor_contable import ErrorValidacionContable, MotorContable

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
DB_PATH = os.path.join(PROJECT_ROOT, "database", "finanzas_sunat.db")
PORT = 8080

motor = MotorContable(DB_PATH)


class FinanzasHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_json(self, data: dict, status: int = 200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/estado-sistema":
            periodo = params.get("periodo", ["2026-06"])[0]
            return self._send_json({
                "ok": True,
                "periodo_activo": periodo,
                "periodos": motor.obtener_periodos(),
                "cuentas_pcge": motor.obtener_cuentas_pcge(),
                "asientos": motor.listar_asientos(),
                "mayor": motor.obtener_libro_mayor(),
                "auditoria": motor.obtener_auditoria(),
            })

        if parsed.path == "/api/asientos":
            return self._send_json({"ok": True, "asientos": motor.listar_asientos()})

        if parsed.path == "/api/exportar/ple":
            periodo = params.get("periodo", ["2026-06"])[0]
            nombre_archivo, contenido = motor.generar_ple_5_1(periodo=periodo)
            raw = contenido.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{nombre_archivo}"')
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            body = self._read_json()

            if parsed.path == "/api/asientos":
                asiento = motor.registrar_asiento(body, usuario=body.get("usuario", "contador"))
                return self._send_json({"ok": True, "asiento": asiento}, status=201)

            if parsed.path == "/api/asientos/extornar":
                res = motor.extornar_asiento(
                    cuo_original=body.get("cuo", ""),
                    motivo=body.get("motivo", ""),
                    usuario=body.get("usuario", "contador"),
                )
                return self._send_json({"ok": True, "extorno": res}, status=201)

            if parsed.path == "/api/periodo/estado":
                res = motor.cambiar_estado_periodo(
                    periodo=body.get("periodo", "2026-06"),
                    nuevo_estado=body.get("estado", "CERRADO"),
                    usuario=body.get("usuario", "contador"),
                )
                return self._send_json({"ok": True, "periodo": res})

            if parsed.path == "/api/reset":
                motor.reiniciar_datos()
                return self._send_json({"ok": True})

            return self._send_json({"ok": False, "error": "Endpoint no encontrado"}, status=404)

        except ErrorValidacionContable as exc:
            return self._send_json({"ok": False, "error": str(exc)}, status=400)
        except Exception as exc:
            return self._send_json({"ok": False, "error": f"Error interno: {exc}"}, status=500)


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}/index.html"
    print("=" * 72)
    print(" MOTOR CONTABLE TRANSACCIONAL — FORMATO 5.1 LIBRO DIARIO SUNAT (PCGE)")
    print(f" Base de datos SQLite : {DB_PATH}")
    print(f" Abrir en navegador   : {url}")
    print("=" * 72)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    server = ThreadingHTTPServer(("127.0.0.1", PORT), FinanzasHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")

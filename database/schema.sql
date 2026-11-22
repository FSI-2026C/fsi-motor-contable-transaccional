-- ============================================================================
-- ESQUEMA RELACIONAL NORMALIZADO — MOTOR CONTABLE TRANSACCIONAL (SUNAT 5.1)
-- Base de datos: SQLite 3 con Integridad Referencial (FOREIGN KEYS) y CHECKS
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. Control de Períodos Contables (Bloqueo por Cierre Mensual)
CREATE TABLE IF NOT EXISTS periodos_contables (
    periodo        TEXT PRIMARY KEY,
    estado         TEXT NOT NULL DEFAULT 'ABIERTO' CHECK (estado IN ('ABIERTO', 'CERRADO')),
    fecha_cierre   TEXT,
    usuario_cierre TEXT
);

-- 2. Catálogo Oficial del Plan Contable General Empresarial (PCGE)
CREATE TABLE IF NOT EXISTS cuentas_pcge (
    codigo       TEXT PRIMARY KEY,
    clase        TEXT NOT NULL,
    denominacion TEXT NOT NULL
);

-- 3. Cabecera de Asientos Contables (Formato 5.1 Libro Diario SUNAT)
CREATE TABLE IF NOT EXISTS asientos_cabecera (
    cuo            TEXT PRIMARY KEY,
    periodo        TEXT NOT NULL,
    fecha          TEXT NOT NULL,
    libro_sunat    TEXT NOT NULL,
    tipo_doc       TEXT NOT NULL,
    num_doc        TEXT NOT NULL,
    ruc_tercero    TEXT NOT NULL,
    razon_social   TEXT NOT NULL DEFAULT '',
    glosa          TEXT NOT NULL,
    estado         TEXT NOT NULL DEFAULT 'REGISTRADO' CHECK (estado IN ('REGISTRADO', 'EXTORNADO', 'EXTORNO')),
    cuo_referencia TEXT,
    creado_en      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (periodo) REFERENCES periodos_contables(periodo)
);

-- 4. Detalle de Apuntes Contables (Partida Doble por Cuenta PCGE)
CREATE TABLE IF NOT EXISTS asientos_detalle (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cuo         TEXT NOT NULL,
    item        INTEGER NOT NULL,
    cuenta_pcge TEXT NOT NULL,
    debe        REAL NOT NULL DEFAULT 0.0 CHECK (debe >= 0),
    haber       REAL NOT NULL DEFAULT 0.0 CHECK (haber >= 0),
    CHECK (NOT (debe > 0 AND haber > 0)),
    CHECK (debe > 0 OR haber > 0),
    FOREIGN KEY (cuo) REFERENCES asientos_cabecera(cuo) ON DELETE CASCADE,
    FOREIGN KEY (cuenta_pcge) REFERENCES cuentas_pcge(codigo)
);

-- 5. Bitácora de Auditoría Transaccional (Trazabilidad Contable)
CREATE TABLE IF NOT EXISTS auditoria_transacciones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    usuario      TEXT NOT NULL,
    accion       TEXT NOT NULL,
    cuo_afectado TEXT,
    detalle      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_asientos_periodo ON asientos_cabecera(periodo);
CREATE INDEX IF NOT EXISTS idx_detalle_cuo ON asientos_detalle(cuo);
CREATE INDEX IF NOT EXISTS idx_detalle_cuenta ON asientos_detalle(cuenta_pcge);

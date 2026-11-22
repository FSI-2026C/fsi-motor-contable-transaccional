# Plan de Pruebas QA — Motor Contable Transaccional (SUNAT Formato 5.1)

**Responsable QA / Pruebas:** Callo Ccagiavilca, Kevin Joel (`KevinCallo`)  
**Módulo:** Motor Contable Transaccional (Tribu Financiera — ERP FSI)  
**Normativa verificada:** R.S. N° 234-2006/SUNAT (Formato 5.1 Libro Diario y PLE) y Plan Contable General Empresarial (PCGE).

---

## 1. Estrategia de Aseguramiento de Calidad (QA)

El control de calidad del módulo se ejecuta de forma automática en cada `push` y `pull_request` mediante GitHub Actions (`.github/workflows/ci-qa-motor-contable.yml` y `.github/workflows/pr-validacion-flujo.yml`), cubriendo 4 niveles:

1. **Verificación Estática y Esquema SQL:** Compilación Python (`compileall`), sintaxis JavaScript (`node --check`) e integridad referencial de `database/schema.sql`.
2. **Pruebas Unitarias del Motor Contable (`tests/test_motor_contable.py`):** Validación directa de reglas SUNAT, partida doble, extornos, cierre de períodos y generación PLE 5.1.
3. **Pruebas de Integración de API REST (`tests/test_api_integracion.py`):** Validación extremo a extremo vía HTTP (`200`, `201`, `400`) contra SQLite transaccional (ACID).
4. **Control de Definition of Done (`DoD`):** Bloqueo automático si se versionan archivos binarios `.db`, `.env` o si el Pull Request incumple la convención de `docs/flujo-de-trabajo.md`.

---

## 2. Matriz de Casos de Prueba Automatizados

| ID | Suite | Caso de Prueba | Regla SUNAT / Criterio Verificado | Resultado Esperado |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Unitaria | Registro de asiento de venta válido | Partida Doble (`Debe = Haber`) + IGV 18% (`4011`) | Registro confirmado en transacción ACID |
| **TC-02** | Unitaria | Rechazo de asiento descuadrado | Principio de Partida Doble (`Debe ≠ Haber`) | Lanza `ErrorValidacionContable` y ejecuta `ROLLBACK` |
| **TC-03** | Unitaria | Rechazo de RUC inválido | Validación SUNAT de 11 dígitos numéricos | Rechaza registro con error descriptivo |
| **TC-04** | Unitaria | Rechazo de cuenta PCGE inexistente | Integridad referencial con catálogo `cuentas_pcge` | Rechaza registro sin afectar la BD |
| **TC-05** | Unitaria | Extorno de asiento contabilizado | Inmutabilidad SUNAT (contra-asiento `Debe ↔ Haber`) | Marca `EXTORNADO`, crea `EXT-CUO-...` y registra auditoría |
| **TC-06** | Unitaria | Bloqueo de doble extorno | Integridad contable | Impide extornar un asiento ya extornado |
| **TC-07** | Unitaria | Cierre y reapertura de período `2026-06` | Control de período cerrado | Bloquea nuevos asientos en período `CERRADO` |
| **TC-08** | Unitaria | Generación oficial PLE Formato 5.1 | 21 campos delimitados por `|` y nomenclatura `LE...txt` | Archivo válido + evento `EXPORTACION_PLE` en auditoría |
| **TC-09** | Unitaria | Cuadre global del Libro Mayor | Consistencia Diario ↔ Mayor (`SUM(Debe) = SUM(Haber)`) | Totales iguales en todas las cuentas PCGE |
| **TC-10** | Integración | `GET /index.html` y `GET /api/estado-sistema` | Disponibilidad Frontend + API REST | HTTP `200 OK` con 5 asientos semilla y catálogo PCGE |
| **TC-11** | Integración | `POST /api/asientos` (caso válido) | Contrato API REST de registro contable | HTTP `201 Created` |
| **TC-12** | Integración | `POST /api/asientos` (caso descuadrado) | Validación en capa HTTP/Backend | HTTP `400 Bad Request` con detalle del descuadre |
| **TC-13** | Integración | `POST /api/asientos/extornar` + cierre período | Bloqueo transaccional vía API REST | HTTP `201` para extorno y `400` al intentar grabar en cierre |
| **TC-14** | Integración | `GET /api/exportar/ple?periodo=2026-06` | Descarga de Libro Electrónico SUNAT | HTTP `200` con header `Content-Disposition` oficial |

---

## 3. Comando de Ejecución Local para QA

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

# Plan de Pruebas QA — Motor Contable Transaccional (SUNAT Formato 5.1)

**Responsable QA / Pruebas:** Callo Ccagiavilca, Kevin Joel (`KevinCallo`)  
**Módulo:** Motor Contable Transaccional (Tribu Financiera — ERP FSI)  
**Normativa verificada:** R.S. N° 234-2006/SUNAT (Formato 5.1 Libro Diario y PLE) y Plan Contable General Empresarial (PCGE).

---

## 1. Arquitectura de Calidad y Workflows CI/CD (GitHub Actions)

| Workflow | Archivo | Disparador | Qué valida |
| :--- | :--- | :--- | :--- |
| **CI / QA Completo** | `.github/workflows/ci-qa-motor-contable.yml` | `push` / `pull_request` (`develop`, `main`) | Lint (`ruff`), SAST seguridad (`bandit`), sintaxis JS (`node --check`), DoD, **Matriz Python 3.11/3.12**, `pytest-cov` (**Quality Gate ≥ 75%**), reportes HTML/JUnit y validador PLE 5.1 |
| **E2E Navegador Real** | `.github/workflows/qa-e2e-navegador.yml` | `push` / `pull_request` (`develop`, `main`) | Pruebas End-to-End con **Playwright + Chromium** simulando al contador real (registro con destino, extorno modal, auditoría) + capturas de evidencia en Artifacts |
| **Regresión y Estrés** | `.github/workflows/qa-pruebas-regresion-programadas.yml` | `schedule` (nocturno) + `workflow_dispatch` | Regresión completa + carga transaccional ACID de **150 asientos consecutivos** y cuadre masivo PLE 5.1 |
| **Quality Gate PR** | `.github/workflows/pr-validacion-flujo.yml` | `pull_request` (`develop`, `main`) | Valida convención de título (`feat/fix/docs/chore/test`), nombre de rama (`feat/...`) y descripción según `docs/flujo-de-trabajo.md` |

---

## 2. Matriz Completa de Casos de Prueba (22 Casos Automatizados)

### A. Pruebas Unitarias Core SUNAT (`tests/test_motor_contable.py`)
| ID | Caso de Prueba | Regla SUNAT / Criterio Verificado | Resultado Esperado |
| :--- | :--- | :--- | :--- |
| **TC-01** | Registro de asiento de venta válido | Partida Doble (`Debe = Haber`) + IGV 18% (`4011`) | Registro confirmado en transacción ACID |
| **TC-02** | Rechazo de asiento descuadrado | Principio de Partida Doble (`Debe ≠ Haber`) | Lanza `ErrorValidacionContable` y ejecuta `ROLLBACK` |
| **TC-03** | Rechazo de RUC inválido | Validación SUNAT de 11 dígitos numéricos | Rechaza registro con error descriptivo |
| **TC-04** | Rechazo de cuenta PCGE inexistente | Integridad referencial con `cuentas_pcge` | Rechaza registro sin afectar la BD |
| **TC-05** | Extorno de asiento contabilizado | Inmutabilidad SUNAT (contra-asiento `Debe ↔ Haber`) | Marca `EXTORNADO`, crea `EXT-CUO-...` y registra auditoría |
| **TC-06** | Bloqueo de doble extorno | Integridad contable | Impide extornar un asiento ya extornado |
| **TC-07** | Cierre y reapertura de período `2026-06` | Control de período cerrado | Bloquea nuevos asientos en período `CERRADO` |
| **TC-08** | Generación oficial PLE Formato 5.1 | 21 campos delimitados por `|` y nomenclatura `LE...txt` | Archivo válido + evento `EXPORTACION_PLE` en auditoría |
| **TC-09** | Cuadre global del Libro Mayor | Consistencia Diario ↔ Mayor (`SUM(Debe) = SUM(Haber)`) | Totales iguales en todas las cuentas PCGE |

### B. Pruebas de Integración HTTP API REST (`tests/test_api_integracion.py`)
| ID | Caso de Prueba | Endpoint / Capa | Resultado Esperado |
| :--- | :--- | :--- | :--- |
| **TC-10** | Carga de frontend y estado inicial | `GET /index.html` y `GET /api/estado-sistema` | HTTP `200 OK` con 5 asientos semilla y catálogo PCGE |
| **TC-11** | Creación de asiento vía REST | `POST /api/asientos` (payload válido) | HTTP `201 Created` |
| **TC-12** | Rechazo de asiento descuadrado vía REST | `POST /api/asientos` (payload descuadrado) | HTTP `400 Bad Request` con mensaje normativo |
| **TC-13** | Extorno y bloqueo de cierre vía REST | `POST /api/asientos/extornar` + `/api/periodo/estado` | HTTP `201` para extorno y `400` en período cerrado |
| **TC-14** | Descarga de Libro Electrónico PLE 5.1 | `GET /api/exportar/ple?periodo=2026-06` | HTTP `200` con header `Content-Disposition` oficial |

### C. Casos Borde, Atomicidad ACID y Estrés (`tests/test_rendimiento_y_reglas_sunat.py`)
| ID | Caso de Prueba | Criterio QA | Resultado Esperado |
| :--- | :--- | :--- | :--- |
| **TC-15** | Línea con Debe y Haber simultáneos | Restricción contable y `CHECK` SQL | Rechazado por validación normativa |
| **TC-16** | Importes negativos o en cero | Validación de dominio monetario | Rechazado sin insertar filas |
| **TC-17** | Rechazo de CUO duplicado | Unicidad de clave primaria SUNAT | Rechaza duplicado preservando integridad |
| **TC-18** | Fecha mal formateada y glosa corta | Requisitos Formato 5.1 | Rechazado (`YYYY-MM-DD` y glosa ≥ 8 caracteres) |
| **TC-19** | Precisión decimal al centavo (`S/ 1,538.47`) | Evitar errores de punto flotante en IGV 18% | Cuadre exacto al céntimo (`0.00` diferencia) |
| **TC-20** | Atomicidad ACID (`ROLLBACK` ante error) | Consistencia transaccional SQLite | Cero cabeceras huérfanas tras fallo en línea 2 |
| **TC-21** | Estrés de 150 asientos consecutivos + PLE | Rendimiento (< 10s) y cuadre masivo (469 líneas PLE) | Aprobado con 0 descuadres en Libro Mayor y PLE |

### D. Pruebas End-to-End en Navegador Chromium (`tests/test_e2e_ui.py`)
| ID | Caso de Prueba | Flujo UI Simulado (Playwright) | Evidencia Generada |
| :--- | :--- | :--- | :--- |
| **TC-22** | Flujo completo de contador en navegador | Carga inicial → Plantilla Compra + Destino → Grabar → Modal Extorno → Pestaña Auditoría | 4 capturas PNG en Artifact `evidencias-e2e-screenshots` |

---

## 3. Comandos de Ejecución Local

```bash
# Suite completa (unitarias + integración + estrés)
python -m unittest discover -s tests -p "test_*.py" -v

# Con pytest y reporte de cobertura (requiere pip install -r requirements-qa.txt)
pytest tests/test_motor_contable.py tests/test_api_integracion.py tests/test_rendimiento_y_reglas_sunat.py --cov=backend --cov-report=term-missing
```

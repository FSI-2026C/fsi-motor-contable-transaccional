# Reporte de Calidad QA — Sprint 1 (Motor Contable Transaccional)

**Fecha:** 2026-11-22  
**Responsable QA:** Callo Ccagiavilca, Kevin Joel (`KevinCallo`)  
**Rama evaluada:** `develop`  
**Veredicto QA:** **APROBADO PARA INTEGRACIÓN (Quality Gates en Verde)**

---

## 1. Resumen Ejecutivo de Pruebas

| Tipo de Prueba | Total Casos | Aprobados | Fallidos | Estado |
| :--- | :---: | :---: | :---: | :--- |
| Pruebas Unitarias (Reglas SUNAT y PCGE) | 9 | 9 | 0 | ✅ Aprobado |
| Pruebas de Integración HTTP (API REST) | 5 | 5 | 0 | ✅ Aprobado |
| Pruebas de Casos Borde, ACID y Carga (150 transacciones) | 7 | 7 | 0 | ✅ Aprobado |
| Pruebas E2E en Navegador Chromium (Playwright CI) | 1 flujo (5 pasos) | 1 | 0 | ✅ Automatizado en CI |
| **TOTAL** | **22** | **22** | **0** | **100% Superado** |

---

## 2. Quality Gates Configurados en GitHub Actions

- **Análisis Estático Python (`ruff`):** Sin errores de sintaxis, variables no definidas ni imports rotos.
- **Análisis de Seguridad SAST (`bandit`):** Sin vulnerabilidades críticas/medias en `backend/`.
- **Sintaxis Frontend (`node --check`):** Validación limpia de `pcge.js` y `app.js`.
- **Matriz Multi-versión:** Validación paralela en **Python 3.11** y **Python 3.12**.
- **Umbral de Cobertura (`pytest-cov`):** Quality Gate mínimo exigido **≥ 75%** con publicación de reporte HTML y JUnit XML en Artifacts.
- **Contrato SUNAT PLE 5.1:** Generación y validación automática de los 21 campos delimitados por `|` (`LE2060184921120260600050100001111.txt`).
- **Cumplimiento de `docs/definition-of-done.md`:** Verificación automática de ausencia de archivos `.db`, `.env` o binarios temporales en Git.

---

## 3. Defectos Detectados y Resueltos durante el Sprint

| ID | Severidad | Descripción | Estado |
| :--- | :--- | :--- | :--- |
| QA-01 | Alta | Persistencia inicial usaba columna JSON única en lugar de tablas relacionales normalizadas con FK | Resuelto (`database/schema.sql`) |
| QA-02 | Alta | Faltaba inmutabilidad SUNAT para anulación de asientos ya contabilizados | Resuelto (Extorno automático `EXT-CUO-...`) |
| QA-03 | Media | Ausencia de exportación oficial en formato texto PLE 5.1 separado por pipes `|` | Resuelto (`GET /api/exportar/ple`) |

---

## 4. Aprobación QA
- [x] Todos los criterios de aceptación del módulo de Asientos Contables Diarios SUNAT han sido verificados.
- [x] Evidencias de cobertura, PLE 5.1 y capturas E2E disponibles en la pestaña **Actions** del repositorio.

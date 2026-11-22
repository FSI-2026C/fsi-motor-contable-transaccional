/**
 * Controlador Frontend del Motor Contable Transaccional (SUNAT Formato 5.1)
 * Se sincroniza con la API REST Python + SQLite cuando se ejecuta app.py,
 * con respaldo en localStorage si se abre index.html directamente.
 */

let catalogoPcge = [...CATALOGO_PCGE_DEFAULT];
let asientos = [];
let auditoria = [];
let estadoPeriodo = "ABIERTO";
const PERIODO_ACTUAL = "2026-06";
const RUC_EMPRESA = "20601849211";

let formLines = [];
let plantillaActual = "venta";
let backendActivo = false;
let cuoPendienteExtorno = null;

function fmtMoney(n) {
  return (Number(n) || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function obtenerNombreCuenta(codigo) {
  const c = catalogoPcge.find((x) => x.codigo === codigo);
  return c ? c.denominacion : "Cuenta Contable PCGE";
}

async function sincronizarEstadoDesdeServidor() {
  try {
    const res = await fetch(`/api/estado-sistema?periodo=${PERIODO_ACTUAL}`);
    if (!res.ok) throw new Error("Sin servidor");
    const data = await res.json();
    if (data.ok) {
      backendActivo = true;
      catalogoPcge = data.cuentas_pcge && data.cuentas_pcge.length ? data.cuentas_pcge : [...CATALOGO_PCGE_DEFAULT];
      asientos = data.asientos || [];
      auditoria = data.auditoria || [];
      const perObj = (data.periodos || []).find((p) => p.periodo === PERIODO_ACTUAL);
      estadoPeriodo = perObj ? perObj.estado : "ABIERTO";
      localStorage.setItem("motor_contable_asientos", JSON.stringify(asientos));
      localStorage.setItem("motor_contable_periodo", estadoPeriodo);
      return true;
    }
  } catch (e) {
    backendActivo = false;
  }

  // Modo respaldo local (apertura directa de index.html)
  const localAsientos = localStorage.getItem("motor_contable_asientos");
  asientos = localAsientos ? JSON.parse(localAsientos) : JSON.parse(JSON.stringify(ASIENTOS_RESPALDO_LOCAL));
  estadoPeriodo = localStorage.getItem("motor_contable_periodo") || "ABIERTO";
  const localAud = localStorage.getItem("motor_contable_auditoria");
  auditoria = localAud ? JSON.parse(localAud) : [
    { id: 1, fecha_hora: "2026-06-05 09:00:00", usuario: "sistema_inicial", accion: "REGISTRO_ASIENTO", cuo_afectado: "CUO-0001", detalle: "Carga inicial de asientos modelo SUNAT 5.1" }
  ];
  return false;
}

async function initApp() {
  await sincronizarEstadoDesdeServidor();
  cargarPlantilla("venta");
  const params = new URLSearchParams(window.location.search);
  setView(params.get("view") || "1");
}

function setView(v) {
  document.querySelectorAll(".view-section").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".topbar-tab").forEach((el) => el.classList.remove("active"));

  const targetSec = document.getElementById(`view-${v}`);
  const targetTab = document.getElementById(`tab-${v}`);
  if (targetSec) targetSec.classList.add("active");
  if (targetTab) targetTab.classList.add("active");

  const headings = {
    "1": "Formato 5.1: Libro Diario",
    "2": "Registro de Asiento Contable Diario",
    "3": "Formato 6.1: Libro Mayor (Saldos por Cuenta PCGE)",
    "4": "Control de Período Contable y Auditoría Transaccional"
  };
  document.getElementById("page-heading").textContent = headings[v] || headings["1"];

  if (v === "2") {
    const nextNum = String(asientos.length + 1).padStart(4, "0");
    document.getElementById("f-cuo").value = `CUO-${nextNum}`;
    validarReglasEnVivo();
  }
  renderTodo();
}

function renderTodo() {
  actualizarIndicadoresYPeriodo();
  renderLibroDiario();
  renderLibroMayor();
  renderAuditoriaYPeriodo();
}

function actualizarIndicadoresYPeriodo() {
  let totalDebe = 0;
  let totalHaber = 0;
  let totalLineas = 0;
  asientos.forEach((a) => {
    (a.lineas || []).forEach((l) => {
      totalDebe += Number(l.debe) || 0;
      totalHaber += Number(l.haber) || 0;
      totalLineas++;
    });
  });
  const diff = Math.round(Math.abs(totalDebe - totalHaber) * 100) / 100;

  document.getElementById("kpi-debe").textContent = `S/ ${fmtMoney(totalDebe)}`;
  document.getElementById("kpi-haber").textContent = `S/ ${fmtMoney(totalHaber)}`;
  document.getElementById("kpi-diff").textContent = `S/ ${fmtMoney(diff)}`;
  document.getElementById("kpi-count").textContent = `${asientos.length} asientos`;
  document.getElementById("kpi-lines-sub").textContent = `${totalLineas} apuntes contables PCGE`;

  const pill = document.getElementById("topbar-period-pill");
  const isClosed = estadoPeriodo === "CERRADO";
  pill.textContent = estadoPeriodo;
  pill.className = `period-pill ${isClosed ? "closed" : "open"}`;

  const closedAlert = document.getElementById("form-closed-alert");
  const btnSave = document.getElementById("btn-grabar-asiento");
  if (closedAlert) closedAlert.style.display = isClosed ? "block" : "none";
  if (btnSave) btnSave.disabled = isClosed;
}

/* ==================== VISTA 1: LIBRO DIARIO (FORMATO 5.1) ==================== */
function renderLibroDiario() {
  const q = (document.getElementById("filter-text").value || "").toLowerCase().trim();
  const lib = document.getElementById("filter-libro").value;
  const mode = document.getElementById("filter-view-mode").value;

  const filtrados = asientos.filter((a) => {
    if (lib !== "TODOS" && a.libro_sunat !== lib) return false;
    if (q) {
      const textoCuentas = (a.lineas || []).map((l) => `${l.cuenta} ${l.denominacion}`).join(" ").toLowerCase();
      const match =
        a.cuo.toLowerCase().includes(q) ||
        a.glosa.toLowerCase().includes(q) ||
        (a.num_doc || "").toLowerCase().includes(q) ||
        (a.razon_social || "").toLowerCase().includes(q) ||
        textoCuentas.includes(q);
      if (!match) return false;
    }
    return true;
  });

  const tbody = document.getElementById("diario-tbody");
  let sumDebe = 0;
  let sumHaber = 0;
  let html = "";

  filtrados.forEach((a) => {
    let asientoDebe = 0;
    let asientoHaber = 0;
    (a.lineas || []).forEach((l) => {
      asientoDebe += Number(l.debe) || 0;
      asientoHaber += Number(l.haber) || 0;
    });
    sumDebe += asientoDebe;
    sumHaber += asientoHaber;

    const estado = (a.estado || "REGISTRADO").toUpperCase();
    let tagHtml = `<span class="status-tag ok">Registrado</span>`;
    let rowClass = "";
    if (estado === "EXTORNADO") {
      tagHtml = `<span class="status-tag err">Extornado</span>`;
      rowClass = "entry-extornado";
    } else if (estado === "EXTORNO") {
      tagHtml = `<span class="status-tag warn">Contra-asiento</span>`;
      rowClass = "entry-extorno";
    }

    const puedeExtornar = estado === "REGISTRADO" && estadoPeriodo === "ABIERTO";
    const btnExtorno = puedeExtornar
      ? `<button class="btn btn-sm btn-danger no-print" onclick="abrirModalExtorno('${a.cuo}')">Extornar</button>`
      : "";

    if (mode === "resumen") {
      const cuentasResumen = (a.lineas || []).map((l) => l.cuenta).join(", ");
      html += `
        <tr class="${rowClass}">
          <td class="code-col"><strong>${a.cuo}</strong></td>
          <td>${a.fecha}</td>
          <td>
            <div style="font-weight:600;">${a.glosa}</div>
            <div style="font-size:11.5px; color:#6b7280;">RUC ${a.ruc_tercero || "-"} · ${a.razon_social || ""}</div>
          </td>
          <td>
            <div>${a.num_doc}</div>
            <div style="font-size:11px; color:#6b7280;">${a.libro_sunat}</div>
          </td>
          <td class="code-col">${cuentasResumen}</td>
          <td>
            ${tagHtml}
            <button class="btn btn-sm no-print" style="margin-left:6px;" onclick="verVoucher('${a.cuo}')">Comprobante</button>
            ${btnExtorno}
          </td>
          <td class="num"><strong>${fmtMoney(asientoDebe)}</strong></td>
          <td class="num"><strong>${fmtMoney(asientoHaber)}</strong></td>
        </tr>
      `;
    } else {
      html += `
        <tr class="entry-header ${rowClass}">
          <td colspan="6">
            ${tagHtml}
            <span style="margin-left:6px;">Asiento <strong>${a.cuo}</strong> | Fecha: ${a.fecha} | ${a.glosa}</span>
            <span style="font-weight:400; color:#6b7280; margin-left:8px;">(${a.tipo_doc}: ${a.num_doc} — RUC ${a.ruc_tercero || "-"} ${a.razon_social || ""})</span>
          </td>
          <td colspan="2" style="text-align:right; white-space:nowrap;">
            <button class="btn btn-sm no-print" onclick="verVoucher('${a.cuo}')">Ver comprobante</button>
            ${btnExtorno}
          </td>
        </tr>
      `;
      (a.lineas || []).forEach((l, idx) => {
        const esHaber = Number(l.haber) > 0;
        html += `
          <tr class="${rowClass}">
            <td class="code-col" style="color:#6b7280;">${a.cuo}-${idx + 1}</td>
            <td>${a.fecha}</td>
            <td style="color:#374151;">${a.glosa}</td>
            <td style="font-size:12px; color:#4b5563;">${a.libro_sunat.slice(0, 22)} · <strong>${a.num_doc}</strong></td>
            <td class="code-col"><strong>${l.cuenta}</strong></td>
            <td style="${esHaber ? "padding-left:22px; color:#4b5563;" : "font-weight:500; color:#111827;"}">${l.denominacion}</td>
            <td class="num">${Number(l.debe) > 0 ? fmtMoney(l.debe) : "0.00"}</td>
            <td class="num">${Number(l.haber) > 0 ? fmtMoney(l.haber) : "0.00"}</td>
          </tr>
        `;
      });
    }
  });

  html += `
    <tr class="table-footer">
      <td colspan="6" style="text-align:right;">TOTALES ACUMULADOS DEL LIBRO DIARIO (SOLES):</td>
      <td class="num">${fmtMoney(sumDebe)}</td>
      <td class="num">${fmtMoney(sumHaber)}</td>
    </tr>
  `;
  tbody.innerHTML = html;
}

/* ==================== VISTA 2: REGISTRO DE ASIENTO ==================== */
function cargarPlantilla(tipo) {
  plantillaActual = tipo;
  document.getElementById("tpl-select").value = tipo;
  const total = Number(document.getElementById("calc-monto").value) || 1180.00;
  const tpl = construirPlantillaContable(tipo, total, catalogoPcge);

  document.getElementById("f-libro").value = tpl.libro;
  document.getElementById("f-tipo-doc").value = tpl.tipo_doc;
  document.getElementById("f-num-doc").value = tpl.num_doc;
  document.getElementById("f-glosa").value = tpl.glosa;
  formLines = tpl.lineas;
  renderLineasFormulario();
}

function recalcularPlantillaActual() {
  cargarPlantilla(plantillaActual);
  showToast("Importes recalculados con IGV (18%).");
}

function renderLineasFormulario() {
  const tbody = document.getElementById("form-lines-tbody");
  tbody.innerHTML = formLines
    .map((l, idx) => {
      const opciones = catalogoPcge
        .map((c) => `<option value="${c.codigo}" ${c.codigo === l.cuenta ? "selected" : ""}>${c.codigo} - ${c.denominacion}</option>`)
        .join("");
      const esCargo = Number(l.debe) >= Number(l.haber);

      return `
        <tr>
          <td class="code-col">${idx + 1}</td>
          <td>
            <select class="form-select" style="width:100%;" onchange="cambiarCuentaLinea(${idx}, this.value)">
              ${opciones}
            </select>
          </td>
          <td>
            <span class="status-tag ${esCargo ? "ok" : "info"}">${esCargo ? "Cargo (Debe)" : "Abono (Haber)"}</span>
          </td>
          <td class="num">
            <input type="number" step="0.01" min="0" class="form-input" style="width:120px; text-align:right; font-family:Consolas,monospace;" value="${Number(l.debe).toFixed(2)}" oninput="cambiarMontoLinea(${idx}, 'debe', this.value)" />
          </td>
          <td class="num">
            <input type="number" step="0.01" min="0" class="form-input" style="width:120px; text-align:right; font-family:Consolas,monospace;" value="${Number(l.haber).toFixed(2)}" oninput="cambiarMontoLinea(${idx}, 'haber', this.value)" />
          </td>
          <td style="text-align:center;">
            <button type="button" class="btn btn-sm" onclick="eliminarLineaFormulario(${idx})">Quitar</button>
          </td>
        </tr>
      `;
    })
    .join("");

  validarReglasEnVivo();
}

function cambiarCuentaLinea(idx, nuevoCodigo) {
  formLines[idx].cuenta = nuevoCodigo;
  formLines[idx].denominacion = obtenerNombreCuenta(nuevoCodigo);
  renderLineasFormulario();
}

function cambiarMontoLinea(idx, campo, valor) {
  formLines[idx][campo] = parseFloat(valor) || 0;
  validarReglasEnVivo();
}

function agregarLineaFormulario() {
  formLines.push({ cuenta: "1041", denominacion: obtenerNombreCuenta("1041"), debe: 0.00, haber: 0.00 });
  renderLineasFormulario();
}

function eliminarLineaFormulario(idx) {
  if (formLines.length <= 2) {
    showToast("El asiento requiere como mínimo 2 líneas contables.");
    return;
  }
  formLines.splice(idx, 1);
  renderLineasFormulario();
}

function cuadrarAutomaticamente() {
  let d = 0;
  let h = 0;
  formLines.forEach((l) => {
    d += Number(l.debe) || 0;
    h += Number(l.haber) || 0;
  });
  const diff = Math.round((d - h) * 100) / 100;
  if (diff === 0) {
    showToast("El asiento ya se encuentra cuadrado.");
    return;
  }
  if (diff > 0) {
    formLines.push({ cuenta: "4212", denominacion: obtenerNombreCuenta("4212"), debe: 0.00, haber: Math.abs(diff) });
  } else {
    formLines.push({ cuenta: "1212", denominacion: obtenerNombreCuenta("1212"), debe: Math.abs(diff), haber: 0.00 });
  }
  renderLineasFormulario();
  showToast(`Diferencia de S/ ${fmtMoney(Math.abs(diff))} cuadrada.`);
}

function agregarAsientoDestinoAutomatico() {
  const linea60 = formLines.find((l) => l.cuenta.startsWith("60"));
  const linea63 = formLines.find((l) => l.cuenta.startsWith("63") || l.cuenta.startsWith("62") || l.cuenta.startsWith("68"));
  if (linea60 && !formLines.some((l) => l.cuenta === "2011")) {
    const m = Number(linea60.debe) || 0;
    formLines.push({ cuenta: "2011", denominacion: obtenerNombreCuenta("2011"), debe: m, haber: 0.00 });
    formLines.push({ cuenta: "6111", denominacion: obtenerNombreCuenta("6111"), debe: 0.00, haber: m });
    renderLineasFormulario();
    showToast("Asiento de destino a almacén (2011 / 6111) agregado.");
  } else if (linea63 && !formLines.some((l) => l.cuenta === "9411")) {
    const m = Number(linea63.debe) || 0;
    formLines.push({ cuenta: "9411", denominacion: obtenerNombreCuenta("9411"), debe: m, haber: 0.00 });
    formLines.push({ cuenta: "7911", denominacion: obtenerNombreCuenta("7911"), debe: 0.00, haber: m });
    renderLineasFormulario();
    showToast("Asiento de destino a gastos (9411 / 7911) agregado.");
  } else {
    showToast("El asiento ya incluye cuentas de destino o no requiere destino.");
  }
}

function validarReglasEnVivo() {
  let sumD = 0;
  let sumH = 0;
  formLines.forEach((l) => {
    sumD += Number(l.debe) || 0;
    sumH += Number(l.haber) || 0;
  });
  sumD = Math.round(sumD * 100) / 100;
  sumH = Math.round(sumH * 100) / 100;
  const diff = Math.round(Math.abs(sumD - sumH) * 100) / 100;

  document.getElementById("form-total-debe").textContent = fmtMoney(sumD);
  document.getElementById("form-total-haber").textContent = fmtMoney(sumH);

  const r1Ok = diff === 0 && sumD > 0;
  const tieneCargo = formLines.some((l) => Number(l.debe) > 0);
  const tieneAbono = formLines.some((l) => Number(l.haber) > 0);
  const r2Ok = formLines.length >= 2 && tieneCargo && tieneAbono;

  const glosa = (document.getElementById("f-glosa").value || "").trim();
  const fecha = document.getElementById("f-fecha").value;
  const r3Ok = glosa.length >= 8 && Boolean(fecha);

  const numDoc = (document.getElementById("f-num-doc").value || "").trim();
  const ruc = (document.getElementById("f-ruc").value || "").trim();
  const r4Ok = numDoc.length >= 4 && /^\d{11}$/.test(ruc);

  const usa60 = formLines.some((l) => l.cuenta.startsWith("60"));
  const usa63 = formLines.some((l) => l.cuenta.startsWith("63"));
  const tieneDestino20 = formLines.some((l) => l.cuenta.startsWith("20"));
  const tieneDestino94 = formLines.some((l) => l.cuenta.startsWith("94") || l.cuenta.startsWith("95"));
  const r5Ok = (!usa60 || tieneDestino20) && (!usa63 || tieneDestino94);

  document.getElementById("v-r1").textContent = r1Ok ? "[OK] Partida doble (Dif: S/ 0.00)" : `[Error] Descuadre: S/ ${fmtMoney(diff)}`;
  document.getElementById("v-r2").textContent = r2Ok ? `[OK] Cuentas PCGE (${formLines.length})` : "[Error] Falta cargo o abono";
  document.getElementById("v-r3").textContent = r3Ok ? "[OK] Glosa y Fecha" : "[Error] Completar glosa/fecha";
  document.getElementById("v-r4").textContent = r4Ok ? `[OK] Doc. ${numDoc} / RUC válido` : "[Error] RUC requiere 11 dígitos";
  document.getElementById("v-r5").textContent = r5Ok ? "[OK] Destino PCGE" : "[Pendiente] Agregar destino (20/94)";

  const allOk = r1Ok && r2Ok && r3Ok && r4Ok && estadoPeriodo === "ABIERTO";
  document.getElementById("validation-bar").className = `validation-bar ${allOk ? "valid" : "invalid"}`;
  return allOk;
}

async function guardarAsientoSunat() {
  if (estadoPeriodo === "CERRADO") {
    showToast("El período contable está CERRADO. No se pueden registrar asientos.");
    return;
  }
  if (!validarReglasEnVivo()) {
    showToast("Verifique las validaciones normativas antes de grabar el asiento.");
    return;
  }

  const nuevo = {
    cuo: document.getElementById("f-cuo").value.trim(),
    fecha: document.getElementById("f-fecha").value,
    libro_sunat: document.getElementById("f-libro").value,
    tipo_doc: document.getElementById("f-tipo-doc").value,
    num_doc: document.getElementById("f-num-doc").value.trim().toUpperCase(),
    ruc_tercero: document.getElementById("f-ruc").value.trim(),
    razon_social: document.getElementById("f-razon").value.trim().toUpperCase(),
    glosa: document.getElementById("f-glosa").value.trim(),
    estado: "REGISTRADO",
    lineas: JSON.parse(JSON.stringify(formLines))
  };

  if (backendActivo) {
    const res = await fetch("/api/asientos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(nuevo)
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      showToast(data.error || "Error al registrar asiento en el motor contable.");
      return;
    }
    await sincronizarEstadoDesdeServidor();
  } else {
    asientos.push(nuevo);
    auditoria.unshift({
      id: auditoria.length + 1,
      fecha_hora: new Date().toLocaleString("sv-SE"),
      usuario: "contador",
      accion: "REGISTRO_ASIENTO",
      cuo_afectado: nuevo.cuo,
      detalle: `Registro de asiento (${nuevo.libro_sunat}) - Doc. ${nuevo.num_doc}`
    });
    localStorage.setItem("motor_contable_asientos", JSON.stringify(asientos));
    localStorage.setItem("motor_contable_auditoria", JSON.stringify(auditoria));
  }

  setView("1");
  showToast(`Asiento ${nuevo.cuo} registrado en el Libro Diario.`);
}

/* ==================== EXTORNO / CONTRA-ASIENTO (INMUTABILIDAD SUNAT) ==================== */
function abrirModalExtorno(cuo) {
  cuoPendienteExtorno = cuo;
  document.getElementById("extorno-cuo-lbl").textContent = cuo;
  document.getElementById("extorno-motivo").value = "Anulación de operación por corrección contable";
  document.getElementById("modal-extorno").classList.add("open");
}

function cerrarModalExtorno() {
  cuoPendienteExtorno = null;
  document.getElementById("modal-extorno").classList.remove("open");
}

async function confirmarExtorno() {
  if (!cuoPendienteExtorno) return;
  const cuo = cuoPendienteExtorno;
  const motivo = (document.getElementById("extorno-motivo").value || "").trim();

  if (backendActivo) {
    const res = await fetch("/api/asientos/extornar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cuo, motivo })
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      showToast(data.error || "No se pudo extornar el asiento.");
      return;
    }
    await sincronizarEstadoDesdeServidor();
  } else {
    const orig = asientos.find((a) => a.cuo === cuo);
    if (!orig) return;
    orig.estado = "EXTORNADO";
    const contraAsiento = {
      ...orig,
      cuo: `EXT-${orig.cuo}`,
      glosa: `EXTORNO DE ${orig.cuo}: ${motivo || orig.glosa}`,
      estado: "EXTORNO",
      lineas: orig.lineas.map((l) => ({
        cuenta: l.cuenta,
        denominacion: l.denominacion,
        debe: l.haber,
        haber: l.debe
      }))
    };
    asientos.push(contraAsiento);
    auditoria.unshift({
      id: auditoria.length + 1,
      fecha_hora: new Date().toLocaleString("sv-SE"),
      usuario: "contador",
      accion: "EXTORNO_ASIENTO",
      cuo_afectado: contraAsiento.cuo,
      detalle: `Contra-asiento automático que extorna ${orig.cuo}`
    });
    localStorage.setItem("motor_contable_asientos", JSON.stringify(asientos));
    localStorage.setItem("motor_contable_auditoria", JSON.stringify(auditoria));
  }

  cerrarModalExtorno();
  renderTodo();
  showToast(`Extorno generado correctamente (Contra-asiento EXT-${cuo}).`);
}

/* ==================== VISTA 3: LIBRO MAYOR (PCGE) ==================== */
function renderLibroMayor() {
  const acum = {};
  catalogoPcge.forEach((c) => {
    acum[c.codigo] = { ...c, debe: 0, haber: 0 };
  });

  asientos.forEach((a) => {
    (a.lineas || []).forEach((l) => {
      if (!acum[l.cuenta]) {
        acum[l.cuenta] = { codigo: l.cuenta, clase: "Cuenta PCGE", denominacion: l.denominacion, debe: 0, haber: 0 };
      }
      acum[l.cuenta].debe += Number(l.debe) || 0;
      acum[l.cuenta].haber += Number(l.haber) || 0;
    });
  });

  const cuentasConMovimiento = Object.values(acum).filter((c) => c.debe > 0 || c.haber > 0);
  const tbody = document.getElementById("mayor-tbody");
  tbody.innerHTML = cuentasConMovimiento
    .map((c) => {
      const diff = Math.round((c.debe - c.haber) * 100) / 100;
      const estadoSaldo =
        diff > 0 ? `${fmtMoney(diff)} (Deudor)` : diff < 0 ? `${fmtMoney(Math.abs(diff))} (Acreedor)` : "0.00 (Saldada)";
      return `
        <tr>
          <td class="code-col"><strong>${c.codigo}</strong></td>
          <td style="color:#4b5563;">${c.clase}</td>
          <td style="font-weight:500;">${c.denominacion}</td>
          <td class="num">${fmtMoney(c.debe)}</td>
          <td class="num">${fmtMoney(c.haber)}</td>
          <td class="num"><strong>${estadoSaldo}</strong></td>
        </tr>
      `;
    })
    .join("");
}

/* ==================== VISTA 4: AUDITORÍA Y CIERRE DE PERÍODO ==================== */
function renderAuditoriaYPeriodo() {
  const statusTag = document.getElementById("periodo-status-tag");
  const btnToggle = document.getElementById("btn-toggle-periodo");
  const isClosed = estadoPeriodo === "CERRADO";

  if (statusTag) {
    statusTag.textContent = estadoPeriodo;
    statusTag.className = `status-tag ${isClosed ? "err" : "ok"}`;
  }
  if (btnToggle) {
    btnToggle.textContent = isClosed ? "Reabrir período 06/2026" : "Cerrar período contable 06/2026";
    btnToggle.className = `btn ${isClosed ? "btn-primary" : "btn-danger"}`;
  }

  const tbody = document.getElementById("auditoria-tbody");
  if (!tbody) return;
  tbody.innerHTML = auditoria
    .map((ev) => {
      let badgeCls = "info";
      if (ev.accion === "EXTORNO_ASIENTO" || ev.accion === "CIERRE_PERIODO") badgeCls = "err";
      if (ev.accion === "REGISTRO_ASIENTO") badgeCls = "ok";
      if (ev.accion === "EXPORTACION_PLE") badgeCls = "warn";
      return `
        <tr>
          <td class="code-col">${ev.id}</td>
          <td class="code-col">${ev.fecha_hora}</td>
          <td>${ev.usuario}</td>
          <td><span class="status-tag ${badgeCls}">${ev.accion}</span></td>
          <td class="code-col"><strong>${ev.cuo_afectado || "-"}</strong></td>
          <td>${ev.detalle}</td>
        </tr>
      `;
    })
    .join("");
}

async function toggleEstadoPeriodo() {
  const nuevoEstado = estadoPeriodo === "ABIERTO" ? "CERRADO" : "ABIERTO";
  if (backendActivo) {
    const res = await fetch("/api/periodo/estado", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ periodo: PERIODO_ACTUAL, estado: nuevoEstado })
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      showToast(data.error || "No se pudo cambiar el estado del período.");
      return;
    }
    await sincronizarEstadoDesdeServidor();
  } else {
    estadoPeriodo = nuevoEstado;
    auditoria.unshift({
      id: auditoria.length + 1,
      fecha_hora: new Date().toLocaleString("sv-SE"),
      usuario: "contador",
      accion: nuevoEstado === "CERRADO" ? "CIERRE_PERIODO" : "REAPERTURA_PERIODO",
      cuo_afectado: PERIODO_ACTUAL,
      detalle: `Período ${PERIODO_ACTUAL} actualizado a estado ${nuevoEstado}`
    });
    localStorage.setItem("motor_contable_periodo", estadoPeriodo);
    localStorage.setItem("motor_contable_auditoria", JSON.stringify(auditoria));
  }

  renderTodo();
  showToast(`Período ${PERIODO_ACTUAL} marcado como ${nuevoEstado}.`);
}

/* ==================== VOUCHER Y EXPORTACIONES (CSV + PLE SUNAT .TXT) ==================== */
function verVoucher(cuo) {
  const a = asientos.find((x) => x.cuo === cuo);
  if (!a) return;
  let sumD = 0;
  let sumH = 0;
  const filas = (a.lineas || [])
    .map((l, i) => {
      sumD += Number(l.debe) || 0;
      sumH += Number(l.haber) || 0;
      return `
        <tr>
          <td style="padding:6px 8px; border-bottom:1px solid #e5e7eb;">${i + 1}</td>
          <td style="padding:6px 8px; border-bottom:1px solid #e5e7eb; font-family:Consolas,monospace; font-weight:700;">${l.cuenta}</td>
          <td style="padding:6px 8px; border-bottom:1px solid #e5e7eb;">${l.denominacion}</td>
          <td style="padding:6px 8px; border-bottom:1px solid #e5e7eb; text-align:right; font-family:Consolas,monospace;">${fmtMoney(l.debe)}</td>
          <td style="padding:6px 8px; border-bottom:1px solid #e5e7eb; text-align:right; font-family:Consolas,monospace;">${fmtMoney(l.haber)}</td>
        </tr>
      `;
    })
    .join("");

  document.getElementById("voucher-body").innerHTML = `
    <div style="border:1px solid #374151; padding:18px; font-size:12.5px;">
      <div style="display:flex; justify-content:space-between; border-bottom:1px solid #374151; padding-bottom:10px; margin-bottom:12px;">
        <div>
          <div style="font-size:15px; font-weight:700;">COMERCIAL ANDINA S.A.C. — RUC ${RUC_EMPRESA}</div>
          <div style="color:#4b5563;">FORMATO 5.1: LIBRO DIARIO · ${a.libro_sunat}</div>
        </div>
        <div style="text-align:right;">
          <div><strong>Asiento: ${a.cuo}</strong> (${a.estado || "REGISTRADO"})</div>
          <div>Fecha: ${a.fecha}</div>
        </div>
      </div>
      <div style="margin-bottom:12px; line-height:1.5;">
        <div><strong>Sustento:</strong> ${a.tipo_doc} N° ${a.num_doc} | <strong>Anexo:</strong> RUC ${a.ruc_tercero} - ${a.razon_social}</div>
        <div><strong>Glosa:</strong> ${a.glosa}</div>
      </div>
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr style="background:#f3f4f6; border-top:1px solid #374151; border-bottom:1px solid #374151;">
            <th style="padding:6px 8px; text-align:left;">Ítem</th>
            <th style="padding:6px 8px; text-align:left;">Cuenta</th>
            <th style="padding:6px 8px; text-align:left;">Denominación PCGE</th>
            <th style="padding:6px 8px; text-align:right;">Debe (S/)</th>
            <th style="padding:6px 8px; text-align:right;">Haber (S/)</th>
          </tr>
        </thead>
        <tbody>
          ${filas}
          <tr style="background:#f9fafb; font-weight:700; border-top:1px solid #374151;">
            <td colspan="3" style="padding:8px; text-align:right;">TOTALES:</td>
            <td style="padding:8px; text-align:right; font-family:Consolas,monospace;">S/ ${fmtMoney(sumD)}</td>
            <td style="padding:8px; text-align:right; font-family:Consolas,monospace;">S/ ${fmtMoney(sumH)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  `;
  document.getElementById("modal-voucher").classList.add("open");
}

function cerrarVoucher() {
  document.getElementById("modal-voucher").classList.remove("open");
}

function exportCSV() {
  const filas = ["CUO,FECHA,ESTADO,LIBRO_SUNAT,TIPO_DOC,NUM_DOC,RUC,RAZON_SOCIAL,GLOSA,CUENTA_PCGE,DENOMINACION,DEBE,HABER"];
  asientos.forEach((a) => {
    (a.lineas || []).forEach((l) => {
      filas.push(
        `${a.cuo},${a.fecha},${a.estado || "REGISTRADO"},"${a.libro_sunat}","${a.tipo_doc}",${a.num_doc},${a.ruc_tercero},"${a.razon_social}","${a.glosa}",${l.cuenta},"${l.denominacion}",${Number(l.debe).toFixed(2)},${Number(l.haber).toFixed(2)}`
      );
    });
  });
  const blob = new Blob(["\uFEFF" + filas.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `formato_5_1_libro_diario_${PERIODO_ACTUAL}.csv`;
  link.click();
  URL.revokeObjectURL(url);
  showToast("Libro Diario exportado en formato CSV / Excel.");
}

async function exportPLE() {
  if (backendActivo) {
    window.location.href = `/api/exportar/ple?periodo=${PERIODO_ACTUAL}`;
    setTimeout(() => sincronizarEstadoDesdeServidor().then(renderTodo), 600);
    showToast("Descargando archivo oficial PLE SUNAT Formato 5.1 (.txt).");
    return;
  }

  // Generación local equivalente del formato PLE 5.1 (.txt con pipes '|')
  const periodoPle = PERIODO_ACTUAL.replace("-", "") + "00";
  const lineasTxt = [];
  asientos.forEach((a) => {
    const fechaDdMmYyyy = a.fecha.split("-").reverse().join("/");
    const codDoc = (a.tipo_doc || "00").split(" ")[0];
    const [serie, num] = (a.num_doc || "0000-0").includes("-") ? a.num_doc.split("-") : ["0000", a.num_doc || "0"];
    (a.lineas || []).forEach((l, idx) => {
      const corr = `M${String(idx + 1).padStart(4, "0")}`;
      const campos = [
        periodoPle, a.cuo, corr, l.cuenta, "", "", "PEN", "6", a.ruc_tercero,
        codDoc, serie, num, fechaDdMmYyyy, "", fechaDdMmYyyy,
        a.glosa.replace(/\|/g, " "), "", Number(l.debe).toFixed(2), Number(l.haber).toFixed(2), "", "1"
      ];
      lineasTxt.push(campos.join("|") + "|");
    });
  });

  const nombre = `LE${RUC_EMPRESA}${periodoPle}050100001111.txt`;
  const blob = new Blob([lineasTxt.join("\r\n")], { type: "text/plain;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nombre;
  link.click();
  URL.revokeObjectURL(url);
  showToast(`Archivo PLE generado: ${nombre}`);
}

async function resetDemoData() {
  if (backendActivo) {
    await fetch("/api/reset", { method: "POST" });
    await sincronizarEstadoDesdeServidor();
  } else {
    asientos = JSON.parse(JSON.stringify(ASIENTOS_RESPALDO_LOCAL));
    estadoPeriodo = "ABIERTO";
    auditoria = [
      { id: 1, fecha_hora: new Date().toLocaleString("sv-SE"), usuario: "sistema", accion: "RESET", cuo_afectado: PERIODO_ACTUAL, detalle: "Restauración de datos base" }
    ];
    localStorage.setItem("motor_contable_asientos", JSON.stringify(asientos));
    localStorage.setItem("motor_contable_periodo", estadoPeriodo);
    localStorage.setItem("motor_contable_auditoria", JSON.stringify(auditoria));
  }
  renderTodo();
  showToast("Base de datos contable restaurada a estado inicial.");
}

function showToast(msg) {
  const c = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = "toast-msg";
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), 3400);
}

window.addEventListener("DOMContentLoaded", initApp);

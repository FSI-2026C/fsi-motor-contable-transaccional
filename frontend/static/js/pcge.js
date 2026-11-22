/**
 * Catálogo Oficial del Plan Contable General Empresarial (PCGE Perú)
 * y plantillas contables automáticas con cálculo de IGV (18%) y Asiento de Destino.
 */

const CATALOGO_PCGE_DEFAULT = [
  { codigo: "1011", clase: "Elemento 1 - Activo Disponible", denominacion: "Caja Moneda Nacional" },
  { codigo: "1041", clase: "Elemento 1 - Activo Disponible", denominacion: "Cuentas corrientes operativas (Banco BCP MN)" },
  { codigo: "1212", clase: "Elemento 1 - Activo Exigible", denominacion: "Facturas, boletas y otros comprobantes por cobrar - Emitidas" },
  { codigo: "2011", clase: "Elemento 2 - Activo Realizable", denominacion: "Mercaderías al costo" },
  { codigo: "3351", clase: "Elemento 3 - Activo Inmovilizado", denominacion: "Muebles, enseres y equipos diversos" },
  { codigo: "3913", clase: "Elemento 3 - Activo Inmovilizado", denominacion: "Depreciación acumulada inmuebles, maquinaria y equipo" },
  { codigo: "4011", clase: "Elemento 4 - Pasivo Tributario", denominacion: "Gobierno Nacional - IGV Cuenta Propia (18%)" },
  { codigo: "4031", clase: "Elemento 4 - Pasivo Tributario", denominacion: "Instituciones públicas - EsSalud (9%) y ONP (13%)" },
  { codigo: "4111", clase: "Elemento 4 - Pasivo Laboral", denominacion: "Remuneraciones por pagar - Sueldos netos" },
  { codigo: "4212", clase: "Elemento 4 - Pasivo Comercial", denominacion: "Facturas, boletas y otros comprobantes por pagar - Emitidas" },
  { codigo: "5011", clase: "Elemento 5 - Patrimonio", denominacion: "Capital social - Acciones y participaciones" },
  { codigo: "6011", clase: "Elemento 6 - Gastos por Naturaleza", denominacion: "Compras de mercaderías" },
  { codigo: "6111", clase: "Elemento 6 - Variación de Existencias", denominacion: "Variación de existencias - Mercaderías" },
  { codigo: "6211", clase: "Elemento 6 - Gastos de Personal", denominacion: "Remuneraciones - Sueldos y salarios" },
  { codigo: "6271", clase: "Elemento 6 - Gastos de Personal", denominacion: "Régimen de prestaciones de salud - EsSalud (9%)" },
  { codigo: "6361", clase: "Elemento 6 - Gastos de Servicios", denominacion: "Servicios básicos - Energía eléctrica, agua e internet" },
  { codigo: "6814", clase: "Elemento 6 - Valuación y Deterioro", denominacion: "Depreciación de inmuebles, maquinaria y equipo" },
  { codigo: "6912", clase: "Elemento 6 - Costo de Ventas", denominacion: "Costo de ventas - Mercaderías venta local" },
  { codigo: "7012", clase: "Elemento 7 - Ingresos", denominacion: "Mercaderías - Venta local" },
  { codigo: "7911", clase: "Elemento 7 - Cargas Imputables", denominacion: "Cargas imputables a cuentas de costos y gastos" },
  { codigo: "9411", clase: "Elemento 9 - Contabilidad Analítica", denominacion: "Gastos de administración" },
  { codigo: "9511", clase: "Elemento 9 - Contabilidad Analítica", denominacion: "Gastos de ventas" }
];

const ASIENTOS_RESPALDO_LOCAL = [
  {
    cuo: "CUO-0001",
    periodo: "2026-06",
    fecha: "2026-06-05",
    libro_sunat: "14 · Registro de Ventas e Ingresos",
    tipo_doc: "01 - Factura",
    num_doc: "F001-00120",
    ruc_tercero: "20601849211",
    razon_social: "COMERCIAL ANDINA S.A.C.",
    glosa: "Por la venta de mercaderías al crédito según Factura Electrónica F001-00120",
    estado: "REGISTRADO",
    lineas: [
      { cuenta: "1212", denominacion: "Facturas, boletas y otros comprobantes por cobrar - Emitidas", debe: 1180.00, haber: 0.00 },
      { cuenta: "4011", denominacion: "Gobierno Nacional - IGV Cuenta Propia (18%)", debe: 0.00, haber: 180.00 },
      { cuenta: "7012", denominacion: "Mercaderías - Venta local", debe: 0.00, haber: 1000.00 }
    ]
  },
  {
    cuo: "CUO-0002",
    periodo: "2026-06",
    fecha: "2026-06-05",
    libro_sunat: "01 · Libro Caja y Bancos",
    tipo_doc: "00 - Otros",
    num_doc: "OP-994120",
    ruc_tercero: "20601849211",
    razon_social: "COMERCIAL ANDINA S.A.C.",
    glosa: "Por el cobro de la Factura F001-00120 mediante transferencia en Cta. Cte. BCP",
    estado: "REGISTRADO",
    lineas: [
      { cuenta: "1041", denominacion: "Cuentas corrientes operativas (Banco BCP MN)", debe: 1180.00, haber: 0.00 },
      { cuenta: "1212", denominacion: "Facturas, boletas y otros comprobantes por cobrar - Emitidas", debe: 0.00, haber: 1180.00 }
    ]
  },
  {
    cuo: "CUO-0003",
    periodo: "2026-06",
    fecha: "2026-06-10",
    libro_sunat: "08 · Registro de Compras",
    tipo_doc: "01 - Factura",
    num_doc: "F002-00450",
    ruc_tercero: "20519283741",
    razon_social: "DISTRIBUIDORA NACIONAL S.A.C.",
    glosa: "Por la compra de mercaderías según Factura F002-00450 y destino a almacén",
    estado: "REGISTRADO",
    lineas: [
      { cuenta: "6011", denominacion: "Compras de mercaderías", debe: 2000.00, haber: 0.00 },
      { cuenta: "4011", denominacion: "Gobierno Nacional - IGV Cuenta Propia (18%)", debe: 360.00, haber: 0.00 },
      { cuenta: "4212", denominacion: "Facturas, boletas y otros comprobantes por pagar - Emitidas", debe: 0.00, haber: 2360.00 },
      { cuenta: "2011", denominacion: "Mercaderías al costo", debe: 2000.00, haber: 0.00 },
      { cuenta: "6111", denominacion: "Variación de existencias - Mercaderías", debe: 0.00, haber: 2000.00 }
    ]
  },
  {
    cuo: "CUO-0004",
    periodo: "2026-06",
    fecha: "2026-06-15",
    libro_sunat: "08 · Registro de Compras",
    tipo_doc: "01 - Factura",
    num_doc: "F010-00890",
    ruc_tercero: "20100070970",
    razon_social: "EMPRESA DE SERVICIOS ELÉCTRICOS S.A.",
    glosa: "Por el recibo de energía eléctrica del mes y destino a gastos administrativos",
    estado: "REGISTRADO",
    lineas: [
      { cuenta: "6361", denominacion: "Servicios básicos - Energía eléctrica, agua e internet", debe: 500.00, haber: 0.00 },
      { cuenta: "4011", denominacion: "Gobierno Nacional - IGV Cuenta Propia (18%)", debe: 90.00, haber: 0.00 },
      { cuenta: "4212", denominacion: "Facturas, boletas y otros comprobantes por pagar - Emitidas", debe: 0.00, haber: 590.00 },
      { cuenta: "9411", denominacion: "Gastos de administración", debe: 500.00, haber: 0.00 },
      { cuenta: "7911", denominacion: "Cargas imputables a cuentas de costos y gastos", debe: 0.00, haber: 500.00 }
    ]
  },
  {
    cuo: "CUO-0005",
    periodo: "2026-06",
    fecha: "2026-06-30",
    libro_sunat: "05 · Libro Diario",
    tipo_doc: "00 - Otros",
    num_doc: "PLN-2026-06",
    ruc_tercero: "20601849211",
    razon_social: "PLANILLA MENSUAL DE TRABAJADORES",
    glosa: "Por la provisión de planilla de sueldos, ONP (13%) y EsSalud (9%) del mes",
    estado: "REGISTRADO",
    lineas: [
      { cuenta: "6211", denominacion: "Remuneraciones - Sueldos y salarios", debe: 3000.00, haber: 0.00 },
      { cuenta: "6271", denominacion: "Régimen de prestaciones de salud - EsSalud (9%)", debe: 270.00, haber: 0.00 },
      { cuenta: "4031", denominacion: "Instituciones públicas - EsSalud (9%) y ONP (13%)", debe: 0.00, haber: 660.00 },
      { cuenta: "4111", denominacion: "Remuneraciones por pagar - Sueldos netos", debe: 0.00, haber: 2610.00 }
    ]
  }
];

function construirPlantillaContable(tipo, totalOperacion, catalogo) {
  const getNom = (cod) => {
    const f = catalogo.find((c) => c.codigo === cod);
    return f ? f.denominacion : "Cuenta Contable PCGE";
  };

  const total = Number(totalOperacion) || 1180.00;
  const base = Math.round((total / 1.18) * 100) / 100;
  const igv = Math.round((total - base) * 100) / 100;

  if (tipo === "venta") {
    return {
      libro: "14 · Registro de Ventas e Ingresos",
      tipo_doc: "01 - Factura",
      num_doc: "F001-00125",
      glosa: "Por la venta de mercaderías según Factura Electrónica F001-00125",
      lineas: [
        { cuenta: "1212", denominacion: getNom("1212"), debe: total, haber: 0.00 },
        { cuenta: "4011", denominacion: getNom("4011"), debe: 0.00, haber: igv },
        { cuenta: "7012", denominacion: getNom("7012"), debe: 0.00, haber: base }
      ]
    };
  }

  if (tipo === "compra_mercaderia") {
    return {
      libro: "08 · Registro de Compras",
      tipo_doc: "01 - Factura",
      num_doc: "F004-00910",
      glosa: "Por la compra de mercaderías según Factura F004-00910 y destino a almacén",
      lineas: [
        { cuenta: "6011", denominacion: getNom("6011"), debe: base, haber: 0.00 },
        { cuenta: "4011", denominacion: getNom("4011"), debe: igv, haber: 0.00 },
        { cuenta: "4212", denominacion: getNom("4212"), debe: 0.00, haber: total },
        { cuenta: "2011", denominacion: getNom("2011"), debe: base, haber: 0.00 },
        { cuenta: "6111", denominacion: getNom("6111"), debe: 0.00, haber: base }
      ]
    };
  }

  if (tipo === "gasto_servicio") {
    return {
      libro: "08 · Registro de Compras",
      tipo_doc: "01 - Factura",
      num_doc: "F012-00340",
      glosa: "Por servicio de energía eléctrica del mes y destino a gastos administrativos",
      lineas: [
        { cuenta: "6361", denominacion: getNom("6361"), debe: base, haber: 0.00 },
        { cuenta: "4011", denominacion: getNom("4011"), debe: igv, haber: 0.00 },
        { cuenta: "4212", denominacion: getNom("4212"), debe: 0.00, haber: total },
        { cuenta: "9411", denominacion: getNom("9411"), debe: base, haber: 0.00 },
        { cuenta: "7911", denominacion: getNom("7911"), debe: 0.00, haber: base }
      ]
    };
  }

  if (tipo === "cobro_banco") {
    return {
      libro: "01 · Libro Caja y Bancos",
      tipo_doc: "00 - Otros",
      num_doc: "OP-884310",
      glosa: "Por la cobranza de factura de cliente en cuenta corriente BCP",
      lineas: [
        { cuenta: "1041", denominacion: getNom("1041"), debe: total, haber: 0.00 },
        { cuenta: "1212", denominacion: getNom("1212"), debe: 0.00, haber: total }
      ]
    };
  }

  const essalud = Math.round(total * 0.09 * 100) / 100;
  const onp = Math.round(total * 0.13 * 100) / 100;
  const neto = Math.round((total - onp) * 100) / 100;
  return {
    libro: "05 · Libro Diario",
    tipo_doc: "00 - Otros",
    num_doc: "PLN-2026-06",
    glosa: "Por la provisión de planilla de remuneraciones, EsSalud (9%) y ONP (13%)",
    lineas: [
      { cuenta: "6211", denominacion: getNom("6211"), debe: total, haber: 0.00 },
      { cuenta: "6271", denominacion: getNom("6271"), debe: essalud, haber: 0.00 },
      { cuenta: "4031", denominacion: getNom("4031"), debe: 0.00, haber: Math.round((essalud + onp) * 100) / 100 },
      { cuenta: "4111", denominacion: getNom("4111"), debe: 0.00, haber: neto }
    ]
  };
}

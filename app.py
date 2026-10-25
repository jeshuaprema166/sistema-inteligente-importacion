# ═══════════════════════════════════════════════════════════════════════
#  SISTEMA DE ANÁLISIS DE IMPORTACIÓN INTELIGENTE
#  Motor original y metodología: Prof. Jesús Pulido V.
# ═══════════════════════════════════════════════════════════════════════

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, timedelta, datetime
import io, os, json, re, unicodedata
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from fpdf import FPDF

try:
    import sheets_db
    SHEETS_DB_OK = True
except ImportError:
    SHEETS_DB_OK = False

CENTAVO = Decimal("0.01")
CERO    = Decimal("0")
UNO     = Decimal("1")

GASTOS_CONTENEDOR = (
    ("Manejo de Puerto",           "peso"),
    ("Flete Terrestre Nacional",   "peso"),
    ("Logística Internacional",    "volumen"),
    ("Derechos de Aduana",         "volumen"),
    ("Gestión Aduanera",           "volumen"),
    ("Gastos Administrativos",     "volumen"),
)

SECTORES = [
    "Ferretería / Herramientas", "Repuestos para motos",
    "Repuestos para automóviles", "Cauchos y neumáticos",
    "Construcción / Materiales", "Agro / Insumos",
    "Tecnología / Electrónica", "Textil / Calzado",
    "Salud / Farmacia", "Otro (especificar)",
]

ORIGENES = [
    "China", "Estados Unidos", "Panamá", "Brasil", "Turquía",
    "India", "Colombia", "México", "Vietnam", "Tailandia",
    "Corea del Sur", "Japón", "Alemania", "España", "Italia",
    "Otro (especificar)",
]

DEFAULTS = {
    "id_perfil": "", "empresa": "", "rif": "", "propietario": "", "email": "",
    "sector": "Ferretería / Herramientas", "sector_otro": "",
    "margen": 30.0, "desc_mayorista": 15.0, "desc_especial": 5.0,
    "origen": "China", "origen_otro": "", "proveedor": "", "factura": "",
    "fecha_proximo_pedido": None, "capital_inicial": 0.0,
    "costo_fijo_semanal": 0.0, "monto_proximo_pedido": 0.0,
}

MONEDAS_DEFAULT = {
    "USD": {"simbolo": "$",   "unidades_por_usd": 1.0},
    "EUR": {"simbolo": "€",   "unidades_por_usd": 0.93},
    "VES": {"simbolo": "Bs.", "unidades_por_usd": 40.0},
}
RUTA_TASAS = "tasas_cambio.json"

PARTIDAS_BASE = {
    "8207.50.00": {"descripcion": "Útiles de taladrar (brocas)", "ad_valorem": 0.05, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "82 - Herramientas"},
    "8207.90.00": {"descripcion": "Otros útiles intercambiables", "ad_valorem": 0.05, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "82 - Herramientas"},
    "7318.15.00": {"descripcion": "Tornillos y pernos de acero", "ad_valorem": 0.10, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "73 - Manufacturas de hierro"},
    "8414.80.20": {"descripcion": "Compresores de aire", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "SENCAMER + Norma COVENIN", "capitulo": "84 - Máquinas y aparatos"},
    "8716.80.00": {"descripcion": "Carretillas de mano", "ad_valorem": 0.20, "iva": 0.16, "requisitos": "Revisar norma técnica", "capitulo": "87 - Vehículos"},
    "8708.10.00": {"descripcion": "Parachoques y sus partes", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "87 - Vehículos"},
    "8708.29.00": {"descripcion": "Partes de carrocería", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "87 - Vehículos"},
    "8708.30.00": {"descripcion": "Frenos y servofrenos", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "Revisar norma técnica", "capitulo": "87 - Vehículos"},
    "8708.40.00": {"descripcion": "Cajas de cambio", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "87 - Vehículos"},
    "8708.50.00": {"descripcion": "Ejes con diferencial", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "87 - Vehículos"},
    "8708.99.00": {"descripcion": "Otras partes y accesorios", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "87 - Vehículos"},
    "8714.10.00": {"descripcion": "Partes de motocicletas", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "87 - Vehículos"},
    "8714.91.00": {"descripcion": "Sillines y partes", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "87 - Vehículos"},
    "4011.10.00": {"descripcion": "Neumáticos para automóviles", "ad_valorem": 0.20, "iva": 0.16, "requisitos": "SENCAMER + Norma COVENIN", "capitulo": "40 - Caucho"},
    "4011.20.00": {"descripcion": "Neumáticos para buses/camiones", "ad_valorem": 0.15, "iva": 0.16, "requisitos": "SENCAMER", "capitulo": "40 - Caucho"},
    "4011.40.00": {"descripcion": "Neumáticos para motocicletas", "ad_valorem": 0.20, "iva": 0.16, "requisitos": "SENCAMER", "capitulo": "40 - Caucho"},
    "8504.40.00": {"descripcion": "Fuentes de poder / cargadores", "ad_valorem": 0.10, "iva": 0.16, "requisitos": "Revisar norma técnica", "capitulo": "85 - Máquinas eléctricas"},
    "8544.42.00": {"descripcion": "Cables y conductores eléctricos", "ad_valorem": 0.10, "iva": 0.16, "requisitos": "Ninguno especial", "capitulo": "85 - Máquinas eléctricas"},
}

def slugify(texto):
    if not texto: return "empresa-sin-nombre"
    t = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii')
    t = re.sub(r'[^a-zA-Z0-9]+', '-', t).strip('-').lower()
    return t or "empresa-sin-nombre"

def texto_efectivo(valor, alterno=""):
    if valor and valor.startswith("Otro"): return alterno.strip() or "No especificado"
    return valor or "No especificado"

def cargar_tasas():
    if SHEETS_DB_OK:
        remotas = sheets_db.leer_tasas()
        if remotas: return {"EUR": remotas["EUR"], "VES": remotas["VES"]}
    if os.path.exists(RUTA_TASAS):
        try:
            with open(RUTA_TASAS, "r", encoding="utf-8") as f:
                d = json.load(f)
            return {"EUR": float(d.get("EUR", 0.93)), "VES": float(d.get("VES", 40.0))}
        except Exception: pass
    return {k: v["unidades_por_usd"] for k, v in MONEDAS_DEFAULT.items() if k != "USD"}

def inicializar_monedas():
    if "monedas" not in st.session_state: st.session_state["monedas"] = cargar_tasas()
    if "moneda_activa" not in st.session_state: st.session_state["moneda_activa"] = "USD"

def formato_moneda(monto_usd, moneda=None):
    try:
        moneda = moneda or st.session_state.get("moneda_activa", "USD")
        tasas  = st.session_state.get("monedas", {})
    except Exception: moneda, tasas = "USD", {}
    valor = Decimal(str(monto_usd)) * Decimal(str(tasas.get(moneda, 1.0)))
    simbolo = MONEDAS_DEFAULT[moneda]["simbolo"]
    return f"{simbolo} {valor.quantize(CENTAVO, ROUND_HALF_UP):,.2f}"

def formato_dinero(valor): return formato_moneda(valor)

def panel_monedas_sidebar(config):
    inicializar_monedas()
    with st.sidebar.expander("💵 Moneda y tipo de cambio", expanded=False):
        if SHEETS_DB_OK:
            remotas = sheets_db.leer_tasas()
            if remotas:
                st.session_state["monedas"]["EUR"] = remotas["EUR"]
                st.session_state["monedas"]["VES"] = remotas["VES"]
                st.caption(f"🔄 {remotas['fecha']} · por {remotas['por']}")
        st.session_state["moneda_activa"] = st.selectbox("Moneda de visualización", ["USD", "EUR", "VES"], index=["USD", "EUR", "VES"].index(st.session_state["moneda_activa"]))
        for m in ["EUR", "VES"]:
            st.session_state["monedas"][m] = st.number_input(f"1 USD = ? {m}", min_value=0.0001, value=float(st.session_state["monedas"].get(m, 1.0)), step=0.01, format="%.4f", key=f"tasa_{m}")
        if st.button("💾 Guardar tasas", key="guardar_tasas"):
            if SHEETS_DB_OK:
                ok, msg = sheets_db.guardar_tasas(usd_eur=st.session_state["monedas"]["EUR"], usd_ves=st.session_state["monedas"]["VES"], usuario=config.get("propietario") or config.get("empresa") or "admin")
                (st.success if ok else st.warning)(msg)
            else:
                try:
                    with open(RUTA_TASAS, "w", encoding="utf-8") as f: json.dump({"EUR": st.session_state["monedas"]["EUR"], "VES": st.session_state["monedas"]["VES"]}, f, indent=2)
                    st.success("✅ Guardadas localmente.")
                except Exception as e: st.error(f"No se pudieron guardar: {e}")

def leer_decimal(texto, etiqueta, permitir_cero=True, es_dinero=False):
    normalizado = str(texto).strip().replace(",", ".")
    if not normalizado: raise ValueError(f"Completa el campo «{etiqueta}».")
    try: valor = Decimal(normalizado)
    except InvalidOperation as error: raise ValueError(f"«{etiqueta}» debe ser un número válido.") from error
    if not valor.is_finite() or valor < CERO: raise ValueError(f"«{etiqueta}» debe ser ≥ 0.")
    if not permitir_cero and valor == CERO: raise ValueError(f"«{etiqueta}» debe ser > 0.")
    if es_dinero: valor = valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return valor

def redondear_entero(valor): return valor.quantize(UNO, rounding=ROUND_HALF_UP)

def verificar_acceso():
    if "PASSWORD_ADMIN" not in st.secrets: return True
    if st.session_state.get("autenticado", False): return True
    for nombre in ("portada.jpg", "portada.png", "IMG-20261021-WA0005.jpg"):
        if os.path.exists(nombre):
            st.image(nombre, use_container_width=True); break
    st.markdown("<h1 style='text-align:center;'>Bienvenidos 🛳️</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>¿Sabe cuánto le cuesta realmente traer los productos desde el exterior hasta su depósito?</h3>", unsafe_allow_html=True)
    st.markdown("* **La verdad** sobre sus costos de importación, márgenes y precios óptimos.\n* **Identificar** los márgenes reales de ganancia antes de nacionalizar.\n* **Optimizar** el espacio de su contenedor.\n* **Alarmas** 🟢🟡🔴 de reposición por IA.\n* **Ingresar** datos desde Excel automáticamente.\n* **Definir** el mejor proveedor del exterior.\n<mark>**✨ Sistema de Importación con IA 🤖 ✨**</mark>", unsafe_allow_html=True)
    col_i, col_c, col_d = st.columns([1, 1, 1])
    with col_c:
        st.markdown("<h4 style='text-align:center;'>Diseñado y elaborado por<br>su Asesor de Importación Inteligente<br>Prof. Jesús Pulido V.</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;'>0424-728.3199 / 0416-291.6426</p>", unsafe_allow_html=True)
        for nombre in ("asesor.jpg", "profesor.jpg"):
            if os.path.exists(nombre):
                st.image(nombre, width=180); break
    st.divider()
    password = st.text_input("Contraseña de acceso", type="password")
    if st.button("Ingresar", type="primary"):
        if password == st.secrets["PASSWORD_ADMIN"]:
            st.session_state["autenticado"] = True; st.rerun()
        else: st.error("❌ Contraseña incorrecta.")
    return False

def prorratear_gasto(monto, productos, campo_base):
    total_centavos = int(monto.quantize(CENTAVO, rounding=ROUND_HALF_UP) * 100)
    bases = [producto[campo_base] for producto in productos]
    suma_bases = sum(bases, CERO)
    if suma_bases <= CERO: raise ValueError(f"No hay base para repartir por {campo_base}.")
    partes_exactas = [Decimal(total_centavos) * base / suma_bases for base in bases]
    partes_en_centavos = [int(parte) for parte in partes_exactas]
    centavos_sobrantes = total_centavos - sum(partes_en_centavos)
    orden_por_resto = sorted(range(len(productos)), key=lambda i: partes_exactas[i] - Decimal(partes_en_centavos[i]), reverse=True)
    for indice in orden_por_resto[:centavos_sobrantes]: partes_en_centavos[indice] += 1
    return [Decimal(parte) / 100 for parte in partes_en_centavos]

def evaluar_semaforo(stock_actual, ventas_semanales, dias_entrega, fecha_proximo_pedido=None):
    if ventas_semanales <= 0:
        return "⚪", "Sin ventas registradas", 0, 0, False
    # Forzamos a que todos sean decimales (float) para evitar el choque de tipos
    stock_actual = float(stock_actual)
    ventas_semanales = float(ventas_semanales)
    dias_entrega = float(dias_entrega)

    semanas_stock   = stock_actual / ventas_semanales
    semanas_entrega = dias_entrega / 7.0
    margen = semanas_stock - semanas_entrega
    sugerido_ahora = int((semanas_entrega * ventas_semanales) + (4 * ventas_semanales) - stock_actual)
    if sugerido_ahora < 0:
        sugerido_ahora = 0
    sugerido_futuro, riesgo_quiebre = 0, False
    if fecha_proximo_pedido and fecha_proximo_pedido > date.today():
        dias_hasta = (fecha_proximo_pedido - date.today()).days
        semanas_hasta = dias_hasta / 7.0
        demanda_futura = (semanas_hasta * ventas_semanales) + (semanas_entrega * ventas_semanales) + (4 * ventas_semanales)
        sugerido_futuro = int(demanda_futura - stock_actual)
        if sugerido_futuro < 0:
            sugerido_futuro = 0
        if semanas_stock < semanas_hasta:
            riesgo_quiebre = True
    if margen <= 0:
        color, mensaje = "🔴", "¡ALERTA ROJA! Pedir YA"
    elif margen <= 2:
        color, mensaje = "🟡", "Precaución: Pedir pronto"
    else:
        color, mensaje = "🟢", "Todo bien: Stock suficiente"
    return color, mensaje, sugerido_ahora, sugerido_futuro, riesgo_quiebre

def evaluar_carga_pesada(p):
    precio_fob = p.get("precio_fob", 0)
    cantidad = p.get("cantidad", 1) or 1
    gastos_totales = sum(p.get("gastos", {}).values())
    gasto_arribo_unitario = gastos_totales / cantidad
    if precio_fob <= 0: return "⚪", "Sin datos", 0
    porcentaje = (gasto_arribo_unitario / precio_fob) * 100
    if porcentaje > 60: return "🔴", f"PELIGRO: Flete = {porcentaje:.1f}% del costo.", 0
    elif porcentaje >= 30: return "🟡", f"CUIDADO: Flete = {porcentaje:.1f}% del costo.", 0
    else: return "🟢", f"RENTABLE: Flete = {porcentaje:.1f}% del costo.", 0

def calcular_pvp_sugerido(precio_fob_usd, costo_nacionalizado_usd, factor_markup_fob=2.6, margen_minimo=0.55, precio_benchmark_local=None):
    fob, costo = Decimal(str(precio_fob_usd)), Decimal(str(costo_nacionalizado_usd))
    pvp_markup = fob * Decimal(str(factor_markup_fob))
    pvp_margen = costo * (Decimal("1") + Decimal(str(margen_minimo)))
    pvp_benchmark = Decimal(str(precio_benchmark_local)) if precio_benchmark_local else None
    pvp_sugerido = max(pvp_markup, pvp_margen)
    if pvp_benchmark: pvp_sugerido = min(pvp_sugerido, pvp_benchmark * Decimal("1.15"))
    pvp_sugerido = pvp_sugerido.quantize(CENTAVO, ROUND_HALF_UP)
    utilidad = (pvp_sugerido - costo).quantize(CENTAVO)
    rentabilidad = (utilidad / costo) if costo > 0 else Decimal("0")
    alerta = ("🔴 Rentabilidad < 30%" if rentabilidad < Decimal("0.30") else "🟡 Rentabilidad ajustada" if rentabilidad < Decimal("0.50") else "🟢 Rentabilidad saludable")
    return {"fob_usd": fob, "costo_nacionalizado_usd": costo, "pvp_sugerido": pvp_sugerido, "utilidad_unitaria": utilidad, "rentabilidad_pct": (rentabilidad * 100).quantize(CENTAVO), "alerta": alerta}

def calcular_costos(productos, gastos_ingresados, config):
    margen, desc_mayorista, desc_especial = Decimal(str(config["margen"])) / Decimal("100"), Decimal(str(config["desc_mayorista"])) / Decimal("100"), Decimal(str(config["desc_especial"])) / Decimal("100")
    gastos = []
    for nombre_gasto, criterio in GASTOS_CONTENEDOR:
        monto = gastos_ingresados[nombre_gasto]
        gastos.append((nombre_gasto, criterio, monto))
        campo_base = "peso_total" if criterio == "peso" else "volumen_total"
        repartos = prorratear_gasto(monto, productos, campo_base)
        for producto, monto_asignado in zip(productos, repartos): producto["gastos"][nombre_gasto] = monto_asignado
    for producto in productos:
        cantidad = producto["cantidad"]
        gastos_totales = sum(producto["gastos"].values(), CERO)
        gasto_unitario = gastos_totales / cantidad
        costo_real = (producto["precio_fob"] + gasto_unitario).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        producto.update({"gastos_totales": gastos_totales, "gasto_unitario": gasto_unitario, "costo_unitario": costo_real})
        producto["pvp_normal"] = redondear_entero(costo_real / (UNO - margen))
        producto["pvp_mayorista"] = redondear_entero(producto["pvp_normal"] * (UNO - desc_mayorista))
        producto["pvp_especial"] = redondear_entero(producto["pvp_normal"] * (UNO - desc_especial))
        res = calcular_pvp_sugerido(precio_fob_usd=float(producto["precio_fob"]), costo_nacionalizado_usd=float(costo_real))
        producto["pvp_sugerido"], producto["rentabilidad_pct"], producto["alerta_pvp"] = Decimal(str(res["pvp_sugerido"])), Decimal(str(res["rentabilidad_pct"])), res["alerta"]
        color, mensaje, _, _, _ = evaluar_semaforo(producto.get("stock_actual", 0), producto.get("ventas_semanales", 0), producto.get("dias_entrega", 0), config.get("fecha_proximo_pedido"))
        producto["semaforo_color"], producto["semaforo"] = color, mensaje
    return gastos
    
# ═══════════════════ 8. PARTIDA ARANCELARIA ════════════════════════════
def consultar_partida(codigo):
    return PARTIDAS_BASE.get(codigo, {
        "descripcion": "No registrada en base local",
        "ad_valorem": None, "iva": None,
        "requisitos": "Consultar con agente aduanal",
        "capitulo": "Desconocido",
    })

def estimar_derechos(codigo, valor_fob_usd, flete_usd=0.0, seguro_usd=0.0):
    info = consultar_partida(codigo)
    if info["ad_valorem"] is None:
        return {"error": "Partida sin información arancelaria local."}
    cif = valor_fob_usd + flete_usd + seguro_usd
    arancel = cif * info["ad_valorem"]
    iva     = (cif + arancel) * info["iva"]
    return {
        "partida": codigo, "descripcion": info["descripcion"],
        "ad_valorem_pct": info["ad_valorem"] * 100,
        "arancel_usd": round(arancel, 2), "iva_usd": round(iva, 2),
        "total_tributos_usd": round(arancel + iva, 2),
        "requisitos": info["requisitos"],
    }

def auditar_partidas(productos):
    filas = []
    for p in productos:
        codigo = p.get("partida_arancelaria")
        if not codigo: continue
        est = estimar_derechos(codigo, float(p["precio_fob"] * p["cantidad"]))
        if "error" in est: continue
        pagado = float(p["gastos"].get("Derechos de Aduana", 0))
        desv   = pagado - est["arancel_usd"]
        estado = ("✅ Coherente" if abs(desv) < 5 else ("⚠️ Revisar — posible sobrepago" if desv > 0 else "⚠️ Revisar — posible subdeclaración"))
        filas.append({
            "Producto": p["nombre"], "Partida": codigo, "Arancel estimado": est["arancel_usd"],
            "Arancel pagado": round(pagado, 2), "Desviación": round(desv, 2), "Estado": estado,
        })
    return filas

# ═══════════════════ 9. ALERTAS DE REPOSICIÓN ══════════════════════════
def generar_alertas_reposicion(productos, config, umbral_rojo=4, umbral_amarillo=8):
    alertas = []
    for p in productos:
        ventas, stock = p.get("ventas_semanales", 0), p.get("stock_actual", 0)
        if ventas <= 0: continue
        semanas = stock / ventas
        if semanas <= umbral_rojo: nivel, accion = "🔴 CRÍTICO", "Emitir orden de compra HOY"
        elif semanas <= umbral_amarillo: nivel, accion = "🟡 PREVENTIVO", "Preparar orden esta semana"
        else: continue
        alertas.append({
            "producto": p["nombre"], "stock": stock, "ventas_semanales": ventas,
            "semanas_cobertura": round(semanas, 1), "nivel": nivel, "accion": accion,
            "proveedor": config.get("proveedor", "N/D"),
        })
    return sorted(alertas, key=lambda x: x["semanas_cobertura"])

def mostrar_alertas_en_panel(alertas):
    if not alertas:
        st.success("✅ Sin alertas. Inventario saludable."); return
    for a in alertas:
        bg = "#FFC7CE" if "CRÍTICO" in a["nivel"] else "#FFEB9C"
        borde = "#C00000" if "CRÍTICO" in a["nivel"] else "#BF8F00"
        st.markdown(f"""
        <div style="background-color:{bg}; padding:12px; border-radius:8px; margin-bottom:8px; border-left:6px solid {borde};">
            <b>{a['nivel']} — {a['producto']}</b><br>
            Stock: <b>{a['stock']:,} unds</b> · Ventas: <b>{a['ventas_semanales']}/sem</b>
            · Cobertura: <b>{a['semanas_cobertura']} semanas</b><br>
            Acción: <i>{a['accion']}</i> — Proveedor: {a['proveedor']}
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════ 10. FLUJO DE CAJA ═════════════════════════════════
def proyectar_flujo_caja(productos, config, semanas=13, crecimiento_semanal=0.02, costo_fijo_semanal=0.0, pago_importacion=None):
    hoy  = date.today()
    saldo = Decimal(str(config.get("capital_inicial", 0)))
    filas = []
    for w in range(1, semanas + 1):
        fecha = hoy + timedelta(weeks=w)
        ingreso = Decimal("0")
        for p in productos:
            ventas = Decimal(str(p.get("ventas_semanales", 0)))
            pvp    = Decimal(str(p.get("pvp_normal", 0)))
            factor = Decimal(str((1 + crecimiento_semanal) ** w))
            ingreso += ventas * pvp * factor
        egreso = Decimal(str(costo_fijo_semanal))
        if pago_importacion and pago_importacion.get("fecha") == fecha:
            egreso += Decimal(str(pago_importacion["monto_usd"]))
        saldo += ingreso - egreso
        filas.append({"Semana": w, "Fecha": fecha.strftime("%Y-%m-%d"), "Ingreso proyectado": float(ingreso.quantize(CENTAVO)), "Egreso proyectado":  float(egreso.quantize(CENTAVO)), "Saldo acumulado":    float(saldo.quantize(CENTAVO))})
    return pd.DataFrame(filas)

def mostrar_flujo_caja(df_flujo):
    st.subheader("📅 Proyección de flujo de caja — 13 semanas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingreso total", f"$ {df_flujo['Ingreso proyectado'].sum():,.0f}")
    c2.metric("Saldo final",   f"$ {df_flujo['Saldo acumulado'].iloc[-1]:,.0f}")
    minimo = df_flujo["Saldo acumulado"].min()
    c3.metric("Saldo mínimo", f"$ {minimo:,.0f}", delta=None if minimo >= 0 else "⚠️ Riesgo de iliquidez")
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(df_flujo["Semana"], df_flujo["Saldo acumulado"], marker="o", color="#1F4E78")
    ax.axhline(0, color="red", linestyle="--", linewidth=1)
    ax.set_xlabel("Semana"); ax.set_ylabel("Saldo acumulado (USD)")
    ax.set_title("Saldo de caja proyectado"); ax.grid(alpha=0.3)
    st.pyplot(fig)

# ═══════════════════ 11. EXPORTACIÓN PARA GOOGLE SHEETS ════════════════
def exportar_csv_para_sheets(productos, config):
    filas = []
    for p in productos:
        filas.append({
            "Producto": p["nombre"], "Partida_Arancelaria": p.get("partida_arancelaria", ""),
            "Cantidad": p["cantidad"], "FOB_Origen_USD": float(p["precio_fob"]),
            "Costo_Real_USD": float(p["costo_unitario"]), "PVP_Normal": float(p["pvp_normal"]),
            "PVP_Sugerido": float(p.get("pvp_sugerido", p["pvp_normal"])),
            "Rentabilidad_Pct": float(p.get("rentabilidad_pct", 0)),
            "Stock_Actual": p.get("stock_actual", 0), "Ventas_Semanales": p.get("ventas_semanales", 0),
            "Semaforo": p.get("semaforo", ""),
        })
    return pd.DataFrame(filas).to_csv(index=False).encode("utf-8-sig")

def boton_exportar_sheets(productos, config):
    csv = exportar_csv_para_sheets(productos, config)
    id_perfil = config.get("id_perfil", "empresa")
    st.download_button("📱 Descargar CSV para Google Sheets", data=csv, file_name=f"importacion_{config.get('factura','SN')}_{id_perfil}.csv", mime="text/csv", help="Súbelo a Google Drive → abrir con Google Sheets → consultar desde el celular.")

# ═══════════════════ 12. REPORTE DE TEXTO Y PDF ════════════════════════
def crear_reporte(productos, gastos_contenedor, config):
    origen_efectivo = texto_efectivo(config.get("origen"), config.get("origen_otro"))
    sector_efectivo = texto_efectivo(config.get("sector"), config.get("sector_otro"))
    encabezado = "\n".join(("=" * 72, "   SISTEMA DE COSTOS DE IMPORTACIÓN", f"   Empresa: {config.get('empresa', 'No especificada')}", f"   RIF: {config.get('rif', 'No especificado')}", f"   Propietario: {config.get('propietario', 'No especificado')}", f"   Sector: {sector_efectivo}", f"   Origen: {origen_efectivo} · Proveedor: {config.get('proveedor','N/D')}", f"   Factura: {config.get('factura','N/D')} · Fecha: {date.today().isoformat()}", "=" * 72))
    lineas = [encabezado, "", "=" * 72, f"   REPORTE DE COSTOS: {len(productos)} productos", "=" * 72]
    for indice, producto in enumerate(productos, start=1):
        cantidad = producto["cantidad"]
        lineas.extend(["", f"PRODUCTO {indice}: {producto['nombre']}", "-" * 72, f"   Cantidad:                       {cantidad:>12,}", f"   Peso total:                     {producto['peso_total']:>12,.3f} kg", f"   Volumen total:                  {producto['volumen_total']:>12,.6f} m³", f"   Precio FOB Origen (por unidad): {formato_dinero(producto['precio_fob'])}", f"   Precio FOB Origen (total):      {formato_dinero(producto['precio_fob'] * cantidad)}", "", "   GASTOS DE ARRIBO ASIGNADOS:"])
    lineas.append(f"      {'Concepto':<28s} | {'Total':>12s} | {'Por Unidad':>12s}")
    lineas.append("      " + "-" * 58)
    for nombre_gasto, criterio, _ in gastos_contenedor:
        asignado = producto["gastos"][nombre_gasto]
        lineas.append(f"      {nombre_gasto:<28s} | {formato_dinero(asignado):>12s} | {formato_dinero(asignado / cantidad):>12s} / u")
        lineas.extend(["", f"   Gastos de arribo (total):        {formato_dinero(producto['gastos_totales'])}", f"   Gastos de arribo (por unidad):   {formato_dinero(producto['gasto_unitario'])}", f"   COSTO REAL EN ESTANTE (unidad):  {formato_dinero(producto['costo_unitario'])}", "   PRECIOS DE VENTA:", f"      PVP Normal:                   $ {producto['pvp_normal']:>12,.0f}", f"      PVP Mayorista:                $ {producto['pvp_mayorista']:>12,.0f}", f"      PVP Especial:                 $ {producto['pvp_especial']:>12,.0f}", f"      PVP Sugerido (3 criterios):   {formato_dinero(producto['pvp_sugerido'])}", f"      Rentabilidad real:            {producto['rentabilidad_pct']:.1f}%  {producto.get('alerta_pvp','')}"])
        if producto.get("partida_arancelaria"):
            info = consultar_partida(producto["partida_arancelaria"])
            lineas.append(f"   PARTIDA ARANCELARIA: {producto['partida_arancelaria']} — {info['descripcion']}")
        color, mensaje, sug_ahora, sug_futuro, riesgo = evaluar_semaforo(producto.get("stock_actual", 0), producto.get("ventas_semanales", 0), producto.get("dias_entrega", 0), config.get("fecha_proximo_pedido"))

        # Convertimos el emoji en texto para el reporte
        if color == "🔴": color_txt = "ROJO"
        elif color == "🟡": color_txt = "AMARILLO"
        elif color == "🟢": color_txt = "VERDE"
        else: color_txt = "SIN ALERTA"

        lineas.extend([f"   SEMÁFORO: [{color_txt}] {mensaje}", f"   ====> Pedir AHORA: {sug_ahora} unds"])
        if sug_futuro > 0 and config.get("fecha_proximo_pedido"): lineas.append(f"   ====> Para el {config['fecha_proximo_pedido']}: {sug_futuro} unds")
        if riesgo: lineas.append("   ⚠️ ALERTA: Se agota antes del próximo pedido.")
        color_carga, mensaje_carga, _ = evaluar_carga_pesada(producto)
        lineas.extend([f"   EVALUACIÓN DE CARGA: {mensaje_carga}", "----------------------------------------"])
    lineas.extend(["", "=" * 60, "  TABLA RESUMEN", "=" * 60, f"  {'Producto':<20s} {'Cant.':>8s} {'Costo U.':>10s} {'PVP N.':>10s} {'PVP M.':>10s} {'PVP E.':>10s} {'PVP Sug.':>10s}", "  " + "-" * 90])
    for producto in productos:
        nombre_corto = str(producto['nombre'])[:33] 
        lineas.append(
            f"  {nombre_corto:<35s} | {producto['cantidad']:>6,} "
            f"| $ {producto['costo_unitario']:>7.2f} | $ {producto['pvp_normal']:>7.2f} "
            f"| $ {producto['pvp_mayorista']:>7.2f} | $ {producto['pvp_especial']:>7.2f} "
            f"| $ {producto['pvp_sugerido']:>7.2f}"
        )
    lineas.extend(["", "=" * 72, "   CONTROL DE PRORRATEO", "=" * 72])
    lineas.append(f"   {'Concepto':<30s} | {'Ingresado':>15s} | {'Repartido':>15s}")
    lineas.append("   " + "-" * 66)
    for nombre_gasto, criterio, monto_ingresado in gastos_contenedor:
        monto_repartido = sum((p["gastos"][nombre_gasto] for p in productos), CERO)
        lineas.append(f"   {nombre_gasto:<30s} | {formato_dinero(monto_ingresado):>15s} | {formato_dinero(monto_repartido):>15s}")
    lineas.extend(["", "=" * 72, "   Diseñado y elaborado por el Prof. Jesús Pulido V.", "   Asesor de Importación Inteligente · 0424-728.3199 / 0416-291.6426", "=" * 72])
    return "\n".join(lineas) + "\n"

def generar_pdf_reporte(reporte_texto, config):
    try:
        pdf = FPDF(); pdf.add_page()
        pdf.set_font("Helvetica", "B", 14); pdf.cell(0, 10, "Sistema de Análisis de Importación", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 9); pdf.cell(0, 6, f"{config.get('empresa','')} · RIF {config.get('rif','')}", ln=True, align="C")
        
        pdf.set_font("Courier", "", 8); pdf.ln(4)
        
        import re
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF" u"\U0001F1E0-\U0001F1FF"
            u"\U00002702-\U000027B0" u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF" u"\U00002500-\U00002BEF"
            "]+", flags=re.UNICODE)

        for linea in reporte_texto.split("\n"):
            linea_limpia = emoji_pattern.sub(r'', linea)
            linea_limpia = linea_limpia.encode("latin-1", "replace").decode("latin-1")
            
            # --- AQUÍ APLICAMOS LOS COLORES AL TEXTO ---
            pdf.set_text_color(0, 0, 0) # Negro por defecto
            if "[ROJO]" in linea_limpia or "ALERTA ROJA" in linea_limpia:
                pdf.set_text_color(200, 0, 0) # Color Rojo
            elif "[AMARILLO]" in linea_limpia or "Precaución" in linea_limpia:
                pdf.set_text_color(200, 150, 0) # Color Naranja/Amarillo
            elif "[VERDE]" in linea_limpia or "Todo bien" in linea_limpia:
                pdf.set_text_color(0, 150, 0) # Color Verde
            
            pdf.set_x(10)
            if not linea_limpia.strip():
                pdf.ln(4)
            else:
                pdf.multi_cell(0, 4, linea_limpia, new_x="LMARGIN", new_y="NEXT")
                
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Error generando PDF: {e}"); return None

# ═══════════════════ 13. CARGA DE EXCEL ════════════════════════════════
def leer_excel(archivo):
    if archivo.name.lower().endswith(".csv"): return pd.read_csv(archivo)
    return pd.read_excel(archivo)

def sugerir_columna(columnas, posibles):
    columnas_lower = {c: str(c).lower() for c in columnas}
    for palabra in posibles:
        for col, col_lower in columnas_lower.items():
            if palabra in col_lower: return col
    return None

def mapear_columnas(df):
    columnas = ["(ninguna)"] + list(df.columns)
    st.markdown("**Mapeo de columnas del Excel**")
    c1, c2, c3 = st.columns(3); c4, c5, c6 = st.columns(3); c7, c8, c9 = st.columns(3)
    sugerencias = {"producto": ["producto", "descripcion", "descripción", "nombre", "articulo"], "cantidad": ["cantidad", "cant", "unidades", "qty"], "precio": ["fob", "precio", "origen", "china", "unitario", "costo"], "peso": ["peso", "kg", "weight"], "volumen": ["volumen", "m3", "cbm", "volume"], "stock": ["stock", "inventario", "existencia"], "ventas": ["venta", "ventas", "semanal", "salida"], "dias": ["dias", "días", "entrega", "llegada", "transito"], "partida": ["partida", "hs", "arancel", "codigo"]}
    def selector(col, etiqueta, keys, key_sel):
        sug = sugerir_columna(df.columns, keys)
        idx = columnas.index(sug) if sug in columnas else 0
        return col.selectbox(etiqueta, columnas, index=idx, key=key_sel)
    return {
        "producto": selector(c1, "Producto / Descripción", sugerencias["producto"], "sel_prod"), "cantidad": selector(c2, "Cantidad", sugerencias["cantidad"], "sel_cant"), "precio": selector(c3, "Precio FOB Origen $/u", sugerencias["precio"], "sel_prec"), "peso": selector(c4, "Peso unitario (kg)", sugerencias["peso"], "sel_peso"), "volumen": selector(c5, "Volumen unitario (m³)", sugerencias["volumen"], "sel_vol"), "stock": selector(c6, "Stock Actual", sugerencias["stock"], "sel_stock"), "ventas": selector(c7, "Ventas Semanales", sugerencias["ventas"], "sel_vent"), "dias": selector(c8, "Días de Entrega", sugerencias["dias"], "sel_dias"), "partida": selector(c9, "Partida Arancelaria", sugerencias["partida"], "sel_part"),
    }

def construir_productos_desde_df(df, mapeo):
    faltantes = [k for k in ["producto","cantidad","precio","peso","volumen","stock","ventas","dias"] if mapeo.get(k) in (None, "(ninguna)")]
    if faltantes: raise ValueError(f"Falta mapear: {', '.join(faltantes)}")
    productos = []
    for i, fila in df.iterrows():
        try:
            nombre, cantidad, precio, peso_u, vol_u = str(fila[mapeo["producto"]]).strip(), int(fila[mapeo["cantidad"]]), Decimal(str(fila[mapeo["precio"]])), Decimal(str(fila[mapeo["peso"]])), Decimal(str(fila[mapeo["volumen"]]))
            stock, ventas, dias = int(fila[mapeo["stock"]]), Decimal(str(fila[mapeo["ventas"]])), int(fila[mapeo["dias"]])
            partida = str(fila[mapeo["partida"]]).strip() if mapeo.get("partida") and mapeo["partida"] != "(ninguna)" else ""
            if cantidad <= 0: raise ValueError("cantidad debe ser > 0")
            productos.append({"nombre": nombre, "cantidad": cantidad, "precio_fob": precio, "peso_total": peso_u * cantidad, "volumen_total": vol_u * cantidad, "stock_actual": stock, "ventas_semanales": ventas, "dias_entrega": dias, "partida_arancelaria": partida, "gastos": {}})
        except Exception as e: st.warning(f"Fila {i + 2} omitida: {e}")
    if not productos: raise ValueError("No se pudo cargar ningún producto válido.")
    return productos

# ═══════════════════ 14. PERFILES DE EMPRESA ═══════════════════════════
def inicializar_estado():
    if "config_empresa" not in st.session_state: st.session_state.config_empresa = dict(DEFAULTS)

def listar_perfiles():
    if SHEETS_DB_OK:
        try: return sheets_db.listar_perfiles()
        except Exception: pass
    return st.session_state.get("perfiles_locales", [])

def guardar_perfil_local(perfil):
    perfiles = st.session_state.get("perfiles_locales", [])
    existentes = {p["id_perfil"]: i for i, p in enumerate(perfiles)}
    if perfil["id_perfil"] in existentes: perfiles[existentes[perfil["id_perfil"]]] = perfil
    else: perfiles.append(perfil)
    st.session_state["perfiles_locales"] = perfiles

def cargar_perfil(perfil):
    for k, v in perfil.items():
        if k in st.session_state.config_empresa: st.session_state.config_empresa[k] = v

def panel_perfil_sidebar():
    st.sidebar.header("🏢 Perfil de Empresa")
    perfiles = listar_perfiles()
    opciones = ["➕ Crear nueva empresa"] + [f"{p['empresa']} ({p['id_perfil']})" for p in perfiles]
    actual_id = st.session_state.config_empresa.get("id_perfil", "")
    idx_actual = 0
    for i, p in enumerate(perfiles):
        if p["id_perfil"] == actual_id: idx_actual = i + 1; break
    sel = st.sidebar.selectbox("Seleccionar empresa", opciones, index=idx_actual)
    if sel == "➕ Crear nueva empresa":
        st.sidebar.markdown("### 🆕 Nueva empresa")
        empresa, rif, prop, email = st.sidebar.text_input("Razón Social *", key="new_empresa"), st.sidebar.text_input("RIF", key="new_rif"), st.sidebar.text_input("Propietario / Responsable", key="new_prop"), st.sidebar.text_input("Email de contacto", key="new_email")
        sector = st.sidebar.selectbox("Sector / Rubro", SECTORES, key="new_sector")
        sector_otro = st.sidebar.text_input("Especifique el sector", key="new_sector_otro") if sector.startswith("Otro") else ""
        origen = st.sidebar.selectbox("Origen principal", ORIGENES, key="new_origen")
        origen_otro = st.sidebar.text_input("Especifique el origen", key="new_origen_otro") if origen.startswith("Otro") else ""
        moneda = st.sidebar.selectbox("Moneda base", ["USD", "EUR", "VES"], key="new_moneda")
        if st.sidebar.button("💾 Crear perfil", type="primary", key="btn_crear_perfil"):
            if not empresa.strip(): st.sidebar.error("La Razón Social es obligatoria.")
            else:
                perfil = {"id_perfil": slugify(empresa), "empresa": empresa.strip(), "rif": rif.strip(), "propietario": prop.strip(), "email": email.strip(), "sector": sector, "sector_otro": sector_otro.strip(), "origen": origen, "origen_otro": origen_otro.strip(), "moneda_default": moneda, "margen": DEFAULTS["margen"], "desc_mayorista": DEFAULTS["desc_mayorista"], "desc_especial": DEFAULTS["desc_especial"], "proveedor": ""}
                if SHEETS_DB_OK:
                    ok, msg = sheets_db.crear_actualizar_perfil(perfil)
                    (st.sidebar.success if ok else st.sidebar.warning)(msg)
                else: guardar_perfil_local(perfil); st.sidebar.success(f"✅ Perfil '{empresa}' creado localmente.")
                cargar_perfil(perfil); st.rerun()
    else:
        idx = opciones.index(sel) - 1
        perfil = perfiles[idx]
        cargar_perfil(perfil)
        st.sidebar.success(f"✅ Perfil activo: **{perfil['empresa']}**")
        st.sidebar.caption(f"ID: `{perfil['id_perfil']}`")
    st.sidebar.divider()

# ═══════════════════ 15. CONFIGURACIÓN AVANZADA SIDEBAR ════════════════
def panel_configuracion_avanzada(config):
    with st.sidebar.expander("⚙️ Ajustes avanzados", expanded=False):
        config["margen"] = st.number_input("Margen normal (%)", 0.0, 99.0, float(config["margen"]), 0.5, key="adv_margen")
        config["desc_mayorista"] = st.number_input("Descuento mayorista (%)", 0.0, 99.0, float(config["desc_mayorista"]), 0.5, key="adv_desc_may")
        config["desc_especial"] = st.number_input("Descuento especial (%)", 0.0, 99.0, float(config["desc_especial"]), 0.5, key="adv_desc_esp")
        config["capital_inicial"] = st.number_input("Capital inicial ($)", 0.0, value=float(config["capital_inicial"]), step=100.0, key="adv_cap")
        config["costo_fijo_semanal"] = st.number_input("Costo fijo semanal ($)", 0.0, value=float(config["costo_fijo_semanal"]), step=10.0, key="adv_cf")
        config["monto_proximo_pedido"] = st.number_input("Monto próximo pedido ($)", 0.0, value=float(config["monto_proximo_pedido"]), step=100.0, key="adv_mpp")
        config["fecha_proximo_pedido"] = st.date_input("Fecha próximo pedido", value=config.get("fecha_proximo_pedido"), key="adv_fpp")
    st.sidebar.divider()
    st.sidebar.subheader("🌍 Origen del embarque")
    config["origen"] = st.sidebar.selectbox("País de origen", ORIGENES, index=ORIGENES.index(config.get("origen", "China")) if config.get("origen") in ORIGENES else 0, key="origen_sel")
    if config["origen"].startswith("Otro"): config["origen_otro"] = st.sidebar.text_input("Especifique el país", value=config.get("origen_otro",""), key="origen_otro_txt")
    config["proveedor"] = st.sidebar.text_input("Proveedor", value=config.get("proveedor",""), key="prov_txt")
    config["factura"]   = st.sidebar.text_input("Nro. de Factura", value=config.get("factura",""), key="fact_txt")
    st.session_state.config_empresa = config
    return config

# ═══════════════════ 16. VISTAS ════════════════════════════════════════
def vista_analisis_costos(productos, config):
    st.subheader("📊 Análisis de costos por producto")
    filas = [{"Producto": p["nombre"], "Cantidad": p["cantidad"], "FOB $/u": float(p["precio_fob"]), "Gasto arribo $/u": float(p["gasto_unitario"]), "Costo real $/u": float(p["costo_unitario"]), "PVP Normal": float(p["pvp_normal"]), "PVP Sugerido": float(p["pvp_sugerido"]), "Rentab. %": float(p["rentabilidad_pct"]), "Partida": p.get("partida_arancelaria", ""), "Alerta PVP": p.get("alerta_pvp", ""), "Semáforo": p.get("semaforo", "")} for p in productos]
    st.dataframe(pd.DataFrame(filas), use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    inv_total, arr_total, mer_total = sum((p["costo_unitario"] * p["cantidad"] for p in productos), CERO), sum((p["gastos_totales"] for p in productos), CERO), sum((p["precio_fob"] * p["cantidad"] for p in productos), CERO)
    en_rojo = sum(1 for p in productos if "🔴" in p.get("semaforo_color", ""))
    c1.metric("Inversión total", formato_dinero(inv_total))
    c2.metric("Gasto arribo / mercancía", f"{(arr_total / mer_total * 100) if mer_total > 0 else 0:.1f}%")
    c3.metric("Productos en rojo", f"{en_rojo} / {len(productos)}")
    c4.metric("Margen promedio", f"{sum(float(p['rentabilidad_pct']) for p in productos)/len(productos):.1f}%")
    fig, ax = plt.subplots(figsize=(10, 4))
    nombres = [p["nombre"][:20] for p in productos]; costos = [float(p["costo_unitario"]) for p in productos]; sugeridos = [float(p["pvp_sugerido"]) for p in productos]
    x = range(len(nombres))
    ax.bar([i - 0.2 for i in x], costos, width=0.4, label="Costo real", color="#C44E52")
    ax.bar([i + 0.2 for i in x], sugeridos, width=0.4, label="PVP sugerido", color="#4C72B0")
    ax.set_xticks(list(x)); ax.set_xticklabels(nombres, rotation=20, ha="right"); ax.set_title("Costo real vs PVP Sugerido"); ax.legend(); ax.grid(alpha=0.3, axis="y")
    st.pyplot(fig)

def vista_auditoria_aduanera(productos):
    st.subheader("🏷️ Auditoría de Partidas Arancelarias")
    auditoria = auditar_partidas(productos)
    if not auditoria: st.warning("Ningún producto tiene partida arancelaria cargada."); return
    st.dataframe(pd.DataFrame(auditoria), use_container_width=True)
    st.markdown("### Detalle por partida")
    for p in productos:
        codigo = p.get("partida_arancelaria")
        if not codigo: continue
        info = consultar_partida(codigo); est = estimar_derechos(codigo, float(p["precio_fob"] * p["cantidad"]))
        st.info(f"**{p['nombre']}** — `{codigo}`  \n{info['descripcion']}  \nAd-valorem: **{info['ad_valorem']*100:.0f}%** · Requisitos: {info['requisitos']}  \nArancel estimado: **${est.get('arancel_usd', 0):,.2f}** · IVA: **${est.get('iva_usd', 0):,.2f}**")

def vista_historial(config):
    st.subheader("📚 Historial persistente de importaciones")
    id_perfil = config.get("id_perfil", "")
    if SHEETS_DB_OK:
        est = sheets_db.estado_conexion(); st.caption(f"Modo: **{est['modo'].upper()}** · {est['mensaje']}")
        df_hist = sheets_db.leer_historial(id_perfil=id_perfil)
    else: st.caption("Modo: **LOCAL** (sin `sheets_db.py`)"); df_hist = pd.DataFrame()
    if df_hist.empty: st.info(f"Aún no hay importaciones guardadas para **{config.get('empresa','esta empresa')}**."); return
    c1, c2, c3 = st.columns(3)
    with c1: f_sel = st.selectbox("Filtrar por factura", ["(Todas)"] + sorted(df_hist["factura"].astype(str).unique().tolist()))
    with c2: p_sel = st.selectbox("Filtrar por producto", ["(Todos)"] + sorted(df_hist["producto"].astype(str).unique().tolist()))
    with c3: sem_filtro = st.selectbox("Filtrar por semáforo", ["(Todos)", "🔴", "🟡", "🟢", "⚪"])
    df_f = df_hist.copy()
    if f_sel != "(Todas)": df_f = df_f[df_f["factura"] == f_sel]
    if p_sel != "(Todos)": df_f = df_f[df_f["producto"] == p_sel]
    if sem_filtro != "(Todos)": df_f = df_f[df_f["semaforo"] == sem_filtro]
    st.dataframe(df_f, use_container_width=True, height=400)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Importaciones", df_f["id_importacion"].nunique()); m2.metric("Productos", len(df_f))
    m3.metric("Gasto arribo USD", f"$ {pd.to_numeric(df_f['gasto_arribo_total_usd'], errors='coerce').sum():,.0f}")
    m4.metric("Productos en rojo", (df_f["semaforo"] == "🔴").sum())
    st.download_button("📥 Descargar historial filtrado (CSV)", data=df_f.to_csv(index=False).encode("utf-8-sig"), file_name=f"historial_{id_perfil}_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

# ═══════════════════ 17. MAIN ══════════════════════════════════════════
def main():
    st.set_page_config(page_title="Sistema de Importación Inteligente", page_icon="🛳️", layout="wide")
    if not verificar_acceso(): return
    inicializar_estado(); inicializar_monedas()
    panel_perfil_sidebar()
    config = st.session_state.config_empresa.copy()
    if not config.get("empresa"): st.warning("👈 Crea o selecciona un **perfil de empresa** en la barra lateral para comenzar."); return
    panel_configuracion_avanzada(config); panel_monedas_sidebar(config)
    st.title("🛳️ Sistema de Análisis de Importación Inteligente")
    st.caption(f"Empresa activa: **{config['empresa']}** · Sector: {texto_efectivo(config.get('sector'), config.get('sector_otro'))} · Origen: {texto_efectivo(config.get('origen'), config.get('origen_otro'))}")
    st.caption("Metodología: **Prof. Jesús Pulido V.** · Asesor de Importación Inteligente")
    with st.sidebar:
        st.markdown("---")
        if SHEETS_DB_OK:
            est = sheets_db.estado_conexion()
            if est["modo"] == "nube": st.success(f"☁️ {est['mensaje']}")
            else: st.info(f"💾 {est['mensaje']}")
        else: st.info("💾 Modo local (sin sheets_db.py)")
        if os.path.exists("Control_Importaciones.xlsx"):
            with open("Control_Importaciones.xlsx", "rb") as f: st.download_button("📥 Dashboard Excel", data=f.read(), file_name="Control_Importaciones.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown("---"); st.caption("📞 0424-728.3199 / 0416-291.6426"); st.caption("✉️ jeshua166@gmail.com")
    archivo = st.file_uploader("📤 Sube tu Excel o CSV con los productos", type=["xlsx", "xls", "csv"])
    if archivo is None:
        st.info("Sube un archivo para comenzar.")
        with st.expander("❓ Columnas esperadas"): st.markdown("- Producto / Descripción\n- Cantidad\n- Precio FOB Origen (unitario)\n- Peso unitario (kg)\n- Volumen unitario (m³)\n- Stock Actual\n- Ventas Semanales\n- Días de Entrega\n- Partida Arancelaria (opcional pero recomendada)")
        return
    try:
        df = leer_excel(archivo); st.success(f"✅ Archivo cargado: **{len(df)}** filas")
        with st.expander("👀 Ver primeras filas"): st.dataframe(df.head(), use_container_width=True)
    except Exception as e: st.error(f"Error al leer archivo: {e}"); return
    mapeo = mapear_columnas(df)
    st.markdown("### 💼 Gastos del contenedor (en USD)")
    cols = st.columns(3); gastos_ingresados = {}
    for i, (nombre, criterio) in enumerate(GASTOS_CONTENEDOR):
        with cols[i % 3]:
            val = st.number_input(f"{nombre} ({criterio})", min_value=0.0, value=0.0, step=10.0, key=f"g_{nombre}")
            gastos_ingresados[nombre] = Decimal(str(val))
    if not st.button("🚀 Calcular análisis completo", type="primary"): return
    try:
        productos = construir_productos_desde_df(df, mapeo)
        gastos_contenedor = calcular_costos(productos, gastos_ingresados, config)
    except Exception as e: st.error(f"Error en cálculo: {e}"); return
    st.success(f"✅ Análisis completado para **{len(productos)}** productos.")
    if SHEETS_DB_OK:
        if st.button("💾 Guardar esta importación en el historial", type="secondary"):
            ok, msg = sheets_db.guardar_importacion(productos, config, usuario=config.get("propietario") or "admin")
            (st.success if ok else st.warning)(msg)
            sheets_db.guardar_alertas(generar_alertas_reposicion(productos, config))
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Análisis de costos", "🚦 Reposición", "📅 Flujo de caja", "🏷️ Auditoría aduanera", "📄 Reporte completo", "📚 Historial"])
    with tab1: vista_analisis_costos(productos, config)
    with tab2: mostrar_alertas_en_panel(generar_alertas_reposicion(productos, config))
    with tab3: mostrar_flujo_caja(proyectar_flujo_caja(productos, config, semanas=13, crecimiento_semanal=0.02, costo_fijo_semanal=config.get("costo_fijo_semanal", 0), pago_importacion={"fecha": config.get("fecha_proximo_pedido"), "monto_usd": config.get("monto_proximo_pedido", 0)}))
    with tab4: vista_auditoria_aduanera(productos)
    with tab5:
        reporte = crear_reporte(productos, gastos_contenedor, config); st.text(reporte)
        col_a, col_b, col_c = st.columns(3)
        with col_a: st.download_button("📄 Descargar TXT", data=reporte, file_name=f"reporte_{config.get('factura','SN')}.txt", mime="text/plain")
        with col_b:
            pdf_bytes = generar_pdf_reporte(reporte, config)
            if pdf_bytes:
                st.download_button("📥 Descargar PDF", data=pdf_bytes, file_name=f"reporte_{config.get('factura','SN')}.pdf", mime="application/pdf")
        with col_c: boton_exportar_sheets(productos, config)
    with tab6: vista_historial(config)

if __name__ == "__main__":
    main()

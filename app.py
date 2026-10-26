# ═══════════════════════════════════════════════════════════════════════
#  SISTEMA DE ANÁLISIS DE IMPORTACIÓN INTELIGENTE 🐉✨ (BLOQUE 1 / 3)
#. Importaciones, Constantes, Utilidades y Lógica de Datos y Semáforo
#  Motor original y metodología: Prof. Jesús Pulido V.
# ═══════════════════════════════════════════════════════════════════════

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, timedelta, datetime
import io, os, json, re, unicodedata
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from xhtml2pdf import pisa
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

def a_decimal(valor, defecto="0"):
    if pd.isna(valor) or valor is None or str(valor).strip() == "":
        return Decimal(str(defecto))
    try:
        val_str = str(valor).strip().replace(",", ".")
        return Decimal(val_str)
    except Exception:
        return Decimal(str(defecto))

def redondear_entero(valor): return valor.quantize(UNO, rounding=ROUND_HALF_UP)

def verificar_acceso():
    if "PASSWORD_ADMIN" not in st.secrets: return True
    if st.session_state.get("autenticado", False): return True
    
    for nombre in ("IMG-20261021-WA0005.jpg", "portada.jpg", "portada.png"):
        if os.path.exists(nombre):
            st.image(nombre, use_container_width=True); break
            
    st.markdown("<h1 style='text-align:center;'>Bienvenidos 🛳️</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>¿Sabe cuánto le cuesta realmente traer los productos desde el exterior hasta su depósito?</h3>", unsafe_allow_html=True)
    st.markdown("""
    - **La verdad** sobre sus costos de importación, márgenes y precios óptimos.
    - **Identificar** los márgenes reales de ganancia antes de nacionalizar.
    - **Optimizar** el espacio de su contenedor.
    - **Alarmas** 🟢🟡🔴 de reposición por IA.
    - **Ingresar** datos desde Excel automáticamente.
    - **Definir** el mejor proveedor del exterior.
    """)
    
    st.markdown("""
    <div style="background-color: #e8f4f8; color: #0b2545; padding: 15px; border-radius: 5px; text-align: center; border-left: 5px solid #2196F3; margin-top: 20px; margin-bottom: 20px;">
    <strong>"UN SISTEMA DE COMERCIALIZACIÓN DISEÑADO PARA PROTEGER SU CAPITAL Y ASEGURAR QUE EL NEGOCIO SIEMPRE CREZCA"</strong>
    </div>
    """, unsafe_allow_html=True)

    col_i, col_c, col_d = st.columns([1, 1, 1])
    with col_c:
        st.markdown("<h4 style='text-align:center;'>Diseñado y elaborado por<br>su Asesor de Importación Inteligente<br>Prof. Jesús Pulido V.</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;'>0424-728.3199 / 0416-291.6426</p>", unsafe_allow_html=True)
        for nombre in ("profesor.jpg", "asesor.jpg"):
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
    stock_actual = float(stock_actual) if stock_actual is not None else 0.0
    ventas_semanales = float(ventas_semanales) if ventas_semanales is not None else 0.0
    dias_entrega = float(dias_entrega) if dias_entrega is not None else 0.0

    if ventas_semanales <= 0:
        return "⚪", "Sin ventas registradas", 0, 0, False

    semanas_stock   = stock_actual / ventas_semanales
    semanas_entrega = dias_entrega / 7.0
    margen = semanas_stock - semanas_entrega
    sugerido_ahora = int((semanas_entrega * ventas_semanales) + (4 * ventas_semanales) - stock_actual)
    if sugerido_ahora < 0:
        sugerido_ahora = 0
    sugerido_futuro, riesgo_quiebre = 0, False
    if fecha_proximo_pedido and isinstance(fecha_proximo_pedido, date) and fecha_proximo_pedido > date.today():
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
    precio_fob = float(p.get("precio_fob", 0))
    cantidad = float(p.get("cantidad", 1) or 1)
    gastos_totales = float(sum(p.get("gastos", {}).values()))
    gasto_arribo_unitario = gastos_totales / cantidad if cantidad > 0 else 0
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
    margen = Decimal(str(config["margen"])) / Decimal("100")
    desc_mayorista = Decimal(str(config["desc_mayorista"])) / Decimal("100")
    desc_especial = Decimal(str(config["desc_especial"])) / Decimal("100")
    
    gastos = []
    for nombre_gasto, criterio in GASTOS_CONTENEDOR:
        monto = gastos_ingresados[nombre_gasto]
        gastos.append((nombre_gasto, criterio, monto))
        campo_base = "peso_total" if criterio == "peso" else "volumen_total"
        repartos = prorratear_gasto(monto, productos, campo_base)
        for producto, monto_asignado in zip(productos, repartos): 
            producto["gastos"][nombre_gasto] = monto_asignado
            
    for producto in productos:
        cantidad = producto["cantidad"]
        gastos_totales = sum(producto["gastos"].values(), CERO)
        gasto_unitario = gastos_totales / Decimal(str(cantidad))
        costo_real = (producto["precio_fob"] + gasto_unitario).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        producto.update({"gastos_totales": gastos_totales, "gasto_unitario": gasto_unitario, "costo_unitario": costo_real})
        
        div = UNO - margen
        producto["pvp_normal"] = redondear_entero(costo_real / div) if div > CERO else costo_real
        producto["pvp_mayorista"] = redondear_entero(producto["pvp_normal"] * (UNO - desc_mayorista))
        producto["pvp_especial"] = redondear_entero(producto["pvp_normal"] * (UNO - desc_especial))
        
        res = calcular_pvp_sugerido(precio_fob_usd=float(producto["precio_fob"]), costo_nacionalizado_usd=float(costo_real))
        producto["pvp_sugerido"] = Decimal(str(res["pvp_sugerido"]))
        producto["rentabilidad_pct"] = Decimal(str(res["rentabilidad_pct"]))
        producto["alerta_pvp"] = res["alerta"]
        
        color, mensaje, _, _, _ = evaluar_semaforo(producto.get("stock_actual", 0), producto.get("ventas_semanales", 0), producto.get("dias_entrega", 0), config.get("fecha_proximo_pedido"))
        producto["semaforo_color"] = color
        producto["semaforo"] = mensaje
    return gastos


# ═══════════════════════════════════════════════════════════════════════
#  SISTEMA DE ANÁLISIS DE IMPORTACIÓN INTELIGENTE (BLOQUE 2 / 3)
#. Aduanas, Alertas, Flujo de Caja, Reportes HTML y Carga de Excel
# ═══════════════════════════════════════════════════════════════════════

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
        est = estimar_derechos(codigo, float(p["precio_fob"] * Decimal(str(p["cantidad"]))))
        if "error" in est: continue
        pagado = float(p["gastos"].get("Derechos de Aduana", 0))
        desv   = pagado - est["arancel_usd"]
        estado = ("✅ Coherente" if abs(desv) < 5 else ("⚠️ Revisar — posible sobrepago" if desv > 0 else "⚠️ Revisar — posible subdeclaración"))
        filas.append({
            "Producto": p["nombre"], "Partida": codigo, "Arancel estimado": est["arancel_usd"],
            "Arancel pagado": round(pagado, 2), "Desviación": round(desv, 2), "Estado": estado,
        })
    return filas

def generar_alertas_reposicion(productos, config, umbral_rojo=4, umbral_amarillo=8):
    alertas = []
    for p in productos:
        ventas = float(p.get("ventas_semanales", 0))
        stock = float(p.get("stock_actual", 0))
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
        <div style="background-color:{bg}; color: #000; padding:12px; border-radius:8px; margin-bottom:8px; border-left:6px solid {borde};">
            <b>{a['nivel']} — {a['producto']}</b><br>
            Stock: <b>{a['stock']:,.0f} unds</b> · Ventas: <b>{a['ventas_semanales']:,.0f}/sem</b>
            · Cobertura: <b>{a['semanas_cobertura']} semanas</b><br>
            Acción: <i>{a['accion']}</i> — Proveedor: {a['proveedor']}
        </div>
        """, unsafe_allow_html=True)

def proyectar_flujo_caja(productos, config, semanas=13, crecimiento_semanal=0.02, costo_fijo_semanal=0.0, pago_importacion=None):
    hoy = date.today()
    saldo = float(config.get("capital_inicial", 0))
    filas = []
    for w in range(1, semanas + 1):
        fecha = hoy + timedelta(weeks=w)
        ingreso = 0.0
        for p in productos:
            ventas = float(p.get("ventas_semanales", 0))
            pvp    = float(p.get("pvp_normal", 0))
            factor = (1.0 + crecimiento_semanal) ** w
            ingreso += ventas * pvp * factor
        egreso = float(costo_fijo_semanal)
        if pago_importacion and pago_importacion.get("fecha") == fecha:
            egreso += float(pago_importacion.get("monto_usd", 0))
        saldo += ingreso - egreso
        filas.append({"Semana": w, "Fecha": fecha.strftime("%Y-%m-%d"), "Ingreso proyectado": round(ingreso, 2), "Egreso proyectado": round(egreso, 2), "Saldo acumulado": round(saldo, 2)})
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

def exportar_csv_para_sheets(productos, config):
    filas = []
    for p in productos:
        filas.append({
            "Producto": p["nombre"], "Partida_Arancelaria": p.get("partida_arancelaria", ""),
            "Cantidad": p["cantidad"], "FOB_Origen_USD": float(p["precio_fob"]),
            "Costo_Real_USD": float(p["costo_unitario"]), "PVP_Normal": float(p["pvp_normal"]),
            "PVP_Sugerido": float(p.get("pvp_sugerido", p["pvp_normal"])),
            "Rentabilidad_Pct": float(p.get("rentabilidad_pct", 0)),
            "Stock_Actual": float(p.get("stock_actual", 0)), "Ventas_Semanales": float(p.get("ventas_semanales", 0)),
            "Semaforo": p.get("semaforo", ""),
        })
    return pd.DataFrame(filas).to_csv(index=False).encode("utf-8-sig")

def boton_exportar_sheets(productos, config):
    csv = exportar_csv_para_sheets(productos, config)
    id_perfil = config.get("id_perfil", "empresa")
    st.download_button("📱 Descargar CSV para Google Sheets", data=csv, file_name=f"importacion_{config.get('factura','SN')}_{id_perfil}.csv", mime="text/csv", help="Súbelo a Google Drive → abrir con Google Sheets.")

def crear_reporte_html(productos, gastos_contenedor, config):
    total_items = len(productos)
    total_unds = sum(p["cantidad"] for p in productos)
    total_mercancia = sum((p["precio_fob"] * Decimal(str(p["cantidad"])) for p in productos), CERO)
    total_gastos = sum((p["gastos_totales"] for p in productos), CERO)
    origen_efectivo = texto_efectivo(config.get("origen"), config.get("origen_otro"))

    html = f"""
    <div style="font-family: Arial, sans-serif; color: #333; max-width: 1000px; margin: auto;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #1f4e78; margin-bottom: 5px;">REPORTE EJECUTIVO DE IMPORTACIÓN</h1>
            <p style="margin: 0; font-size: 14px;"><b>{config.get('empresa', '')}</b> | RIF: {config.get('rif', '')} | Propietario: {config.get('propietario', '')}</p>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">Origen: {origen_efectivo} | Proveedor: {config.get('proveedor', '')} | Factura: {config.get('factura', '')}</p>
        </div>

        <div style="display: flex; justify-content: space-between; margin-bottom: 20px; gap: 10px;">
            <div style="flex: 1; border: 1px solid #ddd; padding: 10px; text-align: center; border-radius: 5px;">
                <div style="font-size: 11px; color: #666; font-weight: bold;">PRODUCTOS</div>
                <div style="font-size: 18px; font-weight: bold; color: #1f4e78;">{total_items} ítems</div>
            </div>
            <div style="flex: 1; border: 1px solid #ddd; padding: 10px; text-align: center; border-radius: 5px;">
                <div style="font-size: 11px; color: #666; font-weight: bold;">CANT. UNIDADES</div>
                <div style="font-size: 18px; font-weight: bold; color: #1f4e78;">{total_unds:,.0f} unds</div>
            </div>
            <div style="flex: 1; border: 1px solid #ddd; padding: 10px; text-align: center; border-radius: 5px;">
                <div style="font-size: 11px; color: #666; font-weight: bold;">COSTO MERCANCÍA</div>
                <div style="font-size: 18px; font-weight: bold; color: #1f4e78;">$ {float(total_mercancia):,.2f}</div>
            </div>
            <div style="flex: 1; border: 1px solid #ddd; padding: 10px; text-align: center; border-radius: 5px;">
                <div style="font-size: 11px; color: #666; font-weight: bold;">GASTOS ARRIBO</div>
                <div style="font-size: 18px; font-weight: bold; color: #1f4e78;">$ {float(total_gastos):,.2f}</div>
            </div>
        </div>

        <h3 style="color: #1f4e78; margin-bottom: 5px;">Resumen General de Costos y Precios de Venta</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 30px;">
            <tr style="background-color: #1f4e78; color: white;">
                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Producto</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Cant.</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Costo U.</th>
                <th style="padding: 8px; border: 1px solid #ddd;">PVP Norm.</th>
                <th style="padding: 8px; border: 1px solid #ddd;">PVP May.</th>
                <th style="padding: 8px; border: 1px solid #ddd;">PVP Esp.</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Semáforo</th>
            </tr>
    """
    
    for p in productos:
        color_txt = "red" if "🔴" in p.get("semaforo_color", "") else ("orange" if "🟡" in p.get("semaforo_color", "") else "green")
        estado_txt = "ROJO" if "🔴" in p.get("semaforo_color", "") else ("AMARILLO" if "🟡" in p.get("semaforo_color", "") else "VERDE")
        html += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: left;">{p['nombre']}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{p['cantidad']}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">$ {float(p['costo_unitario']):,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">$ {float(p['pvp_normal']):,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">$ {float(p['pvp_mayorista']):,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">$ {float(p['pvp_especial']):,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center; font-weight: bold; color: {color_txt};">{estado_txt}</td>
            </tr>
        """
    html += "</table>"

    html += """<h3 style="color: #1f4e78; margin-bottom: 10px;">Desglose Individual y Prorrateo de Gastos</h3>"""
    
    for p in productos:
        color_txt = "#c00000" if "🔴" in p.get("semaforo_color", "") else ("#bf8f00" if "🟡" in p.get("semaforo_color", "") else "#006100")
        estado_txt = "ROJO" if "🔴" in p.get("semaforo_color", "") else ("AMARILLO" if "🟡" in p.get("semaforo_color", "") else "VERDE")
        
        _, _, sug_ahora, sug_futuro, _ = evaluar_semaforo(p.get("stock_actual", 0), p.get("ventas_semanales", 0), p.get("dias_entrega", 0), config.get("fecha_proximo_pedido"))
        
        html += f"""
        <div style="border: 1px solid #b3d4fc; border-radius: 5px; margin-bottom: 15px; overflow: hidden;">
            <div style="background-color: #e6f2ff; padding: 8px 12px; border-bottom: 1px solid #b3d4fc; font-weight: bold; color: #1f4e78;">
                Producto: {p['nombre']}
            </div>
            <div style="padding: 12px; font-size: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div><b style="color: {color_txt};">Estado: {estado_txt}</b> - {p['semaforo']}</div>
                    <div style="text-align: right;"><b>=====> Pedir {sug_ahora} unds</b><br><span style="color: #666; font-style: italic;">Planificación: Pedir {sug_futuro} unds</span></div>
                </div>
                <div style="margin-bottom: 10px; color: #444;">
                    <b>Cant.:</b> {p['cantidad']} unds | <b>FOB U.:</b> $ {float(p['precio_fob']):,.2f} | <b>Peso T.:</b> {float(p['peso_total']):,.2f} kg | <b>Vol. T.:</b> {float(p['volumen_total']):,.4f} m3
                </div>
                <div style="background-color: #f8f9fa; padding: 8px; border-radius: 3px;">
                    <b>Gastos Arribo U.:</b> $ {float(p['gasto_unitario']):,.2f} | <b>COSTO REAL EN ESTANTE:</b> $ {float(p['costo_unitario']):,.2f}
                </div>
                <div style="margin-top: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; color: #555;">
                    <div><b>Gastos (Parte 1):</b> Manejo: ${float(p['gastos']['Manejo de Puerto']):,.2f} | Flete Nac.: ${float(p['gastos']['Flete Terrestre Nacional']):,.2f} | Log. Int.: ${float(p['gastos']['Logística Internacional']):,.2f}</div>
                    <div><b>Gastos (Parte 2):</b> Aduana: ${float(p['gastos']['Derechos de Aduana']):,.2f} | Gestión: ${float(p['gastos']['Gestión Aduanera']):,.2f} | Admin: ${float(p['gastos']['Gastos Administrativos']):,.2f}</div>
                </div>
            </div>
        </div>
        """
    
    html += """
        <div style="text-align: center; margin-top: 30px; padding: 15px; border-top: 2px solid #1f4e78;">
            <p style="margin: 0; color: #1f4e78; font-weight: bold;">Diseñado y elaborado por su Asesor de Importación Inteligente:</p>
            <h3 style="margin: 5px 0; color: #1f4e78;">Prof. Jesús Pulido V.</h3>
            <p style="margin: 0; font-size: 12px; color: #666;">Teléfonos de contacto: 0424-728.3199 / 0416-291.6426 | Correo: jeshua166@gmail.com</p>
        </div>
    </div>
    """
    return html

def generar_pdf_desde_html(html_content):
    try:
        result = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html_content), dest=result)
        return result.getvalue()
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None
        
def leer_excel(archivo):
    if archivo.name.lower().endswith(".csv"): return pd.read_csv(archivo)
    return pd.read_excel(archivo)

def sugerir_columna(columnas, posibles):
    columnas_lower = {i: str(c).lower() for i, c in enumerate(columnas)}
    for palabra in posibles:
        for idx, col_lower in columnas_lower.items():
            if palabra in col_lower: 
                return columnas[idx]
    return None

def mapear_columnas(df):
    columnas_opciones = ["(ninguna)"] + list(df.columns)
    st.markdown("**Mapeo de columnas del Excel**")
    c1, c2, c3 = st.columns(3); c4, c5, c6 = st.columns(3); c7, c8, c9 = st.columns(3)
    
    sugerencias = {
        "producto": ["producto", "descripcion", "descripción", "nombre", "articulo"],
        "cantidad": ["cantidad", "cant", "unidades", "qty"],
        "precio": ["fob", "precio", "origen", "china", "unitario", "costo"],
        "peso": ["peso", "kg", "weight"],
        "volumen": ["volumen", "m3", "cbm", "volume"],
        "stock": ["stock", "inventario", "existencia"],
        "ventas": ["venta", "ventas", "semanal", "salida"],
        "dias": ["dias", "días", "entrega", "llegada", "transito"],
        "partida": ["partida", "hs", "arancel", "codigo"]
    }
    
    def selector(col_st, etiqueta, keys, key_sel):
        sug = sugerir_columna(list(df.columns), keys)
        idx = columnas_opciones.index(sug) if sug in columnas_opciones else 0
        return col_st.selectbox(etiqueta, columnas_opciones, index=idx, key=key_sel)

    return {
        "producto": selector(c1, "Producto / Descripción", sugerencias["producto"], "sel_prod"),
        "cantidad": selector(c2, "Cantidad", sugerencias["cantidad"], "sel_cant"),
        "precio": selector(c3, "Precio FOB Origen $/u", sugerencias["precio"], "sel_prec"),
        "peso": selector(c4, "Peso unitario (kg)", sugerencias["peso"], "sel_peso"),
        "volumen": selector(c5, "Volumen unitario (m³)", sugerencias["volumen"], "sel_vol"),
        "stock": selector(c6, "Stock Actual", sugerencias["stock"], "sel_stock"),
        "ventas": selector(c7, "Ventas Semanales", sugerencias["ventas"], "sel_vent"),
        "dias": selector(c8, "Días de Entrega", sugerencias["dias"], "sel_dias"),
        "partida": selector(c9, "Partida Arancelaria", sugerencias["partida"], "sel_part"),
    }

def construir_productos_desde_df(df, mapeo):
    faltantes = [k for k in ["producto","cantidad","precio","peso","volumen"] if mapeo.get(k) in (None, "(ninguna)")]
    if faltantes: raise ValueError(f"Falta mapear campos obligatorios: {', '.join(faltantes)}")
    
    productos = []
    for i, fila in df.iterrows():
        try:
            nombre = str(fila[mapeo["producto"]]).strip() if pd.notna(fila[mapeo["producto"]]) else f"Producto {i+1}"
            cant_val = a_decimal(fila[mapeo["cantidad"]], "1")
            cantidad = int(cant_val) if cant_val > CERO else 1
            
            precio = a_decimal(fila[mapeo["precio"]], "0.0")
            peso_u = a_decimal(fila[mapeo["peso"]], "0.0")
            vol_u  = a_decimal(fila[mapeo["volumen"]], "0.0")
            
            stock  = int(a_decimal(fila[mapeo["stock"]], "0")) if mapeo.get("stock") and mapeo["stock"] != "(ninguna)" else 0
            ventas = a_decimal(fila[mapeo["ventas"]], "0.0") if mapeo.get("ventas") and mapeo["ventas"] != "(ninguna)" else CERO
            dias   = int(a_decimal(fila[mapeo["dias"]], "60")) if mapeo.get("dias") and mapeo["dias"] != "(ninguna)" else 60
            
            partida = str(fila[mapeo["partida"]]).strip() if mapeo.get("partida") and mapeo["partida"] != "(ninguna)" and pd.notna(fila[mapeo["partida"]]) else ""

            cant_dec = Decimal(str(cantidad))
            productos.append({
                "nombre": nombre, "cantidad": cantidad, "precio_fob": precio,
                "peso_total": peso_u * cant_dec, "volumen_total": vol_u * cant_dec,
                "stock_actual": stock, "ventas_semanales": ventas, "dias_entrega": dias,
                "partida_arancelaria": partida, "gastos": {}
            })
        except Exception as e:
            st.warning(f"Fila {i + 2} omitida por inconveniente en datos: {e}")
            
    if not productos: raise ValueError("No se pudo cargar ningún producto válido desde el archivo.")
    return productos

# ═══════════════════════════════════════════════════════════════════════
#  SISTEMA DE ANÁLISIS DE IMPORTACIÓN INTELIGENTE (BLOQUE 3 / 3)
#  Perfiles, Configuración, Vistas de Pantalla y Función Principal (main)
# ═══════════════════════════════════════════════════════════════════════

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
        empresa = st.sidebar.text_input("Razón Social *", key="new_empresa")
        rif = st.sidebar.text_input("RIF", key="new_rif")
        prop = st.sidebar.text_input("Propietario / Responsable", key="new_prop")
        email = st.sidebar.text_input("Email de contacto", key="new_email")
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

def vista_analisis_costos(productos, config):
    st.subheader("📊 Análisis de costos por producto")
    filas = [{"Producto": p["nombre"], "Cantidad": p["cantidad"], "FOB $/u": float(p["precio_fob"]), "Gasto arribo $/u": float(p["gasto_unitario"]), "Costo real $/u": float(p["costo_unitario"]), "PVP Normal": float(p["pvp_normal"]), "PVP Sugerido": float(p["pvp_sugerido"]), "Rentab. %": float(p["rentabilidad_pct"]), "Partida": p.get("partida_arancelaria", ""), "Alerta PVP": p.get("alerta_pvp", ""), "Semáforo": p.get("semaforo", "")} for p in productos]
    st.dataframe(pd.DataFrame(filas), use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    inv_total = sum((p["costo_unitario"] * Decimal(str(p["cantidad"])) for p in productos), CERO)
    arr_total = sum((p["gastos_totales"] for p in productos), CERO)
    mer_total = sum((p["precio_fob"] * Decimal(str(p["cantidad"])) for p in productos), CERO)
    en_rojo = sum(1 for p in productos if "🔴" in p.get("semaforo_color", ""))
    
    c1.metric("Inversión total", formato_dinero(inv_total))
    c2.metric("Gasto arribo / mercancía", f"{(arr_total / mer_total * 100) if mer_total > CERO else 0:.1f}%")
    c3.metric("Productos en rojo", f"{en_rojo} / {len(productos)}")
    c4.metric("Margen promedio", f"{sum(float(p['rentabilidad_pct']) for p in productos)/len(productos):.1f}%")
    
    fig, ax = plt.subplots(figsize=(10, 4))
    nombres = [p["nombre"][:20] for p in productos]; costos = [float(p["costo_unitario"]) for p in productos]; sugeridos = [float(p["pvp_sugerido"]) for p in productos]
    x = list(range(len(nombres)))
    ax.bar([i - 0.2 for i in x], costos, width=0.4, label="Costo real", color="#C44E52")
    ax.bar([i + 0.2 for i in x], sugeridos, width=0.4, label="PVP sugerido", color="#4C72B0")
    ax.set_xticks(x); ax.set_xticklabels(nombres, rotation=20, ha="right"); ax.set_title("Costo real vs PVP Sugerido"); ax.legend(); ax.grid(alpha=0.3, axis="y")
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
        info = consultar_partida(codigo); est = estimar_derechos(codigo, float(p["precio_fob"] * Decimal(str(p["cantidad"]))))
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

def main():
    st.set_page_config(page_title="Sistema de Importación Inteligente Premium", page_icon="🛳️", layout="wide")
    if not verificar_acceso(): return
    inicializar_estado(); inicializar_monedas()
    panel_perfil_sidebar()
    config = st.session_state.config_empresa.copy()
    if not config.get("empresa"): st.warning("👈 Crea o selecciona un **perfil de empresa** en la barra lateral para comenzar."); return
    panel_configuracion_avanzada(config); panel_monedas_sidebar(config)
    st.title("🛳️ Sistema de Análisis de Importación Inteligente Premium 🐉")
    st.caption(f"Empresa activa: **{config['empresa']}** · Sector: {texto_efectivo(config.get('sector'), config.get('sector_otro'))} · Origen: {texto_efectivo(config.get('origen'), config.get('origen_otro'))}")
    st.caption("Metodología: **Prof. Jesús Pulido V.** · Asesor de Importación Inteligente")
    with st.sidebar:
        st.markdown("---")
        if SHEETS_DB_OK:
            est = sheets_db.estado_conexion()
            if est["modo"] == "nube": st.success(f"☁️ {est['mensaje']}")
            else: st.info(f"💾 {est['mensaje']}")
        else: st.info("💾 Modo local (sin sheets_db.py)")
        st.markdown("---"); st.caption("📞 0424-728.3199 / 0416-291.6426"); st.caption("✉️ jeshua166@gmail.com")
        
    archivo = st.file_uploader("📤 Sube tu Excel o CSV con los productos", type=["xlsx", "xls", "csv"])
    if archivo is None:
        st.info("Sube un archivo Excel o CSV para comenzar el análisis.")
        with st.expander("❓ Columnas esperadas"): st.markdown("- Producto / Descripción\n- Cantidad\n- Precio FOB Origen (unitario)\n- Peso unitario (kg)\n- Volumen unitario (m³)\n- Stock Actual\n- Ventas Semanales\n- Días de Entrega\n- Partida Arancelaria (opcional)")
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
        st.subheader("📄 Reporte Ejecutivo")
        reporte_html = crear_reporte_html(productos, gastos_contenedor, config)
        
        # Renderizado visual correcto del reporte ejecutivo
        components.html(reporte_html, height=1500, scrolling=True)
        
        st.info("💡 Para guardar este reporte como PDF, presione el botón de 'Compartir' de su navegador y seleccione 'Imprimir' o 'Guardar como PDF'.")
        st.divider()
        boton_exportar_sheets(productos, config)


if __name__ == "__main__":
    main()

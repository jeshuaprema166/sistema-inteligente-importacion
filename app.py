# ═══════════════════════════════════════════════════════════════════════
#  SISTEMA DE ANÁLISIS DE IMPORTACIÓN INTELIGENTE 🐉✨ (BLOQUE 1 / 3)
#  Motor original y metodología: Prof. Jesús Pulido V. (New 30/10/26)
# ═══════════════════════════════════════════════════════════════════════

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, timedelta, datetime
import io, os, json, re, unicodedata, random
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

BANCO_PRODUCTOS_SINTETICOS = {
    "Moto Repuestos": [
        {"nombre": "Kit de Arrastre CG150", "peso": 2.10, "vol": 0.0035, "fob": 14.50, "partida": "8714.10.00", "pvp": 35.00},
        {"nombre": "Juego de Pastillas de Freno", "peso": 0.35, "vol": 0.0008, "fob": 1.80, "partida": "8714.10.00", "pvp": 5.00},
        {"nombre": "Amortiguadores Traseros (Par)", "peso": 3.80, "vol": 0.0075, "fob": 18.00, "partida": "8714.10.00", "pvp": 45.00},
        {"nombre": "Casco Integral Certificado", "peso": 1.45, "vol": 0.0220, "fob": 12.00, "partida": "6506.10.00", "pvp": 50.00},
        {"nombre": "Correa de Transmisión Scooter", "peso": 0.18, "vol": 0.0005, "fob": 2.20, "partida": "4010.35.00", "pvp": 6.00},
        {"nombre": "Caucho/Neumático 90/90-18", "peso": 3.20, "vol": 0.0180, "fob": 11.50, "partida": "4011.40.00", "pvp": 30.00},
        {"nombre": "Batería de Gel 12V 7Ah", "peso": 2.10, "vol": 0.0020, "fob": 8.50, "partida": "8507.10.00", "pvp": 22.00},
        {"nombre": "Carburador Completo CG150", "peso": 0.85, "vol": 0.0025, "fob": 9.20, "partida": "8409.91.00", "pvp": 25.00}
    ],
    "Auto Repuestos": [
        {"nombre": "Bomba de Agua Universal", "peso": 1.80, "vol": 0.0040, "fob": 12.50, "partida": "8413.30.00", "pvp": 32.00},
        {"nombre": "Juego de Pastillas Freno Delanteras", "peso": 1.20, "vol": 0.0015, "fob": 6.80, "partida": "8708.30.00", "pvp": 18.00},
        {"nombre": "Disco de Freno Ventilado (Par)", "peso": 9.50, "vol": 0.0120, "fob": 22.00, "partida": "8708.30.00", "pvp": 65.00},
        {"nombre": "Filtro de Aceite Sintético", "peso": 0.30, "vol": 0.0008, "fob": 1.50, "partida": "8421.23.00", "pvp": 5.00},
        {"nombre": "Amortiguador Delantero Hidráulico", "peso": 4.20, "vol": 0.0080, "fob": 19.50, "partida": "8708.80.00", "pvp": 55.00},
        {"nombre": "Kit de Tiempo / Correa Distribución", "peso": 0.90, "vol": 0.0022, "fob": 15.00, "partida": "4010.36.00", "pvp": 40.00}
    ],
    "Ferretería y Herramientas": [
        {"nombre": "Taladro Percutor 1/2'' 750W", "peso": 2.30, "vol": 0.0060, "fob": 16.50, "partida": "8467.21.00", "pvp": 42.00},
        {"nombre": "Juego de Llaves Combinadas 12 pzs", "peso": 1.80, "vol": 0.0025, "fob": 8.20, "partida": "8204.11.00", "pvp": 22.00},
        {"nombre": "Esmeril Recto 4-1/2''", "peso": 2.10, "vol": 0.0050, "fob": 14.00, "partida": "8467.29.00", "pvp": 38.00},
        {"nombre": "Disco de Corte para Metal 4.5'' (Caja 25u)", "peso": 1.10, "vol": 0.0012, "fob": 5.50, "partida": "6804.22.00", "pvp": 15.00},
        {"nombre": "Cinta Métrica 5m Antimpacto", "peso": 0.25, "vol": 0.0004, "fob": 1.10, "partida": "9017.80.10", "pvp": 3.50}
    ],
    "Materiales de Construcción": [
        {"nombre": "Cerradura de Pomo para Dominio", "peso": 0.60, "vol": 0.0018, "fob": 3.80, "partida": "8301.40.00", "pvp": 10.00},
        {"nombre": "Grifería Monomando Cocina", "peso": 1.20, "vol": 0.0045, "fob": 9.50, "partida": "8481.80.00", "pvp": 28.00},
        {"nombre": "Disco Diamantado 7'' Pavimento", "peso": 0.45, "vol": 0.0008, "fob": 4.20, "partida": "6804.21.00", "pvp": 12.00},
        {"nombre": "Nivel de Aluminio 24'' Profesional", "peso": 0.50, "vol": 0.0020, "fob": 2.90, "partida": "9017.30.00", "pvp": 8.50}
    ],
    "Materiales Eléctricos": [
        {"nombre": "Breaker Termomagnético 2P 40A", "peso": 0.22, "vol": 0.0004, "fob": 2.10, "partida": "8536.20.00", "pvp": 6.00},
        {"nombre": "Reflector LED 100W Multivoltaje", "peso": 0.95, "vol": 0.0032, "fob": 6.50, "partida": "9405.40.90", "pvp": 18.00},
        {"nombre": "Rollo Cable THHN #12 (100m)", "peso": 3.80, "vol": 0.0055, "fob": 24.00, "partida": "8544.49.00", "pvp": 55.00},
        {"nombre": "Tomacorriente Doble Regulado", "peso": 0.12, "vol": 0.0003, "fob": 0.85, "partida": "8536.69.00", "pvp": 2.50}
    ]
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
    st.markdown("<h3 style='text-align:center;'>¿Sabe cuánto le cuesta realmente traer los productos desde el exterior hasta su depósito?<br>Este Sistema Inteligente le revela:</h3>", unsafe_allow_html=True)
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
        <table style="page-break-inside: avoid; width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 30px;">
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
        <div style="page-break-inside: avoid; border: 1px solid #b3d4fc; border-radius: 5px; margin-bottom: 15px; overflow: hidden;">
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
        <div style="page-break-inside: avoid; text-align: center; margin-top: 40px; padding: 25px; border-top: 2px solid #1f4e78; background-color: #f8f9fa; border-radius: 8px;">
            <p style="margin: 0 0 10px 0; color: #1f4e78; font-weight: bold; font-size: 14px;">Diseñado y elaborado por su Asesor de Importación Inteligente:</p>
            <h2 style="margin: 0 0 5px 0; color: #1f4e78; font-size: 20px;">Prof. Jesús Pulido V.</h2>
            <p style="margin: 0 0 15px 0; font-size: 12px; color: #444; line-height: 1.5;">
                Teléfonos de contacto: 0424-728.3199 / 0416-291.6426<br>
                Correo: jeshua166@gmail.com
            </p>
            <img src="https://i.postimg.cc/Hxhd38gS/JPV-Asesor-Importacion.jpg" style="width: 140px; border-radius: 8px; border: 2px solid #1f4e78;" />
        </div>
    </div>
    """
    return html.replace('\n', '').strip()

def generar_pdf_desde_html(html_content):
    try:
        result = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html_content), dest=result)
        return result.getvalue()
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

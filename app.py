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
    

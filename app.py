from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import pandas as pd
import streamlit as st
import io
from fpdf import FPDF
import os

# --- CONFIGURACIÓN DE SEGURIDAD ---
def verificar_acceso():
    if "PASSWORD_ADMIN" not in st.secrets:
        return True
    if st.session_state.get("autenticado", False):
        return True
    
    # --- PANTALLA DE BIENVENIDA ---
    # Mostrar la imagen de portada corporativa en la parte superior
    st.image("IMG-20261021-WA0005.jpg", use_container_width=True)
    st.markdown("<h1 style='text-align: center;'>Bienvenidos<br>🛳️</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>¿Sabe cuánto le cuesta realmente traer los productos desde el exterior<br> hasta su depósito?<br>Este Sistema Inteligente le revela:</h3>", unsafe_allow_html=True)
    st.markdown("""
    * La verdad sobre sus costos de importación, márgenes de utilidad y precios óptimos de venta.
    * Identifica los márgenes reales de ganancia antes de nacionalizar, analizando la rentabilidad neta por producto prorrateando con precisión los costos según peso (kg) y volumen (m³). Así sabrá qué productos le dejan ganancia real y cuáles no.
    * Optimizar el espacio de su contenedor y evite pérdidas por costos ocultos.
    * Alarmas de reposición de inventario 🟢🟡🔴 por IA, que permiten monitorear el comportamiento de las existencias, previniendo el desabastecimiento o sobrecompra, que redunda en estancamiento del Capital económico.
    * Ingresar de forma **automática** de **TODOS** los datos y detalles del Excel de sus artículos del inventario al Sistema de Análisis Inteligente de Importación.
    * Definir fácilmente y con certeza a qué proveedor del exterior debe comprar, o si es mejor hacerlo localmente. 
    <mark><span style="font-size: 1.10em; white-space: nowrap;">**✨ Todo con la ayuda de nuestro Sistema de Importación con IA 🤖 ✨**</span></mark>
    """, unsafe_allow_html=True)
    
    # Texto destacado
    st.markdown("""
    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; text-align: center; border-left: 5px solid #2196F3; margin-top: 20px; margin-bottom: 20px;">
    <strong>"UN SISTEMA DE COMERCIALIZACIÓN DISEÑADO PARA PROTEGER SU CAPITAL Y ASEGURAR QUE EL NEGOCIO SIEMPRE CREZCA"</strong>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**Instrucciones:**")
    st.markdown("1. Una vez dentro, vaya al menú de la izquierda (⏪) para configurar los datos de su empresa: Razón Social (Nombre), RIF y Propietario.  También los márgenes (%) de utilidad y descuentos previstos.")
    st.markdown("2. Para ingresar al Sistema, escriba a continuación la contraseña 🔑 suministrada por su Asesor de Importación para comenzar el análisis.")
    
    # --- FIRMA Y FOTO ---
    # Damos 1 espacio vacío, 1 para el texto y 1 para la foto
    col_izq, col_centro, col_der = st.columns([1, 1, 1]) 
    
    with col_centro:
        st.markdown("<h4 style='text-align: center; margin-top: 20px;'>Diseñado y elaborado por<br>su Asesor de Importación Inteligente<br> Prof. Jesús Pulido V.</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Teléfonos de contacto:<br>0424-728.3199 / 0416-291.6426</p>", unsafe_allow_html=True)
        
        # Aquí va la foto, dentro de la columna central
        try:
            st.image("profesor.jpg", width=180) # Ajuste el ancho a su gusto
        except:
            st.write("📷")
    
    st.divider()
    
    # --- CAJA DE CONTRASEÑA ---
    password = st.text_input("Contraseña de acceso", type="password")
    
    if st.button("Ingresar", type="primary"):
        if password == st.secrets["PASSWORD_ADMIN"]:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta. Intente de nuevo.")
        
    return False # actualizado 


CENTAVO = Decimal("0.01")
CERO = Decimal("0")
UNO = Decimal("1")

GASTOS_CONTENEDOR = (
    ("Manejo de Puerto", "peso"),
    ("Flete Terrestre Nacional", "peso"),
    ("Logística Internacional", "volumen"),
    ("Derechos de Aduana", "volumen"),
    ("Gestión Aduanera", "volumen"),
    ("Gastos Administrativos", "volumen"),
)

DEFAULTS = {
    "empresa": "Constructora e Inversiones Los Mangos",
    "rif": "V-189531717",
    "propietario": "Adrian Arellano",
    "margen": 30.0,
    "desc_mayorista": 15.0,
    "desc_especial": 5.0,
}

def leer_decimal(texto, etiqueta, permitir_cero=True, es_dinero=False):
    normalizado = str(texto).strip().replace(",", ".")
    if not normalizado:
        raise ValueError(f"Completa el campo «{etiqueta}».")
    try:
        valor = Decimal(normalizado)
    except InvalidOperation as error:
        raise ValueError(f"«{etiqueta}» debe ser un número válido; puedes usar punto o coma decimal.") from error
    if not valor.is_finite() or valor < CERO:
        raise ValueError(f"«{etiqueta}» debe ser un valor igual o mayor que cero.")
    if not permitir_cero and valor == CERO:
        raise ValueError(f"«{etiqueta}» debe ser mayor que cero.")
    if es_dinero:
        valor = valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return valor

def formato_dinero(valor):
    valor_redondeado = valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return f"$ {valor_redondeado:,.2f}"

def redondear_entero(valor):
    return valor.quantize(UNO, rounding=ROUND_HALF_UP)

def prorratear_gasto(monto, productos, campo_base):
    total_centavos = int(monto.quantize(CENTAVO, rounding=ROUND_HALF_UP) * 100)
    bases = [producto[campo_base] for producto in productos]
    suma_bases = sum(bases, CERO)
    if suma_bases <= CERO:
        raise ValueError(f"No hay base suficiente para repartir el gasto por {campo_base}.")
    partes_exactas = [Decimal(total_centavos) * base / suma_bases for base in bases]
    partes_en_centavos = [int(parte) for parte in partes_exactas]
    centavos_sobrantes = total_centavos - sum(partes_en_centavos)
    orden_por_resto = sorted(
        range(len(productos)),
        key=lambda i: partes_exactas[i] - Decimal(partes_en_centavos[i]),
        reverse=True,
    )
    for indice in orden_por_resto[:centavos_sobrantes]:
        partes_en_centavos[indice] += 1
    return [Decimal(parte) / 100 for parte in partes_en_centavos]

def evaluar_semaforo(stock_actual, ventas_semanales, dias_entrega):
    # Evitar división por cero si aún no hay ventas registradas
    if ventas_semanales <= 0:
        return "⚪", "Sin ventas registradas", 0
    
    # Cálculos matemáticos
    semanas_stock = stock_actual / ventas_semanales
    semanas_entrega = dias_entrega / 7
    margen = semanas_stock - semanas_entrega
    
    # Lógica de los 3 colores
    if margen <= 0:
        color = "🔴"
        mensaje = "¡ALERTA ROJA! Pedir YA"
        sugerido = (semanas_entrega * ventas_semanales) + (4 * ventas_semanales) - stock_actual
    elif margen <= 2:
        color = "🟡"
        mensaje = "Precaución: Pedir pronto"
        sugerido = (semanas_entrega * ventas_semanales) + (4 * ventas_semanales) - stock_actual
    else:
        color = "🟢"
        mensaje = "Todo bien: Stock suficiente"
        sugerido = 0
        
    return color, mensaje, int(sugerido)

def evaluar_carga_pesada(precio_china, gasto_arribo_unitario):
    if precio_china <= 0:
        return "⚪", "Sin datos", 0
    
    # Calcular qué porcentaje del precio es el flete
    porcentaje_flete = (gasto_arribo_unitario / precio_china) * 100
    
    if porcentaje_flete > 60:
        return "🔴", f"PELIGRO: Flete = {porcentaje_flete:.1f}% del costo. Traer local.", porcentaje_flete
    elif porcentaje_flete >= 30:
        return "🟡", f"CUIDADO: Flete = {porcentaje_flete:.1f}% del costo. Evalúe margen.", porcentaje_flete
    else:
        return "🟢", f"RENTABLE: Flete = {porcentaje_flete:.1f}% del costo.", porcentaje_flete

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
        gasto_unitario = gastos_totales / cantidad
        costo_real = (producto["precio_china"] + gasto_unitario).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        producto["gastos_totales"] = gastos_totales
        producto["gasto_unitario"] = gasto_unitario
        producto["costo_unitario"] = costo_real
        producto["pvp_normal"] = redondear_entero(costo_real / (UNO - margen))
        producto["pvp_mayorista"] = redondear_entero(producto["pvp_normal"] * (UNO - desc_mayorista))
        producto["pvp_especial"] = redondear_entero(producto["pvp_normal"] * (UNO - desc_especial))
    return gastos

def crear_reporte(productos, gastos_contenedor, config):
    encabezado = "\n".join((
        "=" * 72,
        "   SISTEMA DE COSTOS DE IMPORTACIÓN",
        f"   {config['empresa']}",
        f"   RIF: {config['rif']}",
        f"   Propietario: {config['propietario']}",
        "=" * 72,
    ))
    lineas = [encabezado, "", "=" * 72, f"   REPORTE DE COSTOS: {len(productos)} productos", "=" * 72]

    for indice, producto in enumerate(productos, start=1):
        cantidad = producto["cantidad"]
        lineas.extend([
            "", f"PRODUCTO {indice}: {producto['nombre']}", "-" * 72,
            f"   Cantidad de unidades:           {cantidad:>12,}",
            f"   Peso total:                     {producto['peso_total']:>12,.3f} kg",
            f"   Volumen total:                  {producto['volumen_total']:>12,.6f} m3",
            f"   Precio China (por unidad):      {formato_dinero(producto['precio_china'])}",
            f"   Precio China (total):           {formato_dinero(producto['precio_china'] * cantidad)}",
            "", "   GASTOS DE ARRIBO ASIGNADOS:",
        ])
        for nombre_gasto, criterio, _ in gastos_contenedor:
            asignado = producto["gastos"][nombre_gasto]
            por_unidad = asignado / cantidad
            lineas.append(f"      {nombre_gasto} ({criterio}): {formato_dinero(asignado)} total; {formato_dinero(por_unidad)} por unidad")
        lineas.extend([
            "",
            f"   Gastos de arribo (total):        {formato_dinero(producto['gastos_totales'])}",
            f"   Gastos de arribo (por unidad):   {formato_dinero(producto['gasto_unitario'])}",
            f"   COSTO REAL EN ESTANTE (unidad):  {formato_dinero(producto['costo_unitario'])}",
            "   PRECIOS DE VENTA:",
            f"      PVP Normal:                   $ {producto['pvp_normal']:>12,.0f}",
            f"      PVP Mayorista:                $ {producto['pvp_mayorista']:>12,.0f}",
            f"      PVP Especial:                 $ {producto['pvp_especial']:>12,.0f}",
        ])
       
        # --- BLOQUE DEL SEMÁFORO EN EL TEXTO ---
        color, mensaje, sugerido = evaluar_semaforo(
            producto.get("stock_actual", 0), 
            producto.get("ventas_semanales", 0), 
            producto.get("dias_entrega", 0)
        )
        lineas.extend([
            f"   SEMÁFORO DE REPOSICIÓN: {color} {mensaje}",
            f"   Unidades sugeridas a pedir: {sugerido}",
            "-" * 72
        ])

        # --- BLOQUE DE CARGA PESADA EN EL TEXTO ---
        color_carga, mensaje_carga, _ = evaluar_carga_pesada(
            producto["precio_china"], 
            producto["gasto_unitario"]
        )
        lineas.extend([
            f"   EVALUACIÓN DE CARGA: {color_carga} {mensaje_carga}",
            "----------------------------------------"
        ])
            
    cantidad_total = sum(p["cantidad"] for p in productos)
    pvp_normal_total = sum((p["pvp_normal"] * p["cantidad"] for p in productos), CERO)
    pvp_mayorista_total = sum((p["pvp_mayorista"] * p["cantidad"] for p in productos), CERO)
    pvp_especial_total = sum((p["pvp_especial"] * p["cantidad"] for p in productos), CERO)

    lineas.extend([
        "", "=" * 60, "  TABLA RESUMEN", "=" * 60,
        f"  {'Producto':<15s} {'Cant.':>8s} {'Costo U.':>12s} {'PVP Norm.':>12s} {'PVP May.':>12s} {'PVP Esp.':>12s}",
        "  " + "-" * 78,
    ])
    for producto in productos:
        lineas.append(f"  {producto['nombre']:<15s} {producto['cantidad']:>8,} $ {producto['costo_unitario']:>10.2f} $ {producto['pvp_normal']:>10.2f} $ {producto['pvp_mayorista']:>10.2f} $ {producto['pvp_especial']:>10.2f}")
    
    lineas.extend([
        "  " + "-" * 78,
        f"  {'TOTALES:':<15s} {cantidad_total:>8,} {'':>12s} $ {pvp_normal_total:>10.2f} $ {pvp_mayorista_total:>10.2f} $ {pvp_especial_total:>10.2f}",
        "=" * 60, "", "=" * 72, "   CONTROL DE PRORRATEO", "=" * 72,
    ])
    for nombre_gasto, criterio, monto_ingresado in gastos_contenedor:
        monto_repartido = sum((p["gastos"][nombre_gasto] for p in productos), CERO)
        lineas.append(f"   {nombre_gasto} ({criterio}): {formato_dinero(monto_ingresado)} ingresados / {formato_dinero(monto_repartido)} repartidos")
    return "\n".join(lineas) + "\n"

def inicializar_estado():
    if "config_empresa" not in st.session_state:
        st.session_state.config_empresa = dict(DEFAULTS)

def panel_configuracion():
    st.sidebar.header("⚙️ Configuración de Empresa y Origen")
    editar = st.sidebar.checkbox("Modificar datos de la empresa, proveedor y márgenes", value=False)
    config = st.session_state.config_empresa.copy()

    if editar:
        config["empresa"] = st.sidebar.text_input("Nombre de la empresa", value=config["empresa"])
        config["rif"] = st.sidebar.text_input("RIF", value=config["rif"])
        config["propietario"] = st.sidebar.text_input("Propietario", value=config["propietario"])
        config["margen"] = st.sidebar.number_input("Margen normal (%)", min_value=0.0, max_value=99.0, value=float(config["margen"]), step=0.5)
        config["desc_mayorista"] = st.sidebar.number_input("Descuento mayorista (%)", min_value=0.0, max_value=99.0, value=float(config["desc_mayorista"]), step=0.5)
        config["desc_especial"] = st.sidebar.number_input("Descuento especial (%)", min_value=0.0, max_value=99.0, value=float(config["desc_especial"]), step=0.5)
    else:
        # El recuadro azul con la info completa (Empresa + Origen)
        info_texto = (
            f"**{config['empresa']}**\n\n"
            f"RIF: {config['rif']}\n\n"
            f"**--- Datos del Origen ---**\n\n"
            f"Origen: {config.get('origen', 'No definido')}\n\n"
            f"Proveedor: {config.get('proveedor', 'No definido')}\n\n"
            f"Factura N°: {config.get('factura', 'No definido')}\n\n"
            f"**--- Márgenes ---**\n\n"
            f"Normal: {config['margen']}% · "
            f"Mayorista: {config['desc_mayorista']}% · "
            f"Especial: {config['desc_especial']}%"
        )
        st.sidebar.info(info_texto)

    # --- CAMPOS DE ORIGEN (SIEMPRE VISIBLES) ---
    st.sidebar.markdown("### 🌍 Datos de Origen")
    config["origen"] = st.sidebar.text_input("Origen (País)", value=config.get("origen", ""))
    config["proveedor"] = st.sidebar.text_input("Proveedor", value=config.get("proveedor", ""))
    config["factura"] = st.sidebar.text_input("Nro. de Factura", value=config.get("factura", ""))
    
    # Guardar cambios en el estado de la sesión para que no se borren
    st.session_state.config_empresa = config

    return config

def leer_excel(archivo):
    if archivo.name.lower().endswith(".csv"):
        return pd.read_csv(archivo)
    return pd.read_excel(archivo)

def sugerir_columna(columnas, posibles):
    columnas_lower = {c: str(c).lower() for c in columnas}
    for palabra in posibles:
        for col, col_lower in columnas_lower.items():
            if palabra in col_lower:
                return col
    return None

def mapear_columnas(df):
    columnas = ["(ninguna)"] + list(df.columns)
    st.markdown("**Mapeo de columnas**")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c7, c8, c9 = st.columns(3)
    
    sugerencias = {
        "producto": ["producto", "descripcion", "descripción", "nombre", "articulo"],
        "cantidad": ["cantidad", "cant", "unidades", "qty"],
        "precio": ["precio", "china", "unitario", "costo", "fob"],
        "peso": ["peso", "kg", "weight"],
        "volumen": ["volumen", "m3", "cbm", "volume"],
        "stock": ["stock", "inventario", "existencia"],
        "ventas": ["venta", "ventas", "semanal", "salida"],
        "dias": ["dias", "días", "entrega", "llegada", "transito"]
    }
    
    def selector(col, etiqueta, keys):
        sug = sugerir_columna(df.columns, keys)
        idx = columnas.index(sug) if sug in columnas else 0
        return col.selectbox(etiqueta, columnas, index=idx)
        
    return {
        "producto": selector(c1, "Producto / Descripción", sugerencias["producto"]),
        "cantidad": selector(c2, "Cantidad", sugerencias["cantidad"]),
        "precio": selector(c3, "Precio en China", sugerencias["precio"]),
        "peso": selector(c4, "Peso unitario (kg)", sugerencias["peso"]),
        "volumen": selector(c5, "Volumen unitario (m³)", sugerencias["volumen"]),
        "stock": selector(c6, "Stock Actual", sugerencias["stock"]),
        "ventas": selector(c7, "Ventas Semanales", sugerencias["ventas"]),
        "dias": selector(c8, "Días de Entrega", sugerencias["dias"]),
    }

def construir_productos_desde_df(df, mapeo):
    faltantes = [k for k, v in mapeo.items() if v == "(ninguna)"]
    if faltantes:
        raise ValueError(f"Falta mapear: {', '.join(faltantes)}")
    productos = []
    for i, fila in df.iterrows():
        try:
            nombre = str(fila[mapeo["producto"]]).strip()
            cantidad = int(fila[mapeo["cantidad"]])
            precio = leer_decimal(fila[mapeo["precio"]], f"precio fila {i+2}", es_dinero=True)
            peso = leer_decimal(fila[mapeo["peso"]], f"peso fila {i+2}", permitir_cero=False)
            volumen = leer_decimal(fila[mapeo["volumen"]], f"volumen fila {i+2}", permitir_cero=False)
            
            # --- NUEVOS DATOS DEL SEMÁFORO ---
            stock = int(fila[mapeo["stock"]])
            ventas = int(fila[mapeo["ventas"]])
            dias = int(fila[mapeo["dias"]])
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Fila {i+2}: {e}")
            
        if not nombre or cantidad <= 0:
            raise ValueError(f"Fila {i+2}: nombre vacío o cantidad inválida.")
            
        productos.append({
            "nombre": nombre, 
            "cantidad": cantidad, 
            "precio_china": precio,
            "peso_total": peso * cantidad, 
            "volumen_total": volumen * cantidad, 
            "gastos": {},
            # --- GUARDAMOS EL SEMÁFORO ---
            "stock_actual": stock,
            "ventas_semanales": ventas,
            "dias_entrega": dias
        })
    return productos

def panel_gastos(prefix=""):
    st.subheader("Gastos de arribo del contenedor")
    datos = {}
    for i in range(0, len(GASTOS_CONTENEDOR), 2):
        cols = st.columns(2)
        for col, (nombre_gasto, criterio) in zip(cols, GASTOS_CONTENEDOR[i:i+2]):
            datos[nombre_gasto] = col.text_input(f"{nombre_gasto} ({criterio}) · total ($)", value="0.00", key=f"{prefix}gasto_{nombre_gasto}")
    return datos

def validar_gastos(datos_gastos):
    gastos = {}
    errores = []
    for nombre_gasto, _ in GASTOS_CONTENEDOR:
        try:
            gastos[nombre_gasto] = leer_decimal(datos_gastos[nombre_gasto], f"gasto {nombre_gasto}", es_dinero=True)
        except ValueError as e:
            errores.append(str(e))
    return gastos, errores

def generar_pdf(productos, gastos_contenedor, config):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- ENCABEZADO CORPORATIVO MEJORADO ---
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(31, 73, 125)
    pdf.cell(0, 10, "REPORTE EJECUTIVO DE IMPORTACIÓN", align="C")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "B", 11)  # Un punto más alto y en negrita
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 6, f"{config['empresa']}  |  RIF: {config['rif']}  |  Propietario: {config['propietario']}", align="C")

    pdf.ln(7) # <--- Salto de línea para separar el propietario del origen
    
    # Datos de Origen en el PDF (limpio y controlado)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    prov_corto = str(config.get('proveedor', 'N/A'))[:40]
    
    pdf.cell(0, 5, f"Origen: {config.get('origen', 'N/A')}  |  Proveedor: {prov_corto}  |  Factura: {config.get('factura', 'N/A')}", align="C")
    pdf.ln(12) 
    
    pdf.set_text_color(50, 50, 50) # Volver al color normal
    
    # --- TARJETAS KPIs SUPERIORES ---
    total_unidades = sum(p["cantidad"] for p in productos)
    gasto_total_contenedor = sum(sum(p["gastos"].values()) for p in productos)
    costo_total_fob = sum(p["precio_china"] * p["cantidad"] for p in productos)
    
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(200, 200, 200)
    
    w_kpi = 44
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(100, 100, 100)
    
    pdf.cell(w_kpi, 5, "PRODUCTOS", border="LRT", align="C", fill=True)
    pdf.cell(2, 5, "")
    pdf.cell(w_kpi, 5, "CANT. UNIDADES", border="LRT", align="C", fill=True)
    pdf.cell(2, 5, "")
    pdf.cell(w_kpi, 5, "COSTO MERCANCÍA", border="LRT", align="C", fill=True)
    pdf.cell(2, 5, "")
    pdf.cell(w_kpi, 5, "GASTOS ARRIBO", border="LRT", align="C", fill=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(31, 73, 125)
    pdf.cell(w_kpi, 8, f"{len(productos)} items", border="LRB", align="C", fill=True)
    pdf.cell(2, 8, "")
    pdf.cell(w_kpi, 8, f"{total_unidades:,} unds", border="LRB", align="C", fill=True)
    pdf.cell(2, 8, "")
    pdf.cell(w_kpi, 8, f"$ {costo_total_fob:,.2f}", border="LRB", align="C", fill=True)
    pdf.cell(2, 8, "")
    pdf.cell(w_kpi, 8, f"$ {gasto_total_contenedor:,.2f}", border="LRB", align="C", fill=True)
    pdf.ln(15)
    
    # --- TABLA RESUMEN GENERAL ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(31, 73, 125)
    pdf.cell(0, 8, "Resumen General de Costos y Precios de Venta")
    pdf.ln(8)
    
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(31, 73, 125)
    
    pdf.cell(50, 7, " Producto", border=1, fill=True)
    pdf.cell(18, 7, "Cant.", border=1, align="C", fill=True)
    pdf.cell(24, 7, "Costo U.", border=1, align="C", fill=True)
    pdf.cell(24, 7, "PVP Norm.", border=1, align="C", fill=True)
    pdf.cell(24, 7, "PVP May.", border=1, align="C", fill=True)
    pdf.cell(24, 7, "PVP Esp.", border=1, align="C", fill=True)
    pdf.cell(26, 7, "Semáforo", border=1, align="C", fill=True)
    pdf.ln(7)
    
    pdf.set_font("Helvetica", "", 8)
    
    for p in productos:
        color, mensaje, sugerido = evaluar_semaforo(p.get("stock_actual", 0), p.get("ventas_semanales", 0), p.get("dias_entrega", 0))
        
        # Determinar texto y color RGB para la tabla resumen
        if "🔴" in color:
            txt_semaforo = "ROJO"
            r_col, g_col, b_col = 200, 0, 0
        elif "🟠" in color:
            txt_semaforo = "NARANJA"
            r_col, g_col, b_col = 220, 130, 0
        else:
            txt_semaforo = "VERDE"
            r_col, g_col, b_col = 0, 150, 0
            
        pdf.set_text_color(40, 40, 40)
        pdf.cell(50, 6, f" {p['nombre'][:25]}", border=1)
        pdf.cell(18, 6, f"{p['cantidad']}", border=1, align="C")
        pdf.cell(24, 6, f"$ {p['costo_unitario']:.2f}", border=1, align="C")
        pdf.cell(24, 6, f"$ {p['pvp_normal']:.2f}", border=1, align="C")
        pdf.cell(24, 6, f"$ {p['pvp_mayorista']:.2f}", border=1, align="C")
        pdf.cell(24, 6, f"$ {p['pvp_especial']:.2f}", border=1, align="C")
        
        # Pintar el texto del semáforo con su color correspondiente
        pdf.set_text_color(r_col, g_col, b_col)
        pdf.cell(26, 6, f"{txt_semaforo}", border=1, align="C")
        pdf.ln(6)
        
    pdf.ln(10)
    
    # --- DESGLOSE DETALLADO POR PRODUCTO ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(31, 73, 125)
    pdf.cell(0, 8, "Desglose Individual y Prorrateo de Gastos")
    pdf.ln(8)
    
    for p in productos:
        color, mensaje, sugerido = evaluar_semaforo(p.get("stock_actual", 0), p.get("ventas_semanales", 0), p.get("dias_entrega", 0))
        
        if "🔴" in color:
            txt_semaforo = "ROJO"
            r_col, g_col, b_col = 200, 0, 0
        elif "🟠" in color:
            txt_semaforo = "NARANJA"
            r_col, g_col, b_col = 220, 130, 0
        else:
            txt_semaforo = "VERDE"
            r_col, g_col, b_col = 0, 150, 0
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 240, 250)
        pdf.set_text_color(31, 73, 125)
        pdf.cell(0, 7, f"  Producto: {p['nombre']} (Pedir: {sugerido} unds)", border=1, fill=True)
        pdf.ln(7)
        
        # Imprimir Estado con su color específico
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(35, 5, "  Estado de Alerta:", border="L")
        pdf.set_text_color(r_col, g_col, b_col)
        pdf.cell(155, 5, f"{txt_semaforo} - {mensaje}", border="R")
        pdf.ln(5)
        
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(50, 50, 50)
        info_izq = f"Cant.: {p['cantidad']} unds | P. China U.: $ {p['precio_china']:.2f} | Peso T.: {p['peso_total']:.2f} kg | Vol. T.: {p['volumen_total']:.4f} m3"
        info_der = f"Gastos Arribo U.: $ {p['gasto_unitario']:.2f} | COSTO REAL EN ESTANTE: $ {p['costo_unitario']:.2f}"
        
        pdf.cell(0, 5, f"  {info_izq}", border="LR")
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, f"  {info_der}", border="LR")
        pdf.ln(5)
        
        # --- DIVIDIR GASTOS ASIGNADOS EN DOS LÍNEAS ---
        gastos_items = list(p["gastos"].items())
        mitad = (len(gastos_items) + 1) // 2
        linea_1 = " | ".join([f"{k}: $ {v:.2f}" for k, v in gastos_items[:mitad]])
        linea_2 = " | ".join([f"{k}: $ {v:.2f}" for k, v in gastos_items[mitad:]])
        
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.cell(0, 4.5, f"  Gastos (Parte 1): {linea_1}", border="LR")
        pdf.ln(4.5)
        pdf.cell(0, 4.5, f"  Gastos (Parte 2): {linea_2}", border="LRB")
        pdf.ln(8)
        
    pdf.ln(5)
    
    # --- FICHA DEL ASESOR DE IMPORTACIÓN EN EL PDF ---
    try:
        pdf.set_fill_color(240, 245, 250)
        pdf.set_draw_color(31, 73, 125)
        pdf.rect(10, pdf.get_y(), 190, 24, style="DF")
        
        y_ficha = pdf.get_y() + 2
        
        if os.path.exists("profesor.jpg"):
            try:
                pdf.image("profesor.jpg", x=12, y=y_ficha, w=20)
            except Exception:
                pass
                
        pdf.set_xy(35, y_ficha)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(31, 73, 125)
        pdf.cell(0, 4, "Diseñado y elaborado por su Asesor de Importación Inteligente:")
        pdf.ln(4)
        
        pdf.set_x(35)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, "Prof. Jesús Pulido V.")
        pdf.ln(5)
        
        pdf.set_x(35)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, "Teléfonos de contacto: 0424-728.3199 / 0416-291.6426  |  Correo: jeshua166@gmail.com")
        pdf.ln(4)
        
        pdf.set_x(35)
        pdf.cell(0, 4, "Ubicación: Santa Bárbara de Barinas, Venezuela")
    except Exception:
        pass
    
    output = pdf.output()
    if isinstance(output, str):
        return output.encode("latin1")
    return bytes(output)
      
def mostrar_resultado(productos, gastos_contenedor, config):
    st.success("✅ Reporte generado correctamente.")
    
    # 1. ESTILOS CSS PERSONALIZADOS
    st.markdown("""
    <style>
        .kpi-container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 18px;
            border-left: 5px solid #1f497d;
            box-shadow: 0 4px 6px rgba(0,0,0,0.04);
            text-align: center;
            margin-bottom: 15px;
        }
        .kpi-title {
            font-size: 0.85rem;
            color: #555555;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        .kpi-value {
            font-size: 1.4rem;
            color: #1f497d;
            font-weight: 800;
        }
        .badge-rojo {
            background-color: #ffebee;
            color: #c62828;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: bold;
        }
        .badge-amarillo {
            background-color: #fffde7;
            color: #f57f17;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: bold;
        }
        .badge-verde {
            background-color: #e8f5e9;
            color: #2e7d32;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    st.divider()

    # 2. ENCABEZADO CORPORATIVO
    st.markdown("<h2 style='text-align: center; color: #1f497d;'>📊 REPORTE EJECUTIVO DE IMPORTACIÓN</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #666666; font-size: 1.05rem;'><b>{config['empresa']}</b> | RIF: {config['rif']} | Propietario: {config['propietario']}</p>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='text-align: left; color: #555555; font-size: 0.9rem; line-height: 1.6;'>"
        f"<b>Origen:</b> {config.get('origen', 'N/A')}<br>"
        f"<b>Proveedor:</b> {config.get('proveedor', 'N/A')}<br>"
        f"<b>Factura N°:</b> {config.get('factura', 'N/A')}"
        f"</p>", 
        unsafe_allow_html=True
    )
    st.markdown("")

    # 3. TARJETAS MÉTRICAS EJECUTIVAS SUPERIORES (KPIs)
    total_unidades = sum(p["cantidad"] for p in productos)
    gasto_total_contenedor = sum(sum(p["gastos"].values()) for p in productos)
    costo_total_fob = sum(p["precio_china"] * p["cantidad"] for p in productos) 

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

    with col_kpi1:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">📦 Productos</div>
            <div class="kpi-value">{len(productos)} ítems</div>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi2:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">🔢 Cant. Unidades</div>
            <div class="kpi-value">{total_unidades:,} unds</div>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi3:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">💰 Costo Mercancía</div>
            <div class="kpi-value">{formato_dinero(costo_total_fob)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi4:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">🚢 Gastos Arribo</div>
            <div class="kpi-value">{formato_dinero(gasto_total_contenedor)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # 4. TABLA RESUMEN INTERACTIVA Y LIMPIA
    st.markdown("<h4 style='color: #1f497d;'>📋 Resumen General de Costos y Precios de Venta</h4>", unsafe_allow_html=True)

    datos_resumen = []
    for p in productos:
        color, mensaje, sugerido = evaluar_semaforo(p.get("stock_actual", 0), p.get("ventas_semanales", 0), p.get("dias_entrega", 0))
        datos_resumen.append({
            "Producto": p["nombre"],
            "Cant.": p["cantidad"],
            "Costo U.": f"$ {p['costo_unitario']:.2f}",
            "PVP Normal": f"$ {p['pvp_normal']:.2f}",
            "PVP Mayorista": f"$ {p['pvp_mayorista']:.2f}",
            "PVP Especial": f"$ {p['pvp_especial']:.2f}",
            "SemáforoIA": f"{color} {mensaje}",
            "Pedir (Unds)": sugerido
        })

    df_resumen = pd.DataFrame(datos_resumen)
    st.dataframe(df_resumen, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 5. DESGLOSE DETALLADO POR PRODUCTO (ACORDEONES / EXPANDERS)
    st.markdown("<h4 style='color: #1f497d;'>🔍 Desglose Individual y Prorrateo de Gastos</h4>", unsafe_allow_html=True)

    for i, p in enumerate(productos, start=1):
        color, mensaje, sugerido = evaluar_semaforo(
            p.get("stock_actual", 0), p.get("ventas_semanales", 0), p.get("dias_entrega", 0)
        )
        
        titulo_expander = f"📦 {p['nombre']}  |  {color} {mensaje} (Pedir: {sugerido} unds)"
        
        with st.expander(titulo_expander, expanded=(i == 1)):
            
            c_left, c_right = st.columns(2)
            
            with c_left:
                st.markdown("##### 📌 Datos Físicos y de Origen")
                st.metric(label="Cantidad de Unidades", value=f"{p['cantidad']:,} unds")
                st.metric(label="Precio en China (Unidad)", value=f"$ {p['precio_china']:,.2f}")
                st.metric(label="Peso Total", value=f"{p['peso_total']:,.3f} kg")
                st.metric(label="Volumen Total", value=f"{p['volumen_total']:,.6f} m³")
            
            with c_right:
                st.markdown("##### 🏷️ Costo Real y Precios Sugeridos")
                st.metric(
                    label="COSTO REAL EN ESTANTE", 
                    value=f"$ {p['costo_unitario']:,.2f}", 
                    delta="Costo de importación (Listo para vender)", 
                    delta_color="off"
                )
                st.metric(label="PVP Normal (Sugerido)", value=f"$ {p['pvp_normal']:,.2f}")
                st.metric(label="PVP Mayorista", value=f"$ {p['pvp_mayorista']:,.2f}")
                st.metric(label="PVP Especial", value=f"$ {p['pvp_especial']:,.2f}")
                
    st.markdown("---")
    st.markdown("##### 🚢 Gastos de Arribo Asignados (Prorrateo DUAL por Peso y Volumen):")
            
    g_col1, g_col2, g_col3 = st.columns(3)
    gastos_items = list(p["gastos"].items())
            
    for idx, (nombre_gasto, monto_asig) in enumerate(gastos_items):
        por_und = monto_asig / p["cantidad"]
        col_target = g_col1 if idx % 3 == 0 else (g_col2 if idx % 3 == 1 else g_col3)
        col_target.metric(
            label=nombre_gasto, 
            value=formato_dinero(monto_asig), 
            delta=f"{formato_dinero(por_und)} /und",
            delta_color="off"
        )
        # --- BLOQUE DEL SEMÁFORO EN PANTALLA ---
        if color == "🔴":
            st.error(f"🚨 **Alerta de Reposición (IA):** {mensaje}. Se sugiere pedir **{sugerido}** unidades de inmediato.")
        elif color == "🟡":
            st.warning(f"⚠️ **Alerta de Reposición (IA):** {mensaje}. Se sugiere pedir **{sugerido}** unidades próximamente.")
        else:
            st.success(f"🟢 **Estado de Inventario:** {mensaje}. No requiere reposición por el momento.")
            
        # --- EVALUACIÓN DE CARGA PESADA (ANEXO C) ---
        color_carga, mensaje_carga, _ = evaluar_carga_pesada(p["precio_china"], p["gasto_unitario"])
        if "🔴" in color_carga:
            st.error(f"⚖️ **Análisis de Carga Pesada:** {mensaje_carga}")
        elif "🟡" in color_carga:
            st.warning(f"⚖️ **Análisis de Carga Pesada:** {mensaje_carga}")
        else:
            st.success(f"⚖️ **Análisis de Carga Pesada:** {mensaje_carga}")

    st.markdown("---")
    
    # 5.5. FICHA DEL ASESOR DE IMPORTACIÓN
    col_foto, col_datos = st.columns([1, 4])
    with col_foto:
        if os.path.exists("profesor.jpg"):
            st.image("profesor.jpg", width=110)
        else:
            st.markdown("📸 **Prof. Jesús Pulido V.**")
            
    with col_datos:
        st.markdown("""
        <div style='background-color: #f0f4f8; padding: 12px; border-radius: 8px; border-left: 4px solid #1f497d;'>
            <h5 style='color: #1f497d; margin:0;'>Diseñado y elaborado por su Asesor de Importación Inteligente</h5>
            <h4 style='color: #111111; margin:4px 0;'>Prof. Jesús Pulido V.</h4>
            <p style='margin:2px 0; font-size:0.85rem; color:#444;'>📞 <b>Teléfonos de contacto:</b> 0424-728.3199 / 0416-291.6426</p>
            <p style='margin:2px 0; font-size:0.85rem; color:#444;'>✉️ <b>Correo:</b> jeshua166@gmail.com</p>
            <p style='margin:2px 0; font-size:0.85rem; color:#666;'>📍 <b>Ubicación:</b> Santa Bárbara de Barinas, Venezuela</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("")

    # 6. ACCIONES Y DESCARGAS
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        reporte_texto = crear_reporte(productos, gastos_contenedor, config)
        st.download_button(
            label="📄 Descargar Reporte en Texto (.txt)",
            data=reporte_texto,
            file_name=f"Reporte_Importacion_{config['empresa'].replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    with col_btn2:
        try:
            pdf_data = generar_pdf(productos, gastos_contenedor, config)
            st.download_button(
                label="📄 Descargar Reporte Ejecutivo (PDF)",
                data=pdf_data,
                file_name=f"Reporte_Importacion_{config['empresa']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"❌ Error al generar PDF: {str(e)}")

    
def main():
    st.set_page_config(page_title="Costos de Importación | Los Mangos", page_icon="📋", layout="wide")
    inicializar_estado()
    config = panel_configuracion()
    st.title(config["empresa"])
    st.caption(f"RIF: {config['rif']}  ·  Propietario: {config['propietario']}")
    st.header("Sistema de costos de importación")

    tab_manual, tab_excel = st.tabs(["Opción A · Ingreso manual", "Opción B · Desde Excel"])

    with tab_manual:
        cantidad_productos = st.number_input("Cantidad de productos diferentes", min_value=1, max_value=50, value=3, step=1)
        with st.form("form_manual"):
            st.subheader("Productos del contenedor")
            datos_productos = []
            for i in range(int(cantidad_productos)):
                st.markdown(f"**Producto {i+1}**")
                c1, c2 = st.columns(2)
                nombre = c1.text_input("Nombre del producto", key=f"n_{i}", placeholder="Ej.: Taladro")
                cantidad = c2.number_input("Cantidad", min_value=1, value=1, step=1, key=f"c_{i}")
                c3, c4, c5 = st.columns(3)
                precio = c3.text_input("Precio China ($)", key=f"p_{i}", placeholder="Ej.: 35.00")
                peso = c4.text_input("Peso unitario (kg)", key=f"pe_{i}", placeholder="Ej.: 3")
                vol = c5.text_input("Volumen unitario (m³)", key=f"v_{i}", placeholder="Ej.: 0.008")
                st.markdown("**Datos para el Semáforo 🚥**")
                c6, c7, c8 = st.columns(3)
                stock_actual = c6.number_input("Stock actual (unidades)", min_value=0, value=0, step=1, key=f"s_{i}")
                ventas_semanales = c7.number_input("Ventas por semana", min_value=0, value=0, step=1, key=f"vs_{i}")
                dias_entrega = c8.number_input("Días de entrega", min_value=1, value=60, step=1, key=f"d_{i}")
            
                datos_productos.append({
                "nombre": nombre, "cantidad": int(cantidad), 
                "precio": precio, "peso": peso, "volumen": vol,
                "stock_actual": int(stock_actual),
                "ventas_semanales": int(ventas_semanales),
                "dias_entrega": int(dias_entrega)
            })
            datos_gastos = panel_gastos(prefix="manual_")
            submit = st.form_submit_button("Calcular costos y generar reporte", type="primary", use_container_width=True)
  
        if submit:
            errores = []
            productos = []
            for i, d in enumerate(datos_productos, start=1):
                try:
                    nombre = d["nombre"].strip()
                    if not nombre: raise ValueError(f"Indica el nombre del producto {i}.")
                    precio = leer_decimal(d["precio"], f"precio producto {i}", es_dinero=True)
                    peso = leer_decimal(d["peso"], f"peso producto {i}", permitir_cero=False)
                    vol = leer_decimal(d["volumen"], f"volumen producto {i}", permitir_cero=False)
                    cantidad = d["cantidad"]
                    productos.append({
                    "nombre": nombre, "cantidad": cantidad,
                    "precio_china": precio,
                    "peso_total": peso * cantidad,
                    "volumen_total": vol * cantidad,
                    "gastos": {},
                    "stock_actual": d["stock_actual"],
                    "ventas_semanales": d["ventas_semanales"],
                    "dias_entrega": d["dias_entrega"]
                })
                except ValueError as e:
                    errores.append(str(e))
            gastos, errores_g = validar_gastos(datos_gastos)
            errores.extend(errores_g)
            if errores:
                for e in errores: st.error(e)
            else:
                gastos_contenedor = calcular_costos(productos, gastos, config)
                mostrar_resultado(productos, gastos_contenedor, config)

    with tab_excel:
        st.write("Sube un archivo Excel (.xlsx) o CSV con tu inventario.")
        archivo = st.file_uploader("Archivo de inventario", type=["xlsx", "csv"])
        if archivo is None:
            st.info("Esperando archivo...")
        else:
            try:
                df = leer_excel(archivo)
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")
                return
            st.success(f"Archivo cargado: {len(df)} filas, {len(df.columns)} columnas.")
            with st.expander("Vista previa del archivo"):
                st.dataframe(df.head(10))
            mapeo = mapear_columnas(df)
            datos_gastos = panel_gastos(prefix="excel_")
            if st.button("Calcular costos y generar reporte", type="primary", use_container_width=True):
                errores = []
                try:
                    productos = construir_productos_desde_df(df, mapeo)
                except ValueError as e:
                    errores.append(str(e))
                gastos, errores_g = validar_gastos(datos_gastos)
                errores.extend(errores_g)
                if errores:
                    for e in errores: st.error(e)
                else:
                    gastos_contenedor = calcular_costos(productos, gastos, config)
                    mostrar_resultado(productos, gastos_contenedor, config)

if __name__ == "__main__":
    # Verificamos la contraseña antes de mostrar la app
    if verificar_acceso():
        if st.sidebar.button("🚪 Cerrar Sesión"):
            st.session_state["autenticado"] = False
            st.rerun()
        main()

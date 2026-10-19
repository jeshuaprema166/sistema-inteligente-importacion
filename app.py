from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE SEGURIDAD ---
def verificar_acceso():
    if "PASSWORD_ADMIN" not in st.secrets:
        return True
    if st.session_state.get("autenticado", False):
        return True
    
    # --- PANTALLA DE BIENVENIDA ---
    st.markdown("<h1 style='text-align: center;'>🏢<br>Bienvenido al Sistema de Gestión Inteligente de Importación<br>🛳️✨</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>¿Sabe cuánto le cuesta realmente traer sus productos? Este Sistema Inteligente le revela:</h3>", unsafe_allow_html=True)
    st.markdown("""
    * La verdad sobre sus márgenes, fletes y precios de venta.
    * Descubra qué productos le dejan ganancia real y cuáles no.
    * Optimice el espacio de su contenedor y evite pérdidas por costos ocultos.
        """)
        
    # Texto destacado
    st.markdown("""
    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; text-align: center; border-left: 5px solid #2196F3; margin-top: 20px; margin-bottom: 20px;">
    <strong>"UNA HERRAMIENTA DISEÑADA PARA PROTEGER SU CAPITAL Y ASEGURAR QUE SU NEGOCIO SIEMPRE CREZCA"</strong>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**Instrucciones:**")
    st.markdown("1. Una vez dentro, vaya al menú de la izquierda (⏪) para configurar los datos de su empresa: Razón Social (Nombre), RIF y Propietario. Así como los márgenes (%) de utilidad y descuentos previstos.")
    st.markdown("2. Para ingresar al Sistema, escriba a continuación la contraseña suministrada por su Asesor de Importación para comenzar el análisis. 🔑")
    
    # --- FIRMA Y FOTO ---
    # Damos 1 espacio vacío, 1 para el texto y 1 para la foto
    col_izq, col_centro, col_der = st.columns([1, 1, 1]) 
    
    with col_centro:
        st.markdown("<h4 style='text-align: center; margin-top: 20px;'>Diseñado por su Asesor de Importación<br>Prof. Jesús Pulido V.</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Teléfonos de contacto:<br>0424-728.3299 / 0416-291.6426</p>", unsafe_allow_html=True)
        
        # Aquí va la foto, dentro de la columna central
        try:
            st.image("profesor.jpg", width=250) # Ajuste el ancho a su gusto
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
    st.sidebar.header("⚙️ Configuración de Empresa")
    editar = st.sidebar.checkbox("Modificar datos de la empresa y márgenes", value=False)
    config = st.session_state.config_empresa.copy()

    if editar:
        config["empresa"] = st.sidebar.text_input("Nombre de la empresa", value=config["empresa"])
        config["rif"] = st.sidebar.text_input("RIF", value=config["rif"])
        config["propietario"] = st.sidebar.text_input("Propietario", value=config["propietario"])
        config["margen"] = st.sidebar.number_input("Margen normal (%)", min_value=0.0, max_value=99.0, value=float(config["margen"]), step=0.5)
        config["desc_mayorista"] = st.sidebar.number_input("Descuento mayorista (%)", min_value=0.0, max_value=99.0, value=float(config["desc_mayorista"]), step=0.5)
        config["desc_especial"] = st.sidebar.number_input("Descuento especial (%)", min_value=0.0, max_value=99.0, value=float(config["desc_especial"]), step=0.5)
        st.session_state.config_empresa = config
    else:
        st.sidebar.info(f"**{config['empresa']}**\n\nRIF: {config['rif']}\n\nMargen: {config['margen']}% · Mayorista: {config['desc_mayorista']}% · Especial: {config['desc_especial']}%")
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
    c1, c2, c3, c4, c5 = st.columns(5)
    sugerencias = {
        "producto": ["producto", "descripcion", "descripción", "nombre", "articulo", "artículo"],
        "cantidad": ["cantidad", "cant", "unidades", "qty"],
        "precio": ["precio", "china", "unitario", "costo", "fob"],
        "peso": ["peso", "kg", "weight"],
        "volumen": ["volumen", "m3", "cbm", "volume"],
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
        except (ValueError, TypeError) as e:
            raise ValueError(f"Fila {i+2}: {e}")
        if not nombre or cantidad <= 0:
            raise ValueError(f"Fila {i+2}: nombre vacío o cantidad inválida.")
        productos.append({
            "nombre": nombre, "cantidad": cantidad, "precio_china": precio,
            "peso_total": peso * cantidad, "volumen_total": volumen * cantidad, "gastos": {},
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

def mostrar_resultado(productos, gastos_contenedor, config):
    reporte = crear_reporte(productos, gastos_contenedor, config)
    st.success("✅ Reporte generado correctamente.")
    st.text_area("Reporte", reporte, height=400)
    st.download_button("📥 Descargar reporte_importacion.txt", data=reporte.encode("utf-8"), file_name="reporte_importacion.txt", mime="text/plain; charset=utf-8", use_container_width=True)

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
                datos_productos.append({"nombre": nombre, "cantidad": int(cantidad), "precio": precio, "peso": peso, "volumen": vol})
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
                    productos.append({"nombre": nombre, "cantidad": cantidad, "precio_china": precio, "peso_total": peso * cantidad, "volumen_total": vol * cantidad, "gastos": {}})
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

# ═══════════════════════════════════════════════════════════════════════
#  sheets_db.py — Persistencia multi-empresa en Google Sheets
# ═══════════════════════════════════════════════════════════════════════
import os, json, re, unicodedata
from datetime import datetime, date
import pandas as pd
import streamlit as st
import re

def fix_private_key(key):
    try:
        import re
        # Extraer SOLO los caracteres válidos de Base64 y el signo '=' 
        # Esto borra cabeceras, saltos de línea, espacios y cualquier carácter invisible.
        clean = re.sub(r"[^a-zA-Z0-9+/=]", "", key)
        
        # Formatear en líneas de 64 caracteres (Requisito estricto de Google)
        lines = [clean[i:i+64] for i in range(0, len(clean), 64)]
        
        # Reconstruir la llave perfecta
        fixed_key = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(lines) + "\n-----END PRIVATE KEY-----\n"
        return fixed_key
    except Exception:
        return key

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_OK = True
except ImportError:
    GSPREAD_OK = False

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

SHEET_TASAS      = "tasas_cambio"
SHEET_HISTORIAL  = "historial_importaciones"
SHEET_PERFILES   = "perfiles_empresa"
SHEET_ALERTAS    = "alertas_reposicion"

RUTA_TASAS_LOCAL     = "tasas_cambio.json"
RUTA_HISTORIAL_LOCAL = "historial_importaciones.csv"

COLS_PERFILES = [
    "id_perfil", "empresa", "rif", "propietario", "email",
    "sector", "sector_otro", "origen", "origen_otro",
    "moneda_default", "margen", "desc_mayorista", "desc_especial",
    "proveedor", "timestamp",
]

COLS_HISTORIAL = [
    "id_perfil", "id_importacion", "fecha", "origen", "proveedor", "factura",
    "producto", "partida_arancelaria",
    "cantidad", "precio_fob_usd", "peso_total_kg", "volumen_total_m3",
    "gasto_arribo_total_usd", "gasto_arribo_unitario_usd",
    "costo_real_unitario_usd",
    "pvp_normal", "pvp_mayorista", "pvp_especial", "pvp_sugerido",
    "rentabilidad_pct", "alerta_pvp",
    "semaforo", "cobertura_semanas", "sugerido_ahora", "sugerido_futuro",
    "evaluacion_carga", "usuario_registro", "timestamp",
]


def slugify(texto):
    if not texto:
        return "empresa-sin-nombre"
    t = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii')
    t = re.sub(r'[^a-zA-Z0-9]+', '-', t).strip('-').lower()
    return t or "empresa-sin-nombre"


# ─────────────────────────────────────────────────────────────────────
#  CONEXIÓN
# ─────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="🔗 Conectando con Google Sheets…")
def conectar():
    if not GSPREAD_OK:
        return None
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = fix_private_key(creds_dict["private_key"])
    except Exception:
        return None
    sheet_id = st.secrets.get("GOOGLE_SHEET_ID", None)
    if not sheet_id:
        return None
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        cliente = gspread.authorize(creds)
        sh = cliente.open_by_key(sheet_id)
        _asegurar_hojas(sh)
        return sh
    except Exception as e:
        st.warning(f"⚠️ No se pudo conectar con Google Sheets: {e}")
        return None


def _asegurar_hojas(sh):
    existentes = {w.title for w in sh.worksheets()}
    if SHEET_TASAS not in existentes:
        w = sh.add_worksheet(title=SHEET_TASAS, rows=500, cols=8)
        w.append_row(["fecha", "usd_eur", "usd_ves", "actualizado_por", "timestamp_iso"])
    if SHEET_HISTORIAL not in existentes:
        w = sh.add_worksheet(title=SHEET_HISTORIAL, rows=2000, cols=len(COLS_HISTORIAL))
        w.append_row(COLS_HISTORIAL)
    if SHEET_PERFILES not in existentes:
        w = sh.add_worksheet(title=SHEET_PERFILES, rows=500, cols=len(COLS_PERFILES))
        w.append_row(COLS_PERFILES)
    if SHEET_ALERTAS not in existentes:
        w = sh.add_worksheet(title=SHEET_ALERTAS, rows=1000, cols=8)
        w.append_row(["fecha", "producto", "nivel", "stock",
                      "ventas_semanales", "cobertura_semanas", "accion", "timestamp_iso"])


def esta_en_nube():
    return conectar() is not None


def estado_conexion():
    if not GSPREAD_OK:
        return {"modo": "local", "mensaje": "Sin librería gspread → modo local."}
    sh = conectar()
    if sh is None:
        return {"modo": "local", "mensaje": "Sin credenciales → modo local."}
    return {"modo": "nube", "mensaje": f"Conectado a: {sh.title}"}


# ─────────────────────────────────────────────────────────────────────
#  TASAS (globales, con tracking de autor)
# ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def leer_tasas():
    sh = conectar()
    if sh is not None:
        try:
            ws = sh.worksheet(SHEET_TASAS)
            regs = ws.get_all_records()
            if regs:
                u = regs[-1]
                return {"EUR": float(u["usd_eur"]), "VES": float(u["usd_ves"]),
                        "fecha": str(u.get("fecha","")), "por": str(u.get("actualizado_por",""))}
        except Exception as e:
            st.warning(f"No se pudo leer tasas en Sheets: {e}")
    if os.path.exists(RUTA_TASAS_LOCAL):
        try:
            with open(RUTA_TASAS_LOCAL, "r", encoding="utf-8") as f:
                d = json.load(f)
            return {"EUR": float(d.get("EUR", 0.93)),
                    "VES": float(d.get("VES", 40.0)),
                    "fecha": d.get("fecha", "local"),
                    "por": d.get("por", "local")}
        except Exception:
            pass
    return None


def guardar_tasas(usd_eur, usd_ves, usuario="admin"):
    ahora = datetime.now()
    payload = {"EUR": float(usd_eur), "VES": float(usd_ves),
               "fecha": ahora.strftime("%Y-%m-%d %H:%M"), "por": usuario}
    try:
        with open(RUTA_TASAS_LOCAL, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    sh = conectar()
    if sh is not None:
        try:
            ws = sh.worksheet(SHEET_TASAS)
            ws.append_row([ahora.strftime("%Y-%m-%d"), float(usd_eur), float(usd_ves),
                           usuario, ahora.isoformat()])
            leer_tasas.clear()
            return True, "✅ Tasas guardadas en Google Sheets y en local."
        except Exception as e:
            return False, f"⚠️ Solo guardadas en local (Sheets falló: {e})"
    return True, "✅ Tasas guardadas en local."


# ─────────────────────────────────────────────────────────────────────
#  PERFILES DE EMPRESA
# ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def listar_perfiles():
    sh = conectar()
    if sh is not None:
        try:
            ws = sh.worksheet(SHEET_PERFILES)
            regs = ws.get_all_records()
            return regs if regs else []
        except Exception as e:
            st.warning(f"No se pudieron leer perfiles: {e}")
    return []


def crear_actualizar_perfil(perfil):
    """Upsert por id_perfil."""
    ahora = datetime.now().isoformat()
    valores = []
    for c in COLS_PERFILES:
        if c == "timestamp":
            valores.append(ahora)
        else:
            valores.append(perfil.get(c, ""))
    sh = conectar()
    if sh is not None:
        try:
            ws = sh.worksheet(SHEET_PERFILES)
            existentes = ws.get_all_values()
            header = existentes[0]
            filas = existentes[1:]
            id_col = header.index("id_perfil") if "id_perfil" in header else 0
            for i, fila in enumerate(filas):
                if len(fila) > id_col and fila[id_col] == perfil["id_perfil"]:
                    ws.update(values=[valores], range_name=f"A{i + 2}")
                    listar_perfiles.clear()
                    return True, f"✅ Perfil '{perfil['empresa']}' actualizado."
            ws.append_row(valores)
            listar_perfiles.clear()
            return True, f"✅ Perfil '{perfil['empresa']}' creado."
        except Exception as e:
            return False, f"⚠️ No se pudo guardar en Sheets: {e}"
    return True, "✅ Perfil guardado en local."


def eliminar_perfil(id_perfil):
    sh = conectar()
    if sh is None:
        return False, "Sin conexión a Sheets."
    try:
        ws = sh.worksheet(SHEET_PERFILES)
        existentes = ws.get_all_values()
        header = existentes[0]
        id_col = header.index("id_perfil") if "id_perfil" in header else 0
        for i, fila in enumerate(existentes[1:], start=2):
            if len(fila) > id_col and fila[id_col] == id_perfil:
                ws.delete_rows(i)
                listar_perfiles.clear()
                return True, f"✅ Perfil '{id_perfil}' eliminado."
        return False, "No se encontró el perfil."
    except Exception as e:
        return False, f"Error: {e}"


# ─────────────────────────────────────────────────────────────────────
#  HISTORIAL (filtrado por id_perfil)
# ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def leer_historial(id_perfil=None):
    sh = conectar()
    if sh is not None:
        try:
            ws = sh.worksheet(SHEET_HISTORIAL)
            regs = ws.get_all_records()
            if regs:
                df = pd.DataFrame(regs)
                if id_perfil and "id_perfil" in df.columns:
                    df = df[df["id_perfil"].astype(str) == str(id_perfil)]
                return df
        except Exception as e:
            st.warning(f"No se pudo leer historial: {e}")
    if os.path.exists(RUTA_HISTORIAL_LOCAL):
        try:
            df = pd.read_csv(RUTA_HISTORIAL_LOCAL)
            if id_perfil and "id_perfil" in df.columns:
                df = df[df["id_perfil"].astype(str) == str(id_perfil)]
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=COLS_HISTORIAL)


def guardar_importacion(productos, config, usuario="admin"):
    factura   = str(config.get("factura", "SN")).strip() or "SN"
    fecha_imp = datetime.now().strftime("%Y-%m-%d")
    id_imp    = f"IMP-{factura}-{fecha_imp}"
    id_perfil = config.get("id_perfil", slugify(config.get("empresa","empresa")))
    ahora     = datetime.now().isoformat()

    filas = []
    for p in productos:
        cobertura = ""
        if p.get("ventas_semanales", 0) > 0:
            cobertura = round(p["stock_actual"] / p["ventas_semanales"], 2)
        filas.append([
            id_perfil, id_imp, fecha_imp,
            str(config.get("origen","")), str(config.get("proveedor","")), factura,
            str(p["nombre"]), str(p.get("partida_arancelaria","")),
            int(p["cantidad"]), float(p["precio_fob"]),
            float(p["peso_total"]), float(p["volumen_total"]),
            float(p["gastos_totales"]), float(p["gasto_unitario"]),
            float(p["costo_unitario"]),
            float(p["pvp_normal"]), float(p["pvp_mayorista"]), float(p["pvp_especial"]),
            float(p.get("pvp_sugerido", p["pvp_normal"])),
            float(p.get("rentabilidad_pct", 0)),
            str(p.get("alerta_pvp","")), str(p.get("semaforo_color","")),
            cobertura, 0, 0, "",
            usuario, ahora,
        ])

    df_nuevo = pd.DataFrame(filas, columns=COLS_HISTORIAL)

    # Local
    try:
        if os.path.exists(RUTA_HISTORIAL_LOCAL):
            df_prev = pd.read_csv(RUTA_HISTORIAL_LOCAL)
        else:
            df_prev = pd.DataFrame(columns=COLS_HISTORIAL)
        df_total = pd.concat([df_prev, df_nuevo], ignore_index=True)
        df_total = df_total.drop_duplicates(subset=["id_perfil","id_importacion","producto"], keep="last")
        df_total.to_csv(RUTA_HISTORIAL_LOCAL, index=False)
    except Exception:
        pass

    # Sheets
    sh = conectar()
    if sh is not None:
        try:
            ws = sh.worksheet(SHEET_HISTORIAL)
            existentes = ws.get_all_values()
            header, data = existentes[0], existentes[1:]
            idx_imp = header.index("id_importacion") if "id_importacion" in header else 1
            idx_prod = header.index("producto") if "producto" in header else 6
            idx_perf = header.index("id_perfil") if "id_perfil" in header else 0
            idx_map = {}
            for i, row in enumerate(data):
                if len(row) > max(idx_imp, idx_prod, idx_perf):
                    k = f"{row[idx_perf]}|{row[idx_imp]}|{row[idx_prod]}"
                    idx_map[k] = i + 2
            for _, fila in df_nuevo.iterrows():
                k = f"{fila['id_perfil']}|{fila['id_importacion']}|{fila['producto']}"
                valores = [str(v) for v in fila.tolist()]
                if k in idx_map:
                    ws.update(values=[valores], range_name=f"A{idx_map[k]}")
                else:
                    ws.append_row(valores)
            leer_historial.clear()
            return True, f"✅ Guardadas {len(filas)} filas en Sheets + local."
        except Exception as e:
            return False, f"⚠️ Solo guardadas en local (Sheets falló: {e})"
    return True, f"✅ Guardadas {len(filas)} filas en local."


# ─────────────────────────────────────────────────────────────────────
#  ALERTAS
# ─────────────────────────────────────────────────────────────────────
def guardar_alertas(alertas):
    if not alertas:
        return True
    ahora = datetime.now()
    sh = conectar()
    if sh is not None:
        try:
            ws = sh.worksheet(SHEET_ALERTAS)
            for a in alertas:
                ws.append_row([
                    ahora.strftime("%Y-%m-%d %H:%M"),
                    a["producto"], a["nivel"],
                    int(a["stock"]), int(a["ventas_semanales"]),
                    float(a["semanas_cobertura"]),
                    a["accion"], ahora.isoformat(),
                ])
            return True
        except Exception:
            return False
    return True
  

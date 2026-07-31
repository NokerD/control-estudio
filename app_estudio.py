import re
import json
import time
import requests
import markdown
from datetime import datetime, date, timedelta, time as dt_time
import streamlit as st
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from requests.exceptions import RequestException

# ------------------ TIMEZONE HELPERS ------------------
try:
    from zoneinfo import ZoneInfo
    _HAS_ZONEINFO = True
except Exception:
    ZoneInfo = None
    _HAS_ZONEINFO = False
    try:
        import pytz
    except Exception:
        pytz = None

def cargar_estilos(color_principal="#00e676", color_principal_rgba="rgba(0, 230, 118, 0.2)"):
    st.markdown(f"""
        <style>
        /* Forzar modo oscuro permanente */
        .stApp {{
            background-color: #0e1117 !important;
            color: #ffffff !important;
        }}
        
        html, body, [class*="css"] {{ font-size: 18px !important; }}
        h1 {{ font-size: 2.5rem !important; }}
        h2 {{ font-size: 2rem !important; }}
        h3 {{ font-size: 1.5rem !important; }}

        /* Estilo de la tarjeta */
        .materia-card {{
            background-color: #262730;
            border: 1px solid #464b5c;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .materia-title {{ font-size: 1.4rem; font-weight: bold; color: #ffffff; margin-bottom: 5px; }}
        
        /* EL TIEMPO */
        .materia-time {{ 
            font-size: 1.6rem; 
            font-weight: bold; 
            color: {color_principal}; 
            font-family: 'Courier New', monospace; 
            margin-bottom: 15px; 
        }}

        .status-badge {{ display: inline-block; padding: 5px 10px; border-radius: 12px; font-size: 0.9rem; font-weight: bold; margin-bottom: 10px; }}
        .status-active {{ background-color: {color_principal_rgba}; color: {color_principal}; border: 1px solid {color_principal}; }}

        div.stButton > button {{ font-size: 1.2rem !important; font-weight: bold !important; border-radius: 12px !important; }}
        .btn-grande div[data-testid="stButton"] button {{ height: 3.5rem !important; }}

        div[data-testid="stColumns"] {{ align-items: flex-start !important; }}

        /* ESTILO DEL HEATMAP (GITHUB) */
        .heatmap-cell {{
            transition: filter 0.15s ease;
        }}
        .heatmap-cell:hover {{
            filter: brightness(1.3);
            cursor: pointer;
        }}
        </style>
    """, unsafe_allow_html=True)

def generar_particulas(color):
    return """
    <style>
    .particles-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }
    .particle {
        position: absolute;
        bottom: -20px;
        width: 6px;
        height: 6px;
        background-color: COLOR_PARTICULA;
        border-radius: 50%;
        box-shadow: 0 0 10px COLOR_PARTICULA, 0 0 20px COLOR_PARTICULA;
        animation: floatUp 5s infinite ease-in;
        opacity: 0;
    }
    @keyframes floatUp {
        0% { transform: translateY(0) scale(1); opacity: 1; }
        100% { transform: translateY(-100vh) scale(0.5); opacity: 0; }
    }
    .particle:nth-child(1) { left: 15%; animation-duration: 6s; animation-delay: 0s; }
    .particle:nth-child(2) { left: 35%; animation-duration: 5s; animation-delay: 2s; }
    .particle:nth-child(3) { left: 55%; animation-duration: 7s; animation-delay: 1s; }
    .particle:nth-child(4) { left: 75%; animation-duration: 4.5s; animation-delay: 3s; }
    .particle:nth-child(5) { left: 85%; animation-duration: 8s; animation-delay: 0.5s; }
    .particle:nth-child(6) { left: 25%; animation-duration: 5.5s; animation-delay: 1.5s; }
    .particle:nth-child(7) { left: 65%; animation-duration: 6.5s; animation-delay: 2.5s; }
    </style>
    <div class="particles-container">
        <div class="particle"></div><div class="particle"></div>
        <div class="particle"></div><div class="particle"></div>
        <div class="particle"></div><div class="particle"></div>
        <div class="particle"></div>
    </div>
    """.replace("COLOR_PARTICULA", color)

def _argentina_now_global():
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo('America/Argentina/Cordoba'))
    if 'pytz' in globals() and pytz is not None:
        return datetime.now(pytz.timezone('America/Argentina/Cordoba'))
    return datetime.now()

def ahora_str():
    dt = _argentina_now_global()
    try:
        return dt.isoformat(sep=" ", timespec="seconds")
    except:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_datetime(s):
    if not s or str(s).strip() == "":
        raise ValueError("Marca vacía")
    s = str(s).strip()
    TZ = _argentina_now_global().tzinfo
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except:
        pass
    fmts = ["%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=TZ)
            return dt.astimezone(TZ)
        except:
            continue
    raise ValueError(f"Formato inválido: {s}")

def hms_a_segundos(hms):
    if not hms: return 0
    try:
        h, m, s = map(int, hms.split(":"))
        return h*3600 + m*60 + s
    except:
        return 0

def segundos_a_hms(seg):
    h = seg // 3600
    m = (seg % 3600) // 60
    s = seg % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def parse_float_or_zero(s):
    if s is None: return 0.0
    try: return float(str(s).replace(",", ".").strip())
    except: return 0.0

def parse_time_cell_to_seconds(val):
    if val is None: return 0
    s = str(val).strip()
    if s == "": return 0
    if ":" in s:
        try: return hms_a_segundos(s)
        except: return 0
    try:
        f = float(s.replace(",", "."))
        if 0 <= f <= 1:
            return int(f * 86400)
        return int(f)
    except:
        return 0

def replace_row_in_range(range_str, new_row):
    if not isinstance(range_str, str): return range_str
    return re.sub(r'(\d+)(\s*$)', str(new_row), range_str)

def sanitize_key(s):
    return re.sub(r'[^a-zA-Z0-9_]', '_', s)

def pedir_rerun():
    st.session_state["_do_rerun"] = True

# ------------------ GOOGLE SHEETS SESSION ------------------
@st.cache_resource
def get_sheets_session():
    try:
        key_dict = json.loads(st.secrets["service_account"])
    except Exception:
        st.error(f"Error leyendo st.secrets['service_account']")
        st.stop()
    try:
        creds = service_account.Credentials.from_service_account_info(
            key_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return AuthorizedSession(creds)
    except Exception:
        st.error(f"Error creando credenciales")
        st.stop()

session = get_sheets_session()

def sheets_batch_get(spreadsheet_id, ranges):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchGet"
    unique_ranges = list(dict.fromkeys(ranges))
    params = []
    for r in unique_ranges:
        params.append(("ranges", r))
    params.append(("valueRenderOption", "FORMATTED_VALUE"))
    try:
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        ordered_results = data.get("valueRanges", [])
        result_map = {r: res for r, res in zip(unique_ranges, ordered_results)}
        return {"valueRanges": [result_map.get(r, {}) for r in ranges]}
    except RequestException as e:
        raise RuntimeError(f"Error HTTP en batchGet: {e}")

def sheets_batch_update(spreadsheet_id, updates):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate"
    data = {
        "valueInputOption": "USER_ENTERED",
        "data": [{"range": r, "values": [[v]]} for r, v in updates]
    }
    try:
        resp = session.post(url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except RequestException as e:
        raise RuntimeError(f"Error HTTP en batchUpdate: {e}")

# ------------------ CONSTANTES ESTRUCTURALES ------------------
FILA_BASE = 5
FILA_BASE2 = 15
FECHA_BASE = date(2026, 1, 1)
SHEET_FACUNDO = "F. Materias"
SHEET_IVAN = "I. Materias"
SHEET_MARCAS = "marcas"

# CELDAS UNICAS Y FIJAS PARA EL OBJETIVO DE CADA UNO (EN MINUTOS)
RANGO_OBJ_IVAN = f"'{SHEET_MARCAS}'!O2"
RANGO_OBJ_FACU = f"'{SHEET_MARCAS}'!P2"

# ------------------ CONFIGURACIÓN DINÁMICA DEL DÍA ------------------
def get_day_config(target_date=None):
    if target_date is None:
        target_date = _argentina_now_global().date()
    
    delta = (target_date - FECHA_BASE).days
    time_row = FILA_BASE + delta
    time_row2 = FILA_BASE2 + delta
    
    users_dict = {
        "Facundo": {
            "Estadística I":     {"time": f"'{SHEET_FACUNDO}'!B{time_row2}", "est": f"'{SHEET_MARCAS}'!Z10"},
            "Estadística II":    {"time": f"'{SHEET_FACUNDO}'!C{time_row2}", "est": f"'{SHEET_MARCAS}'!Z14"},
            "Historia":          {"time": f"'{SHEET_FACUNDO}'!D{time_row2}", "est": f"'{SHEET_MARCAS}'!Z4"},
            "Int. Contabilidad": {"time": f"'{SHEET_FACUNDO}'!E{time_row2}", "est": f"'{SHEET_MARCAS}'!Z5"},
            "Derecho Público":   {"time": f"'{SHEET_FACUNDO}'!F{time_row2}", "est": f"'{SHEET_MARCAS}'!Z6"},
            "Trabajo":           {"time": f"'{SHEET_FACUNDO}'!H{time_row2}", "est": f"'{SHEET_MARCAS}'!Z7", "excluir": True},
        },
        "Iván": {
            "Física":   {"time": f"'{SHEET_IVAN}'!B{time_row}", "est": f"'{SHEET_MARCAS}'!Z8"},
            "Análisis": {"time": f"'{SHEET_IVAN}'!C{time_row}", "est": f"'{SHEET_MARCAS}'!Z9"},
            "Álgebra":  {"time": f"'{SHEET_IVAN}'!D{time_row}", "est": f"'{SHEET_MARCAS}'!Z13"},
        }
    }
    
    return {
        "TIME_ROW": time_row,
        "USERS": users_dict,
    }

# ------------------ CARGA UNIFICADA DE DATOS ------------------
@st.cache_data()
def cargar_datos_unificados(fecha_str):
    cfg = get_day_config()
    USERS_LOCAL = cfg["USERS"]
    
    all_ranges = []
    mapa_indices = {"materias": {}, "objs": {}, "hist_facu": None, "hist_ivan": None}
    idx = 0
    
    for user, materias in USERS_LOCAL.items():
        for m, info in materias.items():
            all_ranges.append(info["est"]); mapa_indices["materias"][(user, m, "est")] = idx; idx += 1
            all_ranges.append(info["time"]); mapa_indices["materias"][(user, m, "time")] = idx; idx += 1

    all_ranges.append(RANGO_OBJ_FACU); mapa_indices["objs"]["Facundo"] = idx; idx += 1
    all_ranges.append(RANGO_OBJ_IVAN); mapa_indices["objs"]["Iván"] = idx; idx += 1

    # HISTORIAL DE LOS ÚLTIMOS 30 DÍAS
    target_date = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    delta_today = (target_date - FECHA_BASE).days

    row_end_facu = FILA_BASE2 + delta_today
    row_start_facu = max(FILA_BASE2, row_end_facu - 29)
    range_hist_facu = f"'{SHEET_FACUNDO}'!H{row_start_facu}:H{row_end_facu}"

    row_end_ivan = FILA_BASE + delta_today
    row_start_ivan = max(FILA_BASE, row_end_ivan - 29)
    range_hist_ivan = f"'{SHEET_IVAN}'!G{row_start_ivan}:G{row_end_ivan}"

    all_ranges.append(range_hist_facu); mapa_indices["hist_facu"] = idx; idx += 1
    all_ranges.append(range_hist_ivan); mapa_indices["hist_ivan"] = idx; idx += 1

    try:
        res = sheets_batch_get(st.secrets["sheet_id"], all_ranges)
    except Exception as e:
        st.error(f"Error API Google Sheets: {e}")
        st.stop()

    values = res.get("valueRanges", [])
    
    def get_val(i, default=""):
        if i >= len(values): return default
        vr = values[i]; rows = vr.get("values", [])
        if not rows: return default
        return rows[0][0] if rows[0] else default

    def get_list_val(i, default_len=30):
        if i >= len(values): return [0.0] * default_len
        vr = values[i]
        rows = vr.get("values", [])
        float_list = []
        for r in rows:
            val = r[0] if r else "0"
            float_list.append(parse_float_or_zero(val))
        
        while len(float_list) < default_len:
            float_list.insert(0, 0.0)
        return float_list[:default_len]

    data_usuarios = {u: {"estado": {}, "tiempos": {}} for u in USERS_LOCAL}
    materia_en_curso = None
    inicio_dt = None

    for user, materias in USERS_LOCAL.items():
        for m in materias:
            idx_est = mapa_indices["materias"][(user, m, "est")]
            raw_est = get_val(idx_est)
            data_usuarios[user]["estado"][m] = raw_est

            idx_time = mapa_indices["materias"][(user, m, "time")]
            raw_time = get_val(idx_time)
            secs = parse_time_cell_to_seconds(raw_time)
            data_usuarios[user]["tiempos"][m] = segundos_a_hms(secs)

            if user == st.session_state.get("usuario_seleccionado") and str(raw_est).strip() != "":
                try:
                    inicio_dt = parse_datetime(raw_est)
                    materia_en_curso = m
                except Exception:
                    pass

    objs = {
        "Facundo": parse_float_or_zero(get_val(mapa_indices["objs"]["Facundo"])),
        "Iván": parse_float_or_zero(get_val(mapa_indices["objs"]["Iván"]))
    }

    hist_facu_vals = get_list_val(mapa_indices["hist_facu"])
    hist_ivan_vals = get_list_val(mapa_indices["hist_ivan"])

    if "usuario_seleccionado" in st.session_state:
        st.session_state["materia_activa"] = materia_en_curso
        st.session_state["inicio_dt"] = inicio_dt

    return {
        "users_data": data_usuarios,
        "objs": objs,
        "hist_facu": hist_facu_vals,
        "hist_ivan": hist_ivan_vals
    }

def batch_write(updates):
    try:
        sheets_batch_update(st.secrets["sheet_id"], updates)
        cargar_datos_unificados.clear()
    except Exception as e:
        st.error(f"Error escribiendo Google Sheets: {e}")
        st.stop()

# ------------------ CALLBACKS ------------------
def start_materia_callback(usuario, materia):
    try:
        cfg = get_day_config()
        info = cfg["USERS"][usuario][materia]
        
        now_str = ahora_str()
        updates = [(info["est"], now_str)] + [
            (m_datos["est"], "")
            for m_datos in cfg["USERS"][usuario].values()
            if m_datos is not None and m_datos is not info
        ]
        batch_write(updates)
        st.session_state["materia_activa"] = materia
        st.session_state["inicio_dt"] = parse_datetime(now_str)
    except Exception as e:
        st.error(f"start_materia error: {e}")
    finally:
        pedir_rerun()

def stop_materia_callback(usuario, materia):
    try:
        cfg = get_day_config()
        info = cfg["USERS"][usuario][materia]
        
        inicio = st.session_state.get("inicio_dt")
        if inicio is None or st.session_state.get("materia_activa") != materia:
            try:
                res = sheets_batch_get(st.secrets["sheet_id"], [info["est"]])
                vr = res.get("valueRanges", [{}])[0]
                prev_est = vr.get("values", [[""]])[0][0] if vr.get("values") else ""
                if not prev_est:
                    st.error("No hay marca de inicio registrada.")
                    pedir_rerun()
                    return
                inicio = parse_datetime(prev_est)
            except Exception as e:
                st.error(f"Error leyendo marca de inicio: {e}")
                pedir_rerun()
                return

        fin = _argentina_now_global()
        if fin <= inicio:
            st.error("Hora fin previa a hora inicio.")
            batch_write([(info["est"], "")])
            pedir_rerun()
            return

        midnight = datetime.combine(inicio.date() + timedelta(days=1), dt_time(0,0)).replace(tzinfo=inicio.tzinfo)
        partes = []
        if inicio.date() == fin.date():
            partes.append((inicio, fin))
        else:
            partes.append((inicio, midnight))
            partes.append((midnight, fin))

        updates = []
        for (p_inicio, p_fin) in partes:
            segs = int((p_fin - p_inicio).total_seconds())
            base_correcta = FILA_BASE2 if usuario == "Facundo" else FILA_BASE
            target_row = base_correcta + (p_inicio.date() - FECHA_BASE).days
            
            current_time_range = cfg["USERS"][usuario][materia]["time"]
            time_cell_for_row = replace_row_in_range(current_time_range, target_row)
            
            try:
                res2 = sheets_batch_get(st.secrets["sheet_id"], [time_cell_for_row])
                vr2 = res2.get("valueRanges", [{}])[0]
                prev_raw = vr2.get("values", [[""]])[0][0] if vr2.get("values") else ""
            except:
                prev_raw = ""
            new_secs = parse_time_cell_to_seconds(prev_raw) + segs
            updates.append((time_cell_for_row, segundos_a_hms(new_secs)))

        updates.append((info["est"], ""))
        batch_write(updates)
        st.session_state["materia_activa"] = None
        st.session_state["inicio_dt"] = None
    except Exception as e:
        st.error(f"stop_materia error: {e}")
    finally:
        pedir_rerun()

def main():
    if st.session_state.get("clear_cache_estudio", False):
        cargar_datos_unificados.clear()
        st.session_state["clear_cache_estudio"] = False

    if st.session_state.get("_do_rerun", False):
        st.session_state["_do_rerun"] = False
        st.rerun()
        
    if "usuario_seleccionado" not in st.session_state or st.session_state["usuario_seleccionado"] not in ["Facundo", "Iván"]:
        st.error("Error: Usuario no seleccionado.")
        st.stop()
        
    hoy_str = _argentina_now_global().strftime("%Y-%m-%d")
    datos_globales = cargar_datos_unificados(hoy_str)
    
    cfg = get_day_config()
    USERS_LOCAL = cfg["USERS"]
    datos = datos_globales["users_data"]

    USUARIO_ACTUAL = st.session_state["usuario_seleccionado"]
    OTRO_USUARIO = "Iván" if USUARIO_ACTUAL == "Facundo" else "Facundo"

    materia_en_curso = st.session_state.get("materia_activa")
    inicio_dt = st.session_state.get("inicio_dt")

    if materia_en_curso is None:
        for m, est_raw in datos[USUARIO_ACTUAL]["estado"].items():
            if str(est_raw).strip() != "":
                try:
                    inicio_dt_sheet = parse_datetime(est_raw)
                    st.session_state["materia_activa"] = m
                    st.session_state["inicio_dt"] = inicio_dt_sheet
                    materia_en_curso = m
                    inicio_dt = inicio_dt_sheet
                except Exception:
                    pass
                break

    usuario_estudiando = materia_en_curso is not None
    materia_otro = next((m for m, v in datos[OTRO_USUARIO]["estado"].items() if str(v).strip() != ""), "")
    otro_estudiando = materia_otro != ""

    # --- PALETAS Y COLORES ---
    if usuario_estudiando and otro_estudiando:
        COLOR_PRINCIPAL = "#00b0ff"
        COLOR_RGBA = "rgba(0, 176, 255, 0.2)"
        emoji_principal = "🔵"
        PALETTE = {0: "#161b22", 1: "#0a3054", 2: "#004d80", 3: "#007acc", 4: "#00b0ff"}
    else:
        COLOR_PRINCIPAL = "#00e676"
        COLOR_RGBA = "rgba(0, 230, 118, 0.2)"
        emoji_principal = "🟢"
        PALETTE = {0: "#161b22", 1: "#0e4429", 2: "#006d32", 3: "#26a641", 4: "#00e676"}
    
    cargar_estilos(COLOR_PRINCIPAL, COLOR_RGBA)

    # --- CÁLCULOS DEL OTRO USUARIO ---
    tiempo_otro_hms = ""
    if otro_estudiando:
        try:
            inicio_otro = parse_datetime(datos[OTRO_USUARIO]["estado"][materia_otro])
            tiempo_otro_seg = int((_argentina_now_global() - inicio_otro).total_seconds())
            tiempo_otro_hms = segundos_a_hms(tiempo_otro_seg)
        except:
            otro_estudiando = False

    tiempo_anadido_seg = 0
    if usuario_estudiando and inicio_dt is not None:
        tiempo_anadido_seg = int((_argentina_now_global() - inicio_dt).total_seconds())

    # --- SUMAR TODOS LOS TIEMPOS DE LAS MATERIAS (IGNORANDO LAS QUE TIENEN "excluir": True) ---
    total_segs = 0
    for materia, info in USERS_LOCAL[USUARIO_ACTUAL].items():
        if info.get("excluir"):
            continue  # Saltear materias excluidas del total superior
        
        base_seg = hms_a_segundos(datos[USUARIO_ACTUAL]["tiempos"][materia])
        if usuario_estudiando and materia == materia_en_curso:
            base_seg += max(0, tiempo_anadido_seg)
        
        total_segs += base_seg

    total_min = total_segs / 60
    total_hms = segundos_a_hms(total_segs)

    # --- OBJETIVO UNICO (CELDA FIJA EN MINUTOS) ---
    m_obj = datos_globales["objs"][USUARIO_ACTUAL]
    objetivo_hms = segundos_a_hms(int(m_obj * 60))
    progreso_pct = min(total_min / max(1.0, m_obj), 1.0) * 100

    if progreso_pct >= 100:
        COLOR_PRINCIPAL = "#ff9800"
        COLOR_RGBA = "rgba(255, 152, 0, 0.2)"
        emoji_principal = "🟠"
        PALETTE = {0: "#161b22", 1: "#5a3200", 2: "#8a4f00", 3: "#c77700", 4: "#ff9800"}
        cargar_estilos(COLOR_PRINCIPAL, COLOR_RGBA)
        
        if "show_celebration" not in st.session_state:
            st.session_state.show_celebration = True

    if st.session_state.get("show_celebration", False):
        st.balloons()
        st.session_state.show_celebration = False

    # Hora de fin estimada (solo si está estudiando una materia no excluida)
    hora_fin_html = "<div></div>"
    materia_actual_excluida = USERS_LOCAL[USUARIO_ACTUAL].get(materia_en_curso, {}).get("excluir", False) if materia_en_curso else False
    if usuario_estudiando and not materia_actual_excluida and total_min < m_obj:
        minutos_restantes = m_obj - total_min
        hora_fin_obj = _argentina_now_global() + timedelta(minutes=minutos_restantes)
        hora_fin_html = f'<div style="color:#aaa;">Terminás a las {hora_fin_obj.strftime("%H:%M")}</div>'

    # --- CÁLCULO DE RACHA (STREAK) ---
    user_hist = datos_globales["hist_facu"] if USUARIO_ACTUAL == "Facundo" else datos_globales["hist_ivan"]
    reversed_hist = user_hist[::-1]
    streak = 0
    if reversed_hist[0] > 0:
        for val in reversed_hist:
            if val > 0: streak += 1
            else: break
    elif len(reversed_hist) > 1 and reversed_hist[1] > 0:
        for val in reversed_hist[1:]:
            if val > 0: streak += 1
            else: break

    if streak > 1:
        streak_html = f'<div style="display:flex; align-items:center; gap: 4px;"><span style="font-size: 0.9rem;">🔥</span><span style="color: #ff9800; font-weight: bold; font-size: 0.9rem;">Racha: {streak} días</span></div>'
    elif streak == 1:
        streak_html = f'<div style="display:flex; align-items:center; gap: 4px;"><span style="font-size: 0.9rem;">🔥</span><span style="color: #ff9800; font-weight: bold; font-size: 0.9rem;">Racha: {streak} día</span></div>'
    else:
        streak_html = f'<div></div>'

    # --- TARJETA PRINCIPAL DE RESUMEN ---
    with st.container():
        st.markdown(f"""
            <div style="background-color: #1e1e1e; padding: 15px; border-radius: 10px; position: relative; z-index: 10;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
                    {streak_html}
                    <div></div>
                </div>
                <div style="width: 100%; font-size: 2.2rem; font-weight: bold; color: #fff; line-height: 1;">{total_hms}</div>
                <div style="width:100%; background-color:#333; border-radius:10px; height:12px; margin: 15px 0;">
                    <div style="width:{progreso_pct}%; background-color:{COLOR_PRINCIPAL}; height:100%; border-radius:10px; transition: width 0.5s;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; color:#888;">
                    {hora_fin_html}
                    <div>Objetivo: {objetivo_hms}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if usuario_estudiando or otro_estudiando:
            st.markdown(generar_particulas(COLOR_PRINCIPAL), unsafe_allow_html=True)
        else:
            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        
        # --- HEATMAP DE HISTORIAL (ESTILO GITHUB) ---
        max_val_hist = max(user_hist) if max(user_hist) > 0 else 1.0
        cells_html = ""
        for val in user_hist:
            if val <= 0:
                level = 0
            else:
                ratio = val / max_val_hist
                if ratio <= 0.25: level = 1
                elif ratio <= 0.50: level = 2
                elif ratio <= 0.75: level = 3
                else: level = 4
            color_celda = PALETTE[level]
            val_str = f"{int(val)} hs" if val == int(val) else f"{val:.1f} hs"
            cells_html += f'<div class="heatmap-cell" style="background-color: {color_celda}; width: 25px; height: 25px; border-radius: 4px;" title="{val_str}"></div>'

        st.markdown(f"""
            <div style="
                background-color: #1e1e1e;
                padding: 15px;
                border-radius: 10px;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
            ">
                <div style="
                    display: grid;
                    grid-template-columns: repeat(10, 25px);
                    grid-template-rows: repeat(3, 25px);
                    gap: 5px;
                    justify-content: center;
                    font-family: sans-serif;
                ">
                    {cells_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        # --- ESTADO DEL OTRO USUARIO ---
        if otro_estudiando:
            st.markdown(f"""
                <div style="
                    background-color: #1e1e1e;
                    padding: 10px 15px;
                    border-radius: 10px;
                    border-left: 4px solid {COLOR_PRINCIPAL};
                    font-size: 1rem;
                    color: #fff;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                ">
                    <span>
                        <strong>{OTRO_USUARIO}:</strong> {materia_otro} hace <span style="color: {COLOR_PRINCIPAL}; font-family: 'Courier New', monospace; font-weight: bold;">{tiempo_otro_hms}</span>
                    </span>
                    <span>{emoji_principal}</span>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        if usuario_estudiando:
            if st.button("🔄 Actualizar", use_container_width=True):
                cargar_datos_unificados.clear()
                st.rerun()
        
        # --- TEXTO MOTIVACIONAL ---
        md_content = st.secrets["facundo_md"] if USUARIO_ACTUAL == "Facundo" else st.secrets["ivan_md"]
        formatted_content = markdown.markdown(md_content)
        
        st.markdown(f"""
        <div style="
            font-style: italic;
            font-size: 0.85rem;
            color: #858585;
            border-left: 2px solid #444;
            padding-left: 12px;
            line-height: 1.5;
            margin-bottom: 20px;
        ">
            {formatted_content}
        </div>
        """, unsafe_allow_html=True)
    
    # --- TARJETAS DE MATERIAS ---
    mis_materias = USERS_LOCAL[USUARIO_ACTUAL]
    for materia in mis_materias:
        base_seg = hms_a_segundos(datos[USUARIO_ACTUAL]["tiempos"][materia])
        tiempo_total_seg = base_seg
        en_curso = materia_en_curso == materia

        if en_curso:
            tiempo_total_seg += max(0, tiempo_anadido_seg)

        tiempo_display = segundos_a_hms(tiempo_total_seg)
        badge_html = f'<div class="status-badge status-active">{emoji_principal} Estudiando...</div>' if en_curso else ''
        
        html_card = f"""<div class="materia-card"><div class="materia-title">{materia}</div>{badge_html}<div class="materia-time">{tiempo_display}</div></div>"""

        with st.container():
            st.markdown(html_card, unsafe_allow_html=True)

            key_start = sanitize_key(f"start_{USUARIO_ACTUAL}_{materia}")
            key_stop = sanitize_key(f"stop_{USUARIO_ACTUAL}_{materia}")
            key_disabled = sanitize_key(f"dis_{USUARIO_ACTUAL}_{materia}")

            cols = st.columns([1,1,1])
            with cols[0]:
                if en_curso:
                    st.button(f"⛔ DETENER {materia[:14]}", key=key_stop, use_container_width=True,
                              on_click=stop_materia_callback, args=(USUARIO_ACTUAL, materia))
                else:
                    if materia_en_curso is None:
                        st.button("▶ INICIAR", key=key_start, use_container_width=True,
                                  on_click=start_materia_callback, args=(USUARIO_ACTUAL, materia))
                    else:
                        st.button("...", disabled=True, key=key_disabled, use_container_width=True)

            with cols[1]:
                with st.expander("🛠️ Corregir tiempo manualmente"):
                    input_key = f"input_{sanitize_key(materia)}"
                    new_val = st.text_input("Tiempo (HH:MM:SS)", value=datos[USUARIO_ACTUAL]["tiempos"][materia], key=input_key)

                    def save_correction_callback(materia_key):
                        if st.session_state.get("materia_activa") is not None:
                            st.error("⛔ No podés corregir el tiempo mientras estás estudiando.")
                            pedir_rerun()
                            return

                        val = st.session_state.get(f"input_{sanitize_key(materia_key)}", "").strip()
                        if ":" not in val:
                            st.error("Formato inválido (debe ser HH:MM:SS)")
                            pedir_rerun()
                            return

                        try:
                            segs = hms_a_segundos(val)
                            hhmmss = segundos_a_hms(segs)
                            cfg_corr = get_day_config()
                            time_cell_for_row = cfg_corr["USERS"][USUARIO_ACTUAL][materia_key]["time"]
                            batch_write([(time_cell_for_row, hhmmss)])
                            st.success("Tiempo corregido correctamente.")
                        except Exception as e:
                            st.error(f"Error al corregir tiempo: {e}")
                        finally:
                            pedir_rerun()

                    if en_curso or usuario_estudiando:
                        st.info("⛔ No podés corregir el tiempo mientras estás estudiando.")
                    else:
                        if st.button("Guardar Corrección", key=f"save_{sanitize_key(materia)}", on_click=save_correction_callback, args=(materia,)):
                            pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Error crítico en main(): {e}")
        if st.sidebar.button("Reiniciar sesión"):
            st.session_state.clear()
            st.rerun()

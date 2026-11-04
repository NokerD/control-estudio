import re
import json
import time
import os
import tempfile
import threading
import requests
import markdown
from pathlib import Path
from datetime import datetime, date, timedelta, time as dt_time
import streamlit as st
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from requests.exceptions import RequestException

st.set_page_config(
    page_title="Temporizador de Estudio",
    page_icon="📚",
    layout="centered",
)

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

        .plan-progress-row {{ margin-top: 14px; }}
        .plan-progress-header {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            color: #d8d8d8;
            font-size: 0.92rem;
            margin-bottom: 6px;
        }}
        .plan-progress-label {{ font-weight: 600; }}
        .plan-progress-meta {{ color: #888; white-space: nowrap; }}
        .plan-progress-track {{
            width: 100%;
            height: 10px;
            background-color: #333;
            border-radius: 10px;
            overflow: hidden;
        }}
        .plan-progress-fill {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s;
        }}

        .record-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 14px;
        }}
        .record-card {{
            min-width: 0;
            padding: 12px 14px;
            border: 1px solid #343942;
            border-radius: 10px;
            background: linear-gradient(145deg, #24262d, #1b1c21);
        }}
        .record-label {{
            color: #969ba5;
            font-size: 0.76rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }}
        .record-value {{
            margin-top: 4px;
            color: #fff;
            font-size: 1.3rem;
            font-weight: 700;
            line-height: 1.2;
            font-variant-numeric: tabular-nums;
        }}
        .record-detail {{
            margin-top: 4px;
            color: #858a94;
            font-size: 0.78rem;
        }}
        @media (max-width: 520px) {{
            .record-grid {{ gap: 7px; }}
            .record-card {{ padding: 10px; }}
            .record-value {{ font-size: 1.12rem; }}
            .record-label, .record-detail {{ font-size: 0.7rem; }}
        }}

        .st-key-tarjeta-resumen {{
            background-color: #1e1e1e;
            padding: 15px;
            border-radius: 10px;
            position: relative;
            z-index: 10;
        }}
        .st-key-selector-perfil {{
            padding: 8px 14px;
            margin-bottom: 12px;
            border: 1px solid #343942;
            border-radius: 12px;
            background: #1b1c21;
        }}
        .st-key-selector-perfil [data-testid="stRadio"] {{
            justify-content: center;
        }}

        div[data-testid="stElementContainer"].st-key-habito_d button,
        div[data-testid="stElementContainer"].st-key-habito_b button,
        div[data-testid="stElementContainer"].st-key-habito_d_solo button,
        .st-key-habito_d div.stButton > button,
        .st-key-habito_b div.stButton > button,
        .st-key-habito_d_solo div.stButton > button,
        .st-key-habito_d button,
        .st-key-habito_b button,
        .st-key-habito_d_solo button {{
            width: 24px !important;
            min-width: 24px !important;
            max-width: 24px !important;
            height: 24px !important;
            min-height: 24px !important;
            max-height: 24px !important;
            padding: 0 !important;
            border: 0 !important;
            border-radius: 50% !important;
            background-color: #005b97 !important;
            color: #ffffff !important;
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        .st-key-habito_d,
        .st-key-habito_b,
        .st-key-habito_d_solo {{
            position: absolute !important;
            top: 15px !important;
            z-index: 20 !important;
        }}
        .st-key-habito_d {{ right: 51px !important; }}
        .st-key-habito_b,
        .st-key-habito_d_solo {{ right: 15px !important; }}

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

def parse_sheet_date(s, default_year=None):
    if not s or str(s).strip() == "":
        return None
    s = str(s).strip()
    if default_year is None:
        default_year = _argentina_now_global().year

    fmts = [
        "%d/%m/%Y", "%d/%m/%y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d-%m-%Y", "%d-%m-%y",
        "%d/%m", "%d-%m"
    ]
    for fmt in fmts:
        try:
            if "%Y" not in fmt and "%y" not in fmt:
                dt = datetime.strptime(f"{s}/{default_year}", f"{fmt}/%Y")
            else:
                dt = datetime.strptime(s, fmt)
            return dt.date()
        except ValueError:
            continue
    return None

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


def parse_historial_study_seconds(value):
    """Interpreta la columna G como duración o como horas decimales."""
    if value is None or str(value).strip() == "":
        return 0
    raw = str(value).strip()
    if ":" in raw:
        return parse_time_cell_to_seconds(raw)
    return max(0, int(round(parse_float_or_zero(raw) * 3600)))


def calcular_records_estudio(historial_diario, fecha_actual, segundos_hoy=0):
    """Obtiene la mayor racha y el mayor tiempo diario del historial completo."""
    dias = {
        fecha: max(0, int(segundos))
        for fecha, segundos in (historial_diario or {}).items()
        if fecha <= fecha_actual
    }
    dias[fecha_actual] = max(dias.get(fecha_actual, 0), int(segundos_hoy or 0))

    record_diario = max(
        ((fecha, segundos) for fecha, segundos in dias.items() if segundos > 0),
        key=lambda item: item[1],
        default=(None, 0),
    )

    mejor_racha = 0
    mejor_inicio = None
    mejor_fin = None
    racha_actual = 0
    inicio_actual = None
    fecha_anterior = None
    for fecha in sorted(dias):
        if dias[fecha] > 0:
            if fecha_anterior == fecha - timedelta(days=1):
                racha_actual += 1
            else:
                racha_actual = 1
                inicio_actual = fecha
            if racha_actual > mejor_racha:
                mejor_racha = racha_actual
                mejor_inicio = inicio_actual
                mejor_fin = fecha
            fecha_anterior = fecha
        else:
            racha_actual = 0
            inicio_actual = None
            fecha_anterior = None

    return {
        "racha_dias": mejor_racha,
        "racha_inicio": mejor_inicio,
        "racha_fin": mejor_fin,
        "diario_segundos": record_diario[1],
        "diario_fecha": record_diario[0],
    }

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
        service_account_config = st.secrets["service_account"]
        if isinstance(service_account_config, str):
            key_dict = json.loads(service_account_config)
        else:
            key_dict = dict(service_account_config)

        required_fields = ("project_id", "private_key", "client_email", "token_uri")
        missing = [field for field in required_fields if not key_dict.get(field)]
        private_key = str(key_dict.get("private_key", ""))
        private_key_body = re.sub(
            r"-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\s+",
            "",
            private_key,
        )
        if private_key and len(private_key_body) < 100 and "private_key" not in missing:
            missing.append("private_key")
        if not str(st.secrets.get("sheet_id", "")).strip():
            missing.append("sheet_id")
        if missing:
            raise ValueError(f"faltan estos campos: {', '.join(missing)}")

        # También acepta claves copiadas como una sola línea con \n.
        key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
    except Exception as e:
        st.error(f"Completá .streamlit/secrets.toml ({e}).")
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

def sheets_batch_update(spreadsheet_id, updates, value_input_option="USER_ENTERED"):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate"
    data = {
        "valueInputOption": value_input_option,
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
RANGO_OBJ_IVAN = f"'{SHEET_MARCAS}'!O2"
RANGO_OBJ_FACU = f"'{SHEET_MARCAS}'!P2"
RANGOS_ESTADO_IVAN = {
    "Física": f"'{SHEET_MARCAS}'!Z8",
    "Análisis": f"'{SHEET_MARCAS}'!Z9",
    "Álgebra": f"'{SHEET_MARCAS}'!Z13",
}
FILA_ENCABEZADO_HABITOS = FILA_BASE2 - 1


def _fila_habitos_para_fecha(fecha_obj):
    return FILA_BASE2 + (fecha_obj - FECHA_BASE).days


def _rango_habitos_para_fecha(fecha_obj):
    fila = _fila_habitos_para_fecha(fecha_obj)
    return f"'{SHEET_MARCAS}'!AA{fila}:AC{fila}"


def asegurar_espacio_habitos(spreadsheet_id, fecha_obj):
    """Amplía la grilla de marcas si todavía no alcanza las columnas o filas usadas."""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    respuesta = session.get(
        url,
        params={
            "fields": "sheets(properties(title,sheetId,gridProperties(rowCount,columnCount)))"
        },
        timeout=30,
    )
    respuesta.raise_for_status()

    hoja = next(
        (
            item.get("properties", {})
            for item in respuesta.json().get("sheets", [])
            if item.get("properties", {}).get("title") == SHEET_MARCAS
        ),
        None,
    )
    if hoja is None:
        raise ValueError(f"No existe la hoja '{SHEET_MARCAS}'.")

    grid = hoja.get("gridProperties", {})
    filas_actuales = int(grid.get("rowCount", 0))
    columnas_actuales = int(grid.get("columnCount", 0))
    fila_necesaria = max(FILA_ENCABEZADO_HABITOS, _fila_habitos_para_fecha(fecha_obj))
    solicitudes = []

    if filas_actuales < fila_necesaria:
        solicitudes.append(
            {
                "appendDimension": {
                    "sheetId": hoja["sheetId"],
                    "dimension": "ROWS",
                    "length": fila_necesaria - filas_actuales,
                }
            }
        )
    if columnas_actuales < 29:
        solicitudes.append(
            {
                "appendDimension": {
                    "sheetId": hoja["sheetId"],
                    "dimension": "COLUMNS",
                    "length": 29 - columnas_actuales,
                }
            }
        )

    if solicitudes:
        actualizacion = session.post(
            f"{url}:batchUpdate",
            json={"requests": solicitudes},
            timeout=30,
        )
        actualizacion.raise_for_status()


# ------------------ PLAN DIARIO LOCAL ------------------
# El plan vive en el temporizador para que el objetivo no dependa de una celda
# genérica de Sheets. Las materias académicas forman el bloque de estudio y
# Personal/Papá forman el bloque de trabajo, sin elegir una materia principal.
def _resolver_tutor_estudio_root():
    for carpeta in Path(__file__).resolve().parents:
        candidata = carpeta / "Facultad" / "Tutor de Estudio"
        if candidata.exists():
            return candidata
    ruta_instalada = Path(r"D:\NO BORRAR2\Facultad\Tutor de Estudio")
    if ruta_instalada.exists():
        return ruta_instalada
    return Path(__file__).resolve().parent / "Tutor de Estudio"


TUTOR_ESTUDIO_ROOT = _resolver_tutor_estudio_root()
REGISTRO_DIARIO_PATH = TUTOR_ESTUDIO_ROOT / "Registro diario de estudio.md"
REGISTRO_DIARIO_IVAN_PATH = TUTOR_ESTUDIO_ROOT / "Registro diario de estudio - Iván.md"
ACTIVIDAD_EXTENSION_PATH = (
    TUTOR_ESTUDIO_ROOT / "tools" / "youtube-codex" / "data" / "actividad.txt"
)
PLAN_ESTUDIO = {
    "objetivo_estudio_seg": 4 * 60 * 60,
    "objetivo_total_seg": 4 * 60 * 60,
    "objetivo_trabajo_seg": 4 * 60 * 60,
    "materias_trabajo": ("Personal", "Papá"),
}
NOMBRES_MATERIAS = {
    "Estadística I": "Estadística I",
    "Estadística II": "Estadística II",
    "Historia": "Historia",
    "Int. Contabilidad": "Contabilidad",
    "Derecho Público": "Derecho",
    "Personal": "Personal",
    "Papá": "Papá",
}
MATERIAS_ORDEN_REGISTRO = (
    "Estadística I",
    "Estadística II",
    "Historia",
    "Int. Contabilidad",
    "Derecho Público",
    "Personal",
    "Papá",
)


def formato_duracion_markdown(segundos):
    """Representa una duración de forma legible y exacta para el registro."""
    segundos = max(0, int(segundos or 0))
    return segundos_a_hms(segundos)


def obtener_materias_trabajo(plan=None):
    """Devuelve las categorías registrables que forman el bloque Trabajo."""
    plan = plan or PLAN_ESTUDIO
    # Conserva compatibilidad con registros creados antes de separar Trabajo.
    return tuple(plan.get("materias_trabajo", (plan.get("materia_trabajo", "Trabajo"),)))


def estado_actividad_extension(materia_en_curso, plan=None):
    """Mapea el timer activo al estado que consume la extensión multimedia."""
    if not materia_en_curso:
        return "nada"
    if materia_en_curso in set(obtener_materias_trabajo(plan)):
        return "trabajando"
    return "estudiando"


def guardar_estado_actividad_extension(materia_en_curso, plan=None, ruta=None):
    """Publica un estado único, con reemplazo atómico y cierre seguro si falla."""
    destino = Path(ruta) if ruta is not None else ACTIVIDAD_EXTENSION_PATH
    contenido = estado_actividad_extension(materia_en_curso, plan) + "\n"
    temporal = None
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(destino.parent),
            prefix=destino.name + ".",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            archivo.write(contenido)
        os.replace(temporal, destino)
        return True
    except Exception:
        if temporal is not None:
            try:
                temporal.unlink(missing_ok=True)
            except Exception:
                pass
        return False


def _mantener_vivo_estado_extension():
    """Refresca la vigencia mientras el proceso del temporizador está abierto."""
    while True:
        time.sleep(10)
        try:
            contenido = ACTIVIDAD_EXTENSION_PATH.read_text(encoding="utf-8").strip()
            if contenido in {"estudiando", "trabajando", "nada"}:
                os.utime(ACTIVIDAD_EXTENSION_PATH, None)
        except Exception:
            pass


@st.cache_resource
def iniciar_heartbeat_actividad_extension():
    hilo = threading.Thread(
        target=_mantener_vivo_estado_extension,
        name="youtube-codex-activity-heartbeat",
        daemon=True,
    )
    hilo.start()
    return True


def obtener_materias_estudio(plan=None, materias_disponibles=None):
    """Devuelve todas las materias que forman el bloque de estudio."""
    plan = plan or PLAN_ESTUDIO
    if materias_disponibles is None:
        materias_disponibles = plan.get(
            "materias_disponibles", MATERIAS_ORDEN_REGISTRO
        )

    materias_trabajo = set(obtener_materias_trabajo(plan))
    return tuple(
        materia
        for materia in materias_disponibles
        if materia not in materias_trabajo
    )


def calcular_resumen_plan(tiempos_segundos, plan=None):
    """Calcula el avance del plan sin mutar los tiempos por materia."""
    plan = plan or PLAN_ESTUDIO
    estudio = sum(
        int(tiempos_segundos.get(materia, 0))
        for materia in obtener_materias_estudio(plan)
    )
    materias_trabajo = obtener_materias_trabajo(plan)
    objetivo_estudio = plan.get(
        "objetivo_estudio_seg", plan.get("objetivo_total_seg", 0)
    )
    return {
        "estudio_seg": estudio,
        "trabajo_seg": sum(
            int(tiempos_segundos.get(materia, 0))
            for materia in materias_trabajo
        ),
        "total_plan_seg": estudio,
        "objetivo_estudio_seg": objetivo_estudio,
        "objetivo_total_seg": objetivo_estudio,
        "objetivo_trabajo_seg": plan.get("objetivo_trabajo_seg", 0),
    }


def construir_seccion_registro_diario(tiempos_segundos, fecha_obj=None, plan=None, actualizado=None):
    """Construye la sección Markdown correspondiente a un único día."""
    plan = plan or PLAN_ESTUDIO
    fecha_obj = fecha_obj or _argentina_now_global().date()
    actualizado = actualizado or _argentina_now_global()
    resumen = calcular_resumen_plan(tiempos_segundos, plan)
    total_plan = resumen["total_plan_seg"]
    objetivo_estudio = resumen["objetivo_estudio_seg"]
    faltante = max(0, objetivo_estudio - total_plan)
    materias_trabajo = obtener_materias_trabajo(plan)
    trabajo_nombre = " + ".join(
        NOMBRES_MATERIAS.get(materia, materia)
        for materia in materias_trabajo
    )
    objetivo_trabajo = resumen["objetivo_trabajo_seg"]
    objetivo_estudio_texto = formato_duracion_markdown(objetivo_estudio)

    lineas = [
        f"## {fecha_obj.isoformat()}",
        f"- Última actualización: {actualizado.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "### Plan del día",
        f"- Estudio: `{objetivo_estudio_texto}` (objetivo diario).",
        (
            f"- Trabajo: **{trabajo_nombre}**, con meta propia de "
            f"`{formato_duracion_markdown(objetivo_trabajo)}`."
            if objetivo_trabajo
            else f"- Trabajo: **{trabajo_nombre}**, con seguimiento separado."
            if materias_trabajo
            else ""
        ),
        "",
        "### Tiempo estudiado por materia",
        "| Materia | Estudiado hoy | Parte del plan |",
        "|---|---:|---|",
    ]

    materias_orden = plan.get("materias_disponibles", MATERIAS_ORDEN_REGISTRO)
    for materia in materias_orden:
        segundos = int(tiempos_segundos.get(materia, 0))
        nombre = NOMBRES_MATERIAS.get(materia, materia)
        if materia in materias_trabajo:
            parte_plan = "Trabajo (meta propia; no se suma al estudio)"
        else:
            parte_plan = f"Estudio (objetivo {objetivo_estudio_texto})"
        lineas.append(
            f"| {nombre} | `{formato_duracion_markdown(segundos)}` | {parte_plan} |"
        )

    lineas.extend(
        [
            "",
            "### Avance del objetivo",
            f"- Estudio: `{formato_duracion_markdown(resumen['estudio_seg'])}` / `{formato_duracion_markdown(objetivo_estudio)}`.",
            (
                f"- Trabajo: `{formato_duracion_markdown(resumen['trabajo_seg'])}` / "
                f"`{formato_duracion_markdown(objetivo_trabajo)}`."
                if objetivo_trabajo
                else f"- Trabajo: `{formato_duracion_markdown(resumen['trabajo_seg'])}` (seguimiento separado)."
            ),
            f"- Total de estudio: `{formato_duracion_markdown(total_plan)}` / `{formato_duracion_markdown(objetivo_estudio)}`.",
            f"- Faltante de estudio: `{formato_duracion_markdown(faltante)}`.",
            "- Estado: **cumplido**." if faltante == 0 else "- Estado: **en progreso**.",
            "",
        ]
    )
    return "\n".join(lineas)


def actualizar_seccion_registro_diario(contenido, seccion, fecha_obj):
    """Reemplaza el día indicado o lo agrega al final del registro."""
    patron = re.compile(
        rf"^## {re.escape(fecha_obj.isoformat())}\s*$.*?(?=^## \d{{4}}-\d{{2}}-\d{{2}}\s*$|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    if patron.search(contenido or ""):
        return patron.sub(seccion.rstrip() + "\n\n", contenido, count=1).rstrip() + "\n"

    base = (contenido or "").rstrip()
    if not base:
        base = "# Registro diario de estudio"
    return f"{base}\n\n{seccion.rstrip()}\n"


def guardar_registro_diario(tiempos_segundos, fecha_obj=None, actualizado=None, plan=None, ruta=None):
    """Actualiza el Markdown local sin interrumpir el funcionamiento del timer."""
    fecha_obj = fecha_obj or _argentina_now_global().date()
    destino = Path(ruta) if ruta is not None else REGISTRO_DIARIO_PATH
    try:
        contenido = (
            destino.read_text(encoding="utf-8")
            if destino.exists()
            else ""
        )
        seccion = construir_seccion_registro_diario(
            tiempos_segundos,
            fecha_obj=fecha_obj,
            actualizado=actualizado,
            plan=plan,
        )
        nuevo_contenido = actualizar_seccion_registro_diario(
            contenido, seccion, fecha_obj
        )
        if nuevo_contenido != contenido:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(nuevo_contenido, encoding="utf-8")
        return True
    except Exception:
        return False

# CELDA UNICA Y FIJA PARA EL OBJETIVO DE FACUNDO (EN MINUTOS)
RANGO_OBJ_FACU = f"'{SHEET_MARCAS}'!P2"
PORTFOLIO_API_URL_DEFAULT = "http://localhost:3122"

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
            "Personal":          {"time": f"'{SHEET_FACUNDO}'!H{time_row2}", "est": f"'{SHEET_MARCAS}'!Z16", "excluir": True},
            "Papá":              {"time": f"'{SHEET_FACUNDO}'!I{time_row2}", "est": f"'{SHEET_MARCAS}'!Z17", "excluir": True},
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
@st.cache_data(ttl=10)
def cargar_datos_unificados(fecha_str):
    cfg = get_day_config()
    USERS_LOCAL = cfg["USERS"]
    target_date = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    
    all_ranges = []
    mapa_indices = {
        "materias": {},
        "objs": {},
        "hist_facu": None,
        "hist_ivan": None,
        "habitos_hoy": None,
        "estados_ivan": {},
    }
    idx = 0
    
    for user, materias in USERS_LOCAL.items():
        for m, info in materias.items():
            all_ranges.append(info["est"]); mapa_indices["materias"][(user, m, "est")] = idx; idx += 1
            all_ranges.append(info["time"]); mapa_indices["materias"][(user, m, "time")] = idx; idx += 1

    all_ranges.append(RANGO_OBJ_FACU); mapa_indices["objs"]["Facundo"] = idx; idx += 1
    all_ranges.append(RANGO_OBJ_IVAN); mapa_indices["objs"]["Iván"] = idx; idx += 1

    range_habitos_hoy = _rango_habitos_para_fecha(target_date)
    all_ranges.append(range_habitos_hoy); mapa_indices["habitos_hoy"] = idx; idx += 1

    for materia, rango in RANGOS_ESTADO_IVAN.items():
        all_ranges.append(rango)
        mapa_indices["estados_ivan"][materia] = idx
        idx += 1

    # RANGOS PARA MAPEAR HISTORIAL POR FECHAS (COLUMNAS A HASTA G)
    delta_today = (target_date - FECHA_BASE).days

    row_end_facu = FILA_BASE2 + delta_today
    range_hist_facu = f"'{SHEET_FACUNDO}'!A15:G{row_end_facu + 10}"
    all_ranges.append(range_hist_facu); mapa_indices["hist_facu"] = idx; idx += 1

    row_end_ivan = FILA_BASE + delta_today
    range_hist_ivan = f"'{SHEET_IVAN}'!A5:G{row_end_ivan + 10}"
    all_ranges.append(range_hist_ivan); mapa_indices["hist_ivan"] = idx; idx += 1

    try:
        asegurar_espacio_habitos(st.secrets["sheet_id"], target_date)
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

    def get_hist_by_date(i, target_date_obj, default_len=30):
        if i >= len(values): return [0.0] * default_len
        vr = values[i]
        rows = vr.get("values", [])
        
        date_map = {}
        for r in rows:
            if not r: continue
            col_a = r[0] if len(r) > 0 else ""
            col_g = r[6] if len(r) > 6 else "0"
            dt = parse_sheet_date(col_a)
            if dt:
                date_map[dt] = parse_float_or_zero(col_g)

        if date_map:
            res_list = []
            start_date = target_date_obj - timedelta(days=default_len - 1)
            for d_offset in range(default_len):
                d = start_date + timedelta(days=d_offset)
                res_list.append(date_map.get(d, 0.0))
            return res_list

        float_list = []
        for r in rows:
            val = r[6] if len(r) > 6 else (r[0] if r else "0")
            float_list.append(parse_float_or_zero(val))
        while len(float_list) < default_len:
            float_list.insert(0, 0.0)
        return float_list[-default_len:]

    data_usuarios = {u: {"estado": {}, "tiempos": {}} for u in USERS_LOCAL}

    for user, materias in USERS_LOCAL.items():
        for m in materias:
            idx_est = mapa_indices["materias"][(user, m, "est")]
            raw_est = get_val(idx_est)
            data_usuarios[user]["estado"][m] = raw_est

            idx_time = mapa_indices["materias"][(user, m, "time")]
            raw_time = get_val(idx_time)
            secs = parse_time_cell_to_seconds(raw_time)
            data_usuarios[user]["tiempos"][m] = segundos_a_hms(secs)

    objs = {
        "Facundo": parse_float_or_zero(get_val(mapa_indices["objs"]["Facundo"])),
        "Iván": parse_float_or_zero(get_val(mapa_indices["objs"]["Iván"])),
    }

    hist_facu_idx = mapa_indices["hist_facu"]
    hist_facu_vals = get_hist_by_date(hist_facu_idx, target_date)
    hist_ivan_idx = mapa_indices["hist_ivan"]
    hist_ivan_vals = get_hist_by_date(hist_ivan_idx, target_date)
    historiales_diarios = {}
    for usuario, historial_idx in (("Facundo", hist_facu_idx), ("Iván", hist_ivan_idx)):
        historial_diario = {}
        if historial_idx < len(values):
            for row in values[historial_idx].get("values", []):
                if not row:
                    continue
                fecha = parse_sheet_date(row[0] if row else "")
                if fecha is None or fecha > target_date:
                    continue
                valor_g = row[6] if len(row) > 6 else ""
                historial_diario[fecha] = parse_historial_study_seconds(valor_g)
        historiales_diarios[usuario] = historial_diario

    estado_ivan = None
    for materia, estado_idx in mapa_indices["estados_ivan"].items():
        marca = str(get_val(estado_idx)).strip()
        if not marca:
            continue
        try:
            inicio = parse_datetime(marca)
        except Exception:
            continue
        if estado_ivan is None or inicio > estado_ivan["inicio"]:
            estado_ivan = {"materia": materia, "inicio": inicio}

    habit_row = []
    habit_idx = mapa_indices["habitos_hoy"]
    if habit_idx < len(values):
        habit_rows = values[habit_idx].get("values", [])
        if habit_rows:
            habit_row = habit_rows[0]
    fecha_habitos = parse_sheet_date(habit_row[0] if habit_row else "")
    hay_fecha_habitos = fecha_habitos == target_date or (
        fecha_habitos is None and any(str(value).strip() for value in habit_row[1:3])
    )
    habitos_hoy = {
        "B": habit_row[1] if hay_fecha_habitos and len(habit_row) > 1 else "",
        "D": habit_row[2] if hay_fecha_habitos and len(habit_row) > 2 else "",
    }

    return {
        "users_data": data_usuarios,
        "objs": objs,
        "hist_facu": hist_facu_vals,
        "hist_ivan": hist_ivan_vals,
        "historiales_diarios": historiales_diarios,
        "habitos_hoy": habitos_hoy,
        "estado_ivan": estado_ivan,
    }

def batch_write(updates):
    try:
        sheets_batch_update(st.secrets["sheet_id"], updates)
        cargar_datos_unificados.clear()
        enviar_resumen_a_portfolio()
    except Exception as e:
        st.error(f"Error escribiendo Google Sheets: {e}")
        st.stop()


def enviar_resumen_a_portfolio():
    """Publica sólo los minutos del día; nunca bloquea el temporizador."""
    try:
        hoy = _argentina_now_global().date()
        fila_hoy = FILA_BASE2 + (hoy - FECHA_BASE).days
        if fila_hoy < FILA_BASE2:
            return

        rango = f"'{SHEET_FACUNDO}'!A{fila_hoy}:I{fila_hoy}"
        respuesta = sheets_batch_get(st.secrets["sheet_id"], [rango])
        filas = respuesta.get("valueRanges", [{}])[0].get("values", [])
        facultad_segundos = 0
        trabajo_segundos = 0
        for fila in filas:
            facultad_segundos += sum(
                parse_time_cell_to_seconds(fila[indice] if len(fila) > indice else "")
                for indice in range(1, 6)
            )
            trabajo_segundos += sum(
                parse_time_cell_to_seconds(fila[indice] if len(fila) > indice else "")
                for indice in (7, 8)
            )

        configured_url = str(st.secrets.get("portfolio_api_url", PORTFOLIO_API_URL_DEFAULT)).rstrip("/")
        url = PORTFOLIO_API_URL_DEFAULT if configured_url == "http://localhost:3001" else configured_url
        payload = {
            "source": "time",
            "period": {
                "kind": "day",
                "start": hoy.isoformat(),
                "end": hoy.isoformat(),
            },
            "metrics": [
                {
                    "key": "faculty_minutes",
                    "actual": facultad_segundos / 60,
                    "target": 240,
                    "unit": "minutos",
                    "status": "provisional",
                },
                {
                    "key": "work_minutes",
                    "actual": trabajo_segundos / 60,
                    "target": 240,
                    "unit": "minutos",
                    "status": "provisional",
                },
            ],
        }
        requests.post(f"{url}/api/metrics", json=payload, timeout=2)
    except Exception:
        # Portfolio Life es opcional: un problema de red no puede impedir guardar tiempo.
        return

# ------------------ CALLBACKS ------------------
def _get_first_value(value_range, default=""):
    rows = value_range.get("values", [])
    if not rows or not rows[0]:
        return default
    return rows[0][0]


def _get_row_values(value_range, width):
    rows = value_range.get("values", [])
    row = rows[0] if rows else []
    return [row[index] if index < len(row) else "" for index in range(width)]


def registrar_habito_callback(codigo):
    codigo = str(codigo).strip().upper()
    if codigo not in {"B", "D"}:
        return

    try:
        ahora = _argentina_now_global()
        if ahora.time() < dt_time(13, 0):
            return
        hoy = ahora.date()
        asegurar_espacio_habitos(st.secrets["sheet_id"], hoy)
        fila = _fila_habitos_para_fecha(hoy)
        rango_encabezados = (
            f"'{SHEET_MARCAS}'!AA{FILA_ENCABEZADO_HABITOS}:AC{FILA_ENCABEZADO_HABITOS}"
        )
        rango_hoy = _rango_habitos_para_fecha(hoy)
        respuesta = sheets_batch_get(
            st.secrets["sheet_id"], [rango_encabezados, rango_hoy]
        )
        rangos = respuesta.get("valueRanges", [])
        encabezados = _get_row_values(rangos[0], 3) if rangos else ["", "", ""]
        fila_hoy = _get_row_values(rangos[1], 3) if len(rangos) > 1 else ["", "", ""]

        encabezados_esperados = ["Fecha", "B", "D"]
        if any(str(valor).strip() for valor in encabezados) and encabezados != encabezados_esperados:
            raise ValueError(
                "El espacio AA:AC de la hoja 'marcas' ya tiene otros encabezados."
            )

        fecha_guardada = parse_sheet_date(fila_hoy[0])
        if fecha_guardada is not None and fecha_guardada != hoy:
            raise ValueError(
                f"La fila {fila} de 'marcas' contiene otra fecha; no se modificó."
            )

        indice_habito = 1 if codigo == "B" else 2
        if str(fila_hoy[indice_habito]).strip():
            cargar_datos_unificados.clear()
            return

        updates = []
        if not any(str(valor).strip() for valor in encabezados):
            updates.extend(
                (
                    (f"'{SHEET_MARCAS}'!AA{FILA_ENCABEZADO_HABITOS}", "Fecha"),
                    (f"'{SHEET_MARCAS}'!AB{FILA_ENCABEZADO_HABITOS}", "B"),
                    (f"'{SHEET_MARCAS}'!AC{FILA_ENCABEZADO_HABITOS}", "D"),
                )
            )
        if fecha_guardada is None:
            updates.append((f"'{SHEET_MARCAS}'!AA{fila}", hoy.isoformat()))
        columna_habito = "AB" if codigo == "B" else "AC"
        updates.append(
            (
                f"'{SHEET_MARCAS}'!{columna_habito}{fila}",
                ahora.isoformat(sep=" ", timespec="seconds"),
            )
        )
        sheets_batch_update(
            st.secrets["sheet_id"], updates, value_input_option="RAW"
        )
        cargar_datos_unificados.clear()
    except Exception as e:
        st.session_state["error_habito_registrado"] = (
            f"No se pudo registrar el hábito {codigo}: {e}"
        )
    finally:
        pedir_rerun()


def _leer_inicio_registrado(info):
    """Lee la marca real de Sheets para no cerrar una sesión con datos obsoletos."""
    res = sheets_batch_get(st.secrets["sheet_id"], [info["est"]])
    value_ranges = res.get("valueRanges", [])
    prev_est = _get_first_value(value_ranges[0], "") if value_ranges else ""
    if not str(prev_est).strip():
        raise ValueError("No hay marca de inicio registrada.")
    return parse_datetime(prev_est)


def _dividir_sesion_por_dia(inicio, fin):
    """Devuelve tramos diarios para asignar cada segundo a la fila correcta."""
    partes = []
    cursor = inicio
    while cursor.date() < fin.date():
        siguiente_dia = cursor.date() + timedelta(days=1)
        medianoche = datetime.combine(siguiente_dia, dt_time(0, 0)).replace(
            tzinfo=cursor.tzinfo
        )
        partes.append((cursor, medianoche))
        cursor = medianoche
    if cursor < fin:
        partes.append((cursor, fin))
    return partes


def _preparar_actualizaciones_de_tiempo(usuario, materia, inicio, fin, cfg):
    """Calcula los nuevos acumulados sin escribir nada todavía."""
    if fin <= inicio:
        raise ValueError("Hora fin previa a hora inicio.")

    if usuario != "Facundo":
        raise ValueError("Esta versión local solo admite a Facundo.")
    base_correcta = FILA_BASE2
    time_range_base = cfg["USERS"][usuario][materia]["time"]
    tramos = _dividir_sesion_por_dia(inicio, fin)

    rangos_y_segundos = []
    for p_inicio, p_fin in tramos:
        target_row = base_correcta + (p_inicio.date() - FECHA_BASE).days
        rango = replace_row_in_range(time_range_base, target_row)
        segundos = int((p_fin - p_inicio).total_seconds())
        if segundos > 0:
            rangos_y_segundos.append((rango, segundos))

    if not rangos_y_segundos:
        return []

    rangos = [rango for rango, _ in rangos_y_segundos]
    res = sheets_batch_get(st.secrets["sheet_id"], rangos)
    value_ranges = res.get("valueRanges", [])

    updates = []
    for idx, (rango, segundos) in enumerate(rangos_y_segundos):
        value_range = value_ranges[idx] if idx < len(value_ranges) else {}
        previo = parse_time_cell_to_seconds(_get_first_value(value_range, ""))
        updates.append((rango, segundos_a_hms(previo + segundos)))
    return updates


def _datetime_a_str(dt):
    try:
        return dt.isoformat(sep=" ", timespec="seconds")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M:%S")


def segundos_sesion_del_dia(inicio, fin=None):
    """Devuelve sólo los segundos de una sesión que pertenecen a la fecha de fin."""
    if inicio is None:
        return 0
    fin = fin or _argentina_now_global()
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=fin.tzinfo)
    medianoche = datetime.combine(fin.date(), dt_time(0, 0)).replace(
        tzinfo=fin.tzinfo
    )
    inicio_del_dia = max(inicio, medianoche)
    return max(0, int((fin - inicio_del_dia).total_seconds()))


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
        inicio = _leer_inicio_registrado(info)
        fin = _argentina_now_global()
        updates = _preparar_actualizaciones_de_tiempo(
            usuario, materia, inicio, fin, cfg
        )
        updates.append((info["est"], ""))
        batch_write(updates)
        st.session_state["materia_activa"] = None
        st.session_state["inicio_dt"] = None
    except Exception as e:
        st.error(f"stop_materia error: {e}")
    finally:
        pedir_rerun()


def switch_materia_callback(usuario, materia_origen, materia_destino):
    """Guarda la sesión actual y activa otra materia en un solo batch."""
    if materia_origen == materia_destino:
        return
    if st.session_state.get("_cambio_materia_en_progreso", False):
        return

    st.session_state["_cambio_materia_en_progreso"] = True
    try:
        cfg = get_day_config()
        materias = cfg["USERS"][usuario]
        info_origen = materias[materia_origen]

        # Sheets es la fuente de verdad: así una pestaña desactualizada no
        # calcula el progreso desde una hora guardada solamente en la sesión.
        inicio = _leer_inicio_registrado(info_origen)
        fin = _argentina_now_global()
        inicio_nuevo = _datetime_a_str(fin)

        updates = _preparar_actualizaciones_de_tiempo(
            usuario, materia_origen, inicio, fin, cfg
        )

        # El tiempo anterior, el cierre de todas las marcas y el nuevo inicio se
        # envían juntos. Si Google rechaza el batch, no queda un cambio a medias.
        updates.extend(
            (info["est"], inicio_nuevo if nombre == materia_destino else "")
            for nombre, info in materias.items()
        )
        batch_write(updates)

        st.session_state["materia_activa"] = materia_destino
        st.session_state["inicio_dt"] = fin
        st.session_state["mensaje_cambio_materia"] = (
            f"Progreso de {materia_origen} guardado. Ahora estudiás {materia_destino}."
        )
    except Exception as e:
        st.session_state["error_cambio_materia"] = f"No se pudo cambiar de materia: {e}"
    finally:
        st.session_state["_cambio_materia_en_progreso"] = False
        pedir_rerun()

def main():
    iniciar_heartbeat_actividad_extension()

    if st.session_state.get("clear_cache_estudio", False):
        cargar_datos_unificados.clear()
        st.session_state["clear_cache_estudio"] = False

    if st.session_state.get("_do_rerun", False):
        st.session_state["_do_rerun"] = False
        st.rerun()
        
    if st.session_state.get("mensaje_cambio_materia"):
        st.success(st.session_state.pop("mensaje_cambio_materia"))
    if st.session_state.get("error_cambio_materia"):
        st.error(st.session_state.pop("error_cambio_materia"))
    if st.session_state.get("error_habito_registrado"):
        st.error(st.session_state.pop("error_habito_registrado"))

    if st.session_state.get("usuario_seleccionado") not in {"Facundo", "Iván"}:
        st.session_state["usuario_seleccionado"] = "Facundo"
    with st.container(key="selector-perfil"):
        st.radio(
            "Perfil",
            options=("Facundo", "Iván"),
            horizontal=True,
            key="usuario_seleccionado",
            label_visibility="collapsed",
        )
    USUARIO_ACTUAL = st.session_state["usuario_seleccionado"]
        
    hoy_str = _argentina_now_global().strftime("%Y-%m-%d")
    datos_globales = cargar_datos_unificados(hoy_str)
    
    cfg = get_day_config()
    USERS_LOCAL = cfg["USERS"]
    datos = datos_globales["users_data"]
    habitos_hoy = datos_globales["habitos_hoy"]

    ahora_argentina = _argentina_now_global()
    OTRO_USUARIO = "Iván" if USUARIO_ACTUAL == "Facundo" else "Facundo"

    def buscar_materia_activa(usuario):
        for materia, marca in datos[usuario]["estado"].items():
            if not str(marca).strip():
                continue
            try:
                return materia, parse_datetime(marca)
            except Exception:
                continue
        return None, None

    materia_en_curso, inicio_dt = buscar_materia_activa(USUARIO_ACTUAL)
    materia_otro, inicio_otro = buscar_materia_activa(OTRO_USUARIO)
    st.session_state["materia_activa"] = materia_en_curso
    st.session_state["inicio_dt"] = inicio_dt
    usuario_estudiando = materia_en_curso is not None
    otro_estudiando = materia_otro is not None
    tiempo_otro_hms = (
        segundos_a_hms(max(0, int((ahora_argentina - inicio_otro).total_seconds())))
        if otro_estudiando and inicio_otro is not None
        else ""
    )

    materia_para_extension = materia_en_curso or (materia_otro if otro_estudiando else None)
    if not guardar_estado_actividad_extension(materia_para_extension, PLAN_ESTUDIO):
        st.warning(
            "No se pudo actualizar el estado para la extensión en "
            "`tools/youtube-codex/data/actividad.txt`."
        )

    # --- PALETAS Y COLORES (10 NIVELES: 0 al 9) ---
    if usuario_estudiando and otro_estudiando:
        COLOR_PRINCIPAL = "#00b0ff"
        COLOR_RGBA = "rgba(0, 176, 255, 0.2)"
        emoji_principal = "🔵"
        PALETTE = {
            0: "#161b22",
            1: "#041629",
            2: "#062240",
            3: "#082d56",
            4: "#0a396d",
            5: "#00487d",
            6: "#005c9e",
            7: "#0070c0",
            8: "#008df5",
            9: "#00b0ff",
        }
    else:
        COLOR_PRINCIPAL = "#00e676"
        COLOR_RGBA = "rgba(0, 230, 118, 0.2)"
        emoji_principal = "🟢"
        PALETTE = {
            0: "#161b22",
            1: "#051f11",
            2: "#08331b",
            3: "#0a4726",
            4: "#0a592e",
            5: "#0c6e39",
            6: "#0e8544",
            7: "#119c50",
            8: "#18ba62",
            9: "#00e676",
        }
    
    cargar_estilos(COLOR_PRINCIPAL, COLOR_RGBA)

    materias_disponibles = tuple(USERS_LOCAL[USUARIO_ACTUAL].keys())
    if USUARIO_ACTUAL == "Facundo":
        plan_estudio = {
            **PLAN_ESTUDIO,
            "materias_disponibles": materias_disponibles,
        }
        ruta_registro = REGISTRO_DIARIO_PATH
    else:
        objetivo_ivan_seg = int(datos_globales["objs"]["Iván"] * 60) or PLAN_ESTUDIO["objetivo_estudio_seg"]
        plan_estudio = {
            **PLAN_ESTUDIO,
            "objetivo_estudio_seg": objetivo_ivan_seg,
            "objetivo_total_seg": objetivo_ivan_seg,
            "objetivo_trabajo_seg": 0,
            "materias_trabajo": (),
            "materias_disponibles": materias_disponibles,
        }
        ruta_registro = REGISTRO_DIARIO_IVAN_PATH

    tiempo_anadido_seg = 0
    if usuario_estudiando and inicio_dt is not None:
        tiempo_anadido_seg = segundos_sesion_del_dia(
            inicio_dt, _argentina_now_global()
        )

    # --- AVANCE DEL PLAN DIARIO ---
    tiempos_hoy_seg = {}
    for materia, info in USERS_LOCAL[USUARIO_ACTUAL].items():
        base_seg = hms_a_segundos(datos[USUARIO_ACTUAL]["tiempos"][materia])
        if usuario_estudiando and materia == materia_en_curso:
            base_seg += max(0, tiempo_anadido_seg)
        tiempos_hoy_seg[materia] = base_seg

    resumen_plan = calcular_resumen_plan(tiempos_hoy_seg, plan_estudio)
    total_segs = resumen_plan["estudio_seg"]
    registro_guardado = guardar_registro_diario(
        tiempos_hoy_seg,
        fecha_obj=_argentina_now_global().date(),
        actualizado=_argentina_now_global(),
        plan=plan_estudio,
        ruta=ruta_registro,
    )
    if not registro_guardado:
        st.warning(
            "No se pudo guardar el registro diario en la carpeta Tutor de Estudio."
        )

    total_min = total_segs / 60
    total_hms = segundos_a_hms(total_segs)
    historiales_por_usuario = datos_globales["historiales_diarios"]
    records_estudio = calcular_records_estudio(
        historiales_por_usuario.get(USUARIO_ACTUAL, {}),
        _argentina_now_global().date(),
        segundos_hoy=total_segs,
    )
    racha_record_valor = (
        f'{records_estudio["racha_dias"]} día'
        f'{"s" if records_estudio["racha_dias"] != 1 else ""}'
        if records_estudio["racha_dias"]
        else "—"
    )
    if records_estudio["racha_inicio"]:
        if records_estudio["racha_inicio"] == records_estudio["racha_fin"]:
            racha_record_detalle = records_estudio["racha_fin"].strftime("%d/%m/%Y")
        else:
            racha_record_detalle = (
                f'{records_estudio["racha_inicio"].strftime("%d/%m/%Y")} – '
                f'{records_estudio["racha_fin"].strftime("%d/%m/%Y")}'
            )
    else:
        racha_record_detalle = "Todavía sin registros"
    diario_record_valor = (
        segundos_a_hms(records_estudio["diario_segundos"])
        if records_estudio["diario_segundos"]
        else "—"
    )
    diario_record_detalle = (
        records_estudio["diario_fecha"].strftime("%d/%m/%Y")
        if records_estudio["diario_fecha"]
        else "Todavía sin registros"
    )

    # --- OBJETIVOS DEL PLAN ---
    m_obj = resumen_plan["objetivo_estudio_seg"] / 60
    estudio_pct = min(
        resumen_plan["estudio_seg"]
        / max(1, resumen_plan["objetivo_estudio_seg"]),
        1.0,
    ) * 100
    trabajo_pct = min(
        resumen_plan["trabajo_seg"] / max(1, resumen_plan["objetivo_trabajo_seg"]),
        1.0,
    ) * 100
    estudio_hms = segundos_a_hms(resumen_plan["estudio_seg"])
    trabajo_hms = segundos_a_hms(resumen_plan["trabajo_seg"])
    objetivo_estudio_hms = segundos_a_hms(resumen_plan["objetivo_estudio_seg"])
    objetivo_trabajo_hms = segundos_a_hms(resumen_plan["objetivo_trabajo_seg"])
    trabajo_progreso_html = ""
    if resumen_plan["objetivo_trabajo_seg"] > 0:
        trabajo_progreso_html = f"""
            <div class="plan-progress-row">
                <div class="plan-progress-header">
                    <span class="plan-progress-label">Trabajo</span>
                    <span class="plan-progress-meta">{trabajo_hms} / {objetivo_trabajo_hms}</span>
                </div>
                <div class="plan-progress-track">
                    <div class="plan-progress-fill" style="width:{trabajo_pct}%; background-color:{COLOR_PRINCIPAL};"></div>
                </div>
            </div>
        """

    if total_min >= m_obj:
        COLOR_PRINCIPAL = "#ff9800"
        COLOR_RGBA = "rgba(255, 152, 0, 0.2)"
        emoji_principal = "🟠"
        PALETTE = {
            0: "#161b22",
            1: "#291600",
            2: "#402200",
            3: "#562d00",
            4: "#6e3a00",
            5: "#854600",
            6: "#9e5300",
            7: "#b86100",
            8: "#d97400",
            9: "#ff9800"
        }
        cargar_estilos(COLOR_PRINCIPAL, COLOR_RGBA)
        
        if "show_celebration" not in st.session_state:
            st.session_state.show_celebration = True

    if st.session_state.get("show_celebration", False):
        st.balloons()
        st.session_state.show_celebration = False

    # Hora de fin estimada
    hora_fin_texto = ""
    materia_actual_excluida = USERS_LOCAL[USUARIO_ACTUAL].get(materia_en_curso, {}).get("excluir", False) if materia_en_curso else False
    materias_del_plan = set(obtener_materias_estudio(plan_estudio))
    if (
        usuario_estudiando
        and not materia_actual_excluida
        and materia_en_curso in materias_del_plan
        and total_min < m_obj
    ):
        minutos_restantes = m_obj - total_min
        hora_fin_obj = _argentina_now_global() + timedelta(minutes=minutos_restantes)
        hora_fin_texto = f'Terminás a las {hora_fin_obj.strftime("%H:%M")}'

    if otro_estudiando:
        estado_ivan_html = (
            f'<strong>{OTRO_USUARIO} está estudiando:</strong> {materia_otro} '
            f'<span style="color:#888;">hace {tiempo_otro_hms}</span>'
        )
    else:
        estado_ivan_html = ""

    # --- CÁLCULO DE RACHA (STREAK) ---
    user_hist = (
        datos_globales["hist_facu"]
        if USUARIO_ACTUAL == "Facundo"
        else datos_globales["hist_ivan"]
    )
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
    mostrar_botones_habitos = ahora_argentina.time() >= dt_time(13, 0)
    habitos_pendientes = [
        codigo for codigo in ("D", "B")
        if USUARIO_ACTUAL == "Facundo"
        and mostrar_botones_habitos
        and not str(habitos_hoy.get(codigo, "")).strip()
    ]
    with st.container(key="tarjeta-resumen"):
        st.markdown(streak_html, unsafe_allow_html=True)
        for codigo in habitos_pendientes:
            clave_boton = f"habito_{codigo.lower()}"
            if codigo == "D" and len(habitos_pendientes) == 1:
                clave_boton = "habito_d_solo"
            st.button(
                codigo,
                key=clave_boton,
                help=f"Registrar hábito {codigo} de hoy",
                on_click=registrar_habito_callback,
                args=(codigo,),
                width="content",
            )

        st.markdown(f"""
                <div style="width: 100%; font-size: 2.2rem; font-weight: bold; color: #fff; line-height: 1; margin-top: 12px;">{total_hms}</div>
                <div class="plan-progress-row">
                    <div class="plan-progress-header">
                        <span class="plan-progress-label">Estudio</span>
                        <span class="plan-progress-meta">{estudio_hms} / {objetivo_estudio_hms}</span>
                    </div>
                    <div class="plan-progress-track">
                        <div class="plan-progress-fill" style="width:{estudio_pct}%; background-color:{COLOR_PRINCIPAL};"></div>
                    </div>
                </div>
                {trabajo_progreso_html}
                <div style="color:#888; margin-top: 12px;">
                    {hora_fin_texto}
                </div>
        """, unsafe_allow_html=True)

        if usuario_estudiando or otro_estudiando:
            st.markdown(generar_particulas(COLOR_PRINCIPAL), unsafe_allow_html=True)
        else:
            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        
# --- HEATMAP DE HISTORIAL (MAPEADO POR FECHA EXACTA) ---
        max_val_hist = max(user_hist) if max(user_hist) > 0 else 1.0
        cells_html = ""
        for val in user_hist:
            if val <= 0:
                level = 0
            else:
                ratio = val / max_val_hist
                if ratio <= 0.11: level = 1
                elif ratio <= 0.22: level = 2
                elif ratio <= 0.33: level = 3
                elif ratio <= 0.44: level = 4
                elif ratio <= 0.55: level = 5
                elif ratio <= 0.66: level = 6
                elif ratio <= 0.77: level = 7
                elif ratio <= 0.88: level = 8
                else: level = 9

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

        st.markdown(f"""
            <div class="record-grid">
                <div class="record-card">
                    <div class="record-label">🏆 Racha récord</div>
                    <div class="record-value" style="color:{COLOR_PRINCIPAL};">{racha_record_valor}</div>
                    <div class="record-detail">{racha_record_detalle}</div>
                </div>
                <div class="record-card">
                    <div class="record-label">⏱ Récord en un día</div>
                    <div class="record-value" style="color:{COLOR_PRINCIPAL};">{diario_record_valor}</div>
                    <div class="record-detail">{diario_record_detalle}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        if st.button("🔄 Actualizar", use_container_width=True):
            cargar_datos_unificados.clear()
            st.rerun()
        
        # --- TEXTO MOTIVACIONAL ---
        clave_motivacional = "facundo_md" if USUARIO_ACTUAL == "Facundo" else "ivan_md"
        md_content = st.secrets.get(clave_motivacional, "")
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
    
    if otro_estudiando:
        st.markdown(f"""
            <div style="
                background-color:#1e1e1e;
                margin-bottom:12px;
                padding:10px 15px;
                border-radius:10px;
                border-left:4px solid {COLOR_PRINCIPAL};
                color:#d8d8d8;
                font-size:0.95rem;
            ">
                {estado_ivan_html}
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
            key_switch = sanitize_key(f"switch_{USUARIO_ACTUAL}_{materia}")

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
                        st.button(
                            f"🔄 CAMBIAR A {materia[:14]}",
                            key=key_switch,
                            use_container_width=True,
                            disabled=st.session_state.get("_cambio_materia_en_progreso", False),
                            on_click=switch_materia_callback,
                            args=(USUARIO_ACTUAL, materia_en_curso, materia),
                        )

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

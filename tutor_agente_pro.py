import streamlit as st
import os
import base64
import sys
from typing import TypedDict, List
from pypdf import PdfReader

if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from groq import Groq

# ─────────────────────────────────────────────
# AVATARES SVG inline (base64 para usar en CSS)
# ─────────────────────────────────────────────

# Maestra primaria — delantal rosado, pelo recogido, sonrisa
SVG_PRIMARIO = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="56" height="56">
  <!-- cuerpo delantal -->
  <ellipse cx="50" cy="78" rx="26" ry="22" fill="#f48fb1"/>
  <rect x="36" y="62" width="28" height="30" rx="6" fill="#f48fb1"/>
  <!-- cuello -->
  <rect x="44" y="56" width="12" height="12" rx="4" fill="#ffe0b2"/>
  <!-- cabeza -->
  <circle cx="50" cy="46" r="20" fill="#ffe0b2"/>
  <!-- pelo castaño recogido -->
  <ellipse cx="50" cy="30" rx="20" ry="12" fill="#6d4c41"/>
  <circle cx="50" cy="28" r="10" fill="#6d4c41"/>
  <circle cx="64" cy="33" r="7" fill="#6d4c41"/>
  <!-- rodete -->
  <circle cx="67" cy="28" r="6" fill="#6d4c41"/>
  <!-- ojos -->
  <circle cx="44" cy="46" r="3" fill="#fff"/>
  <circle cx="56" cy="46" r="3" fill="#fff"/>
  <circle cx="44.8" cy="46.5" r="1.6" fill="#333"/>
  <circle cx="56.8" cy="46.5" r="1.6" fill="#333"/>
  <!-- sonrisa -->
  <path d="M44 53 Q50 59 56 53" stroke="#c0392b" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <!-- mejillas -->
  <circle cx="41" cy="52" r="3" fill="#f8bbd0" opacity="0.7"/>
  <circle cx="59" cy="52" r="3" fill="#f8bbd0" opacity="0.7"/>
  <!-- manzana en mano -->
  <circle cx="76" cy="72" r="7" fill="#e53935"/>
  <path d="M76 65 Q78 62 80 64" stroke="#388e3c" stroke-width="1.5" fill="none"/>
</svg>
"""

# Tutor secundario — joven, camisa azul, corbata, pelo corto
SVG_SECUNDARIO = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="56" height="56">
  <!-- cuerpo camisa -->
  <rect x="30" y="62" width="40" height="32" rx="8" fill="#1565c0"/>
  <!-- corbata -->
  <polygon points="50,64 53,72 50,80 47,72" fill="#e53935"/>
  <!-- cuello -->
  <rect x="43" y="56" width="14" height="12" rx="4" fill="#ffe0b2"/>
  <!-- solapa izq -->
  <polygon points="43,63 38,75 45,68" fill="#0d47a1"/>
  <!-- solapa der -->
  <polygon points="57,63 62,75 55,68" fill="#0d47a1"/>
  <!-- cabeza -->
  <circle cx="50" cy="45" r="20" fill="#ffe0b2"/>
  <!-- pelo corto oscuro -->
  <ellipse cx="50" cy="30" rx="20" ry="10" fill="#212121"/>
  <rect x="30" y="28" width="40" height="12" rx="6" fill="#212121"/>
  <!-- ojos -->
  <circle cx="44" cy="45" r="3" fill="#fff"/>
  <circle cx="56" cy="45" r="3" fill="#fff"/>
  <circle cx="44.8" cy="45.5" r="1.6" fill="#1a237e"/>
  <circle cx="56.8" cy="45.5" r="1.6" fill="#1a237e"/>
  <!-- sonrisa leve -->
  <path d="M45 52 Q50 57 55 52" stroke="#c0392b" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <!-- mejillas -->
  <circle cx="41" cy="50" r="3" fill="#ffccbc" opacity="0.6"/>
  <circle cx="59" cy="50" r="3" fill="#ffccbc" opacity="0.6"/>
</svg>
"""

# Profesor universitario — señor mayor, traje marrón, anteojos, barba canosa
SVG_UNIVERSIDAD = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="56" height="56">
  <!-- cuerpo traje marrón -->
  <rect x="28" y="62" width="44" height="32" rx="8" fill="#5d4037"/>
  <!-- camisa blanca interior -->
  <rect x="44" y="63" width="12" height="20" fill="#fafafa"/>
  <!-- corbata oscura -->
  <polygon points="50,64 52,71 50,78 48,71" fill="#3e2723"/>
  <!-- solapa izq -->
  <polygon points="44,63 30,80 42,70" fill="#4e342e"/>
  <!-- solapa der -->
  <polygon points="56,63 70,80 58,70" fill="#4e342e"/>
  <!-- cuello -->
  <rect x="43" y="55" width="14" height="12" rx="4" fill="#d7b896"/>
  <!-- cabeza -->
  <circle cx="50" cy="44" r="20" fill="#d7b896"/>
  <!-- pelo canoso corto -->
  <ellipse cx="50" cy="29" rx="20" ry="9" fill="#9e9e9e"/>
  <rect x="30" y="27" width="40" height="10" rx="5" fill="#9e9e9e"/>
  <!-- entradas -->
  <ellipse cx="33" cy="35" rx="5" ry="8" fill="#d7b896"/>
  <ellipse cx="67" cy="35" rx="5" ry="8" fill="#d7b896"/>
  <!-- barba canosa -->
  <ellipse cx="50" cy="60" rx="13" ry="7" fill="#bdbdbd" opacity="0.8"/>
  <!-- bigote -->
  <ellipse cx="50" cy="54" rx="8" ry="3" fill="#9e9e9e"/>
  <!-- ojos -->
  <circle cx="43" cy="44" r="3.5" fill="#fff"/>
  <circle cx="57" cy="44" r="3.5" fill="#fff"/>
  <circle cx="43.5" cy="44.5" r="1.8" fill="#4e342e"/>
  <circle cx="57.5" cy="44.5" r="1.8" fill="#4e342e"/>
  <!-- anteojos armazón -->
  <rect x="38" y="40" width="11" height="8" rx="3" fill="none" stroke="#5d4037" stroke-width="1.5"/>
  <rect x="51" y="40" width="11" height="8" rx="3" fill="none" stroke="#5d4037" stroke-width="1.5"/>
  <line x1="49" y1="44" x2="51" y2="44" stroke="#5d4037" stroke-width="1.5"/>
  <line x1="30" y1="43" x2="38" y2="43" stroke="#5d4037" stroke-width="1.5"/>
  <line x1="62" y1="43" x2="70" y2="43" stroke="#5d4037" stroke-width="1.5"/>
  <!-- expresión seria pero amable -->
  <path d="M45 52 Q50 55 55 52" stroke="#8d6e63" stroke-width="1.2" fill="none" stroke-linecap="round"/>
</svg>
"""

def svg_to_b64(svg_str):
    return base64.b64encode(svg_str.strip().encode()).decode()

AVATARES = {
    "Primario":    svg_to_b64(SVG_PRIMARIO),
    "Secundario":  svg_to_b64(SVG_SECUNDARIO),
    "Universidad": svg_to_b64(SVG_UNIVERSIDAD),
}

# ─────────────────────────────────────────────
# TEMAS DE COLOR POR NIVEL
# ─────────────────────────────────────────────
TEMAS = {
    "Primario": {
        "bg":           "linear-gradient(135deg, #fffde7 0%, #fff9c4 40%, #fff59d 70%, #fff176 100%)",
        "marco":        "#f9a825",
        "marco_glow":   "rgba(249,168,37,0.18)",
        "linea_asist":  "#ffe082",
        "linea_user":   "#fce4ec",
        "borde_asist":  "#f9a825",
        "borde_user":   "#e91e63",
        "input_borde":  "#f9a825",
        "titulo_color": "#e65100",
        "sidebar_bg":   "linear-gradient(180deg, #fb8c00 0%, #f57c00 50%, #e65100 100%)",
        "sidebar_borde":"#bf360c",
        "label_color":  "#fff9c4",
        "emoji_bar":    "🌈 ✏️ 🎨 📏 🌟",
        "spinner_msg":  "🍎 La seño está pensando...",
    },
    "Secundario": {
        "bg":           "linear-gradient(135deg, #e8f5e9 0%, #e3f2fd 40%, #ede7f6 70%, #e8eaf6 100%)",
        "marco":        "#5c6bc0",
        "marco_glow":   "rgba(92,107,192,0.15)",
        "linea_asist":  "#c5cae9",
        "linea_user":   "#fce4ec",
        "borde_asist":  "#3949ab",
        "borde_user":   "#e53935",
        "input_borde":  "#5c6bc0",
        "titulo_color": "#283593",
        "sidebar_bg":   "linear-gradient(180deg, #1a237e 0%, #283593 50%, #1a237e 100%)",
        "sidebar_borde":"#0d47a1",
        "label_color":  "#c5cae9",
        "emoji_bar":    "📱 🎧 ✏️ 💡 🚀",
        "spinner_msg":  "💬 Tu profe está respondiendo...",
    },
    "Universidad": {
        "bg":           "linear-gradient(135deg, #eceff1 0%, #e0e6ea 30%, #cfd8dc 60%, #b0bec5 100%)",
        "marco":        "#546e7a",
        "marco_glow":   "rgba(84,110,122,0.15)",
        "linea_asist":  "#b0bec5",
        "linea_user":   "#e8eaf6",
        "borde_asist":  "#37474f",
        "borde_user":   "#5c6bc0",
        "input_borde":  "#546e7a",
        "titulo_color": "#263238",
        "sidebar_bg":   "linear-gradient(180deg, #263238 0%, #37474f 50%, #263238 100%)",
        "sidebar_borde":"#102027",
        "label_color":  "#b0bec5",
        "emoji_bar":    "🔬 📐 🧮 📊 🎓",
        "spinner_msg":  "📖 El Dr. está elaborando la respuesta...",
    },
}

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA (debe ir antes de todo widget)
# ─────────────────────────────────────────────
st.set_page_config(page_title="Tutor IA Multinivel", layout="centered", page_icon="🎓")

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
defaults = {
    "autenticado": False,
    "chat_history": [],
    "contador": 0,
    "ultima_imagen_id": None,
    "descripcion_imagen": None,
    "nivel_actual": "Secundario",
    "nombre_alumno": "",
    "token_vence": "",
    "dias_restantes": 0,
    "ultimo_audio_id": None,
    "prompt_desde_audio": None,
    "ultima_respuesta_tts": None,
    "ultima_camara_id": None,
    "camara_b64_pendiente": None,
    "errores_detectados": [],
    "temas_dominados": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# CSS DINÁMICO según nivel
# ─────────────────────────────────────────────
def inyectar_tema(nivel: str):
    t = TEMAS[nivel]
    av = AVATARES[nivel]
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&family=Nunito:wght@400;600;700&display=swap');

.stApp {{
    background: {t['bg']};
    font-family: 'Nunito', sans-serif;
    transition: background 0.6s ease;
}}
.stApp h1 {{
    font-family: 'Caveat', cursive !important;
    font-size: 2.6rem !important;
    color: {t['titulo_color']} !important;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    letter-spacing: 1px;
}}
[data-testid="stSidebar"] {{
    background: {t['sidebar_bg']} !important;
    border-right: 4px solid {t['sidebar_borde']};
    box-shadow: 4px 0 15px rgba(0,0,0,0.3);
}}
[data-testid="stSidebar"] * {{ color: #ecf0f1 !important; }}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stFileUploader label {{
    color: {t['label_color']} !important;
    font-family: 'Caveat', cursive !important;
    font-size: 1.2rem !important;
    font-weight: 700 !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    color: #ecf0f1 !important;
}}
/* ── FILE UPLOADER: botón y zona de arrastre bien visibles ── */
[data-testid="stSidebar"] [data-testid="stFileUploader"] section {{
    background: rgba(255,255,255,0.18) !important;
    border: 2px dashed rgba(255,255,255,0.7) !important;
    border-radius: 10px !important;
    padding: 10px !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploader"] section:hover {{
    background: rgba(255,255,255,0.28) !important;
    border-color: #fff !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploader"] button {{
    background: rgba(255,255,255,0.90) !important;
    color: #1a237e !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 6px 14px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {{
    background: #fff !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploader"] span,
[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
[data-testid="stSidebar"] [data-testid="stFileUploader"] p {{
    color: rgba(255,255,255,0.92) !important;
    font-size: 0.82rem !important;
}}
[data-testid="stSidebar"] .stButton button {{
    background: linear-gradient(135deg, #e67e22, #d35400) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Caveat', cursive !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 3px 8px rgba(0,0,0,0.3) !important;
}}
[data-testid="stSidebar"] .stButton button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 5px 12px rgba(0,0,0,0.4) !important;
}}
/* ── MENSAJES ASISTENTE: fondo blanco + renglones encima ── */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] {{
    background-color: rgba(255,255,255,0.92) !important;
    background-image: repeating-linear-gradient(
        to bottom,
        transparent 0px, transparent 27px,
        {t['linea_asist']} 27px, {t['linea_asist']} 28px
    ) !important;
    background-size: 100% 28px !important;
    border-radius: 12px !important;
    border-left: 4px solid {t['borde_asist']} !important;
    padding: 12px 16px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    font-family: 'Nunito', sans-serif !important;
    line-height: 28px !important;
}}
/* ── MENSAJES USUARIO: fondo blanco + renglones encima ── */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {{
    background-color: rgba(255,255,255,0.82) !important;
    background-image: repeating-linear-gradient(
        to bottom,
        transparent 0px, transparent 27px,
        {t['linea_user']} 27px, {t['linea_user']} 28px
    ) !important;
    background-size: 100% 28px !important;
    border-radius: 12px !important;
    border-left: 4px solid {t['borde_user']} !important;
    padding: 12px 16px !important;
    line-height: 28px !important;
}}
/* ── AVATAR: contenedor más grande y visible ── */
[data-testid="stChatMessageAvatarAssistant"] {{
    width: 52px !important;
    height: 52px !important;
    min-width: 52px !important;
    border-radius: 50% !important;
    border: 3px solid {t['borde_asist']} !important;
    background: white !important;
    overflow: hidden !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.2) !important;
    font-size: 2rem !important;
}}
[data-testid="stChatMessageAvatarUser"] {{
    width: 52px !important;
    height: 52px !important;
    min-width: 52px !important;
    border-radius: 50% !important;
    border: 3px solid {t['borde_user']} !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.15) !important;
    font-size: 2rem !important;
}}
/* Input */
[data-testid="stChatInput"] {{
    background: rgba(255,255,255,0.9) !important;
    border-radius: 16px !important;
    border: 2px solid {t['input_borde']} !important;
    box-shadow: 0 4px 12px {t['marco_glow']} !important;
}}
[data-testid="stChatInput"] textarea {{
    font-family: 'Caveat', cursive !important;
    font-size: 1.1rem !important;
    color: {t['titulo_color']} !important;
}}
/* Marco área principal */
.main .block-container {{
    background: rgba(255,255,255,0.6) !important;
    border-radius: 20px !important;
    border: 3px solid {t['marco']} !important;
    box-shadow:
        0 0 0 6px {t['marco_glow']},
        0 8px 32px rgba(0,0,0,0.12),
        inset 0 1px 0 rgba(255,255,255,0.8) !important;
    padding: 2rem 2.5rem !important;
    margin-top: 1rem !important;
}}
.pencil-bar {{
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 0.5rem; font-size: 1.8rem; letter-spacing: 4px;
}}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.2) !important; }}
[data-testid="stSidebar"] [data-testid="stAlert"] {{
    background: rgba(39,174,96,0.25) !important;
    border: 1px solid rgba(39,174,96,0.5) !important;
    border-radius: 8px !important;
}}
[data-testid="stExpander"] {{
    background: rgba(255,255,255,0.7) !important;
    border-radius: 10px !important;
    border: 1px solid {t['marco']} !important;
}}
.stDownloadButton button {{
    background: linear-gradient(135deg, #27ae60, #219a52) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important;
    font-family: 'Caveat', cursive !important;
    font-size: 1rem !important; font-weight: 700 !important;
    width: 100% !important; margin-top: 8px !important;
    box-shadow: 0 3px 8px rgba(0,0,0,0.3) !important;
}}
.stDownloadButton button:hover {{
    background: linear-gradient(135deg, #2ecc71, #27ae60) !important;
    transform: translateY(-2px) !important;
}}
/* ── SELECTBOX NIVEL: bien visible ── */
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {{
    background: rgba(255,255,255,0.22) !important;
    border-radius: 10px !important;
    border: 2px solid rgba(255,255,255,0.7) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
}}
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"]:hover {{
    background: rgba(255,255,255,0.32) !important;
    border-color: #fff !important;
}}
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
    color: #ffffff !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
}}
[data-testid="stSidebar"] .stSelectbox svg {{
    fill: #ffffff !important;
}}
/* ── AUDIO INPUT: micrófono resaltado ── */
[data-testid="stSidebar"] [data-testid="stAudioInput"] {{
    background: rgba(255,255,255,0.18) !important;
    border: 2px solid rgba(255,255,255,0.6) !important;
    border-radius: 12px !important;
    padding: 8px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.25) !important;
}}
[data-testid="stSidebar"] [data-testid="stAudioInput"]:hover {{
    border-color: #fff !important;
    background: rgba(255,255,255,0.28) !important;
}}
[data-testid="stSidebar"] [data-testid="stAudioInput"] button {{
    background: linear-gradient(135deg, #e53935, #c62828) !important;
    border-radius: 50% !important;
    width: 42px !important;
    height: 42px !important;
    box-shadow: 0 3px 10px rgba(229,57,53,0.5) !important;
    border: none !important;
}}
[data-testid="stSidebar"] [data-testid="stAudioInput"] button:hover {{
    background: linear-gradient(135deg, #ff5252, #e53935) !important;
    transform: scale(1.08) !important;
    box-shadow: 0 4px 14px rgba(229,57,53,0.7) !important;
}}
[data-testid="stSidebar"] [data-testid="stAudioInput"] button svg {{
    fill: #ffffff !important;
}}
</style>
<div class="pencil-bar">{t['emoji_bar']}</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SISTEMA DE TOKENS
# ─────────────────────────────────────────────
import hmac as _hmac
import hashlib as _hashlib
import base64 as _base64
from datetime import datetime as _datetime

def verificar_token(token: str) -> dict:
    """Verifica si el token es válido, auténtico y no venció."""
    try:
        clave = st.secrets.get("TOKEN_SECRET", "TutorIA_2025_ClaveSecreta_Cambiame")
        token_raw = _base64.urlsafe_b64decode(token.strip().encode()).decode()
        partes = token_raw.split("|")
        if len(partes) != 3:
            return {"valido": False, "motivo": "Token incorrecto"}
        nombre, vencimiento, firma_recibida = partes
        datos = f"{nombre}|{vencimiento}"
        firma_esperada = _hmac.new(
            clave.encode(), datos.encode(), _hashlib.sha256
        ).hexdigest()[:12]
        if not _hmac.compare_digest(firma_recibida, firma_esperada):
            return {"valido": False, "motivo": "Token inválido"}
        fecha_venc = _datetime.strptime(vencimiento, "%Y%m%d")
        if _datetime.now() > fecha_venc:
            dias_vencido = (_datetime.now() - fecha_venc).days
            return {"valido": False, "motivo": f"Tu acceso venció hace {dias_vencido} día(s). Renovalo contactando al profe."}
        dias_restantes = (fecha_venc - _datetime.now()).days
        return {"valido": True, "nombre": nombre,
                "vence": fecha_venc.strftime("%d/%m/%Y"), "dias_restantes": dias_restantes}
    except Exception:
        return {"valido": False, "motivo": "Token incorrecto. Verificá que lo copiaste bien."}

# ─────────────────────────────────────────────
# LOGIN CON TOKEN
# ─────────────────────────────────────────────
if not st.session_state.autenticado:
    inyectar_tema("Secundario")
    st.markdown("""
    <div style='text-align:center; padding: 2rem 0 1rem;'>
        <div style='font-size:4rem;'>🏫</div>
        <h1 style='font-family: Caveat, cursive; font-size:2.5rem; color:#283593;'>Aula Virtual IA</h1>
        <p style='font-family: Nunito, sans-serif; color:#555;'>
            Ingresá tu código de acceso para comenzar la clase.<br>
            <small>¿No tenés uno? Contactá al profe 📲</small>
        </p>
    </div>""", unsafe_allow_html=True)
    token_input = st.text_input("🎟️ Código de acceso:", placeholder="Pegá tu token acá...").strip()
    col_a, col_b, col_c = st.columns([1,2,1])
    with col_b:
        if st.button("✏️ Entrar al Aula", use_container_width=True):
            if token_input:
                resultado = verificar_token(token_input)
                if resultado["valido"]:
                    st.session_state.autenticado      = True
                    st.session_state.nombre_alumno    = resultado["nombre"]
                    st.session_state.token_vence      = resultado["vence"]
                    st.session_state.dias_restantes   = resultado["dias_restantes"]
                    st.rerun()
                else:
                    st.error(f"❌ {resultado['motivo']}")
            else:
                st.warning("Ingresá tu código de acceso.")
    st.stop()

# ─────────────────────────────────────────────
# MODELOS — API Key oculta en Streamlit Secrets
# ─────────────────────────────────────────────
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

MODEL_TEXT = "llama-3.3-70b-versatile"
VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]

try:
    llm_text = ChatGroq(model=MODEL_TEXT, temperature=0.1)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

def get_vision_llm():
    for m in VISION_MODELS:
        try:
            return ChatGroq(model=m, temperature=0.1)
        except Exception:
            continue
    return None

def transcribir_audio(audio_bytes: bytes) -> str:
    """Transcribe audio usando Whisper de Groq."""
    try:
        import tempfile
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            transcripcion = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=("audio.wav", f, "audio/wav"),
                language="es",
            )
        os.unlink(tmp_path)
        return transcripcion.text.strip()
    except Exception as e:
        return f"ERROR_AUDIO: {e}"

def texto_a_voz(texto: str):
    """Convierte texto a audio usando Groq TTS - Orpheus (modelo actual 2025)."""
    texto_corto = texto[:800] + ("..." if len(texto) > 800 else "")
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    try:
        response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            voice="daniel",   # voz masculina clara
            input=texto_corto,
            response_format="wav",
        )
        return response.read(), None
    except Exception as e:
        return None, str(e)

def describir_imagen_automaticamente(img_b64: str) -> str:
    llm_vision = get_vision_llm()
    if llm_vision is None:
        return "No se pudo analizar la imagen (modelo de visión no disponible)."
    try:
        content = [
            {"type": "text", "text": (
                "Describí esta imagen de forma detallada y educativa. "
                "Indicá qué tipo de documento, ejercicio, problema o contenido contiene. "
                "Sé específico para que un tutor pueda responder preguntas sobre ella sin verla."
            )},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
        ]
        response = llm_vision.invoke([HumanMessage(content=content)])
        return response.content
    except Exception as e:
        return f"No se pudo analizar la imagen: {e}"

# ─────────────────────────────────────────────
# AGENTE LANGGRAPH
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    messages: List[BaseMessage]
    contexto_programa: str
    descripcion_imagen: str
    contador_pasos: int
    nivel_educativo: str
    errores_detectados: List[dict]   # {"tema": str, "descripcion": str, "veces": int}
    temas_dominados: List[str]       # temas que el alumno ya entendió bien
    reforzar_tema: str               # tema a reforzar antes de avanzar

def tutor_node(state: AgentState):
    ultimo_msg = state['messages'][-1].content
    roles = {
        "Primario": (
            "Sos una maestra de primaria cariñosa y muy paciente. "
            "Usás palabras simples, analogías con juguetes o animales, frases cortas. "
            "Nunca usés fórmulas sin explicarlas con ejemplos del día a día. "
            "Celebrá cada avance del alumno con mucho entusiasmo y emojis."
        ),
        "Secundario": (
            "Sos un tutor de secundaria motivador y cercano. "
            "Usás lenguaje claro, ejemplos del mundo real y tecnología. "
            "Introducís terminología técnica pero siempre la explicás. "
            "Sos directo pero amable, como un compañero mayor que sabe mucho."
        ),
        "Universidad": (
            "Sos un profesor universitario riguroso y preciso. "
            "Usás notación técnica, asumís conocimientos previos sólidos. "
            "Vas directo al rigor matemático y conceptual. "
            "Ofrecés demostraciones, casos borde y referencias cuando corresponde."
        ),
    }
    perfil = roles.get(state['nivel_educativo'], roles["Secundario"])
    contexto_imagen = ""
    if state.get("descripcion_imagen"):
        contexto_imagen = f"""
IMAGEN ANALIZADA EN ESTA CLASE:
{state['descripcion_imagen']}
Usá esta descripción para responder cualquier pregunta sobre la imagen aunque ya no esté adjunta.
"""
    sys_prompt = f"""
{perfil}
{contexto_imagen}
INSTRUCCIONES:
1. Seguí el HILO de la conversación hasta que el alumno entienda.
2. El PROGRAMA ({state['contexto_programa']}) es tu guía de contenido.
3. Si el alumno dice 'no entiendo', explicá el ÚLTIMO concepto con otro ejemplo más simple.
4. Usá LaTeX $ $ para fórmulas matemáticas.
5. Respondé siempre en español rioplatense (vos, sos, etc.).

REGLAS ANTI-ERROR (MUY IMPORTANTE):
- NUNCA inventes trucos, técnicas o atajos matemáticos que no sean 100% correctos y verificables.
- Si un alumno te señala que algo que dijiste es incorrecto, reconocelo de inmediato, pedí disculpas brevemente y corregí con la explicación correcta. No insistas en lo erróneo.
- Antes de enseñar un "truco" matemático, verificá mentalmente que funciona para TODOS los casos del rango que vas a enseñar, no solo para algunos.
- Si no estás seguro de que una técnica funciona en todos los casos, NO la enseñes. En su lugar, enseñá el método directo y confiable.
- Es mejor admitir "no hay un truco mágico para esto, pero acá te explico cómo aprenderlo de forma segura" que inventar uno que falle.
"""
    response = llm_text.invoke(
        [SystemMessage(content=sys_prompt)] + state['messages'][:-1] + [HumanMessage(content=ultimo_msg)]
    )
    return {"messages": [response], "contador_pasos": state.get("contador_pasos", 0) + 1}

def evaluador_node(state: AgentState):
    """Analiza el último mensaje del alumno buscando errores conceptuales."""
    ultimo_msg = state["messages"][-1].content
    errores = state.get("errores_detectados") or []
    temas_dominados = state.get("temas_dominados") or []

    prompt_eval = f"""Sos un evaluador pedagógico experto en nivel {state["nivel_educativo"]}.
Analizá este mensaje del alumno: "{ultimo_msg}"

Respondé SOLO con un JSON con este formato exacto (sin markdown, sin explicaciones):
{{
  "tiene_error": true/false,
  "tema": "nombre corto del tema o concepto donde hay error",
  "descripcion_error": "descripción breve del error conceptual detectado",
  "nivel_comprension": "bajo/medio/alto"
}}

Si el mensaje es una pregunta sin errores conceptuales, o es saludos/consulta general, poné tiene_error: false.
Solo marcá error si el alumno demuestra una concepción incorrecta o confusión conceptual clara."""

    try:
        import json
        resp = llm_text.invoke([SystemMessage(content=prompt_eval)])
        texto = resp.content.strip()
        # Limpiar posibles backticks
        texto = texto.replace("```json", "").replace("```", "").strip()
        datos = json.loads(texto)

        if datos.get("tiene_error"):
            tema_error = datos.get("tema", "concepto")
            desc_error = datos.get("descripcion_error", "")
            # Buscamos si ya existía este error
            encontrado = False
            for e in errores:
                if tema_error.lower() in e["tema"].lower():
                    e["veces"] += 1
                    e["descripcion"] = desc_error
                    encontrado = True
                    break
            if not encontrado:
                errores.append({"tema": tema_error, "descripcion": desc_error, "veces": 1})
            return {
                "errores_detectados": errores,
                "temas_dominados": temas_dominados,
                "reforzar_tema": tema_error if any(e["veces"] >= 2 for e in errores if e["tema"] == tema_error) else ""
            }
    except Exception as ex_eval:
        # Guardamos el error en session_state para verlo en el sidebar
        import streamlit as _st
        _st.session_state["_debug_evaluador"] = f"❌ Error en evaluador: {ex_eval}\n\nRespuesta LLM: {resp.content if 'resp' in dir() else 'sin respuesta'}"

    return {
        "errores_detectados": errores,
        "temas_dominados": temas_dominados,
        "reforzar_tema": ""
    }

def reforzador_node(state: AgentState):
    """Interviene cuando el alumno repite un error 2+ veces para reforzar el concepto."""
    tema = state.get("reforzar_tema", "")
    errores = state.get("errores_detectados") or []
    desc = next((e["descripcion"] for e in errores if e["tema"] == tema), "")

    roles_reforz = {
        "Primario": "Sos una maestra muy paciente y cariñosa.",
        "Secundario": "Sos un tutor cercano y motivador.",
        "Universidad": "Sos un profesor universitario riguroso.",
    }
    perfil = roles_reforz.get(state["nivel_educativo"], roles_reforz["Secundario"])

    prompt_reforz = f"""{perfil}
El alumno cometió el siguiente error por segunda vez: "{desc}" sobre el tema "{tema}".
Antes de continuar con la clase, explicá este concepto desde cero con un enfoque diferente al anterior.
Usá un ejemplo nuevo, concreto y claro. Sé empático — no lo retés, ayudalo a entender.
Respondé en español rioplatense."""

    response = llm_text.invoke([SystemMessage(content=prompt_reforz)])
    msg = f"📌 **Refuerzo sobre {tema}:**\n\n{response.content}"
    return {"messages": [AIMessage(content=msg)], "reforzar_tema": ""}

def examen_node(state: AgentState):
    errores = state.get("errores_detectados") or []
    resumen_errores = ""
    if errores:
        resumen_errores = "Temas donde el alumno tuvo dificultades: " +             ", ".join([f"{e['tema']} ({e['veces']} vez)" for e in errores])

    prompt = f"""Generá un ejercicio corto y claro para nivel {state["nivel_educativo"]} 
sobre el último tema tratado. {resumen_errores}
Si hay temas con errores frecuentes, incluí al menos una pregunta sobre esos temas para reforzarlos."""
    response = llm_text.invoke([SystemMessage(content=prompt), HumanMessage(content="¡Examen!")])
    return {
        "messages": [AIMessage(content=f"🎓 **DESAFÍO ({state['nivel_educativo']}):**\n\n{response.content}")],
        "contador_pasos": 0,  # ← reinicia el contador para volver al flujo normal después del desafío
    }

def router_principal(state: AgentState):
    """Decide qué nodo sigue después del tutor."""
    if state.get("contador_pasos", 0) >= 6:
        return "examen"
    return "evaluador"

def router_evaluador(state: AgentState):
    """Decide si reforzar o terminar después de evaluar."""
    if state.get("reforzar_tema"):
        return "reforzador"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("tutor", tutor_node)
workflow.add_node("evaluador", evaluador_node)
workflow.add_node("reforzador", reforzador_node)
workflow.add_node("examen", examen_node)
workflow.set_entry_point("tutor")
workflow.add_conditional_edges("tutor", router_principal, {
    "examen": "examen",
    "evaluador": "evaluador"
})
workflow.add_conditional_edges("evaluador", router_evaluador, {
    "reforzador": "reforzador",
    END: END
})
workflow.add_edge("reforzador", END)
workflow.add_edge("examen", END)
app = workflow.compile()

# ─────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ─────────────────────────────────────────────

# Sidebar primero para leer el nivel antes de inyectar el tema
with st.sidebar:
    st.markdown("<div style='font-family: Caveat, cursive; font-size:1.4rem; color:#f0e68c; text-align:center;'>🏫 Aula Virtual</div>", unsafe_allow_html=True)
    # Info del alumno logueado
    nombre = st.session_state.get("nombre_alumno", "")
    vence  = st.session_state.get("token_vence", "")
    dias   = st.session_state.get("dias_restantes", 0)
    if nombre:
        st.markdown(f"""
<div style='background:rgba(39,174,96,0.25); border:1px solid rgba(39,174,96,0.5);
     border-radius:8px; padding:8px 12px; text-align:center;'>
  <div style='font-family:Caveat,cursive; font-size:1.1rem; color:#fff;'>✅ {nombre}</div>
  <div style='font-size:0.75rem; color:rgba(255,255,255,0.75);'>
    Acceso hasta: {vence} · {dias}d restantes
  </div>
</div>""", unsafe_allow_html=True)
    else:
        st.success("✅ Conectado")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Reiniciar", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.contador = 0
            st.session_state.ultima_imagen_id = None
            st.session_state.descripcion_imagen = None
            st.session_state.errores_detectados = []
            st.session_state.temas_dominados = []
            st.rerun()
    with col2:
        if st.button("🚪 Salir", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.session_state.nombre_alumno  = ""
            st.session_state.token_vence    = ""
            st.session_state.dias_restantes = 0
            st.rerun()

    st.divider()
    nivel_edu = st.selectbox(
        "📚 Nivel del Alumno:",
        ["Primario", "Secundario", "Universidad"],
        index=["Primario","Secundario","Universidad"].index(st.session_state.nivel_actual)
    )
    # Detectamos cambio de nivel y reiniciamos chat si cambió
    if nivel_edu != st.session_state.nivel_actual:
        st.session_state.nivel_actual = nivel_edu
        st.session_state.chat_history = []
        st.session_state.contador = 0
        st.rerun()

    st.divider()

    st.divider()
    st.markdown(
        "<div style='font-family:Caveat,cursive; font-size:1.15rem; font-weight:700; color:#f0e68c;'>"
        "🎙️ Consulta por voz</div>",
        unsafe_allow_html=True
    )
    st.caption("1️⃣ Grabá  ·  2️⃣ Detené  ·  3️⃣ Se envía solo")
    audio_input = st.audio_input(" ", key="audio_consulta", label_visibility="collapsed")
    if audio_input is not None:
        audio_bytes = audio_input.getvalue()
        audio_id = str(len(audio_bytes))
        if audio_id != st.session_state.get("ultimo_audio_id"):
            st.session_state.ultimo_audio_id = audio_id
            with st.spinner("🎙️ Transcribiendo..."):
                texto_transcripto = transcribir_audio(audio_bytes)
            if texto_transcripto.startswith("ERROR_AUDIO:"):
                st.warning("No se pudo transcribir. Escribí tu consulta.")
            else:
                st.session_state.prompt_desde_audio = texto_transcripto
                st.success(f'✅ "{texto_transcripto}"')
    st.divider()

    # ── CÁMARA ──
    st.markdown(
        "<div style='font-family:Caveat,cursive; font-size:1.15rem; font-weight:700; color:#f0e68c;'>"
        "📷 Foto con cámara</div>",
        unsafe_allow_html=True
    )
    activar_camara = st.toggle("📸 Activar cámara", value=False, key="toggle_camara")
    if activar_camara:
        st.caption("Encuadrá el ejercicio y presioná el botón de abajo ↓")
        camara_foto = st.camera_input("📸 Tomar foto", key="camara_ejercicio")
        if camara_foto is not None:
            cam_id = str(len(camara_foto.getvalue()))
            if cam_id != st.session_state.get("ultima_camara_id"):
                st.session_state.ultima_camara_id = cam_id
                # Guardamos la foto pero NO analizamos todavía
                cam_b64 = base64.b64encode(camara_foto.getvalue()).decode("utf-8")
                st.session_state.camara_b64_pendiente = cam_b64
                st.session_state.descripcion_imagen = None
                st.session_state.ultima_imagen_id = cam_id
            st.success("✅ Foto lista — hacé tu consulta y la analizaré")
    else:
        if st.session_state.get("ultima_camara_id"):
            st.caption("📷 Foto en memoria · activá para cambiarla")

    st.divider()

    # ── TTS: ESCUCHAR ÚLTIMA RESPUESTA ──
    st.markdown(
        "<div style='font-family:Caveat,cursive; font-size:1.15rem; font-weight:700; color:#f0e68c;'>"
        "🔊 Escuchar respuesta</div>",
        unsafe_allow_html=True
    )
    ultima_resp = st.session_state.get("ultima_respuesta_tts")
    if ultima_resp:
        st.caption("Presioná para escuchar la última respuesta del tutor")
        if st.button("▶️ Reproducir", use_container_width=True, key="btn_tts"):
            with st.spinner("🔊 Generando audio..."):
                audio_bytes_tts, error_tts = texto_a_voz(ultima_resp)
            if audio_bytes_tts:
                st.audio(audio_bytes_tts, format="audio/wav", autoplay=True)
            else:
                st.warning(f"No se pudo generar el audio. Error: {error_tts}")
    else:
        st.caption("Esperá la primera respuesta del tutor")

    st.divider()
    pdf_file  = st.file_uploader("📄 Programa (PDF)", type="pdf")
    img_file  = st.file_uploader("🖼️ Foto Ejercicio", type=["jpg","png","jpeg"])

    # ── DEBUG EVALUADOR (borrarlo una vez que funcione) ──
    if st.session_state.get("_debug_evaluador"):
        st.error(st.session_state["_debug_evaluador"])

    if img_file:
        imagen_id = f"{img_file.name}_{img_file.size}"
        if imagen_id != st.session_state.ultima_imagen_id:
            st.session_state.ultima_imagen_id = imagen_id
            st.session_state.descripcion_imagen = None
            with st.spinner("🔍 Analizando imagen..."):
                img_b64_temp = base64.b64encode(img_file.read()).decode('utf-8')
                img_file.seek(0)
                st.session_state.descripcion_imagen = describir_imagen_automaticamente(img_b64_temp)
        caption = "✅ Analizada y en memoria" if st.session_state.descripcion_imagen else "⏳ Analizando..."
        st.image(img_file, caption=caption, use_container_width=True)
        if st.session_state.descripcion_imagen:
            with st.expander("👁️ Ver descripción detectada"):
                st.write(st.session_state.descripcion_imagen)
    elif st.session_state.ultima_imagen_id is not None:
        st.session_state.ultima_imagen_id = None
        st.session_state.descripcion_imagen = None

    # ── PANEL DE PROGRESO Y ERRORES ──
    errores_sess = st.session_state.get("errores_detectados", [])
    st.divider()
    st.markdown(
        "<div style='font-family:Caveat,cursive; font-size:1.1rem; font-weight:700; color:#f0e68c;'>"
        "📊 Progreso de la clase</div>",
        unsafe_allow_html=True
    )
    if errores_sess:
        with st.expander(f"⚠️ Temas a reforzar ({len(errores_sess)})", expanded=True):
            for e in errores_sess:
                color = "#e74c3c" if e["veces"] >= 2 else "#f39c12"
                icono = "🔴" if e["veces"] >= 2 else "🟡"
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.1); border-left:3px solid {color};"
                    f"border-radius:6px; padding:6px 10px; margin-bottom:6px;'>"
                    f"<span style='color:{color}; font-weight:700;'>{icono} {e['tema']}</span><br>"
                    f"<span style='font-size:0.72rem; color:rgba(255,255,255,0.7);'>{e['descripcion']}</span><br>"
                    f"<span style='font-size:0.68rem; color:rgba(255,255,255,0.5);'>Repetido {e['veces']} vez/veces</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    else:
        st.caption("✅ Sin errores detectados aún")

    if st.session_state.chat_history:
        chat_text = "--- RESUMEN DE CLASE ---\n\n"
        for m in st.session_state.chat_history:
            autor = "ALUMNO" if isinstance(m, HumanMessage) else "PROFESOR"
            chat_text += f"[{autor}]: {m.content}\n\n"
        if errores_sess:
            chat_text += "\n--- ERRORES DETECTADOS EN CLASE ---\n"
            for e in errores_sess:
                chat_text += f"- {e['tema']} (repetido {e['veces']} vez): {e['descripcion']}\n"
        st.download_button("📄 Descargar Clase", chat_text, "clase.txt", "text/plain")

# Inyectamos el tema DESPUÉS de leer el nivel del selectbox
inyectar_tema(nivel_edu)

# Títulos según nivel
titulos = {
    "Primario":    "👩‍🏫 Seño Virtual con Memoria",
    "Secundario":  "👨‍🏫 Tutor Agéntico con Memoria",
    "Universidad": "🎓 Profesor Virtual con Memoria",
}
st.title(titulos[nivel_edu])

# PDF
contexto = "General"
if pdf_file:
    contexto = "".join([p.extract_text() for p in PdfReader(pdf_file).pages])

# Chat — avatar dinámico según nivel
avatar_map = {
    "Primario":    "👩‍🏫",
    "Secundario":  "👨‍💼",
    "Universidad": "👨‍🔬",
}
avatar_asist = avatar_map[nivel_edu]
av_b64       = AVATARES[nivel_edu]
t_actual     = TEMAS[nivel_edu]

nombre_tutor = {
    "Primario":    "Seño Virtual 👩‍🏫",
    "Secundario":  "Tutor Virtual 👨‍💼",
    "Universidad": "Profesor Dr. 👨‍🔬",
}[nivel_edu]

saludo_tutor = {
    "Primario":    "¡Hola! Preguntame lo que quieras 🌟",
    "Secundario":  "Listo para ayudarte con lo que necesites 💡",
    "Universidad": "Proceda con su consulta académica 📚",
}[nivel_edu]

# Tarjeta de presentación del avatar grande
st.markdown(f"""
<div style="display:flex; align-items:center; gap:14px; margin-bottom:16px; padding:12px 16px;
     background:rgba(255,255,255,0.75); border-radius:16px;
     border-left: 5px solid {t_actual['borde_asist']};
     box-shadow: 0 3px 12px rgba(0,0,0,0.10);">
  <img src="data:image/svg+xml;base64,{av_b64}"
       style="width:80px; height:80px; border-radius:50%;
              border: 3px solid {t_actual['borde_asist']};
              background:white; box-shadow:0 4px 12px rgba(0,0,0,0.2);
              flex-shrink:0;" />
  <div>
    <div style="font-family:'Caveat',cursive; font-size:1.3rem;
                color:{t_actual['titulo_color']}; font-weight:700; margin-bottom:2px;">
      {nombre_tutor}
    </div>
    <div style="font-family:'Nunito',sans-serif; font-size:0.88rem; color:#666;">
      {saludo_tutor}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

for m in st.session_state.chat_history:
    if isinstance(m, AIMessage):
        with st.chat_message("assistant", avatar=avatar_asist):
            st.markdown(m.content)
    else:
        with st.chat_message("user"):
            st.markdown(m.content)

spinner_msg = TEMAS[nivel_edu]["spinner_msg"]

st.markdown(
    "<div style='text-align:center; font-family:Nunito,sans-serif; font-size:0.72rem; "
    "color:#aaa; padding: 4px 0 8px;'>"
    "<b>Academia Particular IA</b> utiliza inteligencia artificial y puede cometer errores. "
    "Por favor, verificá las respuestas importantes con tu docente.</div>",
    unsafe_allow_html=True
)

prompt_audio = st.session_state.get("prompt_desde_audio")
if prompt_audio:
    st.session_state.prompt_desde_audio = None

prompt_texto = st.chat_input("✏️ Escribí tu consulta acá...")
prompt = prompt_audio or prompt_texto

# Si hay foto de cámara pendiente de analizar, la analizamos ahora
if prompt and st.session_state.get("camara_b64_pendiente"):
    with st.spinner("🔍 Analizando tu foto..."):
        descripcion_cam = describir_imagen_automaticamente(st.session_state.camara_b64_pendiente)
        st.session_state.descripcion_imagen = descripcion_cam
        st.session_state.camara_b64_pendiente = None

if prompt:
    new_user_msg = HumanMessage(content=prompt)
    st.session_state.chat_history.append(new_user_msg)
    with st.chat_message("user"):
        if prompt_audio:
            st.markdown(f"🎙️ _{prompt}_")
        else:
            st.markdown(prompt)

    with st.spinner(spinner_msg):
        try:
            inputs = {
                "messages":           st.session_state.chat_history,
                "contexto_programa":  contexto,
                "descripcion_imagen": st.session_state.descripcion_imagen,
                "contador_pasos":     st.session_state.contador,
                "nivel_educativo":    nivel_edu,
                "errores_detectados": st.session_state.get("errores_detectados", []),
                "temas_dominados":    st.session_state.get("temas_dominados", []),
                "reforzar_tema":      "",
            }
            output     = app.invoke(inputs)
            resp_final = output["messages"][-1]
            st.session_state.contador = output.get("contador_pasos", 0)
            st.session_state.errores_detectados = output.get("errores_detectados", [])
            st.session_state.temas_dominados = output.get("temas_dominados", [])
            st.session_state.chat_history.append(resp_final)
            st.session_state.ultima_respuesta_tts = resp_final.content
            with st.chat_message("assistant", avatar=avatar_asist):
                st.markdown(resp_final.content)
        except Exception as e:
            error_str = str(e).lower()
            # Rate limit
            if "rate_limit" in error_str or "rate limit" in error_str or "429" in error_str:
                msgs = {
                    "Primario":    "⏳ ¡Uy! El profe está muy ocupado ahora. Esperá 1 minutito y volvé a preguntar. 😊",
                    "Secundario":  "⏳ Demasiadas consultas en este momento. Esperá un minuto y reintentá.",
                    "Universidad": "⏳ Límite de consultas alcanzado. Por favor aguarde 60 segundos antes de reintentar.",
                }
                st.warning(msgs.get(nivel_edu, msgs["Secundario"]))
            # Sin conexión / timeout
            elif "timeout" in error_str or "connection" in error_str or "network" in error_str:
                st.warning("🌐 Problema de conexión. Verificá tu internet y volvé a intentar.")
            # Token / auth
            elif "401" in error_str or "auth" in error_str or "api key" in error_str:
                st.error("🔑 Error de autenticación. Contactá al administrador.")
            # Cualquier otro error
            else:
                st.warning("⚠️ Algo salió mal. Esperá unos segundos y volvé a intentar. Si el problema persiste, usá el botón 🗑️ Reiniciar.")
            # Quitamos el último mensaje del historial para no dejar mensaje sin respuesta
            if st.session_state.chat_history and isinstance(st.session_state.chat_history[-1], HumanMessage):
                st.session_state.chat_history.pop()

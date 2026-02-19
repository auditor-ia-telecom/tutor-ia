import streamlit as st
import os
import base64
import sys
from typing import TypedDict, List
from pypdf import PdfReader

# Forzamos UTF-8 para evitar errores de ASCII en Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&family=Nunito:wght@400;600;700&display=swap');

/* Fondo general con gradiente suave tipo papel/aula */
.stApp {
    background: linear-gradient(135deg, #fef9f0 0%, #fdf0e0 30%, #f5e6d3 60%, #ede0d4 100%);
    font-family: 'Nunito', sans-serif;
}

/* Título principal estilo pizarra */
.stApp h1 {
    font-family: 'Caveat', cursive !important;
    font-size: 2.6rem !important;
    color: #2c3e50 !important;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    letter-spacing: 1px;
}

/* Sidebar con textura de madera/pizarra lateral */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2c3e50 0%, #34495e 40%, #2c3e50 100%) !important;
    border-right: 4px solid #8B6914;
    box-shadow: 4px 0 15px rgba(0,0,0,0.3);
}

[data-testid="stSidebar"] * {
    color: #ecf0f1 !important;
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stFileUploader label {
    color: #f0e68c !important;
    font-family: 'Caveat', cursive !important;
    font-size: 1.1rem !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #ecf0f1 !important;
}

/* Botones sidebar */
[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #e67e22, #d35400) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Caveat', cursive !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 3px 8px rgba(0,0,0,0.3) !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 5px 12px rgba(0,0,0,0.4) !important;
}

/* Área del chat — efecto cuaderno con renglones */
[data-testid="stChatMessageContent"] {
    background: rgba(255,255,255,0.85) !important;
    border-radius: 12px !important;
    border-left: 4px solid #3498db !important;
    padding: 12px 16px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    font-family: 'Nunito', sans-serif !important;
    background-image: repeating-linear-gradient(
        transparent,
        transparent 27px,
        #c8e6f5 27px,
        #c8e6f5 28px
    ) !important;
    background-size: 100% 28px !important;
    line-height: 28px !important;
}

/* Mensajes del usuario */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
    border-left: 4px solid #e74c3c !important;
    background-image: repeating-linear-gradient(
        transparent,
        transparent 27px,
        #fde8e8 27px,
        #fde8e8 28px
    ) !important;
}

/* Input del chat */
[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.9) !important;
    border-radius: 16px !important;
    border: 2px solid #8B6914 !important;
    box-shadow: 0 4px 12px rgba(139,105,20,0.2) !important;
}
[data-testid="stChatInput"] textarea {
    font-family: 'Caveat', cursive !important;
    font-size: 1.1rem !important;
    color: #2c3e50 !important;
}

/* Marco tipo pizarra alrededor del área principal */
.main .block-container {
    background: rgba(255,255,255,0.6) !important;
    border-radius: 20px !important;
    border: 3px solid #8B6914 !important;
    box-shadow:
        0 0 0 6px rgba(139,105,20,0.15),
        0 8px 32px rgba(0,0,0,0.12),
        inset 0 1px 0 rgba(255,255,255,0.8) !important;
    padding: 2rem 2.5rem !important;
    margin-top: 1rem !important;
}

/* Lápices decorativos usando pseudo-elementos en el título */
.pencil-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 0.5rem;
    font-size: 1.8rem;
    letter-spacing: 4px;
}

/* Divider sidebar */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.2) !important;
}

/* Success box */
[data-testid="stSidebar"] [data-testid="stAlert"] {
    background: rgba(39,174,96,0.25) !important;
    border: 1px solid rgba(39,174,96,0.5) !important;
    border-radius: 8px !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.7) !important;
    border-radius: 10px !important;
    border: 1px solid #d4a853 !important;
}

/* Download button */
.stDownloadButton button {
    background: linear-gradient(135deg, #27ae60, #219a52) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Caveat', cursive !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
}

/* Spinner */
.stSpinner {
    color: #e67e22 !important;
}

/* Selectbox */
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
    background: rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
}
</style>

<!-- Barra de lápices decorativa -->
<div class="pencil-bar">✏️ 📏 🖊️ 📐 ✏️</div>
""", unsafe_allow_html=True)

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tutor IA Multinivel", layout="centered", page_icon="🎓")

defaults = {
    "autenticado": False,
    "chat_history": [],
    "contador": 0,
    "ultima_imagen_id": None,
    "descripcion_imagen": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- 2. PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.markdown("""
    <div style='text-align:center; padding: 2rem 0 1rem;'>
        <div style='font-size:4rem;'>🏫</div>
        <h1 style='font-family: Caveat, cursive; font-size:2.5rem; color:#2c3e50;'>Aula Virtual IA</h1>
        <p style='font-family: Nunito, sans-serif; color:#555;'>Ingresá tu API Key de Groq para comenzar la clase</p>
    </div>
    """, unsafe_allow_html=True)
    key_input = st.text_input("🔑 Groq API Key:", type="password", placeholder="gsk_...").strip()
    col_a, col_b, col_c = st.columns([1,2,1])
    with col_b:
        if st.button("✏️ Entrar al Aula", use_container_width=True):
            if key_input.startswith("gsk_"):
                st.session_state.api_key = key_input
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("La clave debe empezar con 'gsk_'.")
    st.stop()

# --- 3. CONFIGURACIÓN DEL MODELO ---
os.environ["GROQ_API_KEY"] = st.session_state.api_key

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
    for model_name in VISION_MODELS:
        try:
            return ChatGroq(model=model_name, temperature=0.1)
        except Exception:
            continue
    return None

# --- 4. DESCRIPCIÓN AUTOMÁTICA DE IMAGEN ---
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

# --- 5. AGENTE LANGGRAPH ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    contexto_programa: str
    descripcion_imagen: str
    contador_pasos: int
    nivel_educativo: str

def tutor_node(state: AgentState):
    ultimo_msg = state['messages'][-1].content

    roles = {
        "Primario": (
            "Sos un maestro de primaria cariñoso y paciente. "
            "Usás palabras simples, analogías con juguetes o animales, frases cortas. "
            "Nunca usés fórmulas sin explicarlas con ejemplos del día a día. "
            "Celebrá cada avance del alumno con entusiasmo."
        ),
        "Secundario": (
            "Sos un tutor de secundaria motivador y cercano. "
            "Usás lenguaje claro, ejemplos del mundo real y tecnología. "
            "Introducís terminología técnica pero siempre la explicás. "
            "Sos directo pero amable, como un compañero mayor que sabe mucho."
        ),
        "Universidad": (
            "Sos un profesor universitario de ingeniería riguroso y preciso. "
            "Usás notación técnica, asumís conocimientos previos sólidos. "
            "Vas directo al rigor matemático y conceptual. "
            "Ofrecés demostraciones, casos borde y referencias técnicas cuando corresponde."
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
1. Seguí el HILO de la conversación. No cambies de tema hasta que el alumno entienda.
2. El PROGRAMA ({state['contexto_programa']}) es tu guía de nivel y contenido.
3. Si el alumno dice 'no entiendo', explicá el ÚLTIMO concepto con otro ejemplo más simple.
4. Usá LaTeX $ $ para fórmulas matemáticas.
5. Respondé siempre en español rioplatense (vos, sos, etc.).
"""

    try:
        response = llm_text.invoke(
            [SystemMessage(content=sys_prompt)] + state['messages'][:-1] + [HumanMessage(content=ultimo_msg)]
        )
    except Exception:
        raise

    return {"messages": [response], "contador_pasos": state.get("contador_pasos", 0) + 1}

def examen_node(state: AgentState):
    prompt = f"Generá un ejercicio corto y claro para nivel {state['nivel_educativo']} sobre el último tema tratado."
    response = llm_text.invoke([SystemMessage(content=prompt), HumanMessage(content="¡Examen!")])
    return {"messages": [AIMessage(content=f"🎓 **DESAFÍO ({state['nivel_educativo']}):** {response.content}")]}

def router(state: AgentState):
    if state.get("contador_pasos", 0) >= 6:
        return "examen"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("tutor", tutor_node)
workflow.add_node("examen", examen_node)
workflow.set_entry_point("tutor")
workflow.add_conditional_edges("tutor", router, {"examen": "examen", END: END})
workflow.add_edge("examen", END)
app = workflow.compile()

# --- 6. INTERFAZ ---
st.title("👨‍🏫 Tutor Agéntico con Memoria")

with st.sidebar:
    st.markdown("<div style='font-family: Caveat, cursive; font-size:1.4rem; color:#f0e68c; text-align:center;'>🏫 Aula Virtual</div>", unsafe_allow_html=True)
    st.success("✅ Profesor Conectado")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Reiniciar", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.contador = 0
            st.session_state.ultima_imagen_id = None
            st.session_state.descripcion_imagen = None
            st.rerun()
    with col2:
        if st.button("🚪 Salir", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.session_state.api_key = ""
            st.rerun()

    st.divider()
    nivel_edu = st.selectbox("📚 Nivel del Alumno:", ["Primario", "Secundario", "Universidad"], index=1)
    st.divider()
    pdf_file = st.file_uploader("📄 Programa (PDF)", type="pdf")
    img_file = st.file_uploader("🖼️ Foto Ejercicio", type=["jpg", "png", "jpeg"])

    # Detección dinámica de imagen nueva
    if img_file:
        imagen_id = f"{img_file.name}_{img_file.size}"
        if imagen_id != st.session_state.ultima_imagen_id:
            st.session_state.ultima_imagen_id = imagen_id
            st.session_state.descripcion_imagen = None
            with st.spinner("🔍 Analizando imagen..."):
                img_b64_temp = base64.b64encode(img_file.read()).decode('utf-8')
                img_file.seek(0)
                descripcion = describir_imagen_automaticamente(img_b64_temp)
                st.session_state.descripcion_imagen = descripcion

        caption = "✅ Analizada y en memoria" if st.session_state.descripcion_imagen else "⏳ Analizando..."
        st.image(img_file, caption=caption, use_container_width=True)
        if st.session_state.descripcion_imagen:
            with st.expander("👁️ Ver descripción detectada"):
                st.write(st.session_state.descripcion_imagen)

    elif st.session_state.ultima_imagen_id is not None:
        st.session_state.ultima_imagen_id = None
        st.session_state.descripcion_imagen = None

    if st.session_state.chat_history:
        chat_text = "--- RESUMEN DE CLASE ---\n\n"
        for m in st.session_state.chat_history:
            autor = "ALUMNO" if isinstance(m, HumanMessage) else "PROFESOR"
            chat_text += f"[{autor}]: {m.content}\n\n"
        st.download_button("📄 Descargar Clase", chat_text, "clase.txt", "text/plain")

# PDF
contexto = "General"
if pdf_file:
    contexto = "".join([p.extract_text() for p in PdfReader(pdf_file).pages])

# Chat
for m in st.session_state.chat_history:
    with st.chat_message("assistant" if isinstance(m, AIMessage) else "user"):
        st.markdown(m.content)

if prompt := st.chat_input("✏️ Escribí tu consulta acá..."):
    new_user_msg = HumanMessage(content=prompt)
    st.session_state.chat_history.append(new_user_msg)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("📝 El profesor está respondiendo..."):
        try:
            inputs = {
                "messages": st.session_state.chat_history,
                "contexto_programa": contexto,
                "descripcion_imagen": st.session_state.descripcion_imagen,
                "contador_pasos": st.session_state.contador,
                "nivel_educativo": nivel_edu
            }
            output = app.invoke(inputs)
            resp_final = output["messages"][-1]
            st.session_state.contador = output.get("contador_pasos", 0)
            st.session_state.chat_history.append(resp_final)
            with st.chat_message("assistant"):
                st.markdown(resp_final.content)
        except Exception as e:
            st.error(f"❌ Error inesperado: {e}\n\nIntentá reiniciar la clase o verificar tu API Key.")



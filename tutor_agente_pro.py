import streamlit as st
import os
import base64
import sys
from io import BytesIO
from typing import TypedDict, List
from PIL import Image
from pypdf import PdfReader

# Forzamos UTF-8 para evitar errores de ASCII en Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tutor IA Multinivel", layout="centered", page_icon="🎓")

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "contador" not in st.session_state:
    st.session_state.contador = 0

# --- 2. PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("🔑 Acceso al Aula Virtual")
    st.write("Ingresá tu API Key de [Groq](https://console.groq.com) para comenzar.")
    key_input = st.text_input("Groq API Key:", type="password").strip()
    if st.button("Ingresar al Aula"):
        if key_input.startswith("gsk_"):
            st.session_state.api_key = key_input
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("La clave debe empezar con 'gsk_'.")
    st.stop()

# --- 3. CONFIGURACIÓN DEL MODELO ---
os.environ["GROQ_API_KEY"] = st.session_state.api_key

# Modelo de texto (rápido, sin visión)
MODEL_TEXT = "llama-3.3-70b-versatile"

# Modelos con visión — se prueban en orden hasta que uno funcione
VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",     # Recomendado, disponible en plan gratuito
    "meta-llama/llama-4-maverick-17b-128e-instruct",  # Alternativa
]

try:
    llm_text = ChatGroq(model=MODEL_TEXT, temperature=0.1)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- 4. LÓGICA DEL AGENTE (LANGGRAPH) ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    contexto_programa: str
    imagen_b64: str
    contador_pasos: int
    nivel_educativo: str

def get_vision_llm():
    """Intenta instanciar un modelo de visión disponible, devuelve None si ninguno funciona."""
    for model_name in VISION_MODELS:
        try:
            return ChatGroq(model=model_name, temperature=0.1)
        except Exception:
            continue
    return None

def tutor_node(state: AgentState):
    ultimo_msg = state['messages'][-1].content
    hay_imagen = bool(state.get("imagen_b64"))

    # Definición de Roles según el nivel
    roles = {
        "Primario": "Maestro de primaria (10 años). Lenguaje simple, cuentos y mucha paciencia.",
        "Secundario": "Tutor de secundaria (15 años). Lenguaje claro, sin tecnicismos pesados, motivador.",
        "Universidad": "Profesor Ingeniero. Rigor matemático, términos técnicos y analogías de ingeniería."
    }
    perfil = roles.get(state['nivel_educativo'], roles["Secundario"])

    sys_prompt = f"""
    {perfil}

    INSTRUCCIONES DE MEMORIA:
    1. Tu prioridad es el HILO de la conversación actual. Si planteaste un ejercicio, quédate ahí hasta que el alumno entienda.
    2. El PROGRAMA ({state['contexto_programa']}) es solo tu guía de nivel, NO ignores lo que acabas de decir.
    3. Si el alumno dice 'no entiendo', explica el ÚLTIMO concepto mencionado con ejemplos simples.
    4. Si hay una imagen adjunta, analizala y describí su contenido en el contexto educativo.
    5. Usa LaTeX $ $ para fórmulas.
    """

    if hay_imagen:
        llm_vision = get_vision_llm()
        if llm_vision is None:
            # Ningún modelo de visión disponible: avisamos amigablemente
            content = ultimo_msg + "\n\n[Nota: No se pudo analizar la imagen porque ningún modelo de visión está disponible en tu plan de Groq. Describí el ejercicio con palabras y te ayudo igual.]"
            llm = llm_text
        else:
            content = [
                {"type": "text", "text": ultimo_msg},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['imagen_b64']}"}}
            ]
            llm = llm_vision
    else:
        content = ultimo_msg
        llm = llm_text

    try:
        response = llm.invoke(
            [SystemMessage(content=sys_prompt)] + state['messages'][:-1] + [HumanMessage(content=content)]
        )
    except Exception as e:
        # Si falla el modelo de visión, caemos a texto con aviso amigable
        if hay_imagen:
            fallback_content = ultimo_msg + "\n\n[Nota: Hubo un problema al procesar la imagen. Describí el ejercicio con palabras y te ayudo igual.]"
            response = llm_text.invoke(
                [SystemMessage(content=sys_prompt)] + state['messages'][:-1] + [HumanMessage(content=fallback_content)]
            )
        else:
            raise

    return {"messages": [response], "contador_pasos": state.get("contador_pasos", 0) + 1}

def examen_node(state: AgentState):
    prompt = f"Genera un ejercicio corto nivel {state['nivel_educativo']} sobre el último tema hablado."
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

# --- 5. INTERFAZ ---
st.title("👨‍🏫 Tutor Agéntico con Memoria")

with st.sidebar:
    st.success("Profesor Conectado")
    nivel_edu = st.selectbox("Nivel del Alumno:", ["Primario", "Secundario", "Universidad"], index=1)
    st.divider()
    pdf_file = st.file_uploader("Programa (PDF)", type="pdf")
    img_file = st.file_uploader("Foto Ejercicio", type=["jpg", "png", "jpeg"])

    if img_file:
        st.image(img_file, caption="Imagen cargada ✅", use_container_width=True)

    if st.button("🗑️ Reiniciar Clase"):
        st.session_state.chat_history = []
        st.session_state.contador = 0
        st.rerun()

    if st.session_state.chat_history:
        chat_text = "--- RESUMEN DE CLASE ---\n\n"
        for m in st.session_state.chat_history:
            autor = "ALUMNO" if isinstance(m, HumanMessage) else "PROFESOR"
            chat_text += f"[{autor}]: {m.content}\n\n"
        st.download_button("📄 Descargar Clase", chat_text, "clase.txt", "text/plain")

contexto = "General"
if pdf_file:
    contexto = "".join([p.extract_text() for p in PdfReader(pdf_file).pages])

img_b64 = None
if img_file:
    img_b64 = base64.b64encode(img_file.read()).decode('utf-8')

# Mostrar Chat
for m in st.session_state.chat_history:
    with st.chat_message("assistant" if isinstance(m, AIMessage) else "user"):
        st.markdown(m.content)

if prompt := st.chat_input("Escribí acá..."):
    new_user_msg = HumanMessage(content=prompt)
    st.session_state.chat_history.append(new_user_msg)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Analizando hilo de conversación..."):
        try:
            inputs = {
                "messages": st.session_state.chat_history,
                "contexto_programa": contexto,
                "imagen_b64": img_b64,
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

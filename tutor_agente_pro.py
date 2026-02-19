import streamlit as st
import os
import base64
import sys
from io import BytesIO
from typing import TypedDict, List
from PIL import Image
from pypdf import PdfReader

# Forzamos UTF-8 para evitar errores de codificación en Windows/Linux
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

# --- 3. CONFIGURACIÓN DEL MODELO CON VISIÓN ---
os.environ["GROQ_API_KEY"] = st.session_state.api_key
try:
    # Usamos el modelo VISION para que pueda ver fotos y procesar PDF
    llm = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1)
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

def tutor_node(state: AgentState):
    ultimo_msg = state['messages'][-1].content
    content = [{"type": "text", "text": ultimo_msg}]
    
    # Si hay imagen, la adjuntamos al mensaje para el modelo Vision
    if state.get("imagen_b64"):
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{state['imagen_b64']}"}
        })
    
    roles = {
        "Primario": "Maestro de primaria. Lenguaje simple, cuentos y mucha paciencia.",
        "Secundario": "Tutor de secundaria. Lenguaje claro, ejemplos diarios, motivador.",
        "Universidad": "Profesor Ingeniero. Rigor matemático y analogías técnicas."
    }
    
    perfil = roles.get(state['nivel_educativo'], roles["Secundario"])
    
    sys_prompt = f"""
    {perfil}
    CONTEXTO DEL PROGRAMA (Resumen): {state['contexto_programa']}
    
    INSTRUCCIONES:
    1. PRIORIDAD: El hilo de la conversación. Si planteas un problema, quédate ahí.
    2. VISIÓN: Si recibes una imagen, descríbela matemáticamente y resuélvela con LaTeX $ $.
    3. Si el alumno no entiende, simplifica la explicación usando analogías.
    """
    
    # Enviamos historial + prompt de sistema + mensaje actual (con imagen si existe)
    response = llm.invoke([SystemMessage(content=sys_prompt)] + state['messages'][:-1] + [HumanMessage(content=content)])
    return {"messages": [response], "contador_pasos": state.get("contador_pasos", 0) + 1}

def examen_node(state: AgentState):
    prompt = f"Genera un ejercicio corto nivel {state['nivel_educativo']} sobre lo último hablado."
    response = llm.invoke([SystemMessage(content=prompt), HumanMessage(content="¡Examen!")])
    return {"messages": [AIMessage(content=f"🎓 **EVALUACIÓN:** {response.content}")]}

def router(state: AgentState):
    if state.get("contador_pasos", 0) >= 6: return "examen"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("tutor", tutor_node)
workflow.add_node("examen", examen_node)
workflow.set_entry_point("tutor")
workflow.add_conditional_edges("tutor", router, {"examen": "examen", END: END})
workflow.add_edge("examen", END)
app = workflow.compile()

# --- 5. INTERFAZ ---
st.title("👨‍🏫 Tutor Agéntico con Visión")

with st.sidebar:
    st.success("Conectado")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Reset"):
            st.session_state.chat_history = []
            st.session_state.contador = 0
            st.rerun()
    with col2:
        if st.button("🚪 Salir"):
            st.session_state.autenticado = False
            st.rerun()

    st.divider()
    nivel_edu = st.selectbox("Nivel del Alumno:", ["Primario", "Secundario", "Universidad"], index=1)
    
    if len(st.session_state.chat_history) > 0:
        chat_text = "--- CLASE ---\n\n"
        for m in st.session_state.chat_history:
            autor = "ALUMNO" if isinstance(m, HumanMessage) else "PROFESOR"
            chat_text += f"[{autor}]: {m.content}\n\n"
        st.download_button("📄 Descargar Clase", chat_text, "clase.txt", "text/plain", key="dl_btn")

    st.divider()
    pdf_file = st.file_uploader("Programa (PDF)", type="pdf")
    img_file = st.file_uploader("Foto Ejercicio", type=["jpg", "png", "jpeg"])

# Procesamiento de Archivos (Optimizados)
contexto = "No se cargó programa."
if pdf_file:
    reader = PdfReader(pdf_file)
    # Leemos máximo 20 páginas para evitar saturar la API
    limite = min(len(reader.pages), 20)
    contexto = "".join([reader.pages[i].extract_text() for i in range(limite)])
    st.sidebar.info(f"PDF cargado (leídas {limite} págs).")

img_b64 = None
if img_file:
    img_b64 = base64.b64encode(img_file.read()).decode('utf-8')
    st.sidebar.image(img_file, caption="Vista previa")

# Mostrar Chat
for m in st.session_state.chat_history:
    with st.chat_message("assistant" if isinstance(m, AIMessage) else "user"):
        st.markdown(m.content)

if prompt := st.chat_input("Escribí acá..."):
    new_user_msg = HumanMessage(content=prompt)
    st.session_state.chat_history.append(new_user_msg)
    with st.chat_message("user"): st.markdown(prompt)

    with st.spinner("Procesando imagen y texto..."):
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
        with st.chat_message("assistant"): st.markdown(resp_final.content)
        st.rerun()

     




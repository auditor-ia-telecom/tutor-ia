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
try:
    # Bajamos la temperatura para que sea más preciso y coherente
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
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
    # Capturamos el último mensaje del alumno
    ultimo_msg = state['messages'][-1].content
    content = [{"type": "text", "text": ultimo_msg}]
    
    if state.get("imagen_b64"):
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['imagen_b64']}"}})
    
    # Definición de Roles según el nivel
    roles = {
        "Primario": "Maestro de primaria (10 años). Lenguaje simple, cuentos y mucha paciencia.",
        "Secundario": "Tutor de secundaria (15 años). Lenguaje claro, sin tecnicismos pesados, motivador.",
        "Universidad": "Profesor Ingeniero. Rigor matemático, términos técnicos y analogías de ingeniería."
    }
    
    perfil = roles.get(state['nivel_educativo'], roles["Secundario"])
    
    # PROMPT DE MEMORIA MEJORADA: Obligamos al modelo a seguir el hilo
    sys_prompt = f"""
    {perfil}
    
    INSTRUCCIONES DE MEMORIA:
    1. Tu prioridad es el HILO de la conversación actual. Si planteaste un ejercicio (ej. Fotosíntesis), quédate ahí hasta que el alumno entienda.
    2. El PROGRAMA ({state['contexto_programa']}) es solo tu guía de nivel, NO ignores lo que acabas de decir.
    3. Si el alumno dice 'no entiendo', explica el ÚLTIMO concepto mencionado con peras y manzanas.
    4. Usa LaTeX $ $ para fórmulas.
    """
    
    # Enviamos todo el historial para que no tenga amnesia
    response = llm.invoke([SystemMessage(content=sys_prompt)] + state['messages'][:-1] + [HumanMessage(content=content)])
    return {"messages": [response], "contador_pasos": state.get("contador_pasos", 0) + 1}

def examen_node(state: AgentState):
    prompt = f"Genera un ejercicio corto nivel {state['nivel_educativo']} sobre el último tema hablado."
    response = llm.invoke([SystemMessage(content=prompt), HumanMessage(content="¡Examen!")])
    return {"messages": [AIMessage(content=f"🎓 **DESAFÍO ({state['nivel_educativo']}):** {response.content}")]}

def router(state: AgentState):
    if state.get("contador_pasos", 0) >= 6: return "examen" # Subimos a 6 para dar más aire
    return END

workflow = StateGraph(AgentState)
workflow.add_node("tutor", tutor_node)
workflow.add_node("examen", examen_node)
workflow.set_entry_point("tutor")
workflow.add_conditional_edges("tutor", router, {"examen": "examen", END: END})
workflow.add_edge("examen", END)
app = workflow.compile()

# --- 5. INTERFAZ ACTUALIZADA ---
st.title("👨‍🏫 Tutor Agéntico con Memoria")

with st.sidebar:
    st.success("Profesor Conectado")
    
    # 1. BOTONES DE CONTROL (ARRIBA DE TODO)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Reset", help="Borra el chat actual"):
            st.session_state.chat_history = []
            st.session_state.contador = 0
            st.rerun()
    with col2:
        if st.button("🚪 Salir", help="Vuelve a la pantalla de login"):
            st.session_state.autenticado = False
            st.rerun()

    st.divider()
    
    # 2. SELECTOR DE NIVEL
    nivel_edu = st.selectbox(
        "Nivel del Alumno:", 
        ["Primario", "Secundario", "Universidad"], 
        index=1,
        key="nivel_selector"
    )
    
    # 3. BOTÓN DE DESCARGA (Solo si hay mensajes)
    if len(st.session_state.chat_history) > 0:
        chat_text = "--- RESUMEN DE CLASE ---\n\n"
        for m in st.session_state.chat_history:
            autor = "ALUMNO" if isinstance(m, HumanMessage) else "PROFESOR"
            chat_text += f"[{autor}]: {m.content}\n\n"
        
        st.download_button(
            label="📄 Descargar Clase",
            data=chat_text,
            file_name="resumen_clase.txt",
            mime="text/plain",
            key="btn_descarga_final"
        )

    st.divider()
    
    # 4. CARGA DE ARCHIVOS
    pdf_file = st.file_uploader("Programa (PDF)", type="pdf")
    img_file = st.file_uploader("Foto Ejercicio", type=["jpg", "png", "jpeg"])

# --- LÓGICA DE PROCESAMIENTO (FUERA DEL SIDEBAR) ---
contexto = "General"
if pdf_file:
    contexto = "".join([p.extract_text() for p in PdfReader(pdf_file).pages])

img_b64 = None
if img_file:
    img_b64 = base64.b64encode(img_file.read()).decode('utf-8')
    st.sidebar.image(img_file, caption="Imagen cargada")

# --- MOSTRAR CHAT ---
for m in st.session_state.chat_history:
    with st.chat_message("assistant" if isinstance(m, AIMessage) else "user"):
        st.markdown(m.content)

# --- INPUT DEL ALUMNO ---
if prompt := st.chat_input("Escribí acá..."):
    new_user_msg = HumanMessage(content=prompt)
    st.session_state.chat_history.append(new_user_msg)
    with st.chat_message("user"): 
        st.markdown(prompt)

    with st.spinner("Analizando hilo de conversación..."):
        inputs = {
            "messages": st.session_state.chat_history, 
            "contexto_programa": contexto, 
            "imagen_b64": img_b64, 
            "contador_pasos": st.session_state.contador,
            "nivel_educativo": nivel_edu
        }
        
        # Invocamos al grafo (App)
        output = app.invoke(inputs)
        resp_final = output["messages"][-1]
        
        # Guardamos estado y mostramos
        st.session_state.contador = output.get("contador_pasos", 0)
        st.session_state.chat_history.append(resp_final)
        
        with st.chat_message("assistant"): 
            st.markdown(resp_final.content)
        
        st.rerun() # Refrescamos para actualizar el botón de descarga en el sidebar




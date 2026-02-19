import streamlit as st
import os
import base64
import sys
from io import BytesIO
from typing import TypedDict, List
from PIL import Image
from pypdf import PdfReader

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Tutor IA Visión", layout="centered", page_icon="🎓")

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "contador" not in st.session_state:
    st.session_state.contador = 0

# --- 2. LOGIN ---
if not st.session_state.autenticado:
    st.title("🔑 Acceso Tutor")
    key_input = st.text_input("Groq API Key:", type="password").strip()
    if st.button("Ingresar"):
        if key_input.startswith("gsk_"):
            st.session_state.api_key = key_input
            st.session_state.autenticado = True
            st.rerun()
    st.stop()

# --- 3. IA CONFIG ---
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

os.environ["GROQ_API_KEY"] = st.session_state.api_key
llm = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1)

# --- 4. GRAFO ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    contexto: str
    imagen_b64: str
    nivel: str

def tutor_node(state: AgentState):
    # Solo enviamos los últimos 4 mensajes para no saturar la memoria
    history = state['messages'][-4:] 
    
    # Construcción del contenido multimodal
    content = [{"type": "text", "text": history[-1].content}]
    if state.get("imagen_b64"):
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['imagen_b64']}"}})
    
    sys_prompt = f"Eres un tutor de nivel {state['nivel']}. Contexto resumen: {state['contexto'][:2000]}"
    
    # Invocación limpia
    response = llm.invoke([SystemMessage(content=sys_prompt)] + history[:-1] + [HumanMessage(content=content)])
    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("tutor", tutor_node)
workflow.set_entry_point("tutor")
workflow.add_edge("tutor", END)
app = workflow.compile()

# --- 5. UI ---
st.title("👨‍🏫 Tutor Agéntico")

with st.sidebar:
    nivel_edu = st.selectbox("Nivel:", ["Primario", "Secundario", "Universidad"], index=1)
    pdf_file = st.file_uploader("PDF (Programa)", type="pdf")
    img_file = st.file_uploader("Foto (Ejercicio)", type=["jpg", "png", "jpeg"])
    if st.button("🗑️ Reset"):
        st.session_state.chat_history = []
        st.rerun()

# Procesamiento ultra-ligero del PDF
contexto_txt = ""
if pdf_file:
    reader = PdfReader(pdf_file)
    # Solo extraemos las primeras 5 páginas y limitamos caracteres
    for i in range(min(len(reader.pages), 5)):
        contexto_txt += reader.pages[i].extract_text()[:500]
    st.sidebar.success("PDF procesado (resumen)")

img_b64 = None
if img_file:
    img_b64 = base64.b64encode(img_file.read()).decode('utf-8')

# Chat
for m in st.session_state.chat_history:
    with st.chat_message("assistant" if isinstance(m, AIMessage) else "user"):
        st.markdown(m.content)

if prompt := st.chat_input("Escribí acá..."):
    st.session_state.chat_history.append(HumanMessage(content=prompt))
    with st.chat_message("user"): st.markdown(prompt)

    inputs = {
        "messages": st.session_state.chat_history,
        "contexto": contexto_txt,
        "imagen_b64": img_b64,
        "nivel": nivel_edu
    }
    
    with st.spinner("Pensando..."):
        output = app.invoke(inputs)
        resp = output["messages"][-1]
        st.session_state.chat_history.append(resp)
        with st.chat_message("assistant"): st.markdown(resp.content)
        st.rerun()






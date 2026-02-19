import streamlit as st
import os
import base64
import sys
import pandas as pd
import numpy as np
import faiss
from io import BytesIO, StringIO
from typing import TypedDict, List
from PIL import Image
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Tutor Agéntico Pro 2026", layout="wide", page_icon="🎓")

# Evitar errores de codificación en Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Cache del modelo de embeddings (tu motor de búsqueda)
@st.cache_resource
def get_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

embed_model = get_embedding_model()

# --- 2. GESTIÓN DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "index" not in st.session_state:
    st.session_state.index = None
    st.session_state.txt_chunks = []

# --- 3. PANTALLA DE ACCESO ---
if not st.session_state.autenticado:
    st.title("🔑 Acceso al Aula Virtual")
    key_input = st.text_input("Ingresá tu Groq API Key:", type="password").strip()
    if st.button("Ingresar"):
        if key_input.startswith("gsk_"):
            st.session_state.api_key = key_input
            st.session_state.autenticado = True
            st.rerun()
    st.stop()

# --- 4. CONFIGURACIÓN DE IA (LANGGRAPH) ---
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

os.environ["GROQ_API_KEY"] = st.session_state.api_key
# Usamos el modelo VISION para que todo funcione (Fotos + Texto)
llm = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1)

class AgentState(TypedDict):
    messages: List[BaseMessage]
    contexto_rag: str
    imagen_b64: str
    nivel: str

def tutor_node(state: AgentState):
    ultimo_msg = state['messages'][-1].content
    
    # Construcción de contenido para Visión
    content = [{"type": "text", "text": ultimo_msg}]
    if state.get("imagen_b64"):
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['imagen_b64']}"}})
    
    sys_prompt = f"""
    Eres un Tutor Experto nivel {state['nivel']}. 
    CONTEXTO DEL PDF (RAG): {state['contexto_rag']}
    
    REGLAS:
    1. Si hay una imagen, analízala detalladamente.
    2. Usa el contexto del PDF para responder con precisión técnica.
    3. Usa LaTeX $ $ para fórmulas matemáticas.
    """
    
    response = llm.invoke([SystemMessage(content=sys_prompt)] + state['messages'][:-1] + [HumanMessage(content=content)])
    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("tutor", tutor_node)
workflow.set_entry_point("tutor")
workflow.add_edge("tutor", END)
app = workflow.compile()

# --- 5. INTERFAZ Y SIDEBAR ---
st.title("👨‍🏫 Tutor Agéntico Senior (RAG + Vision)")

with st.sidebar:
    st.success("Sesión Activa")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Reset"):
            st.session_state.chat_history = []
            st.session_state.index = None
            st.rerun()
    with col2:
        if st.button("🚪 Salir"):
            st.session_state.autenticado = False
            st.rerun()
    
    nivel_edu = st.selectbox("Nivel Educativo:", ["Primario", "Secundario", "Universidad"], index=1)
    
    st.divider()
    pdf_file = st.file_uploader("Subir PDF (Incluso grandes)", type="pdf")
    img_file = st.file_uploader("Subir Foto de Ejercicio", type=["jpg", "png", "jpeg"])

# Procesamiento RAG (Tus 50 páginas ahora funcionan)
if pdf_file and st.session_state.index is None:
    with st.status("Indexando PDF complejo..."):
        reader = PdfReader(pdf_file)
        chunks = []
        for i, page in enumerate(reader.pages):
            t = page.extract_text()
            if t: chunks.append(f"Pág {i+1}: {t}")
        
        embeddings = embed_model.encode(chunks)
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(np.array(embeddings).astype('float32'))
        
        st.session_state.index = index
        st.session_state.txt_chunks = chunks

# --- 6. CHAT Y LÓGICA DE RESPUESTA ---
for m in st.session_state.chat_history:
    with st.chat_message("assistant" if isinstance(m, AIMessage) else "user"):
        st.markdown(m.content)

if prompt := st.chat_input("Escribí acá..."):
    st.session_state.chat_history.append(HumanMessage(content=prompt))
    with st.chat_message("user"): st.markdown(prompt)

    # Búsqueda semántica (RAG)
    contexto_rag = "No hay info en el PDF."
    if st.session_state.index is not None:
        p_vec = embed_model.encode([prompt])
        _, I = st.session_state.index.search(np.array(p_vec).astype('float32'), k=5)
        contexto_rag = "\n".join([st.session_state.txt_chunks[i] for i in I.flatten() if i != -1])

    # Imagen
    img_b64 = None
    if img_file:
        img_b64 = base64.b64encode(img_file.read()).decode('utf-8')

    with st.spinner("El Tutor está analizando..."):
        inputs = {
            "messages": st.session_state.chat_history,
            "contexto_rag": contexto_rag,
            "imagen_b64": img_b64,
            "nivel": nivel_edu
        }
        output = app.invoke(inputs)
        resp = output["messages"][-1]
        st.session_state.chat_history.append(resp)
        with st.chat_message("assistant"): st.markdown(resp.content)
        st.rerun()

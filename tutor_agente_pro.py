import streamlit as st
import os
import base64
import sys
import pandas as pd
import numpy as np
import faiss
from io import BytesIO
from typing import TypedDict, List
from PIL import Image
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Tutor Agéntico Pro 2026", layout="wide", page_icon="🎓")

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

# --- 4. CONFIGURACIÓN DE IA ---
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

os.environ["GROQ_API_KEY"] = st.session_state.api_key
# Modelo Vision 100% compatible
llm = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1)

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
    
    nivel_edu = st.selectbox("Nivel:", ["Primario", "Secundario", "Universidad"], index=1)
    st.divider()
    pdf_file = st.file_uploader("PDF (Max 15 pág)", type="pdf")
    img_file = st.file_uploader("Foto del ejercicio", type=["jpg", "png", "jpeg"])

# --- 6. PROCESAMIENTO RAG (OPTIMIZADO) ---
if pdf_file and st.session_state.index is None:
    with st.status("Indexando información..."):
        reader = PdfReader(pdf_file)
        chunks = []
        # Leemos solo hasta 15 páginas para no saturar memoria
        for i in range(min(len(reader.pages), 15)):
            t = reader.pages[i].extract_text()
            if t: chunks.append(f"Pág {i+1}: {t}")
        
        if chunks:
            embeddings = embed_model.encode(chunks)
            idx = faiss.IndexFlatL2(embeddings.shape[1])
            idx.add(np.array(embeddings).astype('float32'))
            st.session_state.index = idx
            st.session_state.txt_chunks = chunks
            st.success("✅ PDF indexado con éxito.")

# --- 7. CHAT Y LÓGICA ---
for m in st.session_state.chat_history:
    with st.chat_message("assistant" if isinstance(m, AIMessage) else "user"):
        st.markdown(m.content)

if prompt := st.chat_input("Escribí acá..."):
    st.session_state.chat_history.append(HumanMessage(content=prompt))
    with st.chat_message("user"): st.markdown(prompt)

    # Búsqueda semántica
    contexto_rag = "No hay info cargada."
    if st.session_state.index is not None:
        p_vec = embed_model.encode([prompt])
        _, I = st.session_state.index.search(np.array(p_vec).astype('float32'), k=3)
        contexto_rag = "\n".join([st.session_state.txt_chunks[i] for i in I.flatten() if i != -1])

    # Preparar mensaje multimodal
    content =
    if img_file:
        img_b64 = base64.b64encode(img_file.read()).decode('utf-8')
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
        st.sidebar.image(img_file, caption="Vista previa")

    with st.spinner("Pensando..."):
        sys_msg = SystemMessage(content=f"Eres un tutor nivel {nivel_edu}. Contexto: {contexto_rag[:2000]}")
        user_msg = HumanMessage(content=content)
        
        # Invocamos solo con el contexto necesario para evitar BadRequest
        response = llm.invoke([sys_msg, user_msg])
        
        st.session_state.chat_history.append(response)
        with st.chat_message("assistant"): st.markdown(response.content)
        st.rerun()

import streamlit as st
import os
import base64
from PIL import Image
from pypdf import PdfReader
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Tutor IA Visión", layout="centered", page_icon="🎓")

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

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
os.environ["GROQ_API_KEY"] = st.session_state.api_key
llm = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1)

# --- 4. INTERFAZ ---
st.title("👨‍🏫 Tutor Agéntico Pro")

with st.sidebar:
    st.success("Conectado")
    nivel_edu = st.selectbox("Nivel:", ["Primario", "Secundario", "Universidad"], index=1)
    pdf_file = st.file_uploader("Subir PDF (Programa)", type="pdf")
    img_file = st.file_uploader("Subir Foto (Ejercicio)", type=["jpg", "png", "jpeg"])
    if st.button("🗑️ Reset"):
        st.session_state.chat_history = []
        st.rerun()

# Procesamiento de PDF
contexto_txt = ""
if pdf_file:
    reader = PdfReader(pdf_file)
    paginas = min(len(reader.pages), 10)
    for i in range(paginas):
        texto = reader.pages[i].extract_text()
        if texto: contexto_txt += texto + "\n"
    st.sidebar.info(f"PDF cargado ({paginas} pág.)")

# Imagen a Base64
img_b64 = None
if img_file:
    img_b64 = base64.b64encode(img_file.read()).decode('utf-8')
    st.sidebar.image(img_file, caption="Vista previa")

# Mostrar Chat
for m in st.session_state.chat_history:
    role = "assistant" if isinstance(m, AIMessage) else "user"
    with st.chat_message(role):
        st.markdown(m.content)

# --- 5. LÓGICA DE RESPUESTA ---
if prompt := st.chat_input("Escribí acá..."):
    st.session_state.chat_history.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Pensando..."):
        try:
            # Construcción de la carga útil (Payload)
            if img_b64:
                mensaje_usuario = HumanMessage(content=)
            else:
                mensaje_usuario = HumanMessage(content=prompt)

            instruccion = f"Eres un tutor nivel {nivel_edu}. Contexto: {contexto_txt[:3000]}"
            response = llm.invoke([SystemMessage(content=instruccion), mensaje_usuario])
            
            st.session_state.chat_history.append(response)
            with st.chat_message("assistant"):
                st.markdown(response.content)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")



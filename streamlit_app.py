import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    layout="wide", 
    page_title="NEON GEMINI AI", 
    page_icon="🌌"
)

# --- ZAAWANSOWANY CSS (Cyberpunk & Glassmorphism) ---
st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at top right, #0f0c29, #000000);
        color: #e6edf3;
    }
    
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(0, 212, 255, 0.2) !important;
        border-radius: 20px !important;
        margin-bottom: 15px !important;
    }

    .big-title {
        font-size: 45px !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #00d4ff, #8a2be2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 20px;
    }

    .stButton>button {
        border-radius: 20px;
        border: 1px solid #00d4ff;
        background: rgba(0, 212, 255, 0.1);
        color: #00d4ff;
        transition: 0.3s;
        width: 100%;
    }
    
    .stButton>button:hover {
        background: #00d4ff;
        color: black;
        box-shadow: 0 0 20px #00d4ff;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIKA SYSTEMOWA & SECRETS ---
api_key = st.secrets.get("API_KEY", "")
base_url = st.secrets.get("BASE_URL", "")
selected_model = "gemini-3-flash-preview"

if "messages" not in st.session_state:
    st.session_state.messages = []

def clear_chat():
    st.session_state.messages = []

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🌌 PANEL DOWODZENIA")
    
    tab1, tab2 = st.tabs(["⚙️ Parametry", "📂 Pliki"])
    
    with tab1:
        temp = st.slider("Kreatywność", 0.0, 2.0, 0.7, 0.1)
        sys_prompt = st.text_area("System Prompt", "Jesteś pomocnym asystentem AI z poczuciem humoru.")
        st.subheader("🤖 Wybór silnika")
        # Lista modeli
        available_models = [
            "gemini-3-flash", 
            "gemini-3-flash-preview",
            "gemini-2.5-flash", 
            "gemini-2.5-flash-preview",
            "gemini-2.5-pro",
            "gemini-2-flash"
        ]
        # Wybór modelu przez użytkownika
        selected_model = st.selectbox("Aktywny model:", available_models, index=0)
        
        st.divider()
        temp = st.slider("Kreatywność (Temperature)", 0.0, 2.0, 0.7, 0.1)
        sys_prompt = st.text_area("System Prompt", "Jesteś pomocnym asystentem AI.")
        
    with tab2:
        uploaded_file = st.file_uploader("Dodaj załącznik", type=['txt', 'py', 'md', 'png', 'jpg', 'jpeg', 'csv', 'xlsx'])
        
        file_content_to_send = ""
        image_to_send = None
        file_type = ""

        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            if file_type in ['txt', 'py', 'md']:
                file_content_to_send = uploaded_file.read().decode("utf-8")
                st.info("Plik tekstowy wczytany.")
            elif file_type in ['png', 'jpg', 'jpeg']:
                image_to_send = encode_image(uploaded_file)
                st.image(uploaded_file, use_container_width=True)
                if file_type == 'jpg': file_type = 'jpeg'
            elif file_type in ['csv', 'xlsx']:
                df = pd.read_csv(uploaded_file) if file_type == 'csv' else pd.read_excel(uploaded_file)
                file_content_to_send = f"Dane z tabeli:\n{df.to_string(index=False)}"
                st.success("Tabela załadowana.")

    st.divider()
    if st.button("🗑️ Wyczyść Historię"):
        clear_chat()
        st.rerun()

# --- INTERFEJS GŁÓWNY ---
st.markdown('<h1 class="big-title">GEMINI ULTRA VISION</h1>', unsafe_allow_html=True)

# Wyświetlanie historii
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "💎"):
        st.markdown(msg["content"])

# --- LOGIKA CZATU ---
if prompt := st.chat_input("Zadaj pytanie..."):
    if not api_key:
        st.error("Brak klucza API!")
        st.stop()

    client = OpenAI(api_key=api_key, base_url=base_url)

    # UI: Dodaj pytanie użytkownika
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Przygotowanie promptu z kontekstem
    full_prompt = prompt
    if file_content_to_send:
        full_prompt = f"KONTEKST:\n{file_content_to_send}\n\nPYTANIE: {prompt}"

    # Budowanie listy wiadomości dla API
    messages_to_send = [{"role": "system", "content": sys_prompt}]
    for m in st.session_state.messages[-10:-1]: # Historia
        messages_to_send.append({"role": m["role"], "content": m["content"]})

    if image_to_send:
        messages_to_send.append({
            "role": "user",
            "content": [
                {"type": "text", "text": full_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/{file_type};base64,{image_to_send}"}}
            ]
        })
    else:
        messages_to_send.append({"role": "user", "content": full_prompt})

    # Odpowiedź AI (Streaming)
    with st.chat_message("assistant", avatar="💎"):
        placeholder = st.empty()
        full_response = ""

        try:
            stream = client.chat.completions.create(
                model=selected_model,
                messages=messages_to_send,
                temperature=temp,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"Błąd API: {str(e)}")

st.markdown("""<div style="text-align: center; opacity: 0.3; padding-top: 50px;">NEON ENGINE ACTIVE</div>""", unsafe_allow_html=True)
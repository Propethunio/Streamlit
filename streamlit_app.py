import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from datetime import datetime
from gtts import gTTS
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    layout="wide", 
    page_title="NEON GEMINI AI", 
    page_icon="🌌"
)

# --- ZAAWANSOWANY CSS ---
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
    
    audio {
        filter: invert(100%) hue-rotate(180deg) brightness(1.5);
        height: 40px;
        width: 100%;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIKA SYSTEMOWA & SECRETS ---
api_key = st.secrets.get("API_KEY", "")
base_url = st.secrets.get("BASE_URL", "")
client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

if "messages" not in st.session_state:
    st.session_state.messages = []

def clear_chat():
    st.session_state.messages = []

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def text_to_speech_openai(text):
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text[:4096] # Limit znaków dla OpenAI
        )
        audio_data = response.content
        b64 = base64.b64encode(audio_data).decode()
        return f'<audio controls autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except Exception as e:
        st.error(f"Błąd OpenAI TTS: {e}")
        return None

def text_to_speech_free(text):
    try:
        tts = gTTS(text=text, lang='pl')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        audio_b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio controls autoplay="true"><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio>'
    except Exception as e:
        st.error(f"Błąd Free TTS: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🌌 PANEL DOWODZENIA")
    
    tab1, tab2 = st.tabs(["⚙️ Parametry", "📂 Pliki"])
    
    with tab1:
        temp = st.slider("Kreatywność", 0.0, 2.0, 0.7, 0.1)
        sys_prompt = st.text_area("System Prompt", "Jesteś pomocnym asystentem AI.")
        
        st.subheader("🤖 Silnik LLM")
        available_models = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2-flash"]
        selected_model = st.selectbox("Aktywny model:", available_models)
        
        st.divider()
        st.subheader("🔊 Ustawienia Głosu")
        tts_mode = st.radio("Tryb TTS:", ["Premium (OpenAI)", "Free (gTTS)"])

    with tab2:
        uploaded_file = st.file_uploader("Dodaj załącznik", type=['txt', 'py', 'md', 'png', 'jpg', 'jpeg', 'csv', 'xlsx'])
        file_content_to_send = ""
        image_to_send = None
        file_type = ""

        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            if file_type in ['txt', 'py', 'md']:
                file_content_to_send = uploaded_file.read().decode("utf-8")
            elif file_type in ['png', 'jpg', 'jpeg']:
                image_to_send = encode_image(uploaded_file)
                st.image(uploaded_file, use_container_width=True)
                if file_type == 'jpg': file_type = 'jpeg'
            elif file_type in ['csv', 'xlsx']:
                df = pd.read_csv(uploaded_file) if file_type == 'csv' else pd.read_excel(uploaded_file)
                file_content_to_send = f"Dane z tabeli:\n{df.to_string(index=False)}"

    st.divider()
    
    # --- PRZYCISK TTS (ZAWSZE WIDOCZNY JEŚLI JEST ODPOWIEDŹ) ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.markdown("### 🎙️ Ostatnia odpowiedź")
        if st.button("🔊 Odsłuchaj teraz"):
            last_msg = st.session_state.messages[-1]["content"]
            with st.spinner("Generowanie..."):
                html = text_to_speech_openai(last_msg) if tts_mode == "Premium (OpenAI)" else text_to_speech_free(last_msg)
                if html:
                    st.markdown(html, unsafe_allow_html=True)

    if st.button("🗑️ Wyczyść Historię"):
        clear_chat()
        st.rerun()

# --- INTERFEJS GŁÓWNY ---
st.markdown('<h1 class="big-title">GEMINI ULTRA VISION</h1>', unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "💎"):
        st.markdown(msg["content"])

# --- LOGIKA CZATU ---
if prompt := st.chat_input("Zadaj pytanie..."):
    if not api_key:
        st.error("Brak klucza API!")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Budowanie kontekstu
    messages_to_send = [{"role": "system", "content": sys_prompt}]
    for m in st.session_state.messages[-10:]: # Historia
        messages_to_send.append({"role": m["role"], "content": m["content"]})

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
            st.rerun() # Rerun odświeża sidebar i pokazuje przycisk audio

        except Exception as e:
            st.error(f"Błąd API: {str(e)}")

st.markdown("""<div style="text-align: center; opacity: 0.3; padding-top: 50px;">NEON ENGINE ACTIVE</div>""", unsafe_allow_html=True)
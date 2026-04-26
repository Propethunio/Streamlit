import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from gtts import gTTS
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    layout="wide", 
    page_title="NEON GEMINI AI", 
    page_icon="🌌"
)

# --- ZAAWANSOWANY CSS (Cyberpunk, Glassmorphism & Animations) ---
st.markdown("""
    <style>
    /* Główny motyw */
    .stApp {
        background: radial-gradient(circle at top right, #0f0c29, #000000);
        color: #e6edf3;
    }
    
    /* Neonowe bąbelki czatu */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(0, 212, 255, 0.2) !important;
        border-radius: 20px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
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

    /* Animacja pulsującego robota podczas myślenia */
    @keyframes pulse {
        0% { transform: scale(1); opacity: 0.6; filter: drop-shadow(0 0 2px #00d4ff); }
        50% { transform: scale(1.2); opacity: 1; filter: drop-shadow(0 0 10px #00d4ff); }
        100% { transform: scale(1); opacity: 0.6; filter: drop-shadow(0 0 2px #00d4ff); }
    }
    .thinking-bot {
        font-size: 28px;
        animation: pulse 1.5s infinite;
        display: inline-block;
        margin-bottom: 15px;
        color: #00d4ff;
    }

    /* Stylizacja paska Audio */
    audio {
        filter: invert(100%) hue-rotate(180deg) brightness(1.5) drop-shadow(0 0 5px #00d4ff);
        height: 35px;
        width: 100%;
        border-radius: 20px;
        margin-top: 10px;
    }

    /* Przycisk */
    .stButton>button {
        border-radius: 20px;
        border: 1px solid #00d4ff;
        background: rgba(0, 212, 255, 0.1);
        color: #00d4ff;
        transition: 0.3s;
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
            input=text[:4000]
        )
        audio_data = response.content
        b64 = base64.b64encode(audio_data).decode()
        return f'<audio controls autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except Exception:
        return text_to_speech_free(text)

def text_to_speech_free(text):
    try:
        tts = gTTS(text=text, lang='pl')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        audio_b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio controls autoplay="true"><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio>'
    except Exception as e:
        st.error(f"Błąd TTS: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🌌 PANEL DOWODZENIA")
    tab1, tab2 = st.tabs(["⚙️ Parametry", "📂 Pliki"])
    
    with tab1:
        temp = st.slider("Kreatywność", 0.0, 2.0, 0.7, 0.1)
        sys_prompt = st.text_area("System Prompt", "Jesteś pomocnym asystentem AI.")
        selected_model = st.selectbox("Model:", ["gemini-2-flash", "gemini-2.5-flash", "gemini-3-flash-preview"])
        tts_mode = st.radio("Silnik TTS:", ["Premium (OpenAI)", "Free (gTTS)"])
        
    with tab2:
        uploaded_file = st.file_uploader("Dodaj załącznik", type=['txt', 'py', 'md', 'png', 'jpg', 'jpeg', 'csv', 'xlsx'])
        file_content_to_send = ""
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            if file_type in ['txt', 'py', 'md']:
                file_content_to_send = uploaded_file.read().decode("utf-8")
            elif file_type in ['csv', 'xlsx']:
                df = pd.read_csv(uploaded_file) if file_type == 'csv' else pd.read_excel(uploaded_file)
                file_content_to_send = f"Dane z tabeli:\n{df.to_string(index=False)}"

    if st.button("🗑️ Wyczyść Historię"):
        clear_chat()
        st.rerun()

# --- INTERFEJS GŁÓWNY ---
st.markdown('<h1 class="big-title">GEMINI ULTRA VISION</h1>', unsafe_allow_html=True)

# Wyświetlanie historii (zawsze najpierw)
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "💎"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            if st.button(f"🔊 Odsłuchaj", key=f"btn_{i}"):
                with st.spinner("Generowanie audio..."):
                    html = text_to_speech_openai(msg["content"]) if tts_mode == "Premium (OpenAI)" else text_to_speech_free(msg["content"])
                    if html: st.markdown(html, unsafe_allow_html=True)

# --- LOGIKA CZATU ---
if prompt := st.chat_input("Zadaj pytanie..."):
    if not api_key:
        st.error("Brak klucza API!")
        st.stop()

    # 1. Natychmiastowe dodanie i wyświetlenie wiadomości użytkownika
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Przygotowanie kontekstu
    messages_to_send = [{"role": "system", "content": sys_prompt}]
    if file_content_to_send:
        messages_to_send.append({"role": "user", "content": f"KONTEKST Z PLIKU:\n{file_content_to_send}"})
    
    for m in st.session_state.messages[-10:]:
        messages_to_send.append({"role": m["role"], "content": m["content"]})

    # 2. Odpowiedź AI w czasie rzeczywistym
    with st.chat_message("assistant", avatar="💎"):
        status_placeholder = st.empty()
        # Wyświetlamy animowanego robocika
        status_placeholder.markdown('<div class="thinking-bot">🤖⚡ <i>System przetwarza dane...</i></div>', unsafe_allow_html=True)
        
        response_placeholder = st.empty()
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
                    if full_response == "":
                        status_placeholder.empty() # Robocik znika przy pierwszym słowie
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # Rerun na końcu, żeby pod nową wiadomością pojawił się przycisk "Odsłuchaj"
            st.rerun()

        except Exception as e:
            status_placeholder.empty()
            st.error(f"Błąd API: {str(e)}")

st.markdown("""<div style="text-align: center; opacity: 0.3; padding-top: 50px;">NEON ENGINE ACTIVE</div>""", unsafe_allow_html=True)
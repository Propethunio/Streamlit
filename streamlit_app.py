import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from gtts import gTTS
import io
import PyPDF2
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    layout="wide", 
    page_title="NEON GEMINI AI PRO", 
    page_icon="🌌"
)

# --- ZAAWANSOWANY CSS ---
st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at top right, #0f0c29, #0b0d17, #000000);
        color: #e6edf3;
    }
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(0, 212, 255, 0.15) !important;
        border-radius: 15px !important;
    }
    .big-title {
        font-size: 50px !important;
        font-weight: 900 !important;
        background: linear-gradient(90deg, #00d4ff, #8a2be2, #ff00c8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-top: -40px;
    }
    .token-counter {
        padding: 10px;
        border-radius: 10px;
        background: rgba(0, 212, 255, 0.1);
        border: 1px solid #00d4ff;
        font-family: monospace;
        font-size: 12px;
        color: #00d4ff;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIKA SYSTEMOWA ---
api_key = st.secrets.get("API_KEY", "")
base_url = st.secrets.get("BASE_URL", "https://api.openai.com/v1")
client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

# Inicjalizacja stanów sesji
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0

def clear_chat():
    st.session_state.messages = []
    st.session_state.total_tokens = 0
    st.cache_data.clear()

def estimate_tokens(text):
    # Proste przybliżenie: 1 token ≈ 4 znaki dla angielskiego/polskiego
    return len(text) // 4

def text_to_speech(text, mode):
    try:
        if mode == "Premium (OpenAI)":
            response = client.audio.speech.create(model="tts-1", voice="alloy", input=text[:4000])
            audio_data = response.content
        else:
            tts = gTTS(text=text, lang='pl')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            audio_data = fp.getvalue()
        b64 = base64.b64encode(audio_data).decode()
        return f'<audio controls autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except Exception as e:
        st.error(f"Błąd audio: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color: #00d4ff;'>🌌 SYSTEM CONTROL</h2>", unsafe_allow_html=True)
    
    # --- NOWA SEKCJA: OSOBOWOŚĆ ---
    with st.expander("🎭 OSOBOWOŚĆ AI", expanded=True):
        persona = st.selectbox("Wybierz tryb:", [
            "Asystent (Standard)", 
            "Cyberpunk Hacker", 
            "Ekspert Programowania", 
            "Sarkastyczny Bot",
            "Naukowiec"
        ])
        
        persona_prompts = {
            "Asystent (Standard)": "Jesteś pomocnym asystentem AI.",
            "Cyberpunk Hacker": "Mów jak haker z przyszłości, używaj technicznego slangu, bądź tajemniczy i neonowy.",
            "Ekspert Programowania": "Jesteś genialnym programistą. Odpowiadasz czystym kodem i technicznymi konkretami.",
            "Sarkastyczny Bot": "Jesteś inteligentny, ale bardzo sarkastyczny i nieco znudzony pomaganiem ludziom.",
            "Naukowiec": "Jesteś profesorem nauk ścisłych. Twoje odpowiedzi są bardzo szczegółowe i oparte na faktach."
        }
        sys_prompt = st.text_area("System Prompt (Custom):", persona_prompts[persona])

    with st.expander("🛠️ PARAMETRY SILNIKA"):
        selected_model = st.selectbox("Model:", ["gemini-3-flash-preview", "gemini-2.5-flash-preview", "gemini-2-flash-preview"])
        temp = st.slider("Kreatywność", 0.0, 2.0, 0.7, 0.1)
        tts_mode = st.radio("Silnik TTS:", ["Premium (OpenAI)", "Free (gTTS)"])

    # --- LICZNIK TOKENÓW ---
    st.markdown(f"""
        <div class="token-counter">
            📊 STATYSTYKI SESJI:<br>
            • Szacowane Tokeny: {st.session_state.total_tokens}<br>
            • Koszt szac.: ${(st.session_state.total_tokens/1000000 * 0.15):.5f}
        </div>
    """, unsafe_allow_html=True)

    with st.expander("📂 ZAŁĄCZNIKI"):
        uploaded_file = st.file_uploader("Plik (PDF/IMG/TXT)", type=['txt', 'pdf', 'png', 'jpg', 'jpeg'])
        file_payload = None
        if uploaded_file:
            f_type = uploaded_file.name.split('.')[-1].lower()
            if f_type in ['png', 'jpg', 'jpeg']:
                img_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
                file_payload = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                st.image(uploaded_file, caption="Załadowano obraz")
            elif f_type == 'pdf':
                reader = PyPDF2.PdfReader(uploaded_file)
                text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
                file_payload = {"type": "text", "text": f"DANE Z PLIKU:\n{text}"}

    if st.button("🗑️ RESETUJ WSZYSTKO", use_container_width=True):
        clear_chat()
        st.rerun()

# --- GŁÓWNY INTERFEJS ---
st.markdown('<h1 class="big-title">NEON GEMINI PRO</h1>', unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and st.button(f"🔊 Odsłuchaj", key=f"tts_{i}"):
            html = text_to_speech(msg["content"], tts_mode)
            if html: st.markdown(html, unsafe_allow_html=True)

# --- LOGIKA CZATU ---
if prompt := st.chat_input("Zadaj pytanie..."):
    if not api_key:
        st.error("Brak klucza API!")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.total_tokens += estimate_tokens(prompt)
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Przygotowanie API
    api_messages = [{"role": "system", "content": sys_prompt}]
    for m in st.session_state.messages[-6:]: # Pamięć 6 ostatnich wiadomości
        api_messages.append(m)
    
    # Dodanie kontekstu pliku do ostatniej wiadomości
    if file_payload:
        api_messages[-1] = {"role": "user", "content": [{"type": "text", "text": prompt}, file_payload]}

    with st.chat_message("assistant", avatar="🌌"):
        resp_place = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model=selected_model,
                messages=api_messages,
                temperature=temp,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    resp_place.markdown(full_response + "▌")
            
            resp_place.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.total_tokens += estimate_tokens(full_response)
            st.rerun()
            
        except Exception as e:
            st.error(f"Błąd API: {e}")

st.markdown("""<div style="text-align: center; opacity: 0.2; font-size: 10px; margin-top: 50px;">NEON ENGINE V3.0</div>""", unsafe_allow_html=True)
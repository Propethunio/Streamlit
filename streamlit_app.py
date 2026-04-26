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

# --- ZAAWANSOWANY CSS (Cyberpunk & Glassmorphism) ---
st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at top right, #0f0c29, #0b0d17, #000000);
        color: #e6edf3;
    }
    
    /* Neonowe bąbelki czatu */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(0, 212, 255, 0.15) !important;
        border-radius: 15px !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
        transition: 0.3s ease;
    }
    .stChatMessage:hover {
        border: 1px solid rgba(0, 212, 255, 0.4) !important;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);
    }

    .big-title {
        font-size: 55px !important;
        font-weight: 900 !important;
        background: linear-gradient(90deg, #00d4ff, #8a2be2, #ff00c8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-top: -50px;
        filter: drop-shadow(0 0 10px rgba(0, 212, 255, 0.3));
    }

    @keyframes pulse {
        0% { opacity: 0.5; filter: drop-shadow(0 0 2px #00d4ff); }
        50% { opacity: 1; filter: drop-shadow(0 0 12px #00d4ff); }
        100% { opacity: 0.5; filter: drop-shadow(0 0 2px #00d4ff); }
    }
    .thinking-bot {
        font-size: 20px;
        animation: pulse 1.5s infinite;
        color: #00d4ff;
        padding: 10px;
        border-left: 3px solid #00d4ff;
    }

    /* Przycisk wysyłania */
    button[kind="primary"] {
        background: linear-gradient(45deg, #00d4ff, #8a2be2) !important;
        border: none !important;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0b0d17; }
    ::-webkit-scrollbar-thumb { background: #1f2937; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #00d4ff; }
    </style>
""", unsafe_allow_html=True)

# --- LOGIKA SYSTEMOWA ---
api_key = st.secrets.get("API_KEY", "")
base_url = st.secrets.get("BASE_URL", "https://api.openai.com/v1") # Default fallback
client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

if "messages" not in st.session_state:
    st.session_state.messages = []

def clear_chat():
    st.session_state.messages = []
    st.cache_data.clear()

def encode_image(file):
    return base64.b64encode(file.read()).decode('utf-8')

def text_to_speech(text, mode):
    try:
        if mode == "Premium (OpenAI)":
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text[:4000]
            )
            audio_data = response.content
        else:
            tts = gTTS(text=text, lang='pl')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            audio_data = fp.getvalue()
        
        b64 = base64.b64encode(audio_data).decode()
        return f'<audio controls autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except Exception as e:
        st.error(f"TTS Error: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color: #00d4ff;'>🌌 COMMAND CENTER</h2>", unsafe_allow_html=True)
    
    with st.expander("🛠️ MODEL & PARAMETRY", expanded=True):
        selected_model = st.selectbox("Model Silnika:", 
            ["gemini-2.0-flash", "gpt-4o", "gpt-4-turbo"], index=0)
        temp = st.slider("Kreatywność (Temperature)", 0.0, 2.0, 0.7, 0.1)
        tts_mode = st.radio("Silnik Mowy:", ["Premium (OpenAI)", "Free (gTTS)"])

    with st.expander("📂 ANALIZA DANYCH"):
        uploaded_file = st.file_uploader("Dodaj plik (PDF, IMG, CSV...)", 
            type=['txt', 'py', 'md', 'png', 'jpg', 'jpeg', 'csv', 'xlsx', 'pdf'])
        
        file_payload = None
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            if file_type in ['png', 'jpg', 'jpeg']:
                img_b64 = encode_image(uploaded_file)
                file_payload = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                st.image(uploaded_file, caption="Podgląd obrazu", use_container_width=True)
            elif file_type == 'pdf':
                reader = PyPDF2.PdfReader(uploaded_file)
                text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                file_payload = {"type": "text", "text": f"KONTEKST PDF:\n{text}"}
                st.info("PDF wczytany")
            elif file_type in ['csv', 'xlsx']:
                df = pd.read_csv(uploaded_file) if file_type == 'csv' else pd.read_excel(uploaded_file)
                file_payload = {"type": "text", "text": f"DANE TABELARYCZNE:\n{df.to_string()}"}
                st.dataframe(df.head(5))

    st.markdown("---")
    if st.button("🗑️ WYCZYŚĆ SESJĘ", use_container_width=True):
        clear_chat()
        st.rerun()
    
    # Export Chat
    if st.session_state.messages:
        chat_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
        st.download_button("💾 POBIERZ CZAT", chat_text, file_name=f"chat_{datetime.now().strftime('%H%M')}.txt", use_container_width=True)

# --- INTERFEJS GŁÓWNY ---
st.markdown('<h1 class="big-title">NEON GEMINI AI</h1>', unsafe_allow_html=True)

# Wyświetlanie historii
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button(f"🔊 Graj", key=f"tts_{i}"):
                    html = text_to_speech(msg["content"], tts_mode)
                    if html: st.markdown(html, unsafe_allow_html=True)

# --- CZAT LOGIC ---
if prompt := st.chat_input("Napisz wiadomość do systemu..."):
    if not api_key:
        st.error("Błąd: Skonfiguruj klucz API w secrets!")
        st.stop()

    # Dodaj prompt użytkownika do sesji
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Budowanie wiadomości do API
    api_messages = [{"role": "system", "content": "Jesteś zaawansowanym systemem AI o nazwie NEON GEMINI. Odpowiadasz konkretnie, w nowoczesnym stylu, używając Markdown."}]
    
    # Dodaj plik jeśli istnieje (jako kontekst do ostatniej wiadomości)
    current_user_content = [{"type": "text", "text": prompt}]
    if file_payload:
        current_user_content.append(file_payload)
    
    # Historia (ostatnie 10 wiadomości)
    for m in st.session_state.messages[:-1]:
        api_messages.append(m)
    
    api_messages.append({"role": "user", "content": current_user_content})

    with st.chat_message("assistant", avatar="🌌"):
        status = st.empty()
        status.markdown('<div class="thinking-bot">🌀 SYNCHRONIZACJA NEURONALNA...</div>', unsafe_allow_html=True)
        
        response_place = st.empty()
        full_response = ""

        try:
            stream = client.chat.completions.create(
                model=selected_model,
                messages=api_messages,
                temperature=temp,
                stream=True
            )
            
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    status.empty() # Usuń status przy pierwszej paczce danych
                    response_place.markdown(full_response + " ▌")
            
            response_place.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.rerun()

        except Exception as e:
            status.empty()
            st.error(f"BŁĄD SYSTEMU: {str(e)}")

st.markdown("""<div style="text-align: center; opacity: 0.2; font-size: 10px; letter-spacing: 2px; margin-top: 50px;">CORE VERSION 2.5 | NEON PROTOCOL ACTIVE</div>""", unsafe_allow_html=True)
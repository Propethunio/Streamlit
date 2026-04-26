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
    /* Globalne tło */
    .stApp {
        background: radial-gradient(circle at top right, #1e2a44, #0d1117);
        color: #e6edf3;
    }
    
    /* Efekt szklanej karty dla wiadomości */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 15px !important;
        transition: transform 0.2s ease;
    }
    
    .stChatMessage:hover {
        transform: translateY(-2px);
        border-color: #00d4ff !important;
    }

    /* Pasek boczny */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.8) !important;
        border-right: 1px solid #00d4ff33;
    }

    /* Gradientowy tekst dla nagłówka */
    .big-title {
        font-size: 50px !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #00d4ff, #0055ff, #8a2be2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }

    /* Customowe przyciski */
    .stButton>button {
        border-radius: 12px;
        border: 1px solid #00d4ff;
        background: transparent;
        color: #00d4ff;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background: #00d4ff;
        color: black;
        box-shadow: 0 0 15px #00d4ff;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIKA SYSTEMOWA ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.now().strftime("%H:%M:%S")

def clear_chat():
    st.session_state.messages = []

# --- SIDEBAR (CENTRUM DOWODZENIA) ---
with st.sidebar:
    st.markdown("### 🌌 NEON INTERFACE")
    st.caption(f"Sesja aktywna od: {st.session_state.start_time}")
    
    tab1, tab2 = st.tabs(["⚙️ Ustawienia", "📂 Dane"])
    
    with tab1:
        temp = st.select_slider("Poziom Kreatywności", options=[0.0, 0.5, 0.7, 1.0, 1.5], value=0.7)
        sys_prompt = st.text_area("Persona Systemu", "Jesteś ekspertem technologicznym przyszłości.")
        model_choice = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro"])
        
    with tab2:
        uploaded_file = st.file_uploader("Dodaj załącznik", type=['png', 'jpg', 'csv', 'py', 'pdf'])
        if uploaded_file:
            st.success(f"📎 {uploaded_file.name} gotowy!")

    st.spacer = st.container()
    st.divider()
    if st.button("🗑️ Resetuj Macierz", use_container_width=True):
        clear_chat()
        st.rerun()

# --- INTERFEJS GŁÓWNY ---
st.markdown('<h1 class="big-title">GEMINI NEON</h1>', unsafe_allow_html=True)
st.markdown("---")

# Wyświetlanie czatu z avatarami
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# --- OBSŁUGA WEJŚCIA ---
if prompt := st.chat_input("Napisz polecenie dla AI..."):
    # 1. Dodanie kontekstu pliku (uproszczone dla demo)
    final_prompt = prompt
    if uploaded_file:
        final_prompt = f"[Użytkownik załączył plik: {uploaded_file.name}]\n\n{prompt}"

    # 2. Wyświetlenie wiadomości użytkownika
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # 3. Odpowiedź AI
    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        full_response = ""
        
        # Symulacja klienta (tu użyj swojego klienta OpenAI/Gemini)
        with st.spinner("Przetwarzanie w sieci neuronowej..."):
            # Tutaj wstawiasz swoją logikę API (skróconą dla czytelności przykładu)
            # stream = client.chat.completions.create(...)
            
            # TESTOWE ECHO (do sprawdzenia wyglądu)
            full_response = f"Otrzymałem Twoją wiadomość: '{prompt}'. Jestem gotowy do analizy!"
            placeholder.markdown(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- FOOTER / STATYSTYKI ---
st.markdown("""
    <div style="position: fixed; bottom: 10px; right: 10px; opacity: 0.5; font-size: 10px;">
        NEON_OS v2.4 | Latency: 24ms | Engine: Gemini
    </div>
""", unsafe_allow_html=True)
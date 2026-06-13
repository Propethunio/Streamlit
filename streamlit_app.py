import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from gtts import gTTS
import io
from datetime import datetime

# Importy Twoich dwóch nowych modułów
import docloader
import embedder_rag

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    layout="wide", 
    page_title="NEON GEMINI AI PRO", 
    page_icon="🌌"
)

# --- ZAAWANSOWANY CSS ---
st.markdown("""
    <style>
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .loader {
        border: 3px solid rgba(0, 212, 255, 0.1);
        border-top: 3px solid #00d4ff;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        animation: spin 1s linear infinite;
        display: inline-block;
        margin-right: 10px;
        vertical-align: middle;
    }
    .thinking-box {
        background: rgba(0, 212, 255, 0.05);
        border: 1px solid rgba(0, 212, 255, 0.2);
        padding: 15px;
        border-radius: 10px;
        color: #00d4ff;
        font-family: 'Courier New', monospace;
        margin-bottom: 20px;
    }
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

# Inicjalizacja stanów sesji (RAG oraz Czat)
if "messages" not in st.session_state: st.session_state.messages = []
if "total_tokens" not in st.session_state: st.session_state.total_tokens = 0
if "faiss_index" not in st.session_state: st.session_state.faiss_index = None
if "indexed_files" not in st.session_state: st.session_state.indexed_files = []

def clear_chat():
    st.session_state.messages = []
    st.session_state.total_tokens = 0
    st.cache_data.clear()

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

# Inicjalizacja zmiennych dla załączników jednorazowych, aby uniknąć błędu NameError
file_content_to_send = ""
image_payload = None

# --- SIDEBAR (Panel boczny) ---
with st.sidebar:
    st.markdown("<h2 style='color: #00d4ff;'>🌌 SYSTEM CONTROL</h2>", unsafe_allow_html=True)
    
# Wybór osobowości
    with st.expander("🎭 OSOBOWOŚĆ AI", expanded=True):
        persona = st.selectbox("Wybierz tryb:", [
            "Asystent (Standard)", 
            "Cyberpunk Hacker", 
            "Ekspert Programowania", 
            "Sarkastyczny Bot",
            "Naukowiec",
            "Własna (Custom)"
        ])
        
        persona_prompts = {
            "Asystent (Standard)": "Jesteś pomocnym asystentem AI.",
            "Cyberpunk Hacker": "Mów jak haker z przyszłości, używaj technicznego slangu, bądź tajemniczy i neonowy.",
            "Ekspert Programowania": "Jesteś genialnym programistą. Odpowiadasz czystym kodem i technicznymi konkretami.",
            "Sarkastyczny Bot": "Jesteś inteligentny, ale bardzo sarkastyczny i nieco znudzony pomaganiem ludziom.",
            "Naukowiec": "Jesteś profesorem nauk ścisłych. Twoje odpowiedzi są bardzo szczegółowe i oparte na faktach."
        }
        
        # Warunek: Jeśli użytkownik wybierze "Własna (Custom)"
        if persona == "Własna (Custom)":
            sys_prompt = st.text_area(
                "Wpisz swój własny System Prompt:", 
                value="Jesteś pomocnym asystentem AI. Twoje zadanie to..."
            )
        else:
            # Dla gotowych osobowości przypisujemy prompt w tle i ukrywamy okienko
            sys_prompt = persona_prompts[persona]

    # Parametry modelu
    with st.expander("🛠️ PARAMETRY SILNIKA"):
        selected_model = st.selectbox("Model:", ["gemini-2.5-flash", "gemini-2.0-flash", "gpt-4o"])
        temp = st.slider("Kreatywność", 0.0, 2.0, 0.7, 0.1)
        tts_mode = st.radio("Silnik TTS:", ["Premium (OpenAI)", "Free (gTTS)"])

    # 1. JEDNORAZOWE ZAŁĄCZNIKI (Dla bieżącej wiadomości)
    with st.expander("📂 JEDNORAZOWY ZAŁĄCZNIK"):
        uploaded_file = st.file_uploader("Plik (PDF/IMG/TXT)", type=['txt', 'pdf', 'png', 'jpg', 'jpeg'], key="single_file")
        if uploaded_file:
            f_type = uploaded_file.name.split('.')[-1].lower()
            if f_type in ['png', 'jpg', 'jpeg']:
                img_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
                image_payload = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                st.image(uploaded_file, caption="Załadowano obraz do analizy")
            elif f_type == 'pdf':
                # Używamy Twojego docloader do wyciągnięcia tekstu z pojedynczego PDF
                file_content_to_send = docloader.load_pdf_from_stream(uploaded_file)
                st.caption("✅ Wyciągnięto tekst z pliku PDF")
            elif f_type == 'txt':
                file_content_to_send = uploaded_file.read().decode("utf-8")
                st.caption("✅ Załadowano plik tekstowy")

    # 2. TRWAŁA BAZA WIEDZY RAG (Wyszukiwanie FAISS w wielu plikach na raz)
    with st.expander("📚 TRWAŁA BAZA WIEDZY RAG (MULTI-PDF)"):
        rag_files = st.file_uploader("Wgraj dokumenty PDF do bazy wiedzy", type=['pdf'], accept_multiple_files=True, key="rag_files")
        if rag_files:
            if st.button("🚀 INICJALIZUJ BAZĘ RAG", use_container_width=True):
                with st.spinner("Przetwarzanie dokumentów i budowanie indeksu FAISS..."):
                    documents = []
                    for f in rag_files:
                        # Odczyt tekstu przy użyciu docloader
                        text = docloader.load_pdf_from_stream(f)
                        documents.append({"filename": f.name, "text": text})
                    
                    # Tworzenie bazy wektorowej przy użyciu embedder_rag
                    index_obj = embedder_rag.create_index(documents)
                    if index_obj:
                        st.session_state.faiss_index = index_obj
                        st.session_state.indexed_files = [f.name for f in rag_files]
                        st.success("Baza wiedzy zindeksowana pomyślnie!")
                    else:
                        st.error("Nie udało się przetworzyć tekstu z podanych plików.")
        
        if st.session_state.indexed_files:
            st.write("Aktywne pliki w bazie RAG:")
            for name in st.session_state.indexed_files:
                st.caption(f"• {name}")

    # Przycisk resetu
    if st.button("🗑️ RESETUJ WSZYSTKO", use_container_width=True):
        clear_chat()
        st.session_state.faiss_index = None
        st.session_state.indexed_files = []
        st.rerun()

    # Licznik tokenów
    st.markdown(f"""
        <div class="token-counter">
            📊 STATYSTYKI SESJI:<br>
            • Szacowane Tokeny: {st.session_state.total_tokens}<br>
            • Stan bazy RAG: {"AKTYWNA ✅" if st.session_state.faiss_index else "PUSTA ❌"}
        </div>
    """, unsafe_allow_html=True)

# --- GŁÓWNY INTERFEJS ---
st.markdown('<h1 class="big-title">NEON GEMINI RAG PRO</h1>', unsafe_allow_html=True)

# Wyświetlanie historii czatu
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and st.button(f"🔊 Odsłuchaj", key=f"tts_{i}"):
            html = text_to_speech(msg["content"], tts_mode)
            if html: st.markdown(html, unsafe_allow_html=True)

# --- LOGIKA CZATU Z PEŁNĄ INTEGRACJĄ RAG ORAZ ZAŁĄCZNIKÓW ---
if prompt := st.chat_input("Zadaj pytanie systemowi..."):
    if not api_key:
        st.error("Błąd: Skonfiguruj klucz API!")
        st.stop()

    # Dodanie wiadomości użytkownika do sesji i wyświetlenie jej na ekranie
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Przygotowanie system promptu z panelu bocznego
    current_sys_prompt = sys_prompt if 'sys_prompt' in locals() else "Jesteś pomocnym asystentem."
    messages_to_send = [{"role": "system", "content": current_sys_prompt}]
    
    # Budowa dynamicznej struktury wiadomości użytkownika (tekst + potencjalne załączniki)
    user_content = [{"type": "text", "text": prompt}]
    
    # Jeśli użytkownik dodał jednorazowy plik (TXT/PDF)
    if file_content_to_send:
        user_content.append({"type": "text", "text": f"\n\n[DODATKOWY KONTEKST Z ZAŁĄCZONEGO PLIKU]:\n{file_content_to_send}"})
    
    # Jeśli użytkownik dodał jednorazowy obrazek
    if image_payload:
        user_content.append(image_payload)

    # --- INTEGRACJA PRZESZUKIWANIA BAZY WIEDZY RAG ---
    if st.session_state.faiss_index:
        # Przeszukujemy bazę wektorową za pomocą Twojego skryptu embedder_rag
        matched_chunks = embedder_rag.retrieve_docs(prompt, st.session_state.faiss_index, k=3)
        if matched_chunks:
            rag_context = "\n\n[ISTOTNE INFORMACJE ZNALEZIONE W BAZIE WIEDZY RAG - Wykorzystaj je do odpowiedzi]:\n"
            for chunk in matched_chunks:
                rag_context += f"- (Źródło: {chunk['filename']}): \"{chunk['text']}\"\n"
            user_content.append({"type": "text", "text": rag_context})

    # Ładowanie historii (ostatnie 10 wiadomości) bez aktualnego promptu
    for m in st.session_state.messages[-11:-1]:
        messages_to_send.append(m)
    
    # Dodanie na sam koniec aktualnej wiadomości użytkownika z kompletem danych (Prompt + Załącznik + RAG)
    messages_to_send.append({"role": "user", "content": user_content})

    # Odpowiedź asystenta w trybie Stream z animacją "Thinking"
    with st.chat_message("assistant", avatar="🌌"):
        status_placeholder = st.empty()
        status_placeholder.markdown("""
            <div class="thinking-box">
                <div class="loader"></div>
                <span>PRZETWARZANIE DANYCH (RAG SEMANTIC SEARCH)...</span>
            </div>
        """, unsafe_allow_html=True)
        
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
                    # Ukrywamy animację ładowania w momencie pojawienia się pierwszego słowa
                    if full_response == "":
                        status_placeholder.empty()
                    
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
            # Zapisanie odpowiedzi do historii i aktualizacja licznika tokenów
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.total_tokens += (len(prompt) + len(full_response)) // 4
            st.rerun()

        except Exception as e:
            status_placeholder.empty()
            st.error(f"Wystąpił błąd silnika LLM: {str(e)}")

st.markdown("""<div style="text-align: center; opacity: 0.2; font-size: 10px; margin-top: 50px;">NEON ENGINE V3.5 | MODULAR RAG ACTIVE</div>""", unsafe_allow_html=True)
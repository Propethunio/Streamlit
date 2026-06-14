import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from gtts import gTTS
import io
from datetime import datetime

# Importy Twoich modułów (RAG + Nowe moduły gry RPG)
import docloader
import embedder_rag
import rpg_database
import rpg_visuals

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    layout="wide", 
    page_title="NEON GEMINI AI PRO", 
    page_icon="🌌"
)

# --- ZAAWANSOWANY CSS (Z MODYFIKACJĄ PANELU BOCZNEGO I ZAKŁADEK) ---
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
    
    /* STYLIZACJA ZAKŁADEK (TABS) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(0, 212, 255, 0.1) !important;
        padding: 10px 24px !important;
        border-radius: 8px 8px 0px 0px !important;
        color: #b4c6ef !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 212, 255, 0.08) !important;
        border-color: #00d4ff !important;
        color: #00d4ff !important;
        box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
    }

    /* KARTA STYLIZACJI POSTACI RPG W SIDEBARZE */
    .rpg-card {
        background: rgba(138, 43, 226, 0.06);
        border: 1px solid rgba(138, 43, 226, 0.3);
        padding: 14px;
        border-radius: 10px;
        margin-bottom: 12px;
        font-size: 14px;
        line-height: 1.5;
    }
    
    /* STYLIZACJA PANELU BOCZNEGO */
    [data-testid="stSidebar"] {
        background-color: #080911 !important;
        border-right: 1px solid rgba(0, 212, 255, 0.1) !important;
    }
    [data-testid="stSidebar"] .stExpander {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(0, 212, 255, 0.1) !important;
        border-radius: 10px !important;
        margin-bottom: 12px !important;
    }
    [data-testid="stSidebar"] p {
        color: #b4c6ef !important;
    }
            
    /* FIX KONTRASTU DLA CZERWONEGO PRZYCISKU SYSTEMOWEGO */
    [data-testid="stSidebar"] button[kind="primary"] {
        background-color: #ff2a5f !important;
        border: 1px solid #ff003c !important;
        box-shadow: 0 0 10px rgba(255, 42, 95, 0.2) !important;
    }
    [data-testid="stSidebar"] button[kind="primary"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] button[kind="primary"]:hover {
        background-color: #ff003c !important;
        box-shadow: 0 0 15px rgba(255, 42, 95, 0.5) !important;
    }
    
    /* IDEALNIE RÓWNE I DOPASOWANE SEPARATORY */
    .custom-hr {
        margin-top: 0px !important;
        margin-bottom: 15px !important;
        border: 0;
        border-top: 1px solid rgba(0, 212, 255, 0.15);
    }
    
    .token-counter {
        padding: 12px;
        border-radius: 10px;
        background: rgba(0, 212, 255, 0.04);
        border: 1px solid rgba(0, 212, 255, 0.2);
        font-family: monospace;
        font-size: 12px;
        color: #00d4ff;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIKA SYSTEMOWA ---
api_key = st.secrets.get("API_KEY", "")
base_url = st.secrets.get("BASE_URL", "https://api.openai.com/v1")
client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

# --- INICJALIZACJA STANÓW SESJI ---
if "messages" not in st.session_state: st.session_state.messages = []
if "rpg_messages" not in st.session_state: st.session_state.rpg_messages = []
if "last_rpg_image" not in st.session_state: st.session_state.last_rpg_image = None
if "total_tokens" not in st.session_state: st.session_state.total_tokens = 0
if "faiss_index" not in st.session_state: st.session_state.faiss_index = None
if "indexed_files" not in st.session_state: st.session_state.indexed_files = []
if "sys_prompt" not in st.session_state: st.session_state.sys_prompt = "Jesteś pomocnym asystentem AI."
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

def clear_rag_only():
    """Usuwa wyłącznie bazę wektorową i listę zindeksowanych plików."""
    st.session_state.faiss_index = None
    st.session_state.indexed_files = []

def full_factory_reset():
    """Resetuje parametry aplikacji oraz stany gry RPG do stanu początkowego."""
    st.session_state.messages = []
    st.session_state.rpg_messages = []
    st.session_state.last_rpg_image = None
    st.session_state.total_tokens = 0
    st.session_state.faiss_index = None
    st.session_state.indexed_files = []
    st.session_state.sys_prompt = "Jesteś pomocnym asystentem AI."
    if "custom_prompt_value" in st.session_state:
        del st.session_state["custom_prompt_value"]
    st.session_state.reset_key += 1
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

# --- BŁYSKAWICZNY FRAGMENT DLA OSOBOWOŚCI (BEZ LAGA) ---
@st.fragment
def render_personality_selector():
    persona = st.selectbox("Wybierz tryb (Dla klasycznego chatu):", [
        "Asystent (Standard)", 
        "Cyberpunk Hacker", 
        "Ekspert Programowania", 
        "Sarkastyczny Bot",
        "Naukowiec",
        "Własna (Custom)"
    ], key=f"persona_selector_{st.session_state.reset_key}")
    
    persona_prompts = {
        "Asystent (Standard)": "Jesteś pomocnym asystentem AI.",
        "Cyberpunk Hacker": "Mów jak haker z przyszłości, używaj technicznego slangu, bądź tajemniczy i neonowy.",
        "Ekspert Programowania": "Jesteś genialnym programistą. Odpowiadasz czystym kodem i technicznymi konkretami.",
        "Sarkastyczny Bot": "Jesteś inteligentny, ale bardzo sarkastyczny i nieco znudzony pomaganiem ludziom.",
        "Naukowiec": "Jesteś profesorem nauk ścisłych. Twoje odpowiedzi są bardzo szczegółowe i oparte na faktach."
    }
    
    if persona == "Własna (Custom)":
        default_custom = st.session_state.get("custom_prompt_value", "Jesteś pomocnym asystentem AI. Twoje zadanie to...")
        sys_prompt_input = st.text_area("Wpisz swój własny System Prompt:", value=default_custom, key=f"custom_prompt_{st.session_state.reset_key}")
        st.session_state.sys_prompt = sys_prompt_input
        st.session_state.custom_prompt_value = sys_prompt_input
    else:
        st.session_state.sys_prompt = persona_prompts.get(persona, "Jesteś pomocnym asystentem AI.")

# Inicjalizacja zmiennych dla załączników jednorazowych
file_content_to_send = ""
image_payload = None

# --- SIDEBAR (Panel boczny - Wspólny dla obu modułów) ---
with st.sidebar:
    st.markdown("<h2 style='color: #00d4ff; margin-bottom: 2px; font-weight:800; letter-spacing:2px;'>🌌 SYSTEM CONTROL</h2>", unsafe_allow_html=True)
    
    # KARTA AKTYWNEGO BOHATERA RPG (Zaciągana na żywo z SQLite)
    character = rpg_database.get_character()
    if character:
        st.markdown(f"""
            <div class="rpg-card">
                <b style="color: #ff00c8;">👤 BOHATER:</b> {character['name']}<br>
                <b style="color: #8a2be2;">🎭 KLASA:</b> {character['class']}<br>
                <b style="color: #00d4ff;">❤️ PUNKTY ŻYCIA:</b> {character['hp']}/{character['max_hp']}<br>
                <b style="color: #ffd700;">💰 ZŁOTO:</b> {character['gold']} szt.<br>
                <b style="color: #00ffcc;">📍 LOKACJA:</b> {character['location']}
            </div>
        """, unsafe_allow_html=True)
        
        # Wyświetlanie listy przedmiotów z bazy danych
        items = rpg_database.get_inventory()
        if items:
            with st.expander("🎒 EKWIPUNEK POSTACI", expanded=False):
                for it in items:
                    st.caption(f"• {it['name']} ({it['type']}) x{it['qty']}")

    # Wybór osobowości dla tradycyjnego chatu
    with st.expander("🎭 OSOBOWOŚĆ AI", expanded=False):
        render_personality_selector()

    # Parametry modelu
    with st.expander("🛠️ PARAMETRY SILNIKA"):
        selected_model = st.selectbox("Model:", ["gemini-2.5-flash", "gemini-2.0-flash", "gpt-4o"], key=f"model_{st.session_state.reset_key}")
        temp = st.slider("Kreatywność", 0.0, 2.0, 0.7, 0.1, key=f"temp_{st.session_state.reset_key}")
        tts_mode = st.radio("Silnik TTS:", ["Premium (OpenAI)", "Free (gTTS)"], key=f"tts_{st.session_state.reset_key}")

    # 1. JEDNORAZOWE ZAŁĄCZNIKI (Dla tradycyjnego bota)
    with st.expander("📂 JEDNORAZOWY ZAŁĄCZNIK"):
        uploaded_file = st.file_uploader("Plik (PDF/IMG/TXT)", type=['txt', 'pdf', 'png', 'jpg', 'jpeg'], key=f"single_file_{st.session_state.reset_key}")
        if uploaded_file:
            f_type = uploaded_file.name.split('.')[-1].lower()
            if f_type in ['png', 'jpg', 'jpeg']:
                img_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
                image_payload = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                st.image(uploaded_file, caption="Załadowano obraz do analizy")
            elif f_type == 'pdf':
                file_content_to_send = docloader.load_pdf_from_stream(uploaded_file)
                st.caption("✅ Wyciągnięto tekst z pliku PDF")
            elif f_type == 'txt':
                file_content_to_send = uploaded_file.read().decode("utf-8")
                st.caption("✅ Załadowano plik tekstowy")

    # 2. TRWAŁA BAZA WIEDZY RAG
    with st.expander("📚 TRWAŁA BAZA WIEDZY RAG (MULTI-PDF)"):
        rag_files = st.file_uploader("Wgraj dokumenty PDF do bazy wiedzy", type=['pdf'], accept_multiple_files=True, key=f"rag_files_{st.session_state.reset_key}")
        if rag_files:
            if st.button("🚀 INICJALIZUJ BAZĘ RAG", use_container_width=True):
                with st.spinner("Przetwarzanie dokumentów i budowanie indeksu FAISS..."):
                    documents = []
                    for f in rag_files:
                        text = docloader.load_pdf_from_stream(f)
                        documents.append({"filename": f.name, "text": text})
                    
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

    # --- SEKCJA ZARZĄDZANIA RESETAMI ---
    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)
    
    if st.button("🗑️ WYCZYŚĆ BAZĘ WIEDZY RAG", use_container_width=True):
        clear_rag_only()
        st.success("Baza RAG została wyczyszczona!")
        st.rerun()
        
    if st.button("🚨 CAŁKOWITY RESET SYSTEMU", use_container_width=True, type="primary"):
        full_factory_reset()
        st.rerun()

    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)

    # Licznik tokenów i statystyki
    st.markdown(f"""
        <div class="token-counter">
            📊 STATYSTYKI SESJI:<br>
            • Szacowane Tokeny: {st.session_state.total_tokens}<br>
            • Stan bazy RAG: {"AKTYWNA ✅" if st.session_state.faiss_index else "PUSTA ❌"}
        </div>
    """, unsafe_allow_html=True)

# --- GŁÓWNY INTERFEJS Z PODZIAŁEM NA TABY ---
st.markdown('<h1 class="big-title">NEON GEMINI SYSTEM</h1>', unsafe_allow_html=True)

tab_chat, tab_rpg = st.tabs(["💬 ASYSTENT & RAG CHAT", "🎮 MISTRZ GRY RPG"])

# =====================================================================
# ZAKŁADKA 1: KLASYCZNY CHATBOT (KOD KTÓRY MIAŁEŚ DO TEJ PORY)
# =====================================================================
with tab_chat:
    # Wyświetlanie historii czatu tradycyjnego
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and st.button(f"🔊 Odsłuchaj", key=f"tts_chat_{i}"):
                html = text_to_speech(msg["content"], tts_mode)
                if html: st.markdown(html, unsafe_allow_html=True)

    # Logika wejściowa klasycznego czatu
    if prompt := st.chat_input("Zadaj pytanie asystentowi...", key="chat_input_field"):
        if not api_key:
            st.error("Błąd: Skonfiguruj klucz API!")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        
        current_sys_prompt = st.session_state.get("sys_prompt", "Jesteś pomocnym asystentem AI.")
        messages_to_send = [{"role": "system", "content": current_sys_prompt}]
        user_content = [{"type": "text", "text": prompt}]
        
        if file_content_to_send:
            user_content.append({"type": "text", "text": f"\n\n[DODATKOWY KONTEKST Z ZAŁĄCZONEGO PLIKU]:\n{file_content_to_send}"})
        if image_payload:
            user_content.append(image_payload)

        if st.session_state.faiss_index:
            matched_chunks = embedder_rag.retrieve_docs(prompt, st.session_state.faiss_index, k=3)
            if matched_chunks:
                rag_context = "\n\n[ISTOTNE INFORMACJE ZNALEZIONE W BAZIE WIEDZY RAG]:\n"
                for chunk in matched_chunks:
                    rag_context += f"- (Źródło: {chunk['filename']}): \"{chunk['text']}\"\n"
                user_content.append({"type": "text", "text": rag_context})

        for m in st.session_state.messages[-11:-1]:
            messages_to_send.append(m)
        
        messages_to_send.append({"role": "user", "content": user_content})

        with st.chat_message("assistant", avatar="🌌"):
            status_placeholder = st.empty()
            status_placeholder.markdown('<div class="thinking-box"><div class="loader"></div><span>PRZETWARZANIE DANYCH...</span></div>', unsafe_allow_html=True)
            
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
                        status_placeholder.empty()
                        full_response += chunk.choices[0].delta.content
                        response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.session_state.total_tokens += (len(prompt) + len(full_response)) // 4
                st.rerun()
            except Exception as e:
                status_placeholder.empty()
                st.error(f"Wystąpił błąd silnika LLM: {str(e)}")

# =====================================================================
# ZAKŁADKA 2: NOWA FUNKCJONALNOŚĆ - MISTRZ GRY RPG
# =====================================================================
with tab_rpg:
    st.markdown("<h2 style='color: #8a2be2;'>🧙‍♂️ Cyfrowy Mistrz Gry (RPG Engine)</h2>", unsafe_allow_html=True)
    
    # Jeśli w bazie nie ma aktywnego bohatera, renderujemy ekran tworzenia postaci
    if not character:
        st.info("Brak aktywnego bohatera w bazie danych. Stwórz swoją postać, aby rozpocząć kampanię!")
        c1, c2 = st.columns(2)
        with c1:
            hero_name = st.text_input("Imię Twojej postaci:", value="Kaelen")
        with c2:
            hero_class = st.selectbox("Wybierz archetyp klasy:", ["Netrunner Cyber-Haker", "Zwiadowca Pustkowi", "Technomanta Neonu", "Uliczny Wojownik"])
            
        if st.button("🌌 ROZPOCZNIJ PRZYGODĘ & ZAPISZ W BAZIE", use_container_width=True):
            rpg_database.create_character(hero_name, hero_class)
            st.session_state.rpg_messages = [{"role": "assistant", "content": f"Witaj, {hero_name} ({hero_class}). Budzisz się w mrocznym, skąpanym w deszczu i neonach zaułku sektora 7. W dłoni ściskasz uszkodzony cyber-dek, a z dachu nad Tobą kapie syntetyczny płyn. Słyszysz zbliżające się kroki ciężkich buciorów korporacyjnych strażników. Co robisz?"}]
            st.success("Postać zapisana pomyślnie! Przygoda rozpoczęta.")
            st.rerun()
    else:
        # Wyświetlanie aktualnej sceny graficznej wygenerowanej przez DALL-E 3
        if st.session_state.last_rpg_image:
            st.image(st.session_state.last_rpg_image, caption=f"Aktualna lokacja: {character['location']}", use_container_width=True)

        # Renderowanie historii fabularnej
        for msg in st.session_state.rpg_messages:
            with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🧙‍♂️"):
                st.markdown(msg["content"])

        # Akcja gracza
        if rpg_prompt := st.chat_input("Zadeklaruj swoją akcję mistrzowi gry...", key="rpg_input_field"):
            st.session_state.rpg_messages.append({"role": "user", "content": rpg_prompt})
            
            # Dedykowany prompt systemowy dla Mistrza Gry RPG
            rpg_system_prompt = (
                f"Jesteś profesjonalnym Mistrzem Gry RPG prowadzącym mroczną sesję sci-fi/cyberpunk. "
                f"Gracz steruje postacią o imieniu {character['name']} (Klasa: {character['class']}). "
                "Opisuj barwnie konsekwencje akcji gracza, rozwijaj fabułę i buduj klimat neonowego zagrożenia. "
                "Na końcu każdej wypowiedzi zaproponuj graczowi 3 krótkie, klimatyczne opcje ruchu (np. A, B, C)."
            )
            
            rpg_messages_to_send = [{"role": "system", "content": rpg_system_prompt}]
            for m in st.session_state.rpg_messages:
                rpg_messages_to_send.append(m)

            with st.chat_message("assistant", avatar="🧙‍♂️"):
                status = st.empty()
                status.markdown('<div class="thinking-box"><div class="loader"></div><span>Mistrz Gry kształtuje świat...</span></div>', unsafe_allow_html=True)
                
                response_placeholder = st.empty()
                full_rpg_response = ""
                
                # Stream narracji MG
                stream = client.chat.completions.create(
                    model=selected_model,
                    messages=rpg_messages_to_send,
                    temperature=temp,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        status.empty()
                        full_rpg_response += chunk.choices[0].delta.content
                        response_placeholder.markdown(full_rpg_response + "▌")
                
                response_placeholder.markdown(full_rpg_response)
                st.session_state.rpg_messages.append({"role": "assistant", "content": full_rpg_response})
                
                # AUTOMATYCZNE GENEROWANIE ADEKWATNYCH WIZUALIÓW
                with st.spinner("🖼️ Wizualizowanie lokacji przez DALL-E 3..."):
                    img_url = rpg_visuals.generate_game_scene(client, full_rpg_response)
                    if img_url:
                        st.session_state.last_rpg_image = img_url
                
                # Dynamiczna symulacja i uaktualnienie bazy danych po ruchu
                # Zmniejszamy losowo HP (symulacja zmęczenia/walki) i dodajemy 2 kredyty/złoto
                next_hp = max(5, character['hp'] - 3)
                next_gold = character['gold'] + 2
                rpg_database.update_game_state(next_hp, next_gold, "Sektor Widmo", full_rpg_response[:120])
                
                st.rerun()

st.markdown("""<div style="text-align: center; opacity: 0.2; font-size: 10px; margin-top: 50px;">NEON ENGINE V3.5 | MODULAR RAG ACTIVE</div>""", unsafe_allow_html=True)
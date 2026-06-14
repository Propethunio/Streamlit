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

    /* KARTA STYLIZACJI POSTACI RPG */
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
            
    /* FIX KONTRASTU DLA PRZYCISKÓW DANGER */
    [data-testid="stSidebar"] button[kind="primary"], button[data-testid="baseButton-primary"] {
        background-color: #ff2a5f !important;
        border: 1px solid #ff003c !important;
        box-shadow: 0 0 10px rgba(255, 42, 95, 0.2) !important;
    }
    [data-testid="stSidebar"] button[kind="primary"] p, button[data-testid="baseButton-primary"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
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
if "last_rpg_image" not in st.session_state: st.session_state.last_rpg_image = None
if "total_tokens" not in st.session_state: st.session_state.total_tokens = 0
if "faiss_index" not in st.session_state: st.session_state.faiss_index = None
if "indexed_files" not in st.session_state: st.session_state.indexed_files = []
if "sys_prompt" not in st.session_state: st.session_state.sys_prompt = "Jesteś pomocnym asystentem AI."
if "reset_key" not in st.session_state: st.session_state.reset_key = 0

# --- INICJALIZACJA I TRWAŁE ZACIĄGANIE HISTORII RPG Z BAZY ---
if "rpg_messages" not in st.session_state:
    saved_history = rpg_database.get_chat_history()
    if saved_history:
        st.session_state.rpg_messages = saved_history
    else:
        st.session_state.rpg_messages = []

def clear_rag_only():
    st.session_state.faiss_index = None
    st.session_state.indexed_files = []

def full_factory_reset():
    st.session_state.messages = []
    st.session_state.rpg_messages = []
    rpg_database.clear_all_rpg_data()  # Czyści także kompletnie bazę SQLite
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

@st.fragment
def render_personality_selector():
    persona = st.selectbox("Wybierz tryb (Dla klasycznego chatu):", [
        "Asystent (Standard)", "Cyberpunk Hacker", "Ekspert Programowania", "Sarkastyczny Bot", "Naukowiec", "Własna (Custom)"
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

# Załączniki jednorazowe
file_content_to_send = ""
image_payload = None

# --- GLOBALNY PANEL BOCZNY (TYLKO STATYSTYKI OGÓLNE I STEROWANIE SILNIKIEM) ---
with st.sidebar:
    st.markdown("<h2 style='color: #00d4ff; margin-bottom: 2px; font-weight:800; letter-spacing:2px;'>🌌 SYSTEM CONTROL</h2>", unsafe_allow_html=True)
    
    with st.expander("🛠️ PARAMETRY SILNIKA MODELU", expanded=True):
        selected_model = st.selectbox("Model globalny:", ["gemini-2.5-flash", "gemini-2.0-flash", "gpt-4o"], key=f"model_{st.session_state.reset_key}")
        temp = st.slider("Kreatywność (Temperature)", 0.0, 2.0, 0.7, 0.1, key=f"temp_{st.session_state.reset_key}")
        tts_mode = st.radio("Silnik lektora TTS:", ["Premium (OpenAI)", "Free (gTTS)"], key=f"tts_{st.session_state.reset_key}")

    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)
    if st.button("🚨 GŁÓWNY RESET APLIKACJI", use_container_width=True, type="primary"):
        full_factory_reset()
        st.rerun()

    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="token-counter">
            📊 MONITOR SESJI:<br>
            • Zużyte tokeny (szacunkowo): {st.session_state.total_tokens}<br>
            • Baza RAG: {"AKTYWNA ✅" if st.session_state.faiss_index else "PUSTA ❌"}
        </div>
    """, unsafe_allow_html=True)

# --- INTERFEJS GŁÓWNY Z DYNAMICZNYM PODZIAŁEM MODUŁOWYM ---
st.markdown('<h1 class="big-title">NEON GEMINI ADVANCED</h1>', unsafe_allow_html=True)

tab_chat, tab_rpg = st.tabs(["💬 MODUŁ ASYSTENTA & RAG CHAT", "🎮 MODUŁ MISTRZA GRY RPG"])

# =====================================================================
# ZAKŁADKA 1: DEDYKOWANY ASYSTENT + OZNACZONY PANEL CHATU
# =====================================================================
with tab_chat:
    c_left, c_right = st.columns([3, 1])
    
    with c_right:
        st.markdown("<h4 style='color: #00d4ff;'>🛠️ USTAWIENIA CHATU</h4>", unsafe_allow_html=True)
        render_personality_selector()
        
        with st.expander("📂 ZAŁĄCZNIK WIDOCZNY W CZACIE"):
            uploaded_file = st.file_uploader("Plik (PDF/IMG/TXT)", type=['txt', 'pdf', 'png', 'jpg', 'jpeg'], key=f"single_file_{st.session_state.reset_key}")
            if uploaded_file:
                f_type = uploaded_file.name.split('.')[-1].lower()
                if f_type in ['png', 'jpg', 'jpeg']:
                    img_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
                    image_payload = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    st.image(uploaded_file, caption="Załadowano obrazek")
                elif f_type == 'pdf':
                    file_content_to_send = docloader.load_pdf_from_stream(uploaded_file)
                    st.caption("✅ Wyciągnięto tekst z PDF")
                elif f_type == 'txt':
                    file_content_to_send = uploaded_file.read().decode("utf-8")
                    st.caption("✅ Załadowano tekst")

        with st.expander("📚 INTEGRACJA Z BAZĄ RAG"):
            rag_files = st.file_uploader("Wgraj dokumenty RAG (PDF)", type=['pdf'], accept_multiple_files=True, key=f"rag_files_{st.session_state.reset_key}")
            if rag_files and st.button("🚀 INICJALIZUJ RAG", use_container_width=True):
                with st.spinner("Indeksowanie..."):
                    documents = [{"filename": f.name, "text": docloader.load_pdf_from_stream(f)} for f in rag_files]
                    index_obj = embedder_rag.create_index(documents)
                    if index_obj:
                        st.session_state.faiss_index = index_obj
                        st.session_state.indexed_files = [f.name for f in rag_files]
                        st.success("Zindeksowano bazę RAG!")
            if st.session_state.indexed_files:
                st.write("Aktywne pliki:")
                for name in st.session_state.indexed_files: st.caption(f"• {name}")
            if st.button("🗑️ WYCZYŚĆ RAG", use_container_width=True):
                clear_rag_only()
                st.rerun()

    with c_left:
        # Wyświetlanie historii czatu tradycyjnego
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🌌"):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and st.button(f"🔊 Odsłuchaj", key=f"tts_chat_{i}"):
                    html = text_to_speech(msg["content"], tts_mode)
                    if html: st.markdown(html, unsafe_allow_html=True)

        if prompt := st.chat_input("Zadaj pytanie asystentowi...", key="chat_input_field"):
            if not api_key: st.error("Skonfiguruj klucz API!"); st.stop()

            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"): st.markdown(prompt)

            current_sys_prompt = st.session_state.get("sys_prompt", "Jesteś pomocnym asystentem AI.")
            messages_to_send = [{"role": "system", "content": current_sys_prompt}]
            user_content = [{"type": "text", "text": prompt}]
            
            if file_content_to_send:
                user_content.append({"type": "text", "text": f"\n\n[ZAŁĄCZNIK]:\n{file_content_to_send}"})
            if image_payload:
                user_content.append(image_payload)

            if st.session_state.faiss_index:
                matched_chunks = embedder_rag.retrieve_docs(prompt, st.session_state.faiss_index, k=3)
                if matched_chunks:
                    rag_context = "\n\n[KONTEKST RAG]:\n" + "\n".join([f"- {c['filename']}: {c['text']}" for c in matched_chunks])
                    user_content.append({"type": "text", "text": rag_context})

            for m in st.session_state.messages[-11:-1]: messages_to_send.append(m)
            messages_to_send.append({"role": "user", "content": user_content})

            with st.chat_message("assistant", avatar="🌌"):
                status = st.empty()
                status.markdown('<div class="thinking-box"><div class="loader"></div><span>PRZETWARZANIE...</span></div>', unsafe_allow_html=True)
                resp_placeholder = st.empty(); full_response = ""

                try:
                    stream = client.chat.completions.create(model=selected_model, messages=messages_to_send, temperature=temp, stream=True)
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            status.empty()
                            full_response += chunk.choices[0].delta.content
                            resp_placeholder.markdown(full_response + "▌")
                    resp_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.session_state.total_tokens += (len(prompt) + len(full_response)) // 4
                    st.rerun()
                except Exception as e:
                    status.empty(); st.error(f"Błąd LLM: {str(e)}")

# =====================================================================
# ZAKŁADKA 2: SEKCJA RPG Z TRWAŁĄ PAMIĘCIĄ I LOKALNYM RESETEM
# =====================================================================
with tab_rpg:
    c_game, c_stats = st.columns([3, 1])
    character = rpg_database.get_character()

    with c_stats:
        st.markdown("<h4 style='color: #8a2be2;'>👤 STATUS BOHATERA</h4>", unsafe_allow_html=True)
        if character:
            st.markdown(f"""
                <div class="rpg-card">
                    <b style="color: #ff00c8;">👤 BOHATER:</b> {character['name']}<br>
                    <b style="color: #8a2be2;">🎭 KLASA:</b> {character['class']}<br>
                    <b style="color: #00d4ff;">❤️ ŻYCIE:</b> {character['hp']}/{character['max_hp']}<br>
                    <b style="color: #ffd700;">💰 KREDYTY:</b> {character['gold']}<br>
                    <b style="color: #00ffcc;">📍 LOKACJA:</b> {character['location']}
                </div>
            """, unsafe_allow_html=True)
            
            items = rpg_database.get_inventory()
            if items:
                with st.expander("🎒 EKWIPUNEK POSTACI", expanded=True):
                    for it in items: st.caption(f"• {it['name']} ({it['type']}) x{it['qty']}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ RESETM POSTACI (ZACZNIJ OD NOWA)", use_container_width=True, type="primary"):
                rpg_database.clear_all_rpg_data()
                st.session_state.rpg_messages = []
                st.session_state.last_rpg_image = None
                st.success("Wyczyszczono kartę bohatera!")
                st.rerun()
        else:
            st.caption("Brak aktywnego bohatera w bazie danych.")

    with c_game:
        st.markdown("<h2 style='color: #8a2be2; margin-top:-10px;'>🧙‍♂️ Cyfrowy Mistrz Gry RPG</h2>", unsafe_allow_html=True)
        
        if not character:
            st.info("Brak aktywnego bohatera. Stwórz swoją postać, aby zapisać stan gry w bazie danych!")
            col1, col2 = st.columns(2)
            with col1: hero_name = st.text_input("Imię postaci:", value="Kaelen")
            with col2: hero_class = st.selectbox("Archetyp:", ["Netrunner Cyber-Haker", "Zwiadowca Pustkowi", "Technomanta Neonu", "Uliczny Wojownik"])
                
            if st.button("🌌 UTWÓRZ BOHATERA & ROZPOCZNIJ", use_container_width=True):
                rpg_database.create_character(hero_name, hero_class)
                initial_text = f"Witaj, {hero_name} ({hero_class}). Budzisz się w mrocznym, skąpanym w deszczu zaułku sektora 7. W dłoni ściskasz uszkodzony cyber-dek. Słyszysz zbliżające się kroki strażników korporacji. Co robisz?"
                
                # Zapisujemy początkową wiadomość do bazy danych
                rpg_database.save_chat_message("assistant", initial_text)
                st.session_state.rpg_messages = rpg_database.get_chat_history()
                st.success("Postać utworzona!")
                st.rerun()
        else:
            if st.session_state.last_rpg_image:
                st.image(st.session_state.last_rpg_image, caption=f"Aktualne otoczenie: {character['location']}", use_container_width=True)

            # Wyświetlanie trwałej historii kampanii z bazy
            for msg in st.session_state.rpg_messages:
                with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🧙‍♂️"):
                    st.markdown(msg["content"])

            if rpg_prompt := st.chat_input("Zadeklaruj swoją akcję mistrzowi gry...", key="rpg_input_field"):
                # Zapisz akcję gracza do bazy danych
                rpg_database.save_chat_message("user", rpg_prompt)
                st.session_state.rpg_messages = rpg_database.get_chat_history()
                st.rerun()

            # Reakcja bota na ostatni ruch gracza (jeśli ostatnia wiadomość w bazie należy do użytkownika)
            if st.session_state.rpg_messages and st.session_state.rpg_messages[-1]["role"] == "user":
                rpg_system_prompt = (
                    f"Jesteś profesjonalnym Mistrzem Gry RPG prowadzącym sesję cyberpunk. "
                    f"Gracz steruje postacią {character['name']} ({character['class']}). "
                    "Opisuj konsekwencje akcji gracza, rozwijaj fabułę i buduj klimat zagrożenia. "
                    "Na końcu wypowiedzi zaproponuj 3 krótkie opcje wyboru (A, B, C)."
                )
                
                rpg_messages_to_send = [{"role": "system", "content": rpg_system_prompt}]
                for m in st.session_state.rpg_messages:
                    rpg_messages_to_send.append({"role": m["role"], "content": m["content"]})

                with st.chat_message("assistant", avatar="🧙‍♂️"):
                    status = st.empty()
                    status.markdown('<div class="thinking-box"><div class="loader"></div><span>Mistrz Gry modyfikuje kontinuum...</span></div>', unsafe_allow_html=True)
                    resp_p = st.empty(); full_rpg_response = ""
                    
                    try:
                        stream = client.chat.completions.create(model=selected_model, messages=rpg_messages_to_send, temperature=temp, stream=True)
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                status.empty()
                                full_rpg_response += chunk.choices[0].delta.content
                                resp_p.markdown(full_rpg_response + "▌")
                        resp_p.markdown(full_rpg_response)
                        
                        # Zapis odpowiedzi Mistrza Gry do bazy
                        rpg_database.save_chat_message("assistant", full_rpg_response)
                        
                        with st.spinner("🖼️ Generowanie grafiki otoczenia..."):
                            img_url = rpg_visuals.generate_game_scene(client, full_rpg_response)
                            if img_url: st.session_state.last_rpg_image = img_url
                        
                        # Modyfikacja stanu statystyk w SQLite na podstawie tury
                        next_hp = max(10, character['hp'] - 2)
                        next_gold = character['gold'] + 3
                        rpg_database.update_game_state(next_hp, next_gold, "Neonowy Dystrykt", full_rpg_response[:120])
                        
                        st.session_state.rpg_messages = rpg_database.get_chat_history()
                        st.rerun()
                    except Exception as e:
                        status.empty(); st.error(f"Błąd sesji RPG: {str(e)}")

st.markdown("""<div style="text-align: center; opacity: 0.2; font-size: 10px; margin-top: 50px;">NEON ENGINE V3.5 | TRWAŁA INTEGRACJA SQLITE ACTIVE</div>""", unsafe_allow_html=True)
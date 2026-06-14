import base64
import io

import streamlit as st
from gtts import gTTS
from openai import OpenAI

import rpg_database
from chat_tab import render_chat_tab, render_sidebar_chat
from rpg_tab import render_rpg_tab, render_sidebar_rpg
from styles import NEON_CSS

# --- KONFIGURACJA STRONY ---
st.set_page_config(layout="wide", page_title="NEON GEMINI AI PRO", page_icon="🌌")
st.markdown(NEON_CSS, unsafe_allow_html=True)

# --- KLIENT API ---
api_key = st.secrets.get("API_KEY", "")
base_url = st.secrets.get("BASE_URL", "https://api.openai.com/v1")
client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

# --- INICJALIZACJA SESSION STATE ---
_DEFAULTS = {
    "messages": [],
    "last_rpg_image": None,
    "total_tokens": 0,
    "faiss_index": None,
    "indexed_files": [],
    "sys_prompt": "Jesteś pomocnym asystentem AI.",
    "reset_key": 0,
}
for _key, _val in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

if "rpg_messages" not in st.session_state:
    history = rpg_database.get_chat_history()
    st.session_state.rpg_messages = history or []

MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-exp-1206",
    "gemini-3-flash",
]


# --- FUNKCJE POMOCNICZE ---

def text_to_speech(text, mode):
    try:
        if mode == "Premium (OpenAI)" and client:
            resp = client.audio.speech.create(model="tts-1", voice="alloy", input=text[:4000])
            audio_data = resp.content
        else:
            fp = io.BytesIO()
            gTTS(text=text, lang="pl").write_to_fp(fp)
            audio_data = fp.getvalue()
        b64 = base64.b64encode(audio_data).decode()
        return f'<audio controls autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except Exception as e:
        st.error(f"Błąd audio: {e}")
        return None


def full_factory_reset():
    st.session_state.messages = []
    st.session_state.rpg_messages = []
    st.session_state.last_rpg_image = None
    st.session_state.total_tokens = 0
    st.session_state.faiss_index = None
    st.session_state.indexed_files = []
    st.session_state.sys_prompt = "Jesteś pomocnym asystentem AI."
    st.session_state.pop("custom_prompt_value", None)
    st.session_state.reset_key += 1
    rpg_database.clear_all_rpg_data()
    st.cache_data.clear()


# --- SIDEBAR ---
with st.sidebar:
    st.markdown(
        "<h2 style='color: #00d4ff; margin-bottom: 2px; font-weight:800; letter-spacing:2px;'>🌌 NEON INTERFACE</h2>",
        unsafe_allow_html=True,
    )
    app_mode = st.radio(
        "WYBIERZ AKTYWNY MODUŁ SYSTEMU:",
        ["💬 ASYSTENT & RAG CHAT", "🎮 MISTRZ GRY RPG"],
        key="navigation_mode",
    )
    st.markdown('<hr class="custom-hr" style="margin-top:5px !important;">', unsafe_allow_html=True)

    file_content, image_payload = "", None
    if app_mode == "💬 ASYSTENT & RAG CHAT":
        file_content, image_payload = render_sidebar_chat(st.session_state.reset_key)
    else:
        render_sidebar_rpg()

    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)
    st.markdown("<h5 style='color: #b4c6ef;'>⚙️ PARAMETRY SILNIKA</h5>", unsafe_allow_html=True)
    selected_model = st.selectbox("Model językowy:", MODELS, key=f"model_{st.session_state.reset_key}")
    temp = st.slider("Kreatywność (Temp)", 0.0, 2.0, 0.7, 0.1, key=f"temp_{st.session_state.reset_key}")
    tts_mode = st.radio("Silnik audio TTS:", ["Premium (OpenAI)", "Free (gTTS)"], key=f"tts_{st.session_state.reset_key}")
    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)

    if st.button("🚨 GŁÓWNY WIPE CAŁEJ APKI", use_container_width=True):
        full_factory_reset()
        st.rerun()

    st.markdown(
        f'<div class="token-counter" style="margin-top: 10px;">📊 SESJA: {st.session_state.total_tokens} tokenów</div>',
        unsafe_allow_html=True,
    )

# --- MAIN ---
st.markdown('<h1 class="big-title">NEON GEMINI ADVANCED</h1>', unsafe_allow_html=True)

if app_mode == "💬 ASYSTENT & RAG CHAT":
    render_chat_tab(client, selected_model, temp, tts_mode, file_content, image_payload, text_to_speech)
else:
    render_rpg_tab(client, selected_model, temp, tts_mode, text_to_speech)

st.markdown(
    '<div style="text-align: center; opacity: 0.2; font-size: 10px; margin-top: 50px;">'
    "NEON ENGINE V3.8 | LLM DYNAMIC FUNCTION CALLING INTERFACE"
    "</div>",
    unsafe_allow_html=True,
)

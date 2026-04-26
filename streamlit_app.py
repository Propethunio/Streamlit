import streamlit as st
from openai import OpenAI
import base64
import pandas as pd
from io import StringIO

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    layout="wide", 
    page_title="Gemini Ultra Vision", 
    page_icon="🚀"
)

# --- CUSTOM CSS (Dla lepszego wyglądu) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white;
    }
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .stChatInput {
        border-radius: 25px;
    }
    .sidebar .sidebar-content {
        background: rgba(255, 255, 255, 0.05);
    }
    h1 {
        text-shadow: 2px 2px 4px #000000;
        background: -webkit-linear-gradient(#eee, #333);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    </style>
""", unsafe_allow_html=True)

# --- INICJALIZACJA KLIENTA I SESSION STATE ---
api_key = st.secrets.get("API_KEY", "")
base_url = st.secrets.get("BASE_URL", "")
selected_model = "gemini-1.5-flash" # Zmieniłem na nowszą wersję, jeśli dostępna

if "messages" not in st.session_state:
    st.session_state.messages = []
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "Jesteś pomocnym asystentem AI z poczuciem humoru. Odpowiadasz konkretnie i kreatywnie."

# --- FUNKCJE POMOCNICZE ---
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def clear_chat():
    st.session_state.messages = []

# --- SIDEBAR (CENTRUM DOWODZENIA) ---
with st.sidebar:
    st.title("🚀 Panel Sterowania")
    st.divider()

    # Ustawienia AI
    st.subheader("⚙️ Parametry Modelu")
    temp = st.slider("Kreatywność (Temperature)", 0.0, 2.0, 0.7, 0.1)
    sys_prompt = st.text_area("Osobowość AI (System Prompt)", value=st.session_state.system_prompt)

    st.divider()

    # Obsługa plików
    st.subheader("📁 Prześlij dane")
    uploaded_file = st.file_uploader(
        "Obrazy, kody lub arkusze", 
        type=['txt', 'py', 'md', 'png', 'jpg', 'jpeg', 'csv', 'xlsx']
    )

    file_content_to_send = ""
    image_to_send = None
    file_type = ""

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()

        # Pliki Tekstowe / Kod
        if file_type in ['txt', 'py', 'md']:
            file_content_to_send = uploaded_file.read().decode("utf-8")
            st.info(f"Wczytano kod: {uploaded_file.name}")

        # Obrazy
        elif file_type in ['png', 'jpg', 'jpeg']:
            image_to_send = encode_image(uploaded_file)
            st.image(uploaded_file, caption="Podgląd obrazu", use_container_width=True)
            if file_type == 'jpg': file_type = 'jpeg'

        # Arkusze (CSV/Excel)
        elif file_type in ['csv', 'xlsx']:
            try:
                df = pd.read_csv(uploaded_file) if file_type == 'csv' else pd.read_excel(uploaded_file)
                st.dataframe(df.head(5), use_container_width=True)
                file_content_to_send = f"Oto dane z tabeli:\n{df.to_string(index=False)}"
                st.success("Dane załadowane do kontekstu!")
            except Exception as e:
                st.error(f"Błąd ładowania tabeli: {e}")

    st.divider()
    if st.button("🗑️ Wyczyść historię", on_click=clear_chat, use_container_width=True):
        st.rerun()

# --- GŁÓWNY INTERFEJS ---
st.title("💎 Gemini Ultra Vision")
st.caption("Nowoczesny chatbot z obsługą obrazu, kodu i danych")

# Wyświetlanie historii
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- LOGIKA CZATU ---
if prompt := st.chat_input("Zadaj pytanie..."):
    if not api_key:
        st.error("Brak klucza API! Skonfiguruj secrets.")
        st.stop()

    client = OpenAI(api_key=api_key, base_url=base_url)

    # Dodanie wiadomości użytkownika do UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Przygotowanie promptu (System Prompt + Kontekst Pliku)
    full_prompt = prompt
    if file_content_to_send:
        full_prompt = f"KONTEKST PLIKU:\n{file_content_to_send}\n\nPYTANIE: {prompt}"

    # Budowanie wiadomości dla API
    messages_to_send = [{"role": "system", "content": sys_prompt}]

    # Dodajemy historię (ograniczoną do ostatnich 10 wiadomości dla oszczędności)
    for m in st.session_state.messages[-10:-1]:
        messages_to_send.append({"role": m["role"], "content": m["content"]})

    # Obecna wiadomość (z obsługą obrazu lub bez)
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

    # Odpowiedź AI (Streaming!)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            with st.status("🚀 Gemini analizuje...", expanded=False) as status:
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
                status.update(label="Analiza zakończona!", state="complete", expanded=False)

            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"Błąd: {str(e)}")

# Stopka
st.markdown("---")
st.caption("Powered by Gemini 1.5 & Streamlit | Kreatywność bez granic.")
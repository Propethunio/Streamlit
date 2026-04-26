import streamlit as st
from openai import OpenAI
import os
import base64

st.set_page_config(layout="wide", page_title="Gemini chatbot app")
st.title("Gemini chatbot app")

# Pobieranie kluczy z secrets
api_key = st.secrets["API_KEY"]
base_url = st.secrets["BASE_URL"]
selected_model = "gemini-3-flash-preview"

# Funkcja pomocnicza do kodowania obrazu do formatu Base64
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# --- PASEK BOCZNY (FILE UPLOADER) ---
with st.sidebar:
    st.header("Dodatki")
    # Dodano formaty obrazów do uploadera
    uploaded_file = st.file_uploader(
        "Wgraj plik (tekst lub obraz)", 
        type=['txt', 'py', 'md', 'png', 'jpg', 'jpeg']
    )

    file_context = ""
    base64_image = None
    file_type = ""

    if uploaded_file is not None:
        # Pobieranie rozszerzenia pliku
        file_type = uploaded_file.name.split('.')[-1].lower()

        # Obsługa plików tekstowych
        if file_type in ['txt', 'py', 'md']:
            file_context = uploaded_file.read().decode("utf-8")
            st.success("Plik tekstowy wgrany pomyślnie!")
            with st.expander("Podgląd pliku"):
                st.text(file_context[:500] + "...") # Pokazuje pierwsze 500 znaków
        
        # Obsługa plików graficznych
        elif file_type in ['png', 'jpg', 'jpeg']:
            base64_image = encode_image(uploaded_file)
            st.success("Obraz wgrany pomyślnie!")
            with st.expander("Podgląd obrazu"):
                st.image(uploaded_file)
            
            # Poprawka formatu mime (jpg -> jpeg)
            if file_type == 'jpg':
                file_type = 'jpeg'

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

# Wyświetlanie historii czatu
for msg in st.session_state.messages:
    # Upewniamy się, że wyświetlamy tylko tekst, a nie ewentualne skomplikowane struktury JSON z obrazami
    if isinstance(msg["content"], str):
        st.chat_message(msg["role"]).write(msg["content"])

# --- OBSŁUGA CZATU ---
if prompt := st.chat_input():
    if not api_key:
        st.info("Invalid API key.")
        st.stop()

    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    # Zapisujemy w sesji czysty prompt użytkownika, aby historia UI była czytelna
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Budujemy treść zapytania (payload) do API
    if base64_image:
        # Format "Vision" dla modeli wielomodalnych
        api_content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{file_type};base64,{base64_image}"
                }
            }
        ]
    elif file_context:
        # Tradycyjny format tekstowy z wstrzykniętym plikiem
        api_content = f"Oto zawartość pliku:\n---\n{file_context}\n---\nPytanie użytkownika: {prompt}"
    else:
        # Zwykłe pytanie tekstowe
        api_content = prompt

    # Tworzymy ostateczną listę wiadomości do wysłania
    # Zamieniamy 'content' w ostatniej (obecnej) wiadomości na ten przygotowany wyżej
    messages_to_send = st.session_state.messages[:-1] + [{"role": "user", "content": api_content}]

    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages_to_send
        )

        msg = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant").write(msg)

    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
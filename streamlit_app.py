import streamlit as st
from openai import OpenAI
import os

st.set_page_config(layout="wide", page_title="Gemini chatbot app")
st.title("Gemini chatbot app")

# Pobieranie kluczy z secrets
api_key = st.secrets["API_KEY"]
base_url = st.secrets["BASE_URL"]
selected_model = "gemini-3-flash-preview"

# --- PASEK BOCZNY (FILE UPLOADER) ---
with st.sidebar:
    st.header("Dodatki")
    uploaded_file = st.file_uploader("Wgraj plik tekstowy (.txt, .py, .md)", type=['txt', 'py', 'md'])

    file_context = ""
    if uploaded_file is not None:
        # Odczytanie zawartości pliku
        file_context = uploaded_file.read().decode("utf-8")
        st.success("Plik wgrany pomyślnie!")
        with st.expander("Podgląd pliku"):
            st.text(file_context[:500] + "...") # Pokazuje pierwsze 500 znaków

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

# Wyświetlanie historii czatu
for msg in st.session_state.messages:
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

    # Jeśli plik jest wgrany, doklejamy jego treść do zapytania użytkownika
    full_prompt = prompt
    if file_context:
        full_prompt = f"Oto zawartość pliku:\n---\n{file_context}\n---\nPytańie użytkownika: {prompt}"

    # Dodajemy do sesji oryginalny prompt użytkownika (żeby w UI nie było widać całej treści pliku)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Przygotowujemy wiadomości do wysłania (z wstrzykniętym kontekstem pliku w ostatniej wiadomości)
    messages_to_send = st.session_state.messages[:-1] + [{"role": "user", "content": full_prompt}]

    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages_to_send
        )

        msg = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant").write(msg)

    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")
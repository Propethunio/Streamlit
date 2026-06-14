import base64
import streamlit as st
import docloader
import embedder_rag
from styles import THINKING_BOX_HTML

PERSONA_PROMPTS = {
    "Asystent (Standard)": "Jesteś pomocnym asystentem AI.",
    "Cyberpunk Hacker": "Mów jak haker z przyszłości, używaj technicznego slangu, bądź tajemniczy i neonowy.",
    "Ekspert Programowania": "Jesteś genialnym programistą. Odpowiadasz czystym kodem i technicznymi konkretami.",
    "Sarkastyczny Bot": "Jesteś inteligentny, ale bardzo sarkastyczny i nieco znudzony pomaganiem ludziom.",
    "Naukowiec": "Jesteś profesor nauk ścisłych. Twoje odpowiedzi są bardzo szczegółowe i oparte na faktach.",
}


@st.fragment
def _render_personality_selector(reset_key):
    options = list(PERSONA_PROMPTS.keys()) + ["Własna (Custom)"]
    persona = st.selectbox("Osobowość asystenta:", options, key=f"persona_selector_{reset_key}")
    if persona == "Własna (Custom)":
        default = st.session_state.get("custom_prompt_value", "Jesteś pomocnym asystentem AI. Twoje zadanie to...")
        val = st.text_area("Wpisz swój System Prompt:", value=default, key=f"custom_prompt_{reset_key}")
        st.session_state.sys_prompt = val
        st.session_state.custom_prompt_value = val
    else:
        st.session_state.sys_prompt = PERSONA_PROMPTS[persona]


def render_sidebar_chat(reset_key):
    """Renderuje ustawienia chatu w sidebarze. Zwraca (file_content, image_payload)."""
    st.markdown("<h4 style='color: #00d4ff; margin-top:-5px;'>🛠️ USTAWIENIA CHATU</h4>", unsafe_allow_html=True)
    _render_personality_selector(reset_key)

    file_content = ""
    image_payload = None

    with st.expander("📂 JEDNORAZOWY ZAŁĄCZNIK"):
        uploaded_file = st.file_uploader(
            "Plik (PDF/IMG/TXT)",
            type=["txt", "pdf", "png", "jpg", "jpeg"],
            key=f"single_file_{reset_key}",
        )
        if uploaded_file:
            ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
            if ext in ("png", "jpg", "jpeg"):
                img_b64 = base64.b64encode(uploaded_file.read()).decode("utf-8")
                image_payload = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                st.image(uploaded_file, caption="Wczytany obraz")
            elif ext == "pdf":
                file_content = docloader.load_pdf_from_stream(uploaded_file)
                st.caption("✅ Wyodrębniono tekst z PDF")
            elif ext == "txt":
                file_content = uploaded_file.read().decode("utf-8")
                st.caption("✅ Załadowano tekst pliku")

    with st.expander("📚 TRWAŁA BAZA WIEDZY RAG"):
        rag_files = st.file_uploader(
            "Wgraj dokumenty RAG (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            key=f"rag_files_{reset_key}",
        )
        if rag_files and st.button("🚀 BUDUJ INDEKS RAG", use_container_width=True):
            with st.spinner("Budowanie bazy..."):
                documents = [{"filename": f.name, "text": docloader.load_pdf_from_stream(f)} for f in rag_files]
                index_obj = embedder_rag.create_index(documents)
                if index_obj:
                    st.session_state.faiss_index = index_obj
                    st.session_state.indexed_files = [f.name for f in rag_files]
                    st.success("Zindeksowano dokumenty!")

        if st.session_state.indexed_files:
            st.write("Aktywne pliki:")
            for name in st.session_state.indexed_files:
                st.caption(f"• {name}")
            if st.button("🗑️ USUŃ BAZĘ RAG", use_container_width=True):
                st.session_state.faiss_index = None
                st.session_state.indexed_files = []
                st.rerun()

    return file_content, image_payload


def render_chat_tab(client, model, temp, tts_mode, file_content, image_payload, text_to_speech_fn):
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌌"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and st.button("🔊 Odsłuchaj", key=f"tts_chat_{i}"):
                html = text_to_speech_fn(msg["content"], tts_mode)
                if html:
                    st.markdown(html, unsafe_allow_html=True)

    if prompt := st.chat_input("Zadaj pytanie asystentowi...", key="chat_input_field"):
        if not client:
            st.error("Brak klucza API!")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        sys_prompt = st.session_state.get("sys_prompt", "Jesteś pomocnym asystentem AI.")
        messages = [{"role": "system", "content": sys_prompt}]

        user_content = [{"type": "text", "text": prompt}]
        if file_content:
            user_content.append({"type": "text", "text": f"\n\n[ZAŁĄCZNIK]:\n{file_content}"})
        if image_payload:
            user_content.append(image_payload)

        if st.session_state.faiss_index:
            chunks = embedder_rag.retrieve_docs(prompt, st.session_state.faiss_index, k=3)
            if chunks:
                rag_ctx = "\n\n[DANE RAG]:\n" + "\n".join(f"- {c['filename']}: {c['text']}" for c in chunks)
                user_content.append({"type": "text", "text": rag_ctx})

        # Ostatnie 10 wiadomości jako kontekst historii (bez właśnie dodanej wiadomości użytkownika)
        for m in st.session_state.messages[-11:-1]:
            messages.append(m)
        messages.append({"role": "user", "content": user_content})

        with st.chat_message("assistant", avatar="🌌"):
            status = st.empty()
            status.markdown(THINKING_BOX_HTML.format(message="PRZETWARZANIE..."), unsafe_allow_html=True)
            resp_placeholder = st.empty()
            full_response = ""
            try:
                stream = client.chat.completions.create(
                    model=model, messages=messages, temperature=temp, stream=True
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        status.empty()
                        full_response += delta
                        resp_placeholder.markdown(full_response + "▌")
                resp_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.session_state.total_tokens += (len(prompt) + len(full_response)) // 4
                st.rerun()
            except Exception as e:
                status.empty()
                st.error(f"Błąd: {e}")

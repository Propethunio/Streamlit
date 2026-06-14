import re
import streamlit as st
import rpg_database
import rpg_visuals
from rpg_engine import build_rpg_system_prompt, call_rpg_ai, RPG_INITIAL_SCENE
from styles import THINKING_BOX_HTML


def render_sidebar_rpg():
    st.markdown("<h4 style='color: #8a2be2; margin-top:-5px;'>👤 STATUS POSTACI RPG</h4>", unsafe_allow_html=True)
    character = rpg_database.get_character()
    if not character:
        st.info("Brak bohatera. Stwórz go na głównym ekranie.")
        return

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
        with st.expander("🎒 EKWIPUNEK BOHATERA", expanded=True):
            for it in items:
                st.caption(f"• {it['name']} ({it['type']}) x{it['qty']}")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ ZRESETUJ POSTAĆ & GRĘ", use_container_width=True, type="primary"):
        rpg_database.clear_all_rpg_data()
        st.session_state.rpg_messages = []
        st.session_state.last_rpg_image = None
        st.success("Gra wyczyszczona!")
        st.rerun()


def _extract_options(text):
    """Wyciąga opcje A)/B)/C) z tekstu MG. Zwraca (czysty_tekst, lista_opcji)."""
    found = re.findall(r"(?m)^([A-C])\)\s*(.+)$", text)
    if not found:
        return text, []
    options = [opt[1].strip() for opt in found]
    clean = re.sub(r"(?m)^[A-C]\)\s*.+$", "", text).strip()
    return clean, options


def _process_active_action(client, model, temp):
    """Obsługuje akcję gracza: zapis do bazy, wywołanie AI, zapis odpowiedzi, generacja obrazu."""
    action = st.session_state.pop("active_rpg_action")
    rpg_database.save_chat_message("user", action)
    st.session_state.rpg_messages = rpg_database.get_chat_history()

    character = rpg_database.get_character()
    inv_list = [f"{i['name']} (x{i['qty']})" for i in rpg_database.get_inventory()]
    system_prompt = build_rpg_system_prompt(character, inv_list)

    # Ostatnie 4 wiadomości jako kontekst (żeby nie przekroczyć limitu tokenów przy długich sesjach)
    messages = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.rpg_messages[-4:]:
        messages.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant", avatar="🧙‍♂️"):
        status = st.empty()
        status.markdown(
            THINKING_BOX_HTML.format(message="Mistrz Gry przetwarza akcję i oblicza modyfikatory..."),
            unsafe_allow_html=True,
        )
        try:
            full_response = call_rpg_ai(client, model, temp, messages)
            status.empty()

            rpg_database.save_chat_message("assistant", full_response)

            with st.spinner("🖼️ Generowanie rzutu izometrycznego lokacji..."):
                img_url = rpg_visuals.generate_game_scene(None, full_response)
                if img_url:
                    st.session_state.last_rpg_image = img_url

            st.session_state.rpg_messages = rpg_database.get_chat_history()

        except Exception as e:
            status.empty()
            st.error(f"Błąd pętli decyzyjnej MG: {e}")


def _render_character_creation():
    st.info("Brak aktywnego bohatera. Stwórz postać, aby rozpocząć permanentną kampanię.")
    col1, col2 = st.columns(2)
    with col1:
        hero_name = st.text_input("Imię bohatera:", value="Kaelen")
    with col2:
        hero_class = st.selectbox(
            "Wybierz klasę postaci:",
            ["Netrunner Cyber-Haker", "Zwiadowca Pustkowi", "Technomanta Neonu", "Uliczny Wojownik"],
        )
    if st.button("🌌 ZAPISZ POSTAĆ W BAZIE I STWÓRZ ŚWIAT", use_container_width=True):
        rpg_database.create_character(hero_name, hero_class)
        initial_text = RPG_INITIAL_SCENE.format(name=hero_name, char_class=hero_class)
        rpg_database.save_chat_message("assistant", initial_text)
        st.session_state.rpg_messages = rpg_database.get_chat_history()
        st.success("Kampania zainicjalizowana pomyślnie!")
        st.rerun()


def render_rpg_tab(client, model, temp, tts_mode, text_to_speech_fn):
    character = rpg_database.get_character()

    if not character:
        _render_character_creation()
        return

    # Faza 0: przetwarzanie akcji przed renderowaniem (zapobiega skakaniu UI)
    if st.session_state.get("active_rpg_action"):
        _process_active_action(client, model, temp)

    # Faza 1: obraz bieżącej lokacji
    character = rpg_database.get_character()
    if st.session_state.last_rpg_image:
        st.image(
            st.session_state.last_rpg_image,
            caption=f"Bieżąca lokacja: {character['location']}",
            use_container_width=True,
        )

    # Faza 2: wyciąganie opcji z ostatniej wiadomości MG
    messages = st.session_state.rpg_messages
    clean_last_reply = None
    options = []

    if messages and messages[-1]["role"] == "assistant":
        clean_last_reply, options = _extract_options(messages[-1]["content"])

    # Faza 3: historia chatu
    for i, msg in enumerate(messages):
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🧙‍♂️"):
            is_last_assistant = msg["role"] == "assistant" and i == len(messages) - 1
            display_content = clean_last_reply if (is_last_assistant and clean_last_reply is not None) else msg["content"]
            st.markdown(display_content)
            if msg["role"] == "assistant" and st.button("🔊 Odsłuchaj", key=f"tts_rpg_{i}"):
                html = text_to_speech_fn(display_content, tts_mode)
                if html:
                    st.markdown(html, unsafe_allow_html=True)

    # Faza 4: przyciski akcji lub wolny input
    st.markdown("<br>", unsafe_allow_html=True)
    if len(options) >= 2:
        st.write("### 🧭 Wybierz swoje działanie:")
        cols = st.columns(len(options))
        for idx, option_text in enumerate(options):
            with cols[idx]:
                if st.button(
                    option_text,
                    use_container_width=True,
                    type="primary" if idx == 0 else "secondary",
                    key=f"rpg_btn_{idx}_{len(messages)}",
                ):
                    st.session_state.active_rpg_action = option_text
                    st.rerun()
    else:
        if free_prompt := st.chat_input("Mistrz Gry nie dał gotowych opcji. Co robisz?", key="rpg_input_field"):
            st.session_state.active_rpg_action = free_prompt
            st.rerun()

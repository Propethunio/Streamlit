import re
import streamlit as st
import streamlit.components.v1 as components
import rpg_database
from rpg_engine import build_rpg_system_prompt, call_rpg_ai, RPG_INITIAL_SCENE
from styles import THINKING_BOX_HTML, SCROLL_TO_BOTTOM_JS


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
    """
    Wyciąga opcje A)/B)/C) z KOŃCA tekstu MG.
    Skanuje od ostatniej linii w górę — wszystko przed pierwszą linią opcji to narracja.
    Dzięki temu 'A)' w środku tekstu fabularnego nie jest mylnie traktowane jako opcja.
    Zwraca (tekst_narracji, lista_opcji).
    """
    if not text:
        return "", []

    lines = text.split("\n")
    option_map = {}      # litera → treść opcji
    first_option_idx = len(lines)

    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        m = re.match(r"^([A-C])\)\s*(.+)", stripped)
        if m:
            option_map[m.group(1)] = m.group(2).strip()
            first_option_idx = i
        elif stripped == "" and option_map:
            # pusta linia tuż przed blokiem opcji — pomijamy
            continue
        elif option_map:
            # napotkaliśmy normalny tekst — koniec bloku opcji
            break

    if len(option_map) < 2:
        # Za mało opcji — zwracamy cały tekst bez zmian
        return text, []

    story = "\n".join(lines[:first_option_idx]).strip()
    options = [option_map[k] for k in sorted(option_map.keys())]
    return story, options


def _scroll():
    components.html(SCROLL_TO_BOTTOM_JS, height=1)


def _process_active_action(client, model, temp):
    """
    Przetwarza akcję gracza i wyświetla postęp inline (jak zakładka chat):
    1. Zapisuje akcję do bazy
    2. Wywołuje AI — podczas oczekiwania widoczny jest thinking box
    3. Wyświetla czystą odpowiedź (bez opcji A/B/C) w bańce asystenta
    4. Zapisuje odpowiedź do bazy i wyzwala rerun
    """
    action = st.session_state.pop("active_rpg_action")
    rpg_database.save_chat_message("user", action)

    character = rpg_database.get_character()
    inv_list = [f"{i['name']} (x{i['qty']})" for i in rpg_database.get_inventory()]
    system_prompt = build_rpg_system_prompt(character, inv_list)

    history = rpg_database.get_chat_history()
    send_messages = [{"role": "system", "content": system_prompt}]
    for m in history[-4:]:
        send_messages.append({"role": m["role"], "content": m["content"]})

    full_response = None

    with st.chat_message("assistant", avatar="🧙‍♂️"):
        status = st.empty()
        status.markdown(
            THINKING_BOX_HTML.format(message="Mistrz Gry oblicza los twojej decyzji..."),
            unsafe_allow_html=True,
        )
        try:
            full_response = call_rpg_ai(client, model, temp, send_messages)
            status.empty()
            clean_response, _ = _extract_options(full_response)
            # Fallback: jeśli parsowanie wyczyściło cały tekst, pokaż surową odpowiedź
            st.markdown(clean_response if clean_response else full_response)
        except Exception as e:
            status.empty()
            st.error(f"Błąd AI Mistrza Gry: {e}")
            return

    rpg_database.save_chat_message("assistant", full_response)
    st.session_state.total_tokens += (len(action) + len(full_response)) // 4
    st.session_state.rpg_messages = rpg_database.get_chat_history()
    st.rerun()


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


def render_rpg_tab(client, model, temp, text_to_speech_fn):
    character = rpg_database.get_character()

    if not character:
        _render_character_creation()
        return

    # Faza 1: wyciąganie opcji z ostatniej wiadomości MG
    messages = st.session_state.rpg_messages
    clean_last_reply = None
    options = []

    if messages and messages[-1]["role"] == "assistant":
        clean_last_reply, options = _extract_options(messages[-1]["content"])

    # Faza 2: historia chatu — opcje A/B/C usuwane ze WSZYSTKICH wiadomości asystenta
    for i, msg in enumerate(messages):
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🧙‍♂️"):
            if msg["role"] == "assistant":
                is_last = i == len(messages) - 1
                if is_last and clean_last_reply is not None:
                    # Ostatnia wiadomość: użyj już obliczonego clean_last_reply
                    parsed = clean_last_reply
                else:
                    # Starsze wiadomości: parsuj w locie
                    parsed, _ = _extract_options(msg["content"])
                # Fallback: jeśli parsowanie zostawiło pusty tekst, pokaż surową wiadomość
                display_content = parsed if parsed else msg["content"]
            else:
                display_content = msg["content"]

            st.markdown(display_content)
            if msg["role"] == "assistant" and st.button("🔊 Odsłuchaj", key=f"tts_rpg_{i}"):
                html = text_to_speech_fn(display_content)
                if html:
                    st.markdown(html, unsafe_allow_html=True)

    # Faza 3: akcja gracza lub przetwarzanie oczekującej akcji
    st.markdown("<br>", unsafe_allow_html=True)

    pending_action = st.session_state.get("active_rpg_action")

    if pending_action:
        # Pokaż wiadomość gracza od razu, potem przetwarzaj inline (bez ślepego rerunu)
        with st.chat_message("user", avatar="👤"):
            st.markdown(pending_action)
        _process_active_action(client, model, temp)

    elif len(options) >= 2:
        st.write("### 🧭 Wybierz swoje działanie:")
        cols = st.columns(len(options))
        for idx, option_text in enumerate(options):
            with cols[idx]:
                if st.button(option_text, use_container_width=True, key=f"rpg_btn_{idx}_{len(messages)}"):
                    st.session_state.active_rpg_action = option_text
                    st.rerun()

    else:
        if free_prompt := st.chat_input("Mistrz Gry nie dał gotowych opcji. Co robisz?", key="rpg_input_field"):
            st.session_state.active_rpg_action = free_prompt
            st.rerun()

    # Scroll do dołu — działa zarówno po przełączeniu na zakładkę jak i po nowej wiadomości
    _scroll()

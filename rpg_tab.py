import re
import streamlit as st
import streamlit.components.v1 as components
import rpg_database
import docloader
from rpg_engine import build_rpg_system_prompt, call_rpg_ai, generate_opening_scene
from game_lore import GAME_CODEX, DEFAULT_LORE_NAME, load_default_lore_pdf_bytes
from styles import THINKING_BOX_HTML, SCROLL_TO_BOTTOM_JS


@st.dialog("📖 Kodeks Świata", width="large")
def _show_codex_dialog():
    st.caption(f"Aktywny świat: {st.session_state.get('rpg_lore_name', DEFAULT_LORE_NAME)}")
    st.markdown(st.session_state.get("rpg_lore_text", GAME_CODEX))


def _render_codex_controls():
    """Panel kodeksu: podgląd, pobranie wzorcowego PDF, podmiana świata na własny PDF."""
    with st.expander("📖 KODEKS ŚWIATA", expanded=True):
        st.caption(f"Aktywny świat: **{st.session_state.get('rpg_lore_name', DEFAULT_LORE_NAME)}**")

        if st.button("👁️ Podejrzyj kodeks", use_container_width=True, key="rpg_codex_view"):
            _show_codex_dialog()

        pdf_bytes = st.session_state.get("rpg_lore_pdf")
        if pdf_bytes:
            st.download_button(
                "⬇️ Pobierz PDF kodeksu",
                data=pdf_bytes,
                file_name="kodeks_swiata.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="rpg_codex_dl",
            )

        custom = st.file_uploader("Wgraj własny świat (PDF):", type=["pdf"], key="rpg_lore_upload")
        if custom is not None:
            marker = getattr(custom, "file_id", None) or f"{custom.name}:{custom.size}"
            if marker != st.session_state.get("rpg_lore_file_id"):
                try:
                    text = docloader.load_pdf_from_stream(custom)
                except Exception as e:
                    st.error(f"Nie udało się wczytać PDF: {e}")
                    text = ""
                if text.strip():
                    st.session_state.rpg_lore_text = text.strip()
                    st.session_state.rpg_lore_name = custom.name
                    st.session_state.rpg_lore_pdf = custom.getvalue()
                    st.session_state.rpg_lore_file_id = marker
                    st.success("Świat podmieniony! Mistrz Gry użyje nowego kodeksu.")
                    st.rerun()
                else:
                    st.warning("Ten PDF nie zawiera czytelnego tekstu.")

        if st.session_state.get("rpg_lore_name", DEFAULT_LORE_NAME) != DEFAULT_LORE_NAME:
            if st.button("♻️ Przywróć domyślny świat", use_container_width=True, key="rpg_lore_reset"):
                st.session_state.rpg_lore_text = GAME_CODEX
                st.session_state.rpg_lore_name = DEFAULT_LORE_NAME
                st.session_state.rpg_lore_pdf = load_default_lore_pdf_bytes()
                st.session_state.pop("rpg_lore_file_id", None)
                st.session_state.pop("rpg_lore_upload", None)  # wyczyść widget uploadera
                st.rerun()


def render_sidebar_rpg():
    st.markdown("<h4 style='color: #8a2be2; margin-top:-5px;'>👤 STATUS POSTACI RPG</h4>", unsafe_allow_html=True)

    _render_codex_controls()

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
    Wyciąga ostatni ciągły blok opcji A)/B)/C) z tekstu MG.
    Narracja = tekst PRZED blokiem + tekst PO bloku (Gemini czasem daje opcje na początku).
    Obsługuje formaty: "A) tekst", "**A)** tekst", "**A) tekst**".
    """
    if not text:
        return "", []

    lines = text.split("\n")
    # Obsługuje opcjonalne ** przed/po literze i nawiasie
    _OPT = re.compile(r"^\*{0,2}([A-C])\)\*{0,2}\s*(.+)")

    option_map = {}
    first_option_idx = len(lines)
    last_option_idx = -1

    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        m = _OPT.match(stripped)
        if m:
            letter = m.group(1)
            content = re.sub(r"\*+$", "", m.group(2)).strip()
            option_map[letter] = content
            first_option_idx = i
            if last_option_idx == -1:
                last_option_idx = i
        elif stripped == "" and option_map:
            continue
        elif option_map:
            break

    if len(option_map) < 2:
        return text, []

    # Narracja = to co PRZED blokiem opcji + to co PO bloku opcji
    before = "\n".join(lines[:first_option_idx]).rstrip()
    after = "\n".join(lines[last_option_idx + 1:]).lstrip()
    if before and after:
        story = before + "\n\n" + after
    else:
        story = (before + after).strip()

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
    lore_text = st.session_state.get("rpg_lore_text", GAME_CODEX)
    system_prompt = build_rpg_system_prompt(character, inv_list, lore_text)

    history = rpg_database.get_chat_history()
    send_messages = [{"role": "system", "content": system_prompt}]
    for m in history[-8:]:
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
            if not full_response:
                st.error("Mistrz Gry zwrócił pustą odpowiedź. Spróbuj ponownie.")
                return
            story, _ = _extract_options(full_response)
            st.markdown(story if story else full_response)
        except Exception as e:
            status.empty()
            st.error(f"Błąd AI Mistrza Gry: {e}")
            return

    rpg_database.save_chat_message("assistant", full_response)
    st.session_state.total_tokens += (len(action) + len(full_response)) // 4
    st.session_state.rpg_messages = rpg_database.get_chat_history()
    st.rerun()


def _render_character_creation(client, model, temp):
    lore_text = st.session_state.get("rpg_lore_text", GAME_CODEX)
    st.info("Brak aktywnego bohatera. Stwórz postać, aby rozpocząć kampanię w aktywnym świecie.")
    col1, col2 = st.columns(2)
    with col1:
        hero_name = st.text_input("Imię bohatera:", placeholder="np. Marek, Kaelen, Zara...")
    with col2:
        hero_class = st.text_input(
            "Klasa / rola postaci:",
            placeholder="np. Legionista, Haker, Czarownica, Kupiec...",
        )
    st.caption(f"Aktywny świat: **{st.session_state.get('rpg_lore_name', DEFAULT_LORE_NAME)}** — klasa powinna pasować do jego realiów.")

    if st.button("🌌 ZAPISZ POSTAĆ I ROZPOCZNIJ PRZYGODĘ", use_container_width=True):
        if not hero_name.strip():
            st.warning("Podaj imię bohatera.")
            return
        if not hero_class.strip():
            st.warning("Podaj klasę / rolę postaci.")
            return

        rpg_database.create_character(hero_name.strip(), hero_class.strip())
        character = rpg_database.get_character()

        with st.spinner("Mistrz Gry kreuje świat i otwiera przygodę..."):
            try:
                opening = generate_opening_scene(client, model, temp, character, lore_text)
            except Exception as e:
                st.error(f"Błąd generowania sceny otwierającej: {e}")
                return

        if not opening:
            st.error("Mistrz Gry zwrócił pustą scenę. Spróbuj ponownie.")
            return

        rpg_database.save_chat_message("assistant", opening)
        st.session_state.rpg_messages = rpg_database.get_chat_history()
        st.rerun()


def render_rpg_tab(client, model, temp, text_to_speech_fn):
    character = rpg_database.get_character()

    if not character:
        _render_character_creation(client, model, temp)
        return

    # Faza 1: wyciąganie opcji z ostatniej wiadomości MG
    messages = st.session_state.rpg_messages
    options = []

    if messages and messages[-1]["role"] == "assistant":
        _, options = _extract_options(messages[-1]["content"])

    # Faza 2: historia chatu — wyświetlamy narrację bez opcji A/B/C
    for i, msg in enumerate(messages):
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🧙‍♂️"):
            if msg["role"] == "assistant":
                story, _ = _extract_options(msg["content"])
                display_content = story if story else msg["content"]
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

    elif character["hp"] <= 0:
        st.markdown(
            '<p style="text-align:center; font-size:28px; font-weight:800; '
            'color:#ff2a5f; margin:8px 0 4px;">☠️ ZGINĄŁEŚ</p>'
            '<p style="text-align:center; font-size:15px; color:#b4c6ef; margin-bottom:18px;">'
            'Twoja przygoda dobiegła końca. '
            'Zresetuj opowieść, aby narodzić się na nowo.</p>',
            unsafe_allow_html=True,
        )
        if st.button("💀 ZRESETUJ OPOWIEŚĆ I ZACZNIJ OD NOWA", use_container_width=True, type="primary"):
            rpg_database.clear_all_rpg_data()
            st.session_state.rpg_messages = []
            st.session_state.last_rpg_image = None
            st.rerun()

    elif len(options) >= 2:
        st.markdown(
            '<p style="text-align:center; font-size:20px; font-weight:700; '
            'color:#b4c6ef; margin:8px 0 14px;">🧭 Wybierz swoje działanie:</p>',
            unsafe_allow_html=True,
        )
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

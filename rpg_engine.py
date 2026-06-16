import json
import re
import rpg_database

RPG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "modify_stats",
            "description": (
                "Zmienia punkty życia (HP), stan kredytów/złota bohatera, aktualną lokację oraz streszczenie fabuły. "
                "Wywołaj ZAWSZE, gdy akcja gracza lub świata wpływa na jego stan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hp_change": {
                        "type": "integer",
                        "description": "Wartość zmiany HP (np. -15 za obrażenia, +20 za leczenie). Wpisz 0 jeśli bez zmian."
                    },
                    "gold_change": {
                        "type": "integer",
                        "description": "Wartość zmiany gotówki (np. +10 za nagrodę, -20 za zakupy). Wpisz 0 jeśli bez zmian."
                    },
                    "new_location": {
                        "type": "string",
                        "description": (
                            "Nazwa nowej lokacji — TYLKO gdy bohater faktycznie opuścił poprzednią lokację i znalazł się w innym miejscu. "
                            "NIE podawaj tego pola jeśli gracz pozostaje w tej samej lokacji co na początku tury."
                        )
                    },
                    "summary": {
                        "type": "string",
                        "description": (
                            "Jednozdaniowe podsumowanie fabularnego przełomu TEJ tury — zapisywane jako trwały kanon historii. "
                            "Wymagane przy każdym wywołaniu modify_stats. "
                            "Pisz zwięźle o tym co SIĘ WŁAŚNIE WYDARZYŁO: "
                            "'Gracz pokonał strażnika i wkroczył do magazynu.', "
                            "'Podpisano pakt z handlarzem Marcusem.', "
                            "'Gracz odkrył ukryte przejście pod forum.' "
                            "Czas teraźniejszy lub przeszły, jedna konkretna myśl."
                        )
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_inventory_item",
            "description": "Dodaje nowy przedmiot do ekwipunku postaci lub zwiększa jego ilość.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Nazwa przedmiotu (np. 'Karta dostępu Arasaka', 'Stymulant medyczny')."
                    },
                    "item_type": {
                        "type": "string",
                        "description": "Typ przedmiotu (np. 'broń', 'klucz', 'medykament', 'narzędzie')."
                    },
                    "quantity": {"type": "integer", "description": "Ilość sztuk.", "default": 1}
                },
                "required": ["item_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_inventory_item",
            "description": "Usuwa przedmiot z ekwipunku gracza na skutek zużycia, zgubienia lub kradzieży.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Dokładna nazwa przedmiotu do usunięcia."
                    },
                    "quantity": {"type": "integer", "description": "Ilość sztuk do odjęcia.", "default": 1}
                },
                "required": ["item_name"]
            }
        }
    }
]

STARTING_STATS_TOOL = {
    "type": "function",
    "function": {
        "name": "set_starting_stats",
        "description": (
            "Ustawia absolutne statystyki startowe postaci na początku kampanii. "
            "Wywołaj DOKŁADNIE RAZ, przed napisaniem narracji otwierającej. "
            "Dobierz wartości i nazwę waluty do klasy postaci i realiów świata z kodeksu."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "max_hp": {
                    "type": "integer",
                    "description": "Maksymalne HP postaci, np. 140 dla twardego wojownika, 70 dla kupca."
                },
                "current_hp": {
                    "type": "integer",
                    "description": "Aktualne HP na start (najczęściej równe max_hp, chyba że postać jest już ranna)."
                },
                "gold": {
                    "type": "integer",
                    "description": "Startowa ilość waluty, np. 5 dla gladiatora, 80 dla szlachcica."
                },
                "currency_name": {
                    "type": "string",
                    "description": (
                        "Nazwa waluty dopasowana do realiów kodeksu świata. "
                        "Przykłady: 'kredytów' (cyberpunk), 'sztuk złota' (fantasy), 'kapsli' (postapo), "
                        "'denarów' (starożytny Rzym), 'monet' (ogólne), 'soli' (pustynny świat), 'rudy' (steampunk). "
                        "Użyj formy dopełniacza liczby mnogiej (bo: 'zdobyto 10 kredytów')."
                    )
                }
            },
            "required": ["max_hp", "current_hp", "gold", "currency_name"]
        }
    }
}


def build_rpg_system_prompt(character, inventory_list, lore_text):
    inv_str = ", ".join(inventory_list) if inventory_list else "Brak przedmiotów"
    hp = character["hp"]
    max_hp = character["max_hp"]
    return (
        f"Jesteś profesjonalnym Mistrzem Gry RPG prowadzącym sesję w świecie opisanym poniżej.\n\n"
        f"⚠️ BEZWZGLĘDNA ZASADA — REALIA ŚWIATA:\n"
        f"Kodeks poniżej DEFINIUJE jedyne dopuszczalne realia tej gry. "
        f"Technologia, kultura, uzbrojenie, frakcje, klasy postaci i zagrożenia MUSZĄ być w 100% spójne z tym opisem. "
        f"NIE wolno Ci wprowadzać żadnych elementów z innych epok ani gatunków — nawet dla urozmaicenia. "
        f"Przykłady: jeśli kodeks opisuje starożytny Rzym → nie ma broni palnej, internetu, cybertechnologii; "
        f"jeśli opisuje sci-fi → nie zakładaj automatycznie magii, smoków ani średniowiecznych struktur, "
        f"chyba że kodeks wyraźnie je zawiera. "
        f"Trzymaj się WYŁĄCZNIE realiów zdefiniowanych w kodeksie.\n\n"

        f"KANON ŚWIATA GRY:\n{lore_text}\n\n"
        f"AKTUALNY STAN BOHATERA (MUSISZ go uwzględniać w KAŻDEJ odpowiedzi):\n"
        f"- Imię: {character['name']}\n"
        f"- Klasa: {character['class']}\n"
        f"- Życie (HP): {hp}/{max_hp}\n"
        f"- {character.get('currency_name', 'kredytów').capitalize()}: {character['gold']}\n"
        f"- Lokacja: {character['location']}\n"
        f"- Streszczenie dotychczasowej fabuły: {character['summary']}\n"
        f"- Ekwipunek: {inv_str}\n\n"

        f"JAK WYKORZYSTYWAĆ STAN POSTACI:\n"

        f"1. KLASA ma znaczenie: '{character['class']}' jest ekspertem w pasujących do niej akcjach — daj mu wyraźną przewagę "
        f"(mniejsze obrażenia, większe szanse powodzenia, lepsze zdobycze), gdy działa zgodnie ze swoją specjalizacją.\n"

        f"2. EKWIPUNEK ma znaczenie: jeśli gracz ma przedmiot użyteczny w danej sytuacji, "
        f"zwiększ skuteczność akcji i zmniejsz ryzyko, ale zawsze oceniaj jego sens w realiach kodeksu i konkretnej scenie. "
        f"Jeśli gracz ma medykament, narzędzie, broń, dokument, przebranie, zapas lub inny zasób pasujący do sytuacji — wykorzystaj to fabularnie. "
        f"Odwołuj się w narracji do KONKRETNYCH przedmiotów z listy powyżej.\n"

        f"3. HP ma znaczenie: przy wysokim HP bohater jest silny i pewny siebie. Dopiero gdy HP spadnie poniżej 30, "
        f"opisuj wyczerpanie, krew i realne zagrożenie życia.\n\n"

        f"4. ZASADY OBRAŻEŃ I BALANSU (BARDZO WAŻNE — NIE BĄDŹ ZBYT SUROWY):\n"
        f"4.1. NIE karz gracza obrażeniami za KAŻDĄ akcję. Większość sprytnych lub zgodnych z klasą akcji kończy się sukcesem BEZ utraty HP.\n"
        f"4.2. Odważne i agresywne akcje CZĘSTO nagradzaj (łup, przewaga taktyczna, postęp fabuły), zamiast zawsze karać.\n"
        f"4.3. Skaluj obrażenia rozsądnie: zadrapanie -5, realna rana -10 do -20, ciężkie obrażenia -25 do -35. "
        f"4.4. Cios potencjalnie śmiertelny (-40 i więcej) stosuj WYŁĄCZNIE przy rażąco lekkomyślnych, samobójczych akcjach.\n"
        f"4.5. Zanim sprowadzisz HP do 0, daj graczowi ostrzeżenie i szansę reakcji w poprzedniej turze. Śmierć ma być RZADKA i zasłużona.\n"
        f"4.6. Gdy akcja logicznie leczy (odpoczynek, medykament, naprawa) – przywróć HP przez `modify_stats` z DODATNIM hp_change.\n\n"

        f"5. SENSOWNOŚĆ OPCJI WYBORU:\n"
        f"5.1. Opcje muszą wynikać z aktualnej sceny, klasy, ekwipunku i kodeksu świata. "
        f"Nie proponuj akcji wymagających zasobów, których bohater nie posiada, chyba że opcja jest wyraźnie próbą ich zdobycia.\n"
        f"5.2. W miarę możliwości każda opcja powinna prowadzić do innego typu konsekwencji: "
        f"np. walka, rozmowa, podstęp, eksploracja, ucieczka, handel, odpoczynek, przygotowanie albo ryzykowna próba.\n"
        f"5.3. Nie dawaj trzech wariantów tej samej akcji zapisanych innymi słowami.\n\n"

        f"6. CIĄGŁOŚĆ OPOWIEŚCI:\n"
        f"6.1 Nie zmieniaj faktów z dotychczasowej fabuły. Jeśli streszczenie mówi, że ktoś zginął, zniknął, zdradził albo coś zostało utracone, "
        f"traktuj to jako kanon, chyba że gracz odkryje wiarygodne wyjaśnienie w późniejszej fabule.\n"
        f"6.2 Dopóki bohater żyje (HP > 0), opowieść TRWA. Po każdej narracji ZAWSZE podawaj nowe opcje wyboru. "
        f"Nie kończ kampanii ani nie pisz finałowych podsumowań, gdy gracz wciąż ma HP.\n\n"

        f"7. KREATYWNOŚĆ OPOWIEŚCI:\n"
        f"7.1. Mieszaj akcję z fabułą. Kiedy gracz znajduje się w lokacji fabularnej, pozwól mu poczuć świat i wykonać kilka sensownych działań, zanim popchniesz go dalej.\n"
        f"7.2. Nie przesadzaj z nagrodami. Gracz nie powinien co chwilę zdobywać kredytów ani ekwipunku — nagroda ma być rzadsza i satysfakcjonująca.\n"
        f"7.3. Mieszaj napięcie z chwilami ulgi. Jeśli gracz stracił dużo HP, ale przeżył i nie ma bezpośredniego zagrożenia, powinien móc dążyć do uleczenia postaci, jeśli jest to fabularnie sensowne.\n\n"

        f"8. STRUKTURA KAŻDEJ ODPOWIEDZI (OBOWIĄZKOWA, BEZ WYJĄTKU):\n"
        f"8.1. NARRACJA: Napisz fabularny opis skutków akcji gracza — minimum 3-4 zdania, atmosfera, dialogi, rozwój sytuacji. "
        f"NIE zaczynaj od razu od opcji A/B/C.\n"
        f"8.2. OPCJE: Na SAMYM KOŃCU odpowiedzi, po narracji, ZAWSZE podaj 3 opcje w formacie A) B) C). "
        f"⚠️ Brak opcji = błąd krytyczny. Nawet jeśli wywołałeś narzędzia, nawet jeśli narracja jest długa — "
        f"opcje A/B/C MUSZĄ być ostatnim elementem Twojej odpowiedzi.\n\n"

        f"9. ZASADY MODYFIKACJI ŚWIATA (NARZĘDZIA):\n"
        f"9.0. ⚠️ STAN GRY JEST AKTUALNY — AKTUALNY STAN BOHATERA powyżej odzwierciedla wszystkie zmiany "
        f"z poprzednich tur. NIE wywołuj narzędzi aby ponownie zastosować zmiany z WCZEŚNIEJSZYCH tur "
        f"(np. jeśli w historii gracz kupił miecz i zapłacił 10 monet, NIE deducktuj tych monet ani NIE dodawaj miecza ponownie — to już zostało zrobione). "
        f"Wywołuj narzędzia TYLKO dla tego, co dzieje się w BIEŻĄCEJ turze: jeśli w TEJ turze gracz "
        f"znajduje przedmiot → add_inventory_item; traci HP → modify_stats; wchodzi do nowej lokacji → modify_stats.\n"
        f"9.1. Masz pełną władzę nad statystykami i przedmiotami gracza przy użyciu dostarczonych narzędzi.\n"
        f"9.2. Wywołaj `modify_stats` gdy: gracz traci/zyskuje HP, traci/zarabia {character.get('currency_name', 'kredytów')}, "
        f"zmienia lokację (new_location), lub wydarzy się coś fabularnie istotnego (wypełnij wtedy pole summary). "
        f"Możesz wywołać modify_stats RAZEM z add_inventory_item w tej samej turze — to nie są wykluczające się narzędzia.\n"
        f"9.3. ⚠️ ZNALAZŁ PRZEDMIOT = add_inventory_item (ZAWSZE). Jeśli gracz w BIEŻĄCEJ turze znajduje, kupuje lub otrzymuje "
        f"dowolny przedmiot — nawet jeśli to tylko drobiazg — MUSISZ wywołać `add_inventory_item`. "
        f"Zmiana lokacji w modify_stats NIE zastępuje dodania przedmiotu. Gdy gracz go traci/zużywa – wywołaj `remove_inventory_item`.\n"
        f"9.4. Jeśli gracz próbuje użyć przedmiotu, którego nie ma w Ekwipunku, opisz niepowodzenie z powodu braku zasobów.\n\n"

        f"10. ⛔ ABSOLUTNY ZAKAZ — BLOK STATUSU POSTACI:\n"
        f"Nigdy nie dodawaj do odpowiedzi bloku z aktualnym stanem bohatera "
        f"(np. 'AKTUALNY STAN BOHATERA:', 'STATUS POSTACI:', list HP/Kredyty/Lokacja/Ekwipunek). "
        f"Gracz widzi te dane w osobnym panelu interfejsu. "
        f"Twoja odpowiedź ma zawierać WYŁĄCZNIE narrację i opcje — nic poza tym.\n\n"

        f"11. ⛔ ABSOLUTNY ZAKAZ — SYMULOWANIE ZMIAN W TEKŚCIE:\n"
        f"Nigdy NIE pisz w treści odpowiedzi bloków takich jak:\n"
        f"- '📊 Zmiany w tej turze: ...'\n"
        f"- '🎒 Otrzymano: ...' / '🎒 Utracono: ...' jako osobna lista\n"
        f"- '📝 Streszczenie: ...' jako wypunktowanie\n"
        f"Te bloki są GENEROWANE AUTOMATYCZNIE przez system gry wyłącznie na podstawie WYWOŁANYCH NARZĘDZI.\n"

        f"12. ⚠️ KRYTYCZNE: Napisanie w tekście 'gracz otrzymuje X' NIE zapisze X do gry — "
        f"gracz nie zobaczy tego w ekwipunku! "
        f"JEDYNYM sposobem na zmianę stanu gry jest WYWOŁANIE NARZĘDZIA (add_inventory_item, modify_stats itp.). "
        f"Pisanie o zmianach ZAMIAST wywołania narzędzi to BŁĄD KRYTYCZNY.\n\n"

        f"13. FORMAT OPCJI — OSTATNI ELEMENT KAŻDEJ ODPOWIEDZI:\n"
        f"⚠️ ZAWSZE kończ odpowiedź opcjami. Nawet po długiej narracji i wywołaniu narzędzi — opcje muszą być na końcu.\n"
        f"Dokładnie 3 opcje, każda od NOWEJ LINII:\n"
        f"A) Krótki opis pierwszej akcji\n"
        f"B) Krótki opis drugiej akcji\n"
        f"C) Krótki opis trzeciej akcji\n\n"
        f"Nic po opcji C). Wzorzec 'wielka litera + )' tylko w sekcji opcji."
    )


def _dispatch_tool_call(func_name, func_args):
    if func_name == "set_starting_stats":
        return rpg_database.set_starting_stats(
            max_hp=func_args.get("max_hp", 100),
            current_hp=func_args.get("current_hp", 100),
            gold=func_args.get("gold", 50),
            currency_name=func_args.get("currency_name"),
        )
    if func_name == "modify_stats":
        return rpg_database.modify_stats(
            hp_change=func_args.get("hp_change", 0),
            gold_change=func_args.get("gold_change", 0),
            new_location=func_args.get("new_location"),
            summary=func_args.get("summary"),
        )
    if func_name == "add_inventory_item":
        return rpg_database.add_inventory_item(
            item_name=func_args.get("item_name"),
            item_type=func_args.get("item_type", "przedmiot"),
            quantity=func_args.get("quantity", 1),
        )
    if func_name == "remove_inventory_item":
        return rpg_database.remove_inventory_item(
            item_name=func_args.get("item_name"),
            quantity=func_args.get("quantity", 1),
        )
    return f"Nieznane narzędzie: {func_name}"


# Dopasowuje cały blok: nagłówek STAN/STATUS BOHATERA + linie z polami aż do pustej linii lub końca
_STATUS_BLOCK_RE = re.compile(
    r'\n*[^\n]*(?:STAN\s+BOHATERA|STATUS\s+(?:BOHATERA|POSTACI)|AKTUALNE?\s+(?:STAN|STATYSTYKI))[^\n]*\n'
    r'\n?'           # opcjonalna pusta linia po nagłówku
    r'(?:[^\n]+\n?)*',  # kolejne niepuste linie aż do pustej lub końca tekstu
    re.IGNORECASE,
)


def _strip_status_block(text):
    """Usuwa blok statusu postaci jeśli AI go wygenerował mimo zakazu w system promptcie."""
    return _STATUS_BLOCK_RE.sub('', text).strip()


# Dopasowuje AI-generowany blok '📊 Zmiany w tej turze' (bez separatora ---) — zarówno wieloliniowy jak i w jednej linii
_AI_FAKE_SUMMARY_RE = re.compile(
    r'\n*📊[^\n]*(?:Zmiany\s+w\s+tej\s+turze|ZMIANY)[^\n]*(?:\n—[^\n]*)*',
    re.IGNORECASE,
)


def _strip_ai_fake_summary(text):
    """Usuwa AI-generowany blok podsumowania zmian z odpowiedzi — system dodaje go automatycznie z tool callów."""
    return _AI_FAKE_SUMMARY_RE.sub('', text).strip()


def strip_changes_tail_from_history(text):
    """Usuwa nasz auto-generowany blok '--- Zmiany w tej turze' z wiadomości historycznych przed wysłaniem do AI."""
    idx = text.find("\n\n---\n*📊 Zmiany w tej turze:*")
    if idx != -1:
        return text[:idx].strip()
    return text


def _build_changes_summary(changes, currency_name="kredytów"):
    """Buduje czytelne podsumowanie zmian statystyk/ekwipunku/lokacji z listy tool callów."""
    lines = []
    last_summary = ""
    for func_name, func_args in changes:
        if func_name == "modify_stats":
            hp = func_args.get("hp_change", 0)
            gold = func_args.get("gold_change", 0)
            loc = func_args.get("new_location")
            s = func_args.get("summary", "")
            if hp < 0:
                lines.append(f"❤️ Stracono **{abs(hp)} HP**")
            elif hp > 0:
                lines.append(f"❤️ Odzyskano **{hp} HP**")
            if gold < 0:
                lines.append(f"💰 Stracono **{abs(gold)} {currency_name}**")
            elif gold > 0:
                lines.append(f"💰 Zdobyto **{gold} {currency_name}**")
            if loc:
                lines.append(f"📍 Lokacja: **{loc}**")
            if s:
                last_summary = s
        elif func_name == "add_inventory_item":
            name = func_args.get("item_name", "?")
            qty = func_args.get("quantity", 1)
            suffix = f" ×{qty}" if qty > 1 else ""
            lines.append(f"🎒 Otrzymano: **{name}**{suffix}")
        elif func_name == "remove_inventory_item":
            name = func_args.get("item_name", "?")
            qty = func_args.get("quantity", 1)
            suffix = f" ×{qty}" if qty > 1 else ""
            lines.append(f"🎒 Utracono: **{name}**{suffix}")
    if not lines and not last_summary:
        return ""
    body = "\n".join(f"— {l}" for l in lines)
    result = f"\n\n---\n*📊 Zmiany w tej turze:*\n{body}" if lines else "\n\n---"
    if last_summary:
        result += f"\n\n📝 *{last_summary}*"
    return result


def call_rpg_ai(client, model, temp, messages, extra_tools=None, tools_override=None, currency_name="kredytów"):
    """Wywołuje AI z function calling i zwraca końcową odpowiedź tekstową."""
    tools = tools_override if tools_override is not None else RPG_TOOLS + (extra_tools or [])
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temp,
        tools=tools,
        tool_choice="auto",
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if not tool_calls:
        return _strip_ai_fake_summary(response_message.content or "")

    # Gemini często umieszcza narrację w content pierwszej odpowiedzi,
    # a po przetworzeniu tool calls zwraca tylko opcje (lub None).
    # Łączymy oba fragmenty, żeby nie zgubić narracji.
    first_content = (response_message.content or "").strip()

    messages.append(response_message)
    changes = []
    for tool_call in tool_calls:
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        changes.append((func_name, func_args))
        result = _dispatch_tool_call(func_name, func_args)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": func_name,
            "content": result,
        })

    # Przypomnienie o opcjach — bez dosłownego "A) B) C)", bo Gemini kopiuje to literalnie
    messages.append({"role": "user", "content": "Napisz teraz trzy różne opcje dalszych działań dla gracza."})
    second_response = client.chat.completions.create(
        model=model, messages=messages, temperature=temp
    )
    second_content = (second_response.choices[0].message.content or "").strip()

    parts = [p for p in [first_content, second_content] if p]
    combined = _strip_status_block(_strip_ai_fake_summary("\n\n".join(parts)))
    return combined + _build_changes_summary(changes, currency_name)


def generate_opening_scene(client, model, temp, character, lore_text):
    """Generuje klimatyczną scenę otwierającą kampanię, dostosowaną do aktywnego kodeksu świata."""
    system_prompt = build_rpg_system_prompt(character, [], lore_text)
    intro_request = (
        f"Zacznij nową kampanię dla postaci o imieniu {character['name']} ({character['class']}).\n\n"

        f"KROK 1 — OBOWIĄZKOWO wywołaj narzędzie set_starting_stats. Ustaw:\n"
        f"• max_hp i current_hp dopasowane do klasy '{character['class']}' i realiów świata\n"
        f"• gold — startową ilość waluty\n"
        f"• currency_name — NAZWĘ WALUTY tego świata w dopełniaczu l.mn. "
        f"(np. 'sztuk złota', 'denarów', 'kapsli', 'kredytów', 'monet', 'soli'). "
        f"Dobierz do epoki i klimatu kodeksu — to będzie używane przez cały czas trwania gry.\n\n"
        f"Archetypy HP (tylko wskazówki, nie sztywne wartości):\n\n"
        
        f"- Frontowiec / wojownik / gladiator / żołnierz / ochroniarz → max_hp: 110-140, gold: 5-18\n"
        f"- Najemnik / łowca nagród / egzekutor / zawodowy zabijaka → max_hp: 95-125, gold: 10-28\n"
        f"- Zwiadowca / złodziej / skrytobójca / sabotażysta / infiltrator → max_hp: 70-95, gold: 8-25\n"
        f"- Mistyk / kapłan / szaman / mag / okultysta / technomanta → max_hp: 55-80, gold: 8-30\n"
        f"- Medyk / uczony / inżynier / rzemieślnik / specjalista → max_hp: 60-90, gold: 12-32\n"
        f"- Kupiec / arystokrata / polityk / urzędnik / wpływowa persona → max_hp: 55-85, gold: 25-55\n"
        f"- Łowca / tropiciel / survivalowiec / pogranicznik / stalker → max_hp: 80-110, gold: 8-25\n"
        f"- Artysta / bard / mówca / celebryta / manipulator tłumu → max_hp: 60-85, gold: 12-38\n"
        f"- Kultysta / mnich / mutant / eksperyment / wyrzutek z niezwykłą odpornością → max_hp: 75-115, gold: 0-20\n"
        f"- Chłop / bezdomny / dezerter / niewolnik / dłużnik / kaleka / ofiara losu → max_hp: 40-65, gold: 0-8\n\n"

        f"Jeśli klasa postaci nie pasuje dokładnie do żadnej kategorii, wybierz najbliższy archetyp "
        f"albo połącz kilka archetypów. Możesz też lekko wyjść poza zakres, jeśli kodeks świata lub opis postaci to uzasadnia. "
        f"Nie kopiuj wartości mechanicznie — dopasuj je fabularnie. Bądź kreatywny i spójny z realiami kodeksu.\n\n"

        f"KROK 2 — Napisz wciągające, klimatyczne wprowadzenie do świata — minimum 4-5 zdań "
        f"opisujących otoczenie, atmosferę i sytuację startową bohatera. "
        f"Narracja MUSI być w 100% spójna z realiami kodeksu — żadnych anachronizmów.\n\n"

        f"KROK 3 — Na końcu podaj 3 opcje pierwszych działań pasujące do tego świata i klasy postaci."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": intro_request},
    ]
    # tools_override: tylko set_starting_stats — bez modify_stats, żeby nie generować zbędnych zmian lokacji/summary
    return call_rpg_ai(client, model, temp, messages, tools_override=[STARTING_STATS_TOOL])

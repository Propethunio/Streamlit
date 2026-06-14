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
                        "description": "Wartość zmiany gotówki (np. +50 za nagrodę, -20 za zakupy). Wpisz 0 jeśli bez zmian."
                    },
                    "new_location": {
                        "type": "string",
                        "description": "Nazwa nowej lokacji, jeśli bohater przemieścił się w inne miejsce."
                    },
                    "summary": {
                        "type": "string",
                        "description": "Krótkie jednozdaniowe podsumowanie obecnej sytuacji fabularnej."
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
            "Ustawia absolutne statystyki startowe postaci na początku kampanii (max HP, aktualne HP i kredyty/złoto). "
            "Wywołaj DOKŁADNIE RAZ, przed napisaniem narracji otwierającej, aby dostosować wartości do klasy i realiów świata."
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
                    "description": "Aktualne HP na start (najczęściej równe max_hp, chyba że postać już jest ranna)."
                },
                "gold": {
                    "type": "integer",
                    "description": "Startowe kredyty/złoto, np. 15 dla gladiatora, 100 dla szlachcica."
                }
            },
            "required": ["max_hp", "current_hp", "gold"]
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
        f"jeśli opisuje fantasy → nie ma pistoletów ani samochodów; jeśli opisuje sci-fi → nie ma łuków ani mieczy. "
        f"Trzymaj się WYŁĄCZNIE realiów zdefiniowanych w kodeksie.\n\n"
        f"KANON ŚWIATA GRY:\n{lore_text}\n\n"
        f"AKTUALNY STAN BOHATERA (MUSISZ go uwzględniać w KAŻDEJ odpowiedzi):\n"
        f"- Imię: {character['name']}\n"
        f"- Klasa: {character['class']}\n"
        f"- Życie (HP): {hp}/{max_hp}\n"
        f"- Kredyty: {character['gold']}\n"
        f"- Lokacja: {character['location']}\n"
        f"- Streszczenie dotychczasowej fabuły: {character['summary']}\n"
        f"- Ekwipunek: {inv_str}\n\n"
        f"JAK WYKORZYSTYWAĆ STAN POSTACI:\n"
        f"1. KLASA ma znaczenie: '{character['class']}' jest ekspertem w pasujących do niej akcjach — daj mu wyraźną przewagę "
        f"(mniejsze obrażenia, większe szanse powodzenia, lepsze zdobycze), gdy działa zgodnie ze swoją specjalizacją.\n"
        f"2. EKWIPUNEK ma znaczenie: jeśli gracz ma broń – walka jest skuteczna i mniej ryzykowna; jeśli ma medykament – może się leczyć. "
        f"Odwołuj się w narracji do KONKRETNYCH przedmiotów z listy powyżej.\n"
        f"3. HP ma znaczenie: przy wysokim HP bohater jest silny i pewny siebie. Dopiero gdy HP spadnie poniżej 30, "
        f"opisuj wyczerpanie, krew i realne zagrożenie życia.\n\n"
        f"ZASADY OBRAŻEŃ I BALANSU (BARDZO WAŻNE — NIE BĄDŹ ZBYT SUROWY):\n"
        f"1. NIE karz gracza obrażeniami za KAŻDĄ akcję. Większość sprytnych lub zgodnych z klasą akcji kończy się sukcesem BEZ utraty HP.\n"
        f"2. Odważne i agresywne akcje CZĘSTO nagradzaj (łup, przewaga taktyczna, postęp fabuły), zamiast zawsze karać.\n"
        f"3. Skaluj obrażenia rozsądnie: zadrapanie -5, realna rana -10 do -20, ciężkie obrażenia -25 do -35. "
        f"Cios potencjalnie śmiertelny (-40 i więcej) stosuj WYŁĄCZNIE przy rażąco lekkomyślnych, samobójczych akcjach.\n"
        f"4. Zanim sprowadzisz HP do 0, daj graczowi ostrzeżenie i szansę reakcji w poprzedniej turze. Śmierć ma być RZADKA i zasłużona.\n"
        f"5. Gdy akcja logicznie leczy (odpoczynek, medykament, naprawa) – przywróć HP przez `modify_stats` z DODATNIM hp_change.\n\n"
        f"CIĄGŁOŚĆ OPOWIEŚCI:\n"
        f"Dopóki bohater żyje (HP > 0), opowieść TRWA. Po każdej narracji ZAWSZE podawaj nowe opcje wyboru. "
        f"Nie kończ kampanii ani nie pisz finałowych podsumowań, gdy gracz wciąż ma HP.\n\n"
        f"STRUKTURA KAŻDEJ ODPOWIEDZI (OBOWIĄZKOWA):\n"
        f"1. NARRACJA: Najpierw ZAWSZE napisz fabularny opis tego, co się dzieje — minimum 3-4 zdania opisujące skutki akcji gracza, atmosferę, dialogi i rozwój sytuacji. "
        f"NIE zaczynaj odpowiedzi od razu od opcji A/B/C — to byłby błąd.\n"
        f"2. OPCJE: Dopiero po narracji dopisz na końcu sekcję z wyborami.\n\n"
        f"ZASADY MODYFIKACJI ŚWIATA (NARZĘDZIA):\n"
        f"1. Masz pełną władzę nad statystykami i przedmiotami gracza przy użyciu dostarczonych narzędzi.\n"
        f"2. Kiedy gracz wykonuje akcję, która logicznie go rani, leczy, kosztuje pieniądze lub daje zarobek – WYWOŁAJ funkcję `modify_stats`.\n"
        f"3. Kiedy gracz znajduje, kupuje przedmiot lub go zużywa/traci – WYWOŁAJ `add_inventory_item` lub `remove_inventory_item`.\n"
        f"4. Jeśli gracz próbuje użyć przedmiotu, którego nie ma w wyżej wymienionym Ekwipunku, opisz w opowiadaniu niepowodzenie z powodu braku zasobów.\n\n"
        f"⛔ ABSOLUTNY ZAKAZ — BLOK STATUSU POSTACI:\n"
        f"Nigdy nie dodawaj do odpowiedzi bloku z aktualnym stanem bohatera "
        f"(np. 'AKTUALNY STAN BOHATERA:', 'STATUS POSTACI:', list HP/Kredyty/Lokacja/Ekwipunek). "
        f"Gracz widzi te dane w osobnym panelu interfejsu. "
        f"Twoja odpowiedź ma zawierać WYŁĄCZNIE narrację i opcje — nic poza tym.\n\n"
        f"⛔ ABSOLUTNY ZAKAZ — SYMULOWANIE ZMIAN W TEKŚCIE:\n"
        f"Nigdy NIE pisz w treści odpowiedzi bloków takich jak:\n"
        f"- '📊 Zmiany w tej turze: ...'\n"
        f"- '🎒 Otrzymano: ...' / '🎒 Utracono: ...' jako osobna lista\n"
        f"- '📝 Streszczenie: ...' jako wypunktowanie\n"
        f"Te bloki są GENEROWANE AUTOMATYCZNIE przez system gry wyłącznie na podstawie WYWOŁANYCH NARZĘDZI.\n"
        f"⚠️ KRYTYCZNE: Napisanie w tekście 'gracz otrzymuje X' NIE zapisze X do gry — "
        f"gracz nie zobaczy tego w ekwipunku! "
        f"JEDYNYM sposobem na zmianę stanu gry jest WYWOŁANIE NARZĘDZIA (add_inventory_item, modify_stats itp.). "
        f"Pisanie o zmianach ZAMIAST wywołania narzędzi to BŁĄD KRYTYCZNY.\n\n"
        f"FORMAT OPCJI (na samym końcu wypowiedzi):\n"
        f"Maksymalnie 3 opcje, każda od NOWEJ LINII, format:\n"
        f"A) Krótki opis pierwszej akcji\n"
        f"B) Krótki opis drugiej akcji\n"
        f"C) Krótki opis trzeciej akcji\n\n"
        f"Nie dodawaj żadnego tekstu po opcji C).\n"
        f"Nie używaj wzorca 'wielka litera + )' nigdzie indziej w narracji."
    )


def _dispatch_tool_call(func_name, func_args):
    if func_name == "set_starting_stats":
        return rpg_database.set_starting_stats(
            max_hp=func_args.get("max_hp", 100),
            current_hp=func_args.get("current_hp", 100),
            gold=func_args.get("gold", 50),
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


def _build_changes_summary(changes):
    """Buduje czytelne podsumowanie zmian statystyk/ekwipunku/lokacji z listy tool callów."""
    lines = []
    for func_name, func_args in changes:
        if func_name == "modify_stats":
            hp = func_args.get("hp_change", 0)
            gold = func_args.get("gold_change", 0)
            loc = func_args.get("new_location")
            if hp < 0:
                lines.append(f"❤️ Stracono **{abs(hp)} HP**")
            elif hp > 0:
                lines.append(f"❤️ Odzyskano **{hp} HP**")
            if gold < 0:
                lines.append(f"💰 Stracono **{abs(gold)} kredytów**")
            elif gold > 0:
                lines.append(f"💰 Zdobyto **{gold} kredytów**")
            if loc:
                lines.append(f"📍 Lokacja: **{loc}**")
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
    if not lines:
        return ""
    body = "\n".join(f"— {l}" for l in lines)
    return f"\n\n---\n*📊 Zmiany w tej turze:*\n{body}"


def call_rpg_ai(client, model, temp, messages, extra_tools=None):
    """Wywołuje AI z function calling i zwraca końcową odpowiedź tekstową."""
    tools = RPG_TOOLS + (extra_tools or [])
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

    second_response = client.chat.completions.create(
        model=model, messages=messages, temperature=temp
    )
    second_content = (second_response.choices[0].message.content or "").strip()

    parts = [p for p in [first_content, second_content] if p]
    combined = _strip_status_block(_strip_ai_fake_summary("\n\n".join(parts)))
    return combined + _build_changes_summary(changes)


def generate_opening_scene(client, model, temp, character, lore_text):
    """Generuje klimatyczną scenę otwierającą kampanię, dostosowaną do aktywnego kodeksu świata."""
    system_prompt = build_rpg_system_prompt(character, [], lore_text)
    intro_request = (
        f"Zacznij nową kampanię dla postaci o imieniu {character['name']} ({character['class']}). "
        f"KROK 1 — OBOWIĄZKOWO wywołaj narzędzie set_starting_stats, aby ustawić startowe HP i kredyty "
        f"odpowiednie dla klasy '{character['class']}' i realiów świata. "
        f"Przykładowe wartości (dostosuj do klasy i świata):\n"
        f"- Wojownik/gladiator/żołnierz → max_hp: 120-140, gold: 10-25\n"
        f"- Złodziej/skrytobójca/zwiadowca → max_hp: 80-95, gold: 25-45\n"
        f"- Mag/kapłan/szaman → max_hp: 55-75, gold: 40-65\n"
        f"- Kupiec/szlachcic/polityk → max_hp: 65-85, gold: 80-130\n"
        f"- Medyk/rzemieślnik/uczony → max_hp: 75-95, gold: 45-70\n"
        f"- Łowca/zwiadowca/ranger → max_hp: 90-110, gold: 15-35\n"
        f"Bądź kreatywny i spójny z realiami kodeksu. "
        f"KROK 2 — Napisz wciągające, klimatyczne wprowadzenie do świata — minimum 4-5 zdań "
        f"opisujących otoczenie, atmosferę i sytuację startową bohatera. "
        f"Narracja MUSI być w 100% spójna z realiami kodeksu — żadnych anachronizmów. "
        f"Na końcu podaj 3 opcje pierwszych działań pasujące do tego świata i klasy postaci."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": intro_request},
    ]
    return call_rpg_ai(client, model, temp, messages, extra_tools=[STARTING_STATS_TOOL])

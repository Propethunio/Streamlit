import json
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

RPG_INITIAL_SCENE = (
    "Witaj, {name} ({char_class}). "
    "Budzisz się w mrocznym, skąpanym w kwaśnym deszczu zaułku sektora 7. "
    "W dłoni ściskasz uszkodzony cyber-dek. "
    "Słyszysz zbliżające się kroki strażników korporacji Arasaka.\n\n"
    "A) Spróbuj zhakować pobliską skrzynkę bezpieczników, by zgasić neony i ukryć się w cieniu.\n"
    "B) Przygotuj się do walki wręcz i poczekaj w zasadzce.\n"
    "C) Wybiegnij na główną aleję, próbując zgubić pościg w tłumie."
)


def build_rpg_system_prompt(character, inventory_list, lore_text):
    inv_str = ", ".join(inventory_list) if inventory_list else "Brak przedmiotów"
    hp = character["hp"]
    max_hp = character["max_hp"]
    return (
        f"Jesteś profesjonalnym Mistrzem Gry RPG prowadzącym sesję w świecie opisanym poniżej.\n\n"
        f"KANON ŚWIATA GRY (obowiązujące realia, klasy i zasady — trzymaj się ich):\n{lore_text}\n\n"
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
        f"FORMAT OPCJI (na samym końcu wypowiedzi):\n"
        f"Maksymalnie 3 opcje, każda od NOWEJ LINII, format:\n"
        f"A) Krótki opis pierwszej akcji\n"
        f"B) Krótki opis drugiej akcji\n"
        f"C) Krótki opis trzeciej akcji\n\n"
        f"Nie dodawaj żadnego tekstu po opcji C).\n"
        f"Nie używaj wzorca 'wielka litera + )' nigdzie indziej w narracji."
    )


def _dispatch_tool_call(func_name, func_args):
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


def call_rpg_ai(client, model, temp, messages):
    """Wywołuje AI z function calling i zwraca końcową odpowiedź tekstową."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temp,
        tools=RPG_TOOLS,
        tool_choice="auto",
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if not tool_calls:
        return response_message.content or ""

    # Gemini często umieszcza narrację w content pierwszej odpowiedzi,
    # a po przetworzeniu tool calls zwraca tylko opcje (lub None).
    # Łączymy oba fragmenty, żeby nie zgubić narracji.
    first_content = (response_message.content or "").strip()

    messages.append(response_message)
    for tool_call in tool_calls:
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
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
    return "\n\n".join(parts)

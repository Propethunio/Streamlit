"""
Stały kodeks świata gry RPG.

Pełni podwójną rolę:
1. Jest wstrzykiwany do system promptu Mistrza Gry (rpg_engine) — dzięki temu
   AI trzyma się spójnego kanonu świata, klas i zasad.
2. Jest wyświetlany graczowi w oknie "Kodeks Świata" na pasku bocznym (rpg_tab).

Pojedyncze źródło prawdy treści — edytuj TYLKO ten plik, a następnie wygeneruj
PDF poleceniem `py make_lore_pdf.py`, by zaktualizować plik do podglądu/pobrania.
"""

import os

DEFAULT_LORE_NAME = "Domyślny kodeks świata"
DEFAULT_LORE_PDF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_lore.pdf")


def load_default_lore_pdf_bytes():
    """Zwraca bajty domyślnego game_lore.pdf (do podglądu/pobrania) lub None, jeśli brak pliku."""
    try:
        with open(DEFAULT_LORE_PDF_PATH, "rb") as f:
            return f.read()
    except OSError:
        return None


GAME_CODEX = """
## 🌃 ŚWIAT GRY — SEKTOR 7

Rok 2099. Megamiasto tonie w kwaśnym deszczu i blasku neonów. Korporacje rządzą wszystkim,
a ulice należą do gangów, hakerów i najemników. Zaczynasz w **Sektorze 7** — najmroczniejszej
dzielnicy, gdzie życie jest tanie, a dane cenniejsze od krwi.

## 🎭 KLASY POSTACI

- **Netrunner Cyber-Haker** — mistrz włamań do sieci i systemów. Przewaga przy hakowaniu,
  obchodzeniu zabezpieczeń i walce elektronicznej. Słabszy w bezpośrednim starciu.
- **Zwiadowca Pustkowi** — przetrwa wszędzie. Przewaga w terenie, skradaniu, tropieniu i ucieczce.
- **Technomanta Neonu** — łączy technologię z ulicznym okultyzmem. Przewaga przy naprawie sprzętu,
  improwizowanych gadżetach i manipulacji maszynami.
- **Uliczny Wojownik** — urodzony do walki. Przewaga w bezpośrednim starciu, zadaje i wytrzymuje
  więcej obrażeń.

## 📊 STATYSTYKI

- **❤️ Życie (HP)** — gdy spadnie do 0, giniesz i opowieść się kończy.
- **💰 Kredyty** — waluta Sektora. Płacisz nimi za sprzęt, łapówki i usługi.
- **📍 Lokacja** — gdzie aktualnie jesteś; wpływa na dostępne akcje.
- **🎒 Ekwipunek** — przedmioty, których faktycznie możesz użyć. Bez odpowiedniego przedmiotu
  niektóre akcje się nie powiodą.

## ⚔️ ZASADY PRZETRWANIA

- Odwaga popłaca — sprytne i agresywne akcje **często są nagradzane**, nie tylko karane.
- Obrażenia są proporcjonalne: drobne potknięcie kosztuje mało HP, lekkomyślność — dużo.
- Działaj zgodnie ze swoją **klasą** — wtedy masz realną przewagę.
- Używaj **ekwipunku**: broń pomaga w walce, medykamenty leczą, narzędzia otwierają nowe drogi.
- Śmierć przychodzi tylko po rażąco samobójczych decyzjach — zwykle dostaniesz wcześniej ostrzeżenie.

## 🏢 FRAKCJE

- **Korporacja Arasaka** — wszechobecny gigant. Ich strażnicy patrolują ulice; zadarcie z nimi
  bywa śmiertelne, ale ich dane i sprzęt są bezcenne.
- **Gangi uliczne** — kontrolują zaułki. Można z nimi handlować albo walczyć.
- **Fixerzy i netrunnerzy** — pośrednicy i hakerzy. Źródło zleceń, informacji i kłopotów.

## 💡 WSKAZÓWKI

- Czytaj narrację Mistrza Gry — podpowiada konsekwencje i okazje.
- Zarządzaj HP i kredytami; nie rzucaj się na każdego wroga.
- Wybory mają trwałe skutki — świat pamięta twoje decyzje.
"""

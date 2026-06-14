import sqlite3

DB_NAME = "game_storage.db"

def init_db():
    """Inicjalizuje bazę danych i tworzy potrzebne tabele."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabela stanu gry i postaci
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS character_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            character_class TEXT NOT NULL,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            gold INTEGER DEFAULT 10,
            current_location TEXT DEFAULT 'Początek drogi',
            story_summary TEXT DEFAULT 'Rozpoczęto nową przygodę.'
        )
    """)
    
    # 2. Tabela ekwipunku
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            item_type TEXT, -- np. 'broń', 'mikstura', 'kluczowy'
            quantity INTEGER DEFAULT 1
        )
    """)
    
    conn.commit()
    conn.close()

def get_character():
    """Pobiera statystyki postaci (jeśli istnieje)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM character_stats ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0], "name": row[1], "class": row[2],
            "hp": row[3], "max_hp": row[4], "gold": row[5],
            "location": row[6], "summary": row[7]
        }
    return None

def create_character(name, char_class):
    """Tworzy nową postać i czyści stary ekwipunek."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Reset starych danych na potrzeby nowej gry
    cursor.execute("DELETE FROM character_stats")
    cursor.execute("DELETE FROM inventory")
    
    cursor.execute("""
        INSERT INTO character_stats (name, character_class, hp, max_hp, gold, current_location, story_summary)
        VALUES (?, ?, 100, 100, 15, 'Tajemnicza Karczma', 'Budzisz się w zadymionej karczmie...')
    """, (name, char_class))
    
    # Dajmy coś na start do ekwipunku
    cursor.execute("INSERT INTO inventory (item_name, item_type) VALUES ('Zardzewiały Sztylet', 'broń')")
    cursor.execute("INSERT INTO inventory (item_name, item_type) VALUES ('Mikstura Leczenia', 'medykament')")
    
    conn.commit()
    conn.close()

def update_game_state(hp, gold, location, summary):
    """Aktualizuje dynamicznie stan gry po każdym ruchu."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE character_stats 
        SET hp = ?, gold = ?, current_location = ?, story_summary = ?
        WHERE id = (SELECT id FROM character_stats ORDER BY id DESC LIMIT 1)
    """, (hp, gold, location, summary))
    conn.commit()
    conn.close()

def get_inventory():
    """Pobiera listę przedmiotów."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, item_type, quantity FROM inventory")
    rows = cursor.fetchall()
    conn.close()
    return [{"name": r[0], "type": r[1], "qty": r[2]} for r in rows]

# Uruchomienie inicjalizacji przy pierwszym imporcie
init_db()
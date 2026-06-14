import sqlite3

DB_NAME = "game_storage.db"

def init_db():
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
            item_type TEXT,
            quantity INTEGER DEFAULT 1
        )
    """)

    # 3. NOWA TABELA: Historia czatu RPG (do zapamiętywania kampanii)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rpg_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_character():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM character_stats ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    conn.close()
    
    if row:
        return {
            "id": row[0], "name": row[1], "class": row[2],
            "hp": row[3], "max_hp": row[4], "gold": row[5],
            "location": row[6], "summary": row[7]
        }
    return None

def create_character(name, char_class):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM character_stats")
    cursor.execute("DELETE FROM inventory")
    cursor.execute("DELETE FROM rpg_chat_history") # Reset historii przy nowej postaci
    
    cursor.execute("""
        INSERT INTO character_stats (name, character_class, hp, max_hp, gold, current_location, story_summary)
        VALUES (?, ?, 100, 100, 15, 'Sektor 7 - Zaułek', 'Budzisz się w deszczu...')
    """, (name, char_class))
    
    cursor.execute("INSERT INTO inventory (item_name, item_type) VALUES ('Ostrze Monomolekularne', 'broń')")
    cursor.execute("INSERT INTO inventory (item_name, item_type) VALUES ('Stymulant Bojowy', 'medykament')")
    
    conn.commit()
    conn.close()

def update_game_state(hp, gold, location, summary):
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, item_type, quantity FROM inventory")
    rows = cursor.fetchall()
    conn.close()
    return [{"name": r[0], "type": r[1], "qty": r[2]} for r in rows]

# --- NOWE FUNKCJE OBSŁUGI TRWAŁEJ HISTORII CZATU ---

def save_chat_message(role, content):
    """Zapisuje pojedynczą wypowiedź do bazy danych, aby przetrwała odświeżenie strony."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rpg_chat_history (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def get_chat_history():
    """Zwraca pełną historię wiadomości RPG chronologicznie."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT role, content FROM rpg_chat_history ORDER BY id ASC")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def clear_all_rpg_data():
    """Całkowity reset gry RPG - czyszczenie wszystkich tabel."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM character_stats")
    cursor.execute("DELETE FROM inventory")
    cursor.execute("DELETE FROM rpg_chat_history")
    conn.commit()
    conn.close()

init_db()
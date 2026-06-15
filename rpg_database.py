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

    # 3. Historia czatu RPG
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rpg_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. Embeddingi wiadomości do RAG historii
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rpg_message_embeddings (
            message_id INTEGER PRIMARY KEY,
            embedding BLOB NOT NULL
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
    cursor.execute("DELETE FROM rpg_chat_history")
    
    cursor.execute("""
        INSERT INTO character_stats (name, character_class, hp, max_hp, gold, current_location, story_summary)
        VALUES (?, ?, 100, 100, 50, 'Nieznana lokacja', 'Przygoda się rozpoczyna.')
    """, (name, char_class))

    conn.commit()
    conn.close()

def get_inventory():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, item_type, quantity FROM inventory")
    rows = cursor.fetchall()
    conn.close()
    return [{"name": r[0], "type": r[1], "qty": r[2]} for r in rows]

# --- ZAAWANSOWANE FUNKCJE DLA ASYSTENTA AI ---

def modify_stats(hp_change=0, gold_change=0, new_location=None, summary=""):
    """Pozwala AI na zmianę zdrowia, złota i lokacji bohatera (wartości relatywne)"""
    char = get_character()
    if not char:
        return "Błąd: Postać nie istnieje."
    
    new_hp = max(0, min(char['max_hp'], char['hp'] + hp_change))
    new_gold = max(0, char['gold'] + gold_change)
    loc = new_location if new_location else char['location']
    sum_text = summary if summary else char['summary']
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE character_stats 
        SET hp = ?, gold = ?, current_location = ?, story_summary = ?
        WHERE id = ?
    """, (new_hp, new_gold, loc, sum_text, char['id']))
    conn.commit()
    conn.close()
    return f"Zaktualizowano postać. Nowe HP: {new_hp}, Nowe Złoto: {new_gold}, Lokacja: {loc}"

def add_inventory_item(item_name, item_type="przedmiot", quantity=1):
    """Pozwala AI na dodawanie przedmiotów lub zwiększanie ich ilości"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM inventory WHERE LOWER(item_name) = LOWER(?)", (item_name,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", (quantity, row[0]))
    else:
        cursor.execute("INSERT INTO inventory (item_name, item_type, quantity) VALUES (?, ?, ?)", (item_name, item_type, quantity))
    
    conn.commit()
    conn.close()
    return f"Dodano do ekwipunku: {item_name} x{quantity}"

def remove_inventory_item(item_name, quantity=1):
    """Pozwala AI na usuwanie przedmiotów na skutek zużycia lub kradzieży"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM inventory WHERE LOWER(item_name) = LOWER(?)", (item_name,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return f"Postać nie posiada przedmiotu: {item_name}"
    
    current_qty = row[1]
    if current_qty <= quantity:
        cursor.execute("DELETE FROM inventory WHERE id = ?", (row[0],))
        result = f"Usunięto całkowicie przedmiot: {item_name}"
    else:
        cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (quantity, row[0]))
        result = f"Zmniejszono ilość przedmiotu {item_name} o {quantity}"
        
    conn.commit()
    conn.close()
    return result

def set_starting_stats(max_hp, current_hp, gold):
    """Ustawia absolutne wartości startowe HP i złota na początku kampanii."""
    char = get_character()
    if not char:
        return "Błąd: Postać nie istnieje."
    current_hp = max(1, min(max_hp, current_hp))
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE character_stats SET hp = ?, max_hp = ?, gold = ? WHERE id = ?",
        (current_hp, max_hp, gold, char["id"]),
    )
    conn.commit()
    conn.close()
    return f"Ustawiono statystyki startowe: HP {current_hp}/{max_hp}, Kredyty: {gold}"


def save_chat_message(role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rpg_chat_history (role, content) VALUES (?, ?)", (role, content))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def save_message_embedding(message_id, embedding_bytes):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO rpg_message_embeddings (message_id, embedding) VALUES (?, ?)",
        (message_id, embedding_bytes),
    )
    conn.commit()
    conn.close()

def get_history_with_embeddings():
    """Zwraca wszystkie wiadomości historii z ich embeddingami (lub None jeśli brak)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT h.id, h.role, h.content, e.embedding
            FROM rpg_chat_history h
            LEFT JOIN rpg_message_embeddings e ON h.id = e.message_id
            ORDER BY h.id ASC
        """)
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return [{"id": r[0], "role": r[1], "content": r[2], "embedding": r[3]} for r in rows]

def get_chat_history():
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM character_stats")
    cursor.execute("DELETE FROM inventory")
    cursor.execute("DELETE FROM rpg_chat_history")
    cursor.execute("DELETE FROM rpg_message_embeddings")
    conn.commit()
    conn.close()

init_db()
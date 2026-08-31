import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any

DB_PATH = "imkopfhaben.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                category TEXT DEFAULT 'Notiz',
                priority TEXT DEFAULT 'normal',
                raw_transcript TEXT,
                created_at TEXT NOT NULL,
                is_done INTEGER DEFAULT 0
            )
        """)
        conn.commit()

def save_note(title: str, body: str, category: str = "Notiz", priority: str = "normal", raw_transcript: str = "") -> Dict[str, Any]:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (title, body, category, priority, raw_transcript, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, body, category, priority, raw_transcript, created_at))
        conn.commit()
        note_id = cursor.lastrowid
        return get_note_by_id(note_id)

def get_all_notes(limit: int = 50) -> List[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_note_by_id(note_id: int) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_note(note_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        return cursor.rowcount > 0

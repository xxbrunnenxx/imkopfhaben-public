import difflib
import sqlite3
from datetime import datetime, timedelta
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


def update_note(note_id: int, body: Optional[str] = None, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Titel wird beim Speichern immer auf die Kategorie gesetzt (wie beim
    urspruenglichen save_note) - beide Felder sollen nicht auseinanderlaufen."""
    felder, werte = [], []
    if body is not None:
        felder.append("body = ?")
        werte.append(body)
    if category is not None:
        felder.append("category = ?")
        werte.append(category)
        felder.append("title = ?")
        werte.append(category)
    if not felder:
        return get_note_by_id(note_id)
    werte.append(note_id)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE notes SET {', '.join(felder)} WHERE id = ?", werte)
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_note_by_id(note_id)


def find_similar_recent(raw_transcript: str, minutes: int = 10, threshold: float = 0.85) -> Optional[Dict[str, Any]]:
    """Sucht in den letzten `minutes` Minuten nach einer Notiz mit sehr
    aehnlichem Transkript (z.B. Doppel-Aufnahmen durch Testdruecken oder
    versehentliches Nachsprechen). Reiner String-Vergleich reicht hier -
    kein Embedding noetig fuer nahezu identische Transkripte."""
    if not raw_transcript:
        return None
    cutoff = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE created_at >= ? ORDER BY id DESC", (cutoff,))
        kandidaten = cursor.fetchall()
    for row in kandidaten:
        ratio = difflib.SequenceMatcher(None, raw_transcript.lower(), (row["raw_transcript"] or "").lower()).ratio()
        if ratio >= threshold:
            return dict(row)
    return None

import difflib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

DB_PATH = Path(__file__).parent / "imkopfhaben.db"

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

# priority und is_done: bewusst ungenutzt/reserviert. priority wird beim
# Speichern immer hart auf "normal" gesetzt und nirgends gelesen, is_done
# nirgends geschrieben oder gelesen - keine versteckte Funktion, die hier
# fehlt. Siehe Issue #5 fuer die Alternativen (aktiv nutzen z.B. als
# "Erledigt"-Haekchen in der Web-UI, oder Spalten per Migration entfernen).

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


def get_diary_entry_for_date(date_str: str) -> Optional[Dict[str, Any]]:
    """Sucht den (einen) Tagebuch-Eintrag fuer einen Kalendertag (`date_str`
    als "%Y-%m-%d"). Tagebuch-Eintraege werden pro Tag zusammengefuehrt statt
    als einzelne Notizen gefuehrt - hier wird geprueft, ob heute schon einer
    existiert."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM notes WHERE category = 'Tagebuch' AND created_at LIKE ? ORDER BY id DESC LIMIT 1",
            (f"{date_str}%",),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def _aehnlichster_treffer(text: str, kandidaten: List[str], threshold: float = 0.85) -> Optional[int]:
    """Vergleicht `text` per difflib.SequenceMatcher (Groß-/Kleinschreibung
    ignoriert) gegen jeden String in `kandidaten` und liefert den Index des
    ersten Treffers ab `threshold` Aehnlichkeit, sonst None. Gemeinsame Basis
    fuer diary_hat_aehnliches_segment() und find_similar_recent()."""
    text_lower = text.lower()
    for index, kandidat in enumerate(kandidaten):
        ratio = difflib.SequenceMatcher(None, text_lower, (kandidat or "").lower()).ratio()
        if ratio >= threshold:
            return index
    return None


def diary_hat_aehnliches_segment(eintrag: Dict[str, Any], transcript: str, threshold: float = 0.85) -> bool:
    """Prueft, ob der neue Transkript-Text einem bereits im Tageseintrag
    enthaltenen Abschnitt sehr aehnlich ist (Segmente sind per '\\n---\\n'
    getrennt, jeweils mit '[HH:MM] '-Praefix). Der normale
    find_similar_recent()-Dedupe greift beim Tagebuch nicht, weil dort
    immer an denselben Datensatz angehaengt statt eine neue Notiz erzeugt
    wird - ohne diesen Check haetten Doppel-Sendungen (z.B. durch die
    Warteschlange bei einem fluechtigen Netzwerkfehler) den Tageseintrag
    beliebig oft mit demselben Inhalt aufgebläht."""
    roh = eintrag.get("raw_transcript") or ""
    segmente = roh.split("\n---\n")
    inhalte = [
        segment.split("] ", 1)[1] if segment.startswith("[") and "] " in segment else segment
        for segment in segmente
    ]
    return _aehnlichster_treffer(transcript, inhalte, threshold) is not None


def append_to_diary(note_id: int, zeit: str, zusatz_body: str, zusatz_transcript: str) -> Optional[Dict[str, Any]]:
    """Haengt einen weiteren Eintrag mit Uhrzeit-Praefix an einen bestehenden
    Tagebuch-Tageseintrag an, statt eine neue Notiz anzulegen."""
    bestehend = get_note_by_id(note_id)
    if not bestehend:
        return None
    neuer_body = f"{bestehend['body']}\n[{zeit}] {zusatz_body}"
    bisheriges_transkript = bestehend.get("raw_transcript") or ""
    neues_transkript = f"{bisheriges_transkript}\n---\n[{zeit}] {zusatz_transcript}" if bisheriges_transkript else f"[{zeit}] {zusatz_transcript}"
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET body = ?, raw_transcript = ? WHERE id = ?",
            (neuer_body, neues_transkript, note_id),
        )
        conn.commit()
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
    index = _aehnlichster_treffer(raw_transcript, [row["raw_transcript"] for row in kandidaten], threshold)
    return dict(kandidaten[index]) if index is not None else None

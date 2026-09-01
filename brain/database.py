import difflib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

DB_PATH = Path(__file__).parent / "imkopfhaben.db"

# Die 7 Grundkategorien, die es schon vor der Kategorien-Pflege (Issue #16,
# Punkt 5) gab - werden beim ersten Start in die categories-Tabelle
# gesät und per ist_geschuetzt=1 vor automatischem Loeschen bewahrt, auch
# wenn gerade zufaellig keine Notiz dieser Kategorie existiert.
GRUNDKATEGORIEN = {
    "Todo": "#ff8c00",
    "Idee": "#3399ff",
    "Notiz": "#3ecf8e",
    "Termin": "#e64ac9",
    "Wichtig": "#e0453f",
    "Tagebuch": "#b088f5",
    "Unklar": "#7a8290",
}


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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY,
                color TEXT NOT NULL,
                ist_geschuetzt INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        # Eigene Tabelle mit Referenz auf notes statt einer Spalte an notes
        # selbst (Issue #16, Design-Entscheidung) - erlaubt spaeter mehrere
        # Veredelungs-Versionen/Historie pro Notiz, ohne das notes-Schema
        # anzufassen.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS veredelte_notizen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                veredelter_body TEXT NOT NULL,
                veredelte_kategorie TEXT,
                erstellt_am TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buendel_vorschlaege (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_ids TEXT NOT NULL,
                begruendung TEXT,
                erstellt_am TEXT NOT NULL
            )
        """)
        jetzt = datetime.now().strftime("%Y-%m-%d %H:%M")
        for name, color in GRUNDKATEGORIEN.items():
            cursor.execute(
                "INSERT OR IGNORE INTO categories (name, color, ist_geschuetzt, created_at) VALUES (?, ?, 1, ?)",
                (name, color, jetzt),
            )
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
        # Kein PRAGMA foreign_keys=ON gesetzt (muesste bei jeder Verbindung
        # wiederholt werden) - Aufraeumen der Veredelung hier von Hand statt
        # auf ON DELETE CASCADE zu vertrauen.
        cursor.execute("DELETE FROM veredelte_notizen WHERE note_id = ?", (note_id,))
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


def get_categories() -> Dict[str, str]:
    """Name -> Farbe, sortiert nach Anlagedatum. Einzige Quelle der Wahrheit
    fuer gueltige Kategorien (Live-Prompt, /api/config, Web-UI, Notebook)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, color FROM categories ORDER BY created_at")
        return dict(cursor.fetchall())


def add_category(name: str, color: str, ist_geschuetzt: bool = False) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO categories (name, color, ist_geschuetzt, created_at) VALUES (?, ?, ?, ?)",
            (name, color, int(ist_geschuetzt), datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        conn.commit()


def loesche_leere_kategorien() -> List[str]:
    """Entfernt echt (nicht nur ausgeblendet) alle Kategorien ohne
    zugehoerige Notiz - Besitzer-Entscheidung (Issue #16): eine leere
    Kategorie kann per Definition nichts verwaisen lassen, da keine Notiz
    darauf verweist. Geschuetzte Grundkategorien bleiben immer erhalten,
    auch wenn gerade leer. Gibt die Namen der geloeschten Kategorien zurueck."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM categories
            WHERE ist_geschuetzt = 0
              AND name NOT IN (SELECT DISTINCT category FROM notes)
        """)
        leere = [row[0] for row in cursor.fetchall()]
        if leere:
            cursor.executemany("DELETE FROM categories WHERE name = ?", [(n,) for n in leere])
            conn.commit()
        return leere


def save_veredelung(note_id: int, veredelter_body: str, veredelte_kategorie: Optional[str] = None) -> Dict[str, Any]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO veredelte_notizen (note_id, veredelter_body, veredelte_kategorie, erstellt_am) VALUES (?, ?, ?, ?)",
            (note_id, veredelter_body, veredelte_kategorie, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        conn.commit()
        cursor.execute("SELECT * FROM veredelte_notizen WHERE id = ?", (cursor.lastrowid,))
        return dict(cursor.fetchone())


def get_veredelung_for_note(note_id: int) -> Optional[Dict[str, Any]]:
    """Neueste Veredelung fuer eine Notiz, falls vorhanden."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM veredelte_notizen WHERE note_id = ? ORDER BY id DESC LIMIT 1",
            (note_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_notes_ohne_veredelung(limit: int = 1) -> List[Dict[str, Any]]:
    """Aelteste zuerst noch nicht veredelte Notizen - Basis fuer den
    Idle-Veredelungs-Trigger, der jeweils EINE Notiz pro Durchlauf
    veredelt (unterbrechbar zwischen den Schritten)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM notes
            WHERE id NOT IN (SELECT DISTINCT note_id FROM veredelte_notizen)
            ORDER BY id ASC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_category_counts() -> Dict[str, int]:
    """Fuer GET /api/counts - Notebook pollt das periodisch, um Server-
    seitige Aenderungen (Web-UI-Edits, Veredelung) zu erkennen, ohne dass
    das lokale Archiv aus dem Tritt geraet (Issue #11/#16)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT category, COUNT(*) FROM notes GROUP BY category")
        return dict(cursor.fetchall())


def speichere_buendel_vorschlaege(vorschlaege: List[Dict[str, Any]]) -> None:
    jetzt = datetime.now().strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO buendel_vorschlaege (note_ids, begruendung, erstellt_am) VALUES (?, ?, ?)",
            [(json.dumps(v["ids"]), v.get("begruendung", ""), jetzt) for v in vorschlaege],
        )
        conn.commit()


def get_buendel_vorschlaege() -> List[Dict[str, Any]]:
    """Fuer die Web-UI (roh+veredelt/Vorschlaege nebeneinander) - die
    Veredelung schlaegt Buendel nur vor, gemergt wird weiterhin ueber den
    bestehenden POST /api/notes/merge, den ein Mensch anstoesst."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM buendel_vorschlaege ORDER BY id DESC")
        ergebnis = []
        for row in cursor.fetchall():
            d = dict(row)
            d["note_ids"] = json.loads(d["note_ids"])
            ergebnis.append(d)
        return ergebnis


def loesche_buendel_vorschlag(vorschlag_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM buendel_vorschlaege WHERE id = ?", (vorschlag_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_alte_tagebuch_eintraege(vor_datum: str) -> List[Dict[str, Any]]:
    """Tagebuch-Tageseintraege vor `vor_datum` ("%Y-%m-%d"), aeltester
    zuerst - Basis fuer die mehrtaegige Verdichtung (Issue #16, Punkt 4)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM notes WHERE category = 'Tagebuch' AND created_at < ? ORDER BY created_at ASC",
            (vor_datum,),
        )
        return [dict(row) for row in cursor.fetchall()]


def zaehle_kategorie_vorschlag(name: str) -> int:
    """Wie oft `name` bereits als kategorie_vorschlag in gespeicherten
    Veredelungen auftaucht - Basis fuer die Schwelle, ab der die Veredelung
    eine neue Kategorie tatsaechlich anlegt (Issue #16, Punkt 5)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM veredelte_notizen WHERE veredelte_kategorie = ?",
            (name,),
        )
        return cursor.fetchone()[0]


def get_hoechste_notiz_id() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM notes")
        return cursor.fetchone()[0]


def get_hoechste_veredelung_id() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM veredelte_notizen")
        return cursor.fetchone()[0]


def get_veredelte_seit(seit_id: int) -> List[Dict[str, Any]]:
    """Fuer den Rueckkanal (Issue #16) - eigener Endpoint, getrennt vom
    allgemeinen /api/counts-Polling. Liefert veredelte Notizen mitsamt
    ihrem rohen Original, damit das Notebook beides ablegen/anzeigen
    kann (Diff-Vergleich)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.id AS veredelung_id, v.note_id, v.veredelter_body,
                   v.veredelte_kategorie, v.erstellt_am,
                   n.body AS roh_body, n.category AS roh_kategorie,
                   n.created_at AS notiz_erstellt_am
            FROM veredelte_notizen v
            JOIN notes n ON n.id = v.note_id
            WHERE v.id > ?
            ORDER BY v.id ASC
        """, (seit_id,))
        return [dict(row) for row in cursor.fetchall()]


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

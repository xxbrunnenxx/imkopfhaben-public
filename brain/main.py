import asyncio
import os
import shutil
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import database
import ai_service
import veredelung_service

STATIC_DIR = Path(__file__).parent / "static"

# Idle-Zeit-Veredelung (Issue #16): Pausenerkennung ist adaptiv/laenger
# gewaehlt (Entscheidung im Issue), kein knapper Wert - ein einzelner
# Veredelungsschritt braucht selbst schon 1-3 Minuten, da soll nicht nach
# jeder kurzen Sprechpause sofort losgelegt werden.
VEREDELUNG_PAUSE_SEK = 20 * 60
VEREDELUNG_CHECK_INTERVALL_SEK = 60

_letzte_process_zeit = time.monotonic()


async def _veredelungs_hintergrundschleife():
    """Prueft periodisch, ob seit VEREDELUNG_PAUSE_SEK kein /process mehr
    kam, und fuehrt dann GENAU EINEN Veredelungsschritt aus (in einem
    eigenen Thread, damit /process waehrenddessen nicht blockiert wird).
    Unterbrechung passiert dadurch, dass ein neuer /process-Aufruf
    _letzte_process_zeit sofort aktualisiert - der naechste Tick hier sieht
    dann wieder Aktivitaet und startet keinen neuen Schritt. Ein bereits
    laufender Schritt wird NICHT mitten in der Generierung abgebrochen
    (Design-Entscheidung aus Issue #16 - technisch nur mit deutlich mehr
    Aufwand sauber moeglich, bei seltenen, kurzen Ueberschneidungen nicht
    den Aufwand wert)."""
    while True:
        await asyncio.sleep(VEREDELUNG_CHECK_INTERVALL_SEK)
        idle_sek = time.monotonic() - _letzte_process_zeit
        if idle_sek < VEREDELUNG_PAUSE_SEK:
            continue
        try:
            ergebnis = await asyncio.to_thread(veredelung_service.fuehre_veredelung_schritt_aus)
            if ergebnis:
                print(f"[Veredelung] {ergebnis}")
        except Exception as e:
            print(f"[Veredelung Fehler] {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    hintergrund_task = asyncio.create_task(_veredelungs_hintergrundschleife())
    yield
    hintergrund_task.cancel()

app = FastAPI(title="imkopfhaben-brain API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
@app.get("/health")
def health_check():
    return {"status": "ok", "backend": "Pi 5", "model": ai_service.MODEL_NAME}

@app.get("/api/config")
def get_config():
    return {"categories": database.get_categories()}

@app.get("/api/notes")
def list_notes(limit: int = Query(50, ge=1, le=500)):
    return database.get_all_notes(limit=limit)

@app.get("/api/counts")
def get_counts():
    """Fuers periodische Notebook-Polling (Issue #16/#11) - erkennt
    Server-seitige Aenderungen (Web-UI-Edits, Veredelung), analog zum
    bestehenden 60s-Warteschlangen-Retry-Rhythmus im Notebook."""
    return {
        "counts": database.get_category_counts(),
        "hoechste_notiz_id": database.get_hoechste_notiz_id(),
        "hoechste_veredelung_id": database.get_hoechste_veredelung_id(),
    }

@app.get("/api/veredelt")
def list_veredelte(seit_id: int = Query(0, ge=0)):
    """Rueckkanal fuer veredelte Notizen (Issue #16) - eigener Endpunkt,
    getrennt vom allgemeinen /api/counts-Polling. `seit_id` = zuletzt
    abgeholte veredelung_id, damit das Notebook nur Neues nachlaedt."""
    return database.get_veredelte_seit(seit_id)

@app.get("/api/buendel-vorschlaege")
def get_buendel_vorschlaege():
    return database.get_buendel_vorschlaege()

@app.delete("/api/buendel-vorschlaege/{vorschlag_id}")
def loesche_buendel_vorschlag(vorschlag_id: int):
    success = database.loesche_buendel_vorschlag(vorschlag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden")
    return {"status": "deleted", "id": vorschlag_id}

# /process ist die Route, die dein Pi Zero (app.py) anspricht!
@app.post("/process")
@app.post("/api/process-audio")
async def process_audio(file: UploadFile = File(...)):
    global _letzte_process_zeit
    _letzte_process_zeit = time.monotonic()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # 1. Sprache zu Text mit Faster-Whisper
        transcript = ai_service.transcribe_audio(tmp_path)
        print(f"[Brain] Transkript: {transcript}")

        # 2. KI-Zusammenfassung mit Ollama (Llama 3.2)
        result = ai_service.structure_with_llm(transcript)
        print(f"[Brain] Ergebnis: {result}")

        # 3. In SQLite Datenbank archivieren.
        tag = result.get("tag", "Notiz")
        if tag == "Tagebuch":
            # Tagebuch-Eintraege werden pro Kalendertag zusammengefuehrt statt
            # als einzelne Notizen angelegt - jeder weitere Eintrag am selben
            # Tag wird mit Uhrzeit an den bestehenden Tageseintrag angehaengt.
            heute = datetime.now().strftime("%Y-%m-%d")
            zeit = datetime.now().strftime("%H:%M")
            bestehend = database.get_diary_entry_for_date(heute)
            if bestehend:
                if database.diary_hat_aehnliches_segment(bestehend, transcript):
                    print(f"[Brain] Tagebuch-Duplikat erkannt (Eintrag #{bestehend['id']}) - nicht erneut angehängt.")
                else:
                    database.append_to_diary(bestehend["id"], zeit, result.get("note", transcript), transcript)
            else:
                database.save_note(
                    title="Tagebuch",
                    body=f"[{zeit}] {result.get('note', transcript)}",
                    category="Tagebuch",
                    priority="normal",
                    raw_transcript=f"[{zeit}] {transcript}",
                )
        else:
            # Nicht speichern, wenn ein sehr aehnliches Transkript erst
            # kuerzlich schon gespeichert wurde (z.B. Doppel-Aufnahmen beim
            # Testen oder aus Versehen).
            doppelt = database.find_similar_recent(transcript)
            if doppelt:
                print(f"[Brain] Duplikat erkannt (Notiz #{doppelt['id']}) - nicht erneut gespeichert.")
            else:
                database.save_note(
                    title=tag,
                    body=result.get("note", transcript),
                    category=tag,
                    priority="normal",
                    raw_transcript=transcript
                )

        # Exaktes Format zurückgeben, das app.py erwartet:
        return {
            "tag": result.get("tag", "Notiz"),
            "note": result.get("note", transcript),
            "transcript": transcript
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int):
    success = database.delete_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notiz nicht gefunden")
    return {"status": "deleted", "id": note_id}


class NoteUpdate(BaseModel):
    body: Optional[str] = None
    category: Optional[str] = None


@app.patch("/api/notes/{note_id}")
def patch_note(note_id: int, update: NoteUpdate):
    updated = database.update_note(note_id, body=update.body, category=update.category)
    if not updated:
        raise HTTPException(status_code=404, detail="Notiz nicht gefunden")
    return updated


class NoteMerge(BaseModel):
    ids: List[int]
    body: Optional[str] = None
    category: Optional[str] = None


@app.post("/api/notes/merge")
def merge_notes(merge: NoteMerge):
    notizen = [n for n in (database.get_note_by_id(i) for i in merge.ids) if n]
    if len(notizen) < 2:
        raise HTTPException(status_code=400, detail="Mindestens 2 vorhandene Notizen noetig")
    notizen.sort(key=lambda n: n["created_at"])

    zusammengefasst_body = merge.body or " / ".join(n["body"] for n in notizen)
    zusammengefasste_kategorie = merge.category or notizen[0]["category"]
    zusammengefasstes_transkript = "\n---\n".join(n["raw_transcript"] or "" for n in notizen)

    neue_notiz = database.save_note(
        title=zusammengefasste_kategorie,
        body=zusammengefasst_body[:300],
        category=zusammengefasste_kategorie,
        priority="normal",
        raw_transcript=zusammengefasstes_transkript,
    )
    for n in notizen:
        database.delete_note(n["id"])
    return neue_notiz


@app.get("/", response_class=HTMLResponse)
def web_ui():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

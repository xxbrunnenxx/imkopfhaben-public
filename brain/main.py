import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import database
import ai_service

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="imkopfhaben-brain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    database.init_db()

@app.get("/api/health")
@app.get("/health")
def health_check():
    return {"status": "ok", "backend": "Pi 5", "model": ai_service.MODEL_NAME}

@app.get("/api/notes")
def list_notes(limit: int = 50):
    return database.get_all_notes(limit=limit)

# /process ist die Route, die dein Pi Zero (app.py) anspricht!
@app.post("/process")
@app.post("/api/process-audio")
async def process_audio(file: UploadFile = File(...)):
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

        # 3. In SQLite Datenbank archivieren - aber nicht, wenn ein sehr
        # aehnliches Transkript erst kuerzlich schon gespeichert wurde
        # (z.B. Doppel-Aufnahmen beim Testen oder aus Versehen).
        doppelt = database.find_similar_recent(transcript)
        if doppelt:
            print(f"[Brain] Duplikat erkannt (Notiz #{doppelt['id']}) - nicht erneut gespeichert.")
        else:
            database.save_note(
                title=result.get("tag", "Notiz"),
                body=result.get("note", transcript),
                category=result.get("tag", "Notiz"),
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

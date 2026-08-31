import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import database
import ai_service

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

        # 3. In SQLite Datenbank archivieren
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

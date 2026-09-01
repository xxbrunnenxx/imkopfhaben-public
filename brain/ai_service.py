import json
import requests
from faster_whisper import WhisperModel

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

print("Lade Faster-Whisper Modell (medium)...")
whisper_model = WhisperModel(
    "medium",
    device="cpu",
    compute_type="int8",
    cpu_threads=4
)

def transcribe_audio(audio_path: str) -> str:
    try:
        segments, _ = whisper_model.transcribe(
            audio_path,
            language="de",
            beam_size=5,
            vad_filter=True
        )
        transcript = " ".join([segment.text for segment in segments]).strip()
        return transcript
    except Exception as e:
        print(f"[Whisper Fehler]: {e}")
        return ""

def structure_with_llm(transcript: str) -> dict:
    if not transcript:
        return {
            "tag": "Unklar",
            "note": "Keine Sprache erkannt.",
            "transcript": ""
        }

    prompt = f"""Transkript: "{transcript}"

Aufgabe:
1. Bestimme die passende Kategorie als 'tag': Wähle genau eines aus ["Todo", "Idee", "Notiz", "Termin", "Wichtig", "Tagebuch", "Unklar"].
   - "Wichtig" NUR bei einem echten Dringlichkeits- oder Warnsignal (z.B. Gesundheit, Sicherheit, eine explizite Frist wie "sofort"/"dringend").
     Nicht einfach nehmen, weil der Ton auffällig, vulgär oder unklar ist.
   - "Tagebuch" für persönliche Rückblicke/Erlebnisse: wie der Tag/eine Aktivität war, Stimmung,
     Schlaf, was jemand oder etwas (auch ein Haustier) gerade gemacht hat. Erkennbar daran, dass
     es kein Auftrag/keine Idee ist, sondern eine Beobachtung oder Erinnerung ueber etwas Erlebtes.
   - "Unklar" für alles, das kein erkennbarer, in sich sinnvoller Inhalt ist: einzelne
     Wörter ohne Kontext, Fülllaute, Testphrasen ("Test", "Testnotiz"), Hintergrundrauschen,
     abgehackte Fragmente. Im Zweifel lieber "Unklar" als eine der anderen Kategorien erzwingen.
2. Fasse den Inhalt in 'note' prägnant zusammen (maximal 120 Zeichen).
   - Halte dich strikt an den Inhalt des Transkripts.
   - Erfinde keine zusätzlichen Informationen dazu.
   - Wenn das Transkript ein Spruch, Zitat oder Scherz ist, gib ihn sinngemäß als 'Notiz' oder 'Idee' wieder.
   - Bei "Unklar": gib einfach das Transkript selbst zurück, ohne es zu interpretieren.

Antworte ausschließlich im JSON-Format:
{{"tag": "<KATEGORIE>", "note": "<ZUSAMMENFASSUNG>"}}"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": -1,
        "options": {
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        raw_text = response.json().get("response", "{}")
        data = json.loads(raw_text)
        
        tag = data.get("tag", "Notiz")
        note = data.get("note", transcript).strip()
        
        return {
            "tag": tag,
            "note": note[:140],
            "transcript": transcript
        }
    except Exception as e:
        print(f"[LLM Fallback / Fehler]: {e}")
        return {
            "tag": "Notiz",
            "note": transcript[:140],
            "transcript": transcript
        }

# 🧠 imkopfhaben

> Ein lokales, sprachgesteuertes Notizbuch im Hosentaschenformat.
> Verarbeitet Sprachnotizen ohne Cloud, fasst sie per lokalem LLM zusammen und zeigt strukturierte Sticky-Notes auf einem runden Whisplay-Display an.

---

## 📐 Architektur

```text
┌──────────────────────────────────────┐        WLAN / HTTP         ┌─────────────────────────────────────────┐
│  notebook/  —  Pi Zero 2 W           │ ─────────────────────────> │  brain/  —  Raspberry Pi 5               │
│  - PiSugar Whisplay HAT              │   POST /process (.wav)     │  - STT: Faster-Whisper (Modell medium)   │
│  - 1,69" Farb-Display (240x280)      │                            │  - LLM: Ollama (qwen2.5:7b)               │
│  - Push-to-Talk Taster               │ <───────────────────────── │  - DB: SQLite (imkopfhaben.db)           │
│  - Audio: WM8960 Codec @ 48 kHz      │   JSON {"tag", "note"}     │  - FastAPI REST Server (Port 8000)       │
└──────────────────────────────────────┘                            └─────────────────────────────────────────┘
```

Dieses Repo enthält beide Seiten in einem Monorepo, aber sauber getrennt:

- **`brain/`** — läuft auf dem Pi 5, macht Spracherkennung + Zusammenfassung + Ablage
- **`notebook/`** — läuft auf dem Pi Zero 2 W, nimmt die Sprachnotiz auf und zeigt das Ergebnis an

Die beiden Teile kommunizieren ausschließlich über HTTP (ein `POST` mit der WAV-Datei, eine JSON-Antwort zurück) — kein gemeinsamer Code, kein gemeinsamer Prozess.

---

## 🛠️ Hardware

**Client (`notebook/`)**
- Raspberry Pi Zero 2 W
- PiSugar Whisplay HAT (1,69" LCD, WM8960 Audio-Codec, Push-Button, RGB-LED)

**Server (`brain/`)**
- Raspberry Pi (ausreichend RAM für ein 7B-Modell resident im Speicher, z. B. Pi 5 mit 16 GB)
- Lokale KI-Umgebung mit Faster-Whisper und Ollama (`qwen2.5:7b` oder vergleichbar)

---

## ⚙️ Technische Besonderheiten

**WM8960 48-kHz-Audioaufnahme**
Der WM8960-Codec des Whisplay HAT wird mit 48 kHz betrieben, um PLL-Taktfehler und Knackgeräusche beim Aufnehmen zu vermeiden (ein 16-kHz-Direktzugriff auf die Hardware bringt den Codec-Takt durcheinander). Faster-Whisper resampelt das Audio serverseitig automatisch auf 16 kHz.

**RAM-residentes LLM**
Mittels `keep_alive: -1` bleibt das Ollama-Modell dauerhaft im Arbeitsspeicher resident — keine Kaltstartverzögerung bei jeder Notiz.

**Automatischer Word-Wrap**
Notizen werden anhand der tatsächlichen Pixelbreite der Schrift umgebrochen, nicht anhand fester Zeichenzahlen — passt sich damit an unterschiedliche Fonts/Displaybreiten an.

---

## 🚀 Installation & Start

### A. `brain/` (Pi 5 / Server)

```bash
cd brain
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# LLM laden
ollama pull qwen2.5:7b

# Starten
uvicorn main:app --host 0.0.0.0 --port 8000
```

Für Dauerbetrieb: `imkopfhaben-brain.service` nach `/etc/systemd/system/` kopieren, Pfade in `WorkingDirectory`/`ExecStart` an die eigene Installation anpassen, dann:

```bash
sudo systemctl enable --now imkopfhaben-brain.service
```

### B. `notebook/` (Pi Zero 2 W / Client)

Voraussetzung: der PiSugar-Whisplay-Treiber (`whisplay_client.py`) ist bereits installiert und im Pfad erreichbar.

```bash
cd notebook
pip3 install -r requirements.txt

# Starten
python3 app.py
```

In `app.py` steht `SERVER_URL` auf den Hostnamen des Brain-Servers im eigenen Netz — vor dem ersten Start anpassen.

Für Dauerbetrieb: `imkopfhaben-notebook.service` nach `/etc/systemd/system/` kopieren, Pfade/User anpassen, dann:

```bash
sudo systemctl enable --now imkopfhaben-notebook.service
```

---

## 📡 API-Spezifikation (`brain/`)

### `POST /process` (Alias: `POST /api/process-audio`)
- Payload: `multipart/form-data` (`file`: WAV-Audiodatei)
- Response:
  ```json
  {
    "tag": "Todo | Idee | Notiz | Termin | Wichtig",
    "note": "Zusammenfassung der Notiz",
    "transcript": "Wortwörtlich gesprochener Text"
  }
  ```

### `GET /api/notes`
Gibt alle Notizen aus der SQLite-Datenbank zurück, neueste zuerst.

### `DELETE /api/notes/{note_id}`
Löscht eine einzelne Notiz.

### `GET /api/health` (Alias: `GET /health`)
Kurzer Status-Check, meldet u. a. das aktive LLM-Modell.

---

## 📁 Aufbau

```text
imkopfhaben/
├── .gitignore
├── README.md
├── brain/
│   ├── main.py
│   ├── ai_service.py
│   ├── database.py
│   ├── requirements.txt
│   └── imkopfhaben-brain.service
└── notebook/
    ├── app.py
    ├── requirements.txt
    └── imkopfhaben-notebook.service
```

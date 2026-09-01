# 🧠 imkopfhaben

> Ein lokales, sprachgesteuertes Notizbuch im Hosentaschenformat.
> Verarbeitet Sprachnotizen ohne Cloud, fasst sie per lokalem LLM zusammen, zeigt sie auf einem runden Whisplay-Display an und lässt sie sich über eine Web-Oberfläche aufräumen.

---

## 📐 Architektur

```text
┌──────────────────────────────────────┐        WLAN / HTTP         ┌─────────────────────────────────────────┐
│  notebook/  —  Pi Zero 2 W           │ ─────────────────────────> │  brain/  —  Raspberry Pi 5               │
│  - PiSugar Whisplay HAT              │   POST /process (.wav)     │  - STT: Faster-Whisper (Modell medium)   │
│  - 1,69" Farb-Display               │                            │  - LLM: Ollama (qwen2.5:7b)               │
│  - Push-Taster (Toggle-Aufnahme)     │ <───────────────────────── │  - DB: SQLite (imkopfhaben.db)           │
│  - Audio: WM8960 Codec @ 48 kHz      │   JSON {"tag", "note"}     │  - FastAPI REST Server + Web-UI (Port 8000) │
│  - Warteschlange bei Verbindungsausfall │                         │                                           │
└──────────────────────────────────────┘                            └─────────────────────────────────────────┘
```

Dieses Repo enthält beide Seiten in einem Monorepo, aber sauber getrennt:

- **`brain/`** — läuft auf dem Pi 5: Spracherkennung, Zusammenfassung, Ablage, Web-Oberfläche zum Aufräumen der Notizen
- **`notebook/`** — läuft auf dem Pi Zero 2 W: nimmt die Sprachnotiz auf, zeigt das Ergebnis an, hält Notizen bei Verbindungsausfall lokal in einer Warteschlange zurück

Die beiden Teile kommunizieren ausschließlich über HTTP (ein `POST` mit der WAV-Datei, eine JSON-Antwort zurück) — kein gemeinsamer Code, kein gemeinsamer Prozess.

---

## 🎛️ Bedienung (`notebook/`)

Ein einziger Taster, per Toggle statt Halten:

| Zustand | Kurz drücken | Lang halten |
|---|---|---|
| Dashboard | Aufnahme starten | Rein ins Durchblättern |
| Aufnahme läuft | Beenden & senden (egal wie lang gedrückt) | — |
| Durchblättern | Eine Notiz weiter (am Ende wieder von vorn) | Zurück ins Dashboard |

Das Dashboard zeigt Anzahl offener Todos/Ideen/Notizen, den vom Akku-Lerner geschätzten Ladezustand und — falls vorhanden — wie viele Notizen gerade in der Warteschlange auf eine Verbindung zum Brain warten.

---

## 🛠️ Hardware

**Client (`notebook/`)**
- Raspberry Pi Zero 2 W
- PiSugar Whisplay HAT (LCD, WM8960 Audio-Codec, Push-Button, RGB-LED)

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

**Warteschlange statt Datenverlust**
Ist der Brain nicht erreichbar, landet die fertige Aufnahme statt in einer einzelnen überschreibbaren Datei in `~/notiz_warteschlange/` (Zeitstempel-Dateiname). Zwei Trigger arbeiten sie ab: sofort beim nächsten Tastendruck, und alle 60s automatisch im Hintergrund, solange das Dashboard steht. Ältestenzuerst, bricht beim ersten Fehlschlag ab, ein `threading.Lock` verhindert, dass beide Trigger sich gleichzeitig an derselben Datei zu schaffen machen.

**Akku-Lerner**
`notebook/akku_lernen.py` (Vorbild: `barthal/akku_lernen.py` aus dem Schwesterprojekt barthalomeus) — eigener, unabhängiger Dienst, der beobachtet, wie lange der Akku zwischen zwei echten Stromausfällen durchhält, und daraus eine Prozentschätzung lernt. Zeigt "Baked!" statt eines erfundenen Werts, bis der erste echte Zyklus abgeschlossen ist.

**Duplikat-Erkennung & geschärfte Kategorisierung**
`brain/database.find_similar_recent()` vergleicht neue Transkripte gegen die letzten 10 Minuten (String-Ähnlichkeit) und verhindert Doppel-Notizen. Die Kategorie "Wichtig" wird nur bei echtem Dringlichkeitssignal vergeben, unklare/zu kurze Transkripte landen in der eigenen Kategorie "Unklar" statt zwangsweise in einer der Sinn-Kategorien.

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

Läuft `brain/` stattdessen manuell mit einem Shell-Redirect (z. B. `... > brain.log 2>&1 &`), wächst `brain.log` sonst unbegrenzt. `imkopfhaben-brain.logrotate` nach `/etc/logrotate.d/` kopieren (Pfad darin an die eigene Installation anpassen):

```bash
sudo cp brain/imkopfhaben-brain.logrotate /etc/logrotate.d/imkopfhaben-brain
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

Für Dauerbetrieb: `imkopfhaben-notebook.service` **und** `imkopfhaben-notebook-akku-lerner.service` nach `/etc/systemd/system/` kopieren, Pfade/User anpassen, dann:

```bash
sudo systemctl enable --now imkopfhaben-notebook.service
sudo systemctl enable --now imkopfhaben-notebook-akku-lerner.service
```

---

## 🌐 Web-Oberfläche

Unter `http://<brain-host>:8000/` (z.B. `http://kraken.local:8000/`) liegt eine kleine Oberfläche zum Aufräumen der Notizen: nach Kategorie filtern, Text und Kategorie bearbeiten, einzeln oder mehrfach löschen, mehrere Notizen zu einer zusammenführen.

---

## 📡 API-Spezifikation (`brain/`)

### `POST /process` (Alias: `POST /api/process-audio`)
- Payload: `multipart/form-data` (`file`: WAV-Audiodatei)
- Response:
  ```json
  {
    "tag": "Todo | Idee | Notiz | Termin | Wichtig | Unklar",
    "note": "Zusammenfassung der Notiz",
    "transcript": "Wortwörtlich gesprochener Text"
  }
  ```

### `GET /api/notes`
Gibt alle Notizen aus der SQLite-Datenbank zurück, neueste zuerst.

### `PATCH /api/notes/{note_id}`
Bearbeitet `body` und/oder `category` einer bestehenden Notiz.

### `POST /api/notes/merge`
Führt mehrere Notizen (`ids`, optional `body`/`category`) zu einer neuen zusammen und löscht die Originale.

### `DELETE /api/notes/{note_id}`
Löscht eine einzelne Notiz.

### `GET /api/health` (Alias: `GET /health`)
Kurzer Status-Check, meldet u. a. das aktive LLM-Modell.

### `GET /`
Liefert die Web-Oberfläche aus.

---

## 📁 Aufbau

```text
imkopfhaben/
├── .gitignore
├── README.md
├── OFFENE_PUNKTE.md
├── brain/
│   ├── main.py
│   ├── ai_service.py
│   ├── database.py
│   ├── static/
│   │   └── index.html
│   ├── requirements.txt
│   ├── imkopfhaben-brain.service
│   └── imkopfhaben-brain.logrotate
└── notebook/
    ├── app.py
    ├── akku_lernen.py
    ├── requirements.txt
    ├── imkopfhaben-notebook.service
    └── imkopfhaben-notebook-akku-lerner.service
```

Offene Punkte und bekannte Baustellen: siehe [`OFFENE_PUNKTE.md`](OFFENE_PUNKTE.md).

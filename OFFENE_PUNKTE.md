# Offene Punkte

Stand: 2026-08-31.

## Hohe Prio

- [ ] **Notizen gehen bei nicht erreichbarem Brain verloren** — `notebook/app.py` (`_send_recording`) macht genau einen synchronen `POST /process` mit 60s Timeout, ohne Retry oder Zwischenspeicherung. Ist Kraken/Brain nicht erreichbar, zeigt das Display 3s einen Fehler und geht zurück zum Dashboard — die Aufnahme selbst (`/tmp/note.wav`) bleibt zwar liegen, wird aber beim nächsten Tastendruck kommentarlos überschrieben. Keine Warteschlange, kein späteres Nachsenden. Braucht: lokale Warteschlange (z.B. WAV-Dateien mit Zeitstempel in einem Ordner behalten, bei jedem erfolgreichen Health-Check/Sendeversuch der Reihe nach abarbeiten), bis dahin ist ein Ausfall von Kraken während des Testzeitraums ein echter Datenverlust.

## Übrige Punkte

- [x] **Akku-Lerner-Modul einbauen** — `notebook/akku_lernen.py` (Vorbild: `barthal/akku_lernen.py` auf barthalomeus), läuft als eigener Dienst `imkopfhaben-notebook-akku-lerner.service`, Anzeige nur im Dashboard ("Akku: ..."), auf dem Gerät installiert und aktiv.
- [x] **Autostart für `notebook/`** — `imkopfhaben-notebook.service` installiert und aktiviert, startet nach Reboot/Stromausfall wieder von selbst ins Dashboard.
- [ ] **Display drehen** — `notebook/`: Anzeige läuft aktuell im Hochformat, muss auf Querformat (90°) gedreht werden.
- [ ] **Display-Struktur/Optik verbessern** — *low priority*, da das Whisplay-Display nicht die finale Ausbaustufe ist. Ziel-Hardware ist ein ESP32-S3-Board mit E-Ink-Display; Aufwand hier entsprechend gering halten.
- [ ] **Autostart für `brain/`** — läuft aktuell nur manuell im Hintergrund, kein systemd-Dienst aktiv (die Unit-Datei `brain/imkopfhaben-brain.service` liegt bereits im Repo, ist aber nirgends installiert). Nach einem Neustart des Pi 5 bleibt das Backend tot, bis es von Hand gestartet wird. **Wird separat behandelt, noch nicht jetzt.**
- [ ] **Log-Rotation für `brain.log`** — wächst unbegrenzt, solange der Prozess läuft.
- [ ] **Kaltstart-Zeit** — Faster-Whisper (medium) lädt bei jedem Neustart neu, das Backend braucht dadurch spürbar Anlaufzeit, bevor die erste Notiz verarbeitet werden kann.
- [ ] **Web-Oberfläche für Notizen** — Notizen bearbeiten, verschieben, zusammenführen usw. über eine Webseite, die auf Kraken läuft (horcht dort, `brain/`-seitig).

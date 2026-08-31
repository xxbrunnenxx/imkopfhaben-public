# Offene Punkte

Stand: 2026-08-31.

- [x] **Akku-Lerner-Modul einbauen** — `notebook/akku_lernen.py` (Vorbild: `barthal/akku_lernen.py` auf barthalomeus), läuft als eigener Dienst `imkopfhaben-notebook-akku-lerner.service`, Anzeige nur im Dashboard ("Akku: ..."), auf dem Gerät installiert und aktiv.
- [x] **Autostart für `notebook/`** — `imkopfhaben-notebook.service` installiert und aktiviert, startet nach Reboot/Stromausfall wieder von selbst ins Dashboard.
- [ ] **Display drehen** — `notebook/`: Anzeige läuft aktuell im Hochformat, muss auf Querformat (90°) gedreht werden.
- [ ] **Display-Struktur/Optik verbessern** — *low priority*, da das Whisplay-Display nicht die finale Ausbaustufe ist. Ziel-Hardware ist ein ESP32-S3-Board mit E-Ink-Display; Aufwand hier entsprechend gering halten.
- [ ] **Autostart für `brain/`** — läuft aktuell nur manuell im Hintergrund, kein systemd-Dienst aktiv (die Unit-Datei `brain/imkopfhaben-brain.service` liegt bereits im Repo, ist aber nirgends installiert). Nach einem Neustart des Pi 5 bleibt das Backend tot, bis es von Hand gestartet wird. **Wird separat behandelt, noch nicht jetzt.**
- [ ] **Log-Rotation für `brain.log`** — wächst unbegrenzt, solange der Prozess läuft.
- [ ] **Kaltstart-Zeit** — Faster-Whisper (medium) lädt bei jedem Neustart neu, das Backend braucht dadurch spürbar Anlaufzeit, bevor die erste Notiz verarbeitet werden kann.
- [ ] **Web-Oberfläche für Notizen** — Notizen bearbeiten, verschieben, zusammenführen usw. über eine Webseite, die auf Kraken läuft (horcht dort, `brain/`-seitig).

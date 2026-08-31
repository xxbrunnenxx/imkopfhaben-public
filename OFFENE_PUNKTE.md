# Offene Punkte

Stand: 2026-08-31. Gesammelt, noch nicht umgesetzt.

- [ ] **Display drehen** — `notebook/`: Anzeige läuft aktuell im Hochformat, muss auf Querformat (90°) gedreht werden.
- [ ] **Akku-Lerner-Modul einbauen** — muss ins `notebook/` integriert werden (Vorbild: `barthal-akku-lerner.service` auf barthalomeus).
- [ ] **Display-Struktur/Optik verbessern** — *low priority*, da das Whisplay-Display nicht die finale Ausbaustufe ist. Ziel-Hardware ist ein ESP32-S3-Board mit E-Ink-Display; Aufwand hier entsprechend gering halten.
- [ ] **Autostart für `brain/`** — läuft aktuell nur manuell im Hintergrund, kein systemd-Dienst aktiv (die Unit-Datei `brain/imkopfhaben-brain.service` liegt bereits im Repo, ist aber nirgends installiert). Nach einem Neustart des Pi 5 bleibt das Backend tot, bis es von Hand gestartet wird.
- [ ] **Log-Rotation für `brain.log`** — wächst unbegrenzt, solange der Prozess läuft.
- [ ] **Kaltstart-Zeit** — Faster-Whisper (medium) lädt bei jedem Neustart neu, das Backend braucht dadurch spürbar Anlaufzeit, bevor die erste Notiz verarbeitet werden kann.

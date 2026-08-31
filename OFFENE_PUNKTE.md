# Offene Punkte

Stand: 2026-08-31.

## Übrige Punkte

- [x] **Notizen gehen bei nicht erreichbarem Brain verloren** — behoben: `notebook/app.py` verschiebt jede fertige Aufnahme in `~/notiz_warteschlange/` (Zeitstempel-Dateiname, `shutil.move` statt `Path.rename`, weil `/tmp` und `~` auf verschiedenen Geräten liegen — reines `rename()` scheiterte live mit "Invalid cross-device link"). `_verarbeite_warteschlange()` sendet ältestenzuerst, bricht beim ersten Fehlschlag ab. Zwei Trigger: sofort bei jedem neuen Tastendruck, plus alle 60s im Hintergrund (`run()`), solange das Dashboard steht. Ein `threading.Lock` verhindert, dass beide sich gleichzeitig an derselben Datei zu schaffen machen (live als Race Condition beobachtet: "No such file or directory", weil beide dieselbe Datei parallel verarbeitet haben). Live getestet: 3 Notizen bei totem Brain aufgenommen, alle sicher in der Warteschlange gelandet, nach Neustart des Brain automatisch nachgesendet, keine verloren.
- [x] **Tastermodell überarbeitet** — von "halten = aufnehmen" auf Toggle umgestellt: kurz drücken = Aufnahme starten, nochmal drücken (egal wie lang) = beenden & senden, lang halten = Blättern rein/raus, im Blättern kurz = weiter (am Ende wieder von vorn). Nebenbei einen Bug gefixt, der das alte Blättern komplett unerreichbar gemacht hat (`_on_press` startete im Dashboard-Modus immer sofort eine Aufnahme, die Weiche für "lang halten" in `_on_release` kam nie dran).
- [x] **Akku-Lerner-Modul einbauen** — `notebook/akku_lernen.py` (Vorbild: `barthal/akku_lernen.py` auf barthalomeus), läuft als eigener Dienst `imkopfhaben-notebook-akku-lerner.service`, Anzeige nur im Dashboard ("Akku: ..."), auf dem Gerät installiert und aktiv.
- [x] **Autostart für `notebook/`** — `imkopfhaben-notebook.service` installiert und aktiviert, startet nach Reboot/Stromausfall wieder von selbst ins Dashboard.
- [ ] **Display drehen** — `notebook/`: Anzeige läuft aktuell im Hochformat, muss auf Querformat (90°) gedreht werden.
- [ ] **Display-Struktur/Optik verbessern** — *low priority*, da das Whisplay-Display nicht die finale Ausbaustufe ist. Ziel-Hardware ist ein ESP32-S3-Board mit E-Ink-Display; Aufwand hier entsprechend gering halten.
- [ ] **Autostart für `brain/`** — läuft aktuell nur manuell im Hintergrund, kein systemd-Dienst aktiv (die Unit-Datei `brain/imkopfhaben-brain.service` liegt bereits im Repo, ist aber nirgends installiert). Nach einem Neustart des Pi 5 bleibt das Backend tot, bis es von Hand gestartet wird. **Wird separat behandelt, noch nicht jetzt.**
- [ ] **Log-Rotation für `brain.log`** — wächst unbegrenzt, solange der Prozess läuft.
- [ ] **Kaltstart-Zeit** — Faster-Whisper (medium) lädt bei jedem Neustart neu, das Backend braucht dadurch spürbar Anlaufzeit, bevor die erste Notiz verarbeitet werden kann.
- [ ] **Web-Oberfläche für Notizen** — Notizen bearbeiten, verschieben, zusammenführen usw. über eine Webseite, die auf Kraken läuft (horcht dort, `brain/`-seitig).

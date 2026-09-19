# imkopfhaben-brain -- Anleitung zum Starten und Stoppen

Dieser Ordner ist das "Gehirn" auf dem Kraken (dein Pi 5) fuer das
ESP32-Notizbuch. Das Geraet selbst nimmt deine Sprache auf und schickt sie
an den Kraken. Hier auf dem Kraken passieren zwei Dinge:

1. **Aus Sprache wird Text** (das erledigt "Whisper").
2. **Ein kleines Sprachmodell** (gemma-4-e2b, laeuft in "LM Studio") wird
   benutzt, wenn du am Geraet auf "Zusammenfassen" drueckst.

Damit das Geraet mit dem Kraken reden kann, muessen diese zwei Dienste
laufen.

---

## Wichtig: das laeuft NICHT von allein

Bewusste Entscheidung: Diese Dienste starten **nicht automatisch**. Der
Kraken soll im Ruhezustand nichts unnoetig im Hintergrund laufen lassen und
sparsam bleiben. Das heisst:

> **Nach jedem Neustart des Kraken ist alles aus.** Du musst den Start
> jedes Mal selbst eingeben, wenn du das Notizbuch benutzen willst.

Das ist kein Fehler, das ist so gewollt.

---

## So startest du (Schritt fuer Schritt)

Du brauchst dazu ein Terminal auf dem Kraken. Wenn der Kraken gerade frisch
hochgefahren ist, meldest du dich zuerst an. Am Anmelde-Bildschirm steht:

```
kraken login:
```

- Benutzername: **kraken**
- (Der Rechner heisst ebenfalls **kraken**, deshalb steht dort
  `kraken@kraken`, sobald du drin bist. Das ist normal.)

Bist du angemeldet, gib genau diese zwei Zeilen ein:

```bash
cd ~/imkopfhaben-public/brain
./imkopfhaben-start.sh
```

Jetzt heisst es kurz warten. Beim ersten Start nach einem Neustart laedt der
Kraken die Modelle in den Speicher, das dauert eine Weile (bis zu ein, zwei
Minuten). Du siehst mitlaufende Punkte. Wenn alles bereit ist, steht am Ende:

```
=== Beide Dienste bereit ===
Das Geraet kann jetzt aufnehmen. ...
```

**Ab jetzt** kannst du das ESP32-Geraet benutzen: aufnehmen, es schickt an
den Kraken, du bekommst deinen Text zurueck.

Sollte etwas nicht hochkommen, bricht das Skript mit einer klaren
`FEHLER:`-Zeile ab und sagt, woran es lag.

---

## So stoppst du (wenn du fertig bist)

Damit der Kraken wieder lastfrei ist und nichts im Speicher haengen bleibt:

```bash
cd ~/imkopfhaben-public/brain
./imkopfhaben-stop.sh
```

Danach ist beides aus: das Sprachmodell ist aus dem Speicher geworfen, der
Whisper-Dienst ist beendet. Am Ende steht:

```
=== Fertig -- der Kraken ist wieder lastfrei ===
```

Du musst nicht zwingend stoppen, bevor du den Kraken ausschaltest -- ein
Neustart raeumt ohnehin alles weg. Das Stoppen ist fuer den Fall, dass du
den Kraken anlaesst, aber das Notizbuch gerade nicht brauchst.

---

## Haeufige Fragen

**Ich habe den Kraken neu gestartet und das Geraet findet ihn nicht mehr.**
Richtig, nach einem Neustart ist alles aus. Einmal `./imkopfhaben-start.sh`
(siehe oben), dann geht es wieder.

**Muss ich etwas installieren?**
Nein, wenn der Kraken schon eingerichtet ist. Das Skript nutzt, was da ist
(LM Studio und die brain-Umgebung `venv`). Fehlt die `venv`, sagt das Skript
es dir mit dem passenden Befehl.

**Woran erkenne ich, dass es laeuft?**
Nach dem Start kannst du in einem Terminal auf dem Kraken pruefen:

```bash
curl http://127.0.0.1:8000/api/health
```

Kommt `{"status":"ok",...}` zurueck, laeuft der Whisper-Dienst.

**Wo landen meine Notizen?**
Die Aufnahmen und ihre Texte liegen auf der SD-Karte **im Geraet selbst**,
nicht auf dem Kraken. Der Kraken macht nur aus Sprache Text und schickt ihn
zurueck -- er speichert die Notizen nicht. Der Text kommt so zurueck, wie
Whisper ihn verstanden hat (roh, ohne Nachpolieren) -- das ist bewusst so.

---

## Was da technisch laeuft (Kurzfassung)

| Dienst | Port | Aufgabe | Startbefehl im Skript |
|---|---|---|---|
| LM Studio | 1234 | Sprachmodell gemma-4-e2b fuer "Zusammenfassen" | `lms server start` + `lms load` |
| brain | 8000 | Whisper: Sprache -> Text | `uvicorn main:app` |

Beide horchen auf `0.0.0.0`, damit das ESP32 sie ueber `kraken.local`
erreicht. Die Firmware ist ab Werk auf `http://kraken.local:1234/v1/` und
`http://kraken.local:8000/api/transcribe-raw` eingestellt.

## Notizen auf den USB-Stick legen (offline weiterarbeiten)

`brain/notizen-exportieren.py` schreibt den Bestand als gewöhnliche
Markdown-Dateien auf den Stick, in einer Form, die Obsidian direkt lesen
kann (YAML-Frontmatter mit Tags). Danach lässt sich ohne Pi, ohne Gerät
und ohne Netz damit arbeiten — ein Texteditor genügt.

```bash
brain/notizen-exportieren.py                   # Standardziel auf dem Stick
brain/notizen-exportieren.py --ziel /pfad      # woanders hin
brain/notizen-exportieren.py --host 10.0.0.5   # anderes Gerät
```

Standardziel ist `/mnt/gigastick/Pi5Backup_old version/vault/07-imkopfhaben/`
— **im** Obsidian-Vault, nicht daneben. Obsidian zeigt ausschließlich, was
unterhalb des Vault-Ordners liegt (erkennbar an dessen `.obsidian/`); ein
Ordner eine Ebene darüber bleibt unsichtbar. Hängt der Stick nicht, einmal
`sudo mount /dev/sda1 /mnt/gigastick`.

Was entsteht:

| Datei | Inhalt |
|---|---|
| `00-Uebersicht.md` | Stand, Verteilung, Erklärung |
| `01-Tagebuch/` | je Tag eine Datei, chronologisch |
| `02-Aufgaben.md` | Aufgaben als abhakbare Liste, offen und erledigt getrennt |
| `03-Ideen.md` | Ideen und Notizen |
| `04-Zusammenfassungen/` | die Fassungen, die das Gerät erzeugt hat |
| `05-Eigene-Notizen/` | deins. Der Export fasst dieses Verzeichnis nie an |

Zwei Dinge, die man wissen muss:

**Der Export überschreibt.** Ein zweiter Lauf frischt den Stand auf und
schreibt die Dateien oben neu. Eigene Gedanken gehören deshalb nach
`05-Eigene-Notizen/`, das bleibt unangetastet.

**Der Export geht nur in eine Richtung.** Ein Haken, den du auf dem Stick
setzt, wandert nicht zum Gerät zurück. Das Gerät bleibt die Quelle, der
Stick trägt eine Kopie. Eine echte Synchronisierung wäre ein eigenes
Vorhaben mit eigenen Fallen (zwei Seiten, die beide geändert wurden) und
ist bewusst nicht gebaut.

Ist das Gerät nicht erreichbar, läuft der Export allein aus der
Mitschrift (`~/imkopfhaben-mitschrift/`). Dann fehlen Tags, Erledigt-Haken
und Zusammenfassungen, der Text ist aber vollständig da.

### Stündlich von selbst, solange die Dienste laufen (19.09.2026)

Der Abgleich läuft automatisch, **hängt aber an den Diensten**:
`imkopfhaben-start.sh` startet `imkopfhaben-stick.timer` mit,
`imkopfhaben-stop.sh` stoppt ihn wieder. Von Hand ist nichts weiter zu tun.

Der Timer hat bewusst **kein `[Install]`** und springt deshalb beim Booten
nicht von selbst an — `systemctl enable` greift bei ihm gar nicht, das ist
Absicht. Grund: sind die Dienste aus, entstehen keine neuen Notizen. Ein
Zeitgeber, der dann trotzdem stündlich aufwacht, den Stick einhängt und
dieselben Dateien noch einmal schreibt, wäre genau die Dauerlast, die auf
diesem Pi nicht sein soll.

Beim Start läuft zusätzlich sofort ein Abgleich, statt bis zur vollen
Stunde zu warten: während die Dienste aus waren, kann das Gerät Notizen
nachgereicht haben.

```bash
systemctl list-timers imkopfhaben-stick.timer   # wann läuft er das nächste Mal
journalctl -u imkopfhaben-stick.service -n 20   # was war beim letzten Mal
sudo systemctl start imkopfhaben-stick.service  # jetzt sofort abgleichen
sudo systemctl stop imkopfhaben-stick.timer     # nur für diese Sitzung aus
```

**Der Stick darf fehlen.** Steckt er nicht, meldet der Lauf „Stick steckt
nicht" und endet ohne Fehler — kein rotes systemd-Unit, kein Alarm. Steckt
er beim nächsten Mal wieder, wird er an seiner UUID erkannt, eingehängt,
beschrieben und **wieder ausgehängt**. Du kannst ihn also jederzeit
abziehen, ohne etwas anzuhalten.

Erkannt wird er an der UUID `B218B41F18B3E111`, nicht an `/dev/sda1`: die
Gerätenamen vergibt der Kernel nach Steckreihenfolge, und ein Skript, das
einhängt und schreibt, darf nicht auf die falsche Platte greifen. Ein
anderer Stick braucht eine neue UUID in `notizen-auf-stick.sh` (`lsblk -no
UUID,LABEL`).

War der Pi aus, als ein Lauf fällig gewesen wäre, holt `Persistent=true`
ihn beim nächsten Hochfahren nach. Ein Rückstand kann sich ohnehin nicht
anhäufen: der Export schreibt immer den vollen Stand, nicht die Differenz.

Warum ein Timer hier vertretbar ist, obwohl LM Studio bewusst keinen Dienst
hat: der Lauf dauert Sekunden und liest nur. Er hält den Pi nicht wach und
weckt kein Sprachmodell.

**Was er nicht tut:** neu zusammenfassen. Die Zusammenfassungen entstehen
weiterhin nur auf Knopfdruck am Gerät — das weckt das Sprachmodell und
kostet Minuten. Der Timer trägt den jeweils vorhandenen Stand auf den Stick.

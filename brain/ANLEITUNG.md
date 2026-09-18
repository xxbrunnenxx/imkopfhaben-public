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

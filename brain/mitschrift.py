"""Mitschrift: jedes Transkript beim Entstehen wegschreiben.

Warum es das gibt
-----------------
Der Text entsteht hier auf Kraken, in `/api/transcribe-raw` -- das Geraet
schickt die Aufnahme her, bekommt den Text zurueck und legt ihn auf seiner
SD-Karte ab. Bis hierher war die SD-Karte die einzige Kopie. Wer
nachschauen wollte, war darauf angewiesen, dass das Geraet an und im WLAN
ist. Ist es aus, im Rucksack oder die Karte hin, ist der Text weg.

Diese Mitschrift greift ihn dort ab, wo er ohnehin durchkommt, und legt
ihn strukturiert ab -- ohne das Geraet zu fragen und ohne es zu belasten.
Sie ist bewusst kein zweiter Datenbestand mit eigener Wahrheit: die
Hoheit ueber Tags, Erledigt-Haken und Loeschen bleibt beim Geraet. Hier
liegt ein Mitschnitt, und ein Mitschnitt darf nichts entscheiden.

Was abgelegt wird
-----------------
Zwei Formen derselben Sache, beide unter ~/imkopfhaben-mitschrift/:

- `transkripte.jsonl` -- eine Zeile JSON je Transkript, angehaengt, nie
  ueberschrieben. Das ist die Quelle: maschinenlesbar, robust gegen
  Abbrueche (eine kaputte Zeile kostet eine Zeile, nicht die Datei) und
  ohne Datenbank, die mitlaufen muesste.
- `YYYY-MM-DD.md` -- je Tag eine Markdown-Datei zum Lesen, aus derselben
  Zeile miterzeugt.

Warum JSONL und nicht SQLite: es wird nur angehaengt und der Reihe nach
gelesen, nie quer abgefragt. Eine Datenbank waere ein Dienst mehr, der
laufen, sperren und kaputtgehen kann -- fuer einen Mitschnitt zu viel.

Ein Fehler beim Mitschreiben darf die Transkription **nie** umwerfen.
Deshalb faengt `mitschreiben()` alles ab und meldet den Fehler nur ins
Log: lieber eine Luecke in der Mitschrift als eine verlorene Aufnahme.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

ORDNER = Path.home() / "imkopfhaben-mitschrift"
QUELLE = ORDNER / "transkripte.jsonl"


def _tagesdatei(zeitpunkt: datetime) -> Path:
    return ORDNER / f"{zeitpunkt:%Y-%m-%d}.md"


def _anhaengen_atomar(pfad: Path, text: str) -> None:
    """Anhaengen und auf die Platte zwingen.

    Ohne flush/fsync steht bei einem Stromausfall womoeglich eine halbe
    Zeile in der Datei -- genau der Fall, gegen den die Mitschrift
    ueberhaupt antritt. Der Aufwand ist vertretbar: ein Transkript
    entsteht alle paar Minuten, nicht tausendfach pro Sekunde.
    """
    with open(pfad, "a", encoding="utf8") as datei:
        datei.write(text)
        datei.flush()
        os.fsync(datei.fileno())


def mitschreiben(transkript: str, *, dauer_sekunden: float = 0.0,
                 bytes_empfangen: int = 0, quelle: str = "transcribe-raw") -> None:
    """Ein Transkript wegschreiben. Wirft nie."""
    if not transkript or not transkript.strip():
        return

    try:
        ORDNER.mkdir(exist_ok=True)
        jetzt = datetime.now()

        eintrag = {
            "zeitpunkt": jetzt.isoformat(timespec="seconds"),
            "unix_sekunden": int(jetzt.timestamp()),
            "transkript": transkript.strip(),
            "dauer_sekunden": round(dauer_sekunden, 1),
            "bytes_empfangen": bytes_empfangen,
            "quelle": quelle,
        }
        _anhaengen_atomar(QUELLE, json.dumps(eintrag, ensure_ascii=False) + "\n")

        tagesdatei = _tagesdatei(jetzt)
        kopf = "" if tagesdatei.exists() else f"# Mitschrift {jetzt:%d.%m.%Y}\n\n"
        _anhaengen_atomar(
            tagesdatei,
            f"{kopf}- **{jetzt:%H:%M}** ({dauer_sekunden:.1f}s) {transkript.strip()}\n",
        )
    except Exception as fehler:  # bewusst breit: nichts darf hier hochschlagen
        print(f"[mitschrift] konnte nicht schreiben: {fehler!r}", flush=True)


def lesen(seit_unix_sekunden: int = 0) -> list:
    """Alle mitgeschriebenen Transkripte, aelteste zuerst.

    Kaputte Zeilen werden uebersprungen statt die Lesung abzubrechen --
    eine angehaengte Datei kann am Ende eine unvollstaendige Zeile haben,
    wenn genau dort der Strom ausging.
    """
    if not QUELLE.exists():
        return []

    eintraege = []
    with open(QUELLE, encoding="utf8") as datei:
        for zeile in datei:
            zeile = zeile.strip()
            if not zeile:
                continue
            try:
                eintrag = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if eintrag.get("unix_sekunden", 0) >= seit_unix_sekunden:
                eintraege.append(eintrag)
    return eintraege

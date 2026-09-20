#!/usr/bin/env python3
"""Legt die Notizen des Geraets strukturiert auf dem USB-Stick ab.

Warum auf den Stick
-------------------
Bis hierher lagen die Inhalte an zwei Orten, die beide einen laufenden
Rechner brauchen: auf der SD-Karte im Geraet (nur lesbar, solange es an
und im WLAN ist) und in der Mitschrift auf dem Pi. Wer offline daran
arbeiten will -- im Zug, am Laptop, ohne Pi -- kam an keinen von beiden.

Dieses Skript schreibt den Bestand als gewoehnliche Markdown-Dateien auf
den Stick. Kein Programm noetig, kein Dienst, keine Datenbank: ein
Texteditor genuegt. Die Form ist Obsidian-tauglich (YAML-Frontmatter mit
Tags), weil auf dem Stick schon ein Obsidian-Vault liegt und die Dateien
sich dort einfach hineinziehen lassen.

Woher die Inhalte kommen
------------------------
Zwei Quellen, in dieser Reihenfolge:

1. Das Geraet, falls erreichbar. Es ist die vollstaendigere Quelle: nur
   dort stehen Tag (Notiz/Aufgabe/Idee), Erledigt-Haken, Nachfassen-Marker
   und die Zusammenfassungen.
2. Die Mitschrift auf dem Pi. Sie hat nur Text und Zeitpunkt, dafuer auch
   das, was das Geraet zwischenzeitlich geloescht hat -- und sie antwortet,
   wenn das Geraet aus ist.

Ist das Geraet nicht erreichbar, laeuft der Export allein aus der
Mitschrift. Das ist der Normalfall fuer "mal eben mitnehmen".

Was NICHT passiert
------------------
Nichts wird zum Geraet zurueckgeschrieben. Der Export ist eine
Einbahnstrasse: Geraet und Pi bleiben die Quelle, der Stick traegt eine
Kopie zum Lesen und Weiterschreiben. Wer auf dem Stick etwas aendert,
aendert nichts am Geraet -- das waere eine Synchronisierung, und die ist
ein eigenes Vorhaben mit eigenen Fallen (zwei Seiten, die beide
geaendert wurden), nicht bestellt und deshalb nicht gebaut.

Vor jedem Lauf wird der zuletzt geschriebene Bestand geleert und frisch
geschrieben. So verschwindet, was auf dem Geraet geloescht wurde, auch
vom Stick, statt als Altdatei liegenzubleiben. Angefasst wird nur, was
der Export selbst anlegt (00/02/03 und die Ordner 01/04) --
"05-Eigene-Notizen" und alles Fremde im Zielordner bleibt unberuehrt.
Was du selbst in die verwalteten Dateien schreibst, geht beim naechsten
Lauf verloren -- lege eigene Gedanken deshalb in `05-Eigene-Notizen/` ab,
das Verzeichnis fasst der Export nie an.

    brain/notizen-exportieren.py                   # Standardziel auf dem Stick
    brain/notizen-exportieren.py --ziel /pfad      # woanders hin
    brain/notizen-exportieren.py --host 10.0.0.5   # anderes Geraet
"""

import argparse
import json
import shutil
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mitschrift  # noqa: E402

STANDARD_HOST = "192.168.178.75"
# In den Vault hinein, nicht daneben. Obsidian zeigt ausschliesslich, was
# unterhalb des Vault-Ordners liegt (erkennbar an seinem `.obsidian/`) --
# ein Ordner eine Ebene darueber ist fuer Obsidian unsichtbar. Beim ersten
# Lauf am 19.09.2026 lag der Export genau dort falsch.
STANDARD_ZIEL = Path("/mnt/gigastick/Pi5Backup_old version/vault/07-imkopfhaben")

# Wie das Geraet seine Aufnahmen einsortiert, uebersetzt in Klartext.
TAG_NAMEN = {"note": "Notiz", "task": "Aufgabe", "idea": "Idee"}


def hole(host: str, pfad: str, timeout: int = 60):
    with urllib.request.urlopen(f"http://{host}{pfad}", timeout=timeout) as antwort:
        return json.load(antwort)


def geraet_lesen(host: str):
    """Aufnahmen und Zusammenfassungen holen, oder (None, None)."""
    try:
        return hole(host, "/api/archive/recordings"), hole(host, "/api/archive/summaries")
    except OSError as fehler:
        print(f"Geraet unter {host} nicht erreichbar ({fehler}) -- Export nur aus der Mitschrift.")
        return None, None


def track_lesen(host: str):
    """Holt den 420-Track vom Geraet (`/api/420track`), oder None.

    Anders als der Rest hat der 420-Track keine Zweitquelle auf dem Pi: sein
    Protokoll liegt allein im NVS des Geraets (und als Kopie auf dem Stick).
    Ist das Geraet aus, wird die vorhandene Stick-Datei deshalb NICHT geleert,
    sondern unberuehrt gelassen -- sonst faellt die Kopie beim naechsten
    Leerlauf-Export weg. Der Aufrufer prueft dafuer auf None.
    """
    try:
        return hole(host, "/api/420track", timeout=15)
    except OSError as fehler:
        print(f"420-Track vom Geraet nicht erreichbar ({fehler}) -- 06-420Track.md bleibt, wie es ist.")
        return None


def eintraege_sammeln(aufnahmen, mitschrift_eintraege):
    """Beide Quellen zu einer Liste zusammenfuehren.

    Das Geraet hat Vorrang, weil nur es Tag und Erledigt-Stand kennt. Aus
    der Mitschrift kommt dazu, was das Geraet nicht (mehr) hat -- erkannt
    am Wortlaut, denn eine gemeinsame ID gibt es nicht (siehe
    mitschrift-nachholen.py).
    """
    gesammelt = []
    vom_geraet = set()

    if aufnahmen:
        for eintrag in aufnahmen["recordings"]:
            text = (eintrag.get("transcript") or "").strip()
            if not text:
                continue
            vom_geraet.add(text)
            gesammelt.append({
                "text": text,
                "unix": eintrag["created_unix_seconds"] or eintrag["modified_unix_seconds"],
                "art": TAG_NAMEN.get(eintrag["tag"], eintrag["tag"]),
                "erledigt": eintrag["completed"],
                "nachfassen": eintrag["follow_up"],
                "dauer": eintrag["duration_ms"] / 1000,
                "quelle": "Geraet",
            })

    for eintrag in mitschrift_eintraege:
        text = eintrag["transkript"].strip()
        if text in vom_geraet:
            continue
        gesammelt.append({
            "text": text,
            "unix": eintrag["unix_sekunden"],
            # Die Mitschrift kennt die Einsortierung nicht -- ehrlich offen
            # lassen statt raten.
            "art": "Unsortiert",
            "erledigt": False,
            "nachfassen": False,
            "dauer": eintrag.get("dauer_sekunden", 0.0),
            "quelle": "Mitschrift (nicht mehr auf dem Geraet)",
        })

    gesammelt.sort(key=lambda e: e["unix"])
    return gesammelt


# Was der Export selbst verwaltet und deshalb vor dem Schreiben leert. Alles
# andere im Zielordner bleibt unangetastet -- vor allem "05-Eigene-Notizen".
VERWALTETE_DATEIEN = ("00-Uebersicht.md", "02-Aufgaben.md", "03-Ideen.md")
VERWALTETE_ORDNER = ("01-Tagebuch", "04-Zusammenfassungen")


def ziel_aufraeumen(ziel: Path) -> None:
    """Entfernt den zuletzt geschriebenen Bestand, bevor neu geschrieben wird.

    So verschwindet, was auf dem Geraet geloescht wurde, auch vom Stick,
    statt als Altdatei liegenzubleiben (z. B. eine Tagesdatei, fuer die es
    keine Eintraege mehr gibt). Angefasst wird nur, was der Export selbst
    anlegt -- "05-Eigene-Notizen" und alles Fremde im Ordner bleibt.
    """
    for name in VERWALTETE_DATEIEN:
        (ziel / name).unlink(missing_ok=True)
    for name in VERWALTETE_ORDNER:
        shutil.rmtree(ziel / name, ignore_errors=True)


def schreiben(pfad: Path, inhalt: str) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf8")


def tagesdateien_schreiben(ziel: Path, eintraege) -> int:
    """Je Tag eine Datei -- so, wie die Notizen entstanden sind."""
    nach_tag = defaultdict(list)
    for eintrag in eintraege:
        nach_tag[datetime.fromtimestamp(eintrag["unix"]).date()].append(eintrag)

    for tag, tages_eintraege in nach_tag.items():
        zeilen = [
            "---",
            f"datum: {tag:%Y-%m-%d}",
            "tags: [imkopfhaben/tagebuch]",
            "---",
            "",
            f"# Notizen vom {tag:%d.%m.%Y}",
            "",
        ]
        for eintrag in tages_eintraege:
            uhr = datetime.fromtimestamp(eintrag["unix"]).strftime("%H:%M")
            marken = []
            if eintrag["erledigt"]:
                marken.append("erledigt")
            if eintrag["nachfassen"]:
                marken.append("nachfassen")
            anhang = f" _({', '.join(marken)})_" if marken else ""
            zeilen.append(f"## {uhr} · {eintrag['art']}{anhang}")
            zeilen.append("")
            zeilen.append(eintrag["text"])
            zeilen.append("")
        schreiben(ziel / "01-Tagebuch" / f"{tag:%Y-%m-%d}.md", "\n".join(zeilen))
    return len(nach_tag)


def aufgaben_schreiben(ziel: Path, eintraege) -> int:
    """Alle Aufgaben als abhakbare Liste.

    Bewusst Markdown-Checkboxen: die lassen sich offline in jedem Editor
    anhaken. Dass der Haken nicht zum Geraet zurueckwandert, steht in der
    Datei selbst -- lieber einmal deutlich gesagt als stillschweigend
    falsche Erwartung erzeugt.
    """
    aufgaben = [e for e in eintraege if e["art"] == "Aufgabe"]
    if not aufgaben:
        return 0

    zeilen = [
        "---",
        "tags: [imkopfhaben/aufgaben]",
        "---",
        "",
        "# Aufgaben",
        "",
        "> Haken hier gelten nur auf dem Stick. Das Geraet erfaehrt nichts",
        "> davon -- es bleibt die Quelle, diese Datei ist eine Kopie.",
        "",
    ]
    offen = [e for e in aufgaben if not e["erledigt"]]
    erledigt = [e for e in aufgaben if e["erledigt"]]

    zeilen.append(f"## Offen ({len(offen)})")
    zeilen.append("")
    for eintrag in offen:
        datum = datetime.fromtimestamp(eintrag["unix"]).strftime("%d.%m.")
        nach = " ⟳" if eintrag["nachfassen"] else ""
        zeilen.append(f"- [ ] {eintrag['text']}{nach}  _{datum}_")
    zeilen.append("")

    if erledigt:
        zeilen.append(f"## Erledigt ({len(erledigt)})")
        zeilen.append("")
        for eintrag in erledigt:
            datum = datetime.fromtimestamp(eintrag["unix"]).strftime("%d.%m.")
            zeilen.append(f"- [x] {eintrag['text']}  _{datum}_")
        zeilen.append("")

    schreiben(ziel / "02-Aufgaben.md", "\n".join(zeilen))
    return len(aufgaben)


def ideen_schreiben(ziel: Path, eintraege) -> int:
    ideen = [e for e in eintraege if e["art"] in ("Idee", "Notiz")]
    if not ideen:
        return 0

    zeilen = ["---", "tags: [imkopfhaben/ideen]", "---", "", "# Ideen und Notizen", ""]
    for eintrag in ideen:
        datum = datetime.fromtimestamp(eintrag["unix"]).strftime("%d.%m.%Y")
        zeilen.append(f"- {eintrag['text']}  _{datum}_")
    zeilen.append("")
    schreiben(ziel / "03-Ideen.md", "\n".join(zeilen))
    return len(ideen)


def zusammenfassungen_schreiben(ziel: Path, zusammenfassungen) -> int:
    if not zusammenfassungen:
        return 0

    geschrieben = 0
    for schluessel, titel in (("notes", "Notizen"), ("todos", "Aufgaben")):
        eintrag = zusammenfassungen[schluessel]
        if not eintrag["available"]:
            continue
        herkunft = eintrag["metadata"]
        erzeugt = datetime.fromtimestamp(herkunft["generated_unix_seconds"])
        zeilen = [
            "---",
            f"erzeugt: {erzeugt:%Y-%m-%d %H:%M}",
            "tags: [imkopfhaben/zusammenfassung]",
            "---",
            "",
            f"# Zusammenfassung: {titel}",
            "",
            f"Erzeugt am {erzeugt:%d.%m.%Y um %H:%M} aus "
            f"{herkunft['transcript_item_count']} von {herkunft['source_item_count']} "
            f"Aufnahmen der letzten {herkunft['window_days']} Tage.",
            "",
            eintrag["text"].strip(),
            "",
        ]
        schreiben(ziel / "04-Zusammenfassungen" / f"{titel}.md", "\n".join(zeilen))
        geschrieben += 1
    return geschrieben


# Die 420-Track-Dateien im Zielordner. Die generierte Datei wird bei einem
# erfolgreichen Lauf ueberschrieben; die Vermerke-Datei ist des Besitzers und
# wird NIE angefasst, nur beim ersten Mal als leere Vorlage angelegt (Weg 1).
TRACK_DATEI = "06-420Track.md"
TRACK_VERMERKE_DATEI = "06-420Track-Vermerke.md"


def track_tag_als_datum(tag: int):
    """YYYYMMDD (int) -> date, oder None wenn 0/ungueltig (Uhr ungestellt)."""
    if not tag:
        return None
    try:
        return datetime.strptime(str(int(tag)), "%Y%m%d").date()
    except ValueError:
        return None


def track_vermerke_lesen(ziel: Path):
    """Liest die vom Besitzer gepflegte Vermerke-Datei, Vermerk je Datum.

    Format bewusst simpel und von Hand pflegbar: eine Ueberschrift je Tag
    (`## 2026-09-20`), darunter Freitext bis zur naechsten Ueberschrift. Der
    Text wird unveraendert unter den passenden Tag der generierten Datei
    gehaengt. Fehlt die Datei, gibt es eben keine Vermerke.
    """
    pfad = ziel / TRACK_VERMERKE_DATEI
    if not pfad.exists():
        return {}
    vermerke = {}
    aktueller_tag = None
    puffer: list[str] = []

    def ablegen():
        if aktueller_tag and puffer:
            text = "\n".join(puffer).strip()
            if text:
                vermerke[aktueller_tag] = text

    for zeile in pfad.read_text(encoding="utf8").splitlines():
        if zeile.startswith("## "):
            ablegen()
            kopf = zeile[3:].strip()
            aktueller_tag = None
            puffer = []
            try:
                aktueller_tag = datetime.strptime(kopf[:10], "%Y-%m-%d").date()
            except ValueError:
                aktueller_tag = None
        elif aktueller_tag is not None:
            puffer.append(zeile)
    ablegen()
    return vermerke


def track_vermerke_vorlage_anlegen(ziel: Path) -> None:
    """Legt die Vermerke-Datei einmalig an, falls sie fehlt. Nie ueberschreiben."""
    pfad = ziel / TRACK_VERMERKE_DATEI
    if pfad.exists():
        return
    zeilen = [
        "---",
        "tags: [imkopfhaben/420track/vermerke]",
        "---",
        "",
        "# 420-Track — Vermerke",
        "",
        "Diese Datei ist deine. Der Export fasst sie **nie** an — er liest sie",
        "nur und haengt deinen Text unter den passenden Tag in `06-420Track.md`.",
        "",
        "Schreib pro Tag eine Ueberschrift im Format `## JJJJ-MM-TT`, darunter",
        "frei, was du festhalten willst (Sorte, Anlass, Wirkung, was auch immer).",
        "",
        "## 2026-01-01",
        "",
        "_Beispiel — diesen Block kannst du loeschen._",
        "",
    ]
    schreiben(pfad, "\n".join(zeilen))


def track_schreiben(ziel: Path, track, vermerke) -> int:
    """Schreibt `06-420Track.md` aus der Board-Route, Vermerke nach Datum gemerged.

    Gibt die Zahl der protokollierten Tage zurueck. `track` ist die Antwort von
    `/api/420track`; ist sie None (Geraet aus), wird nichts geschrieben und die
    vorhandene Datei bleibt stehen -- der Aufrufer entscheidet das.
    """
    tage = track.get("days") or []
    ziel_richtwert = track.get("goal", 0)
    heute = track.get("today_count", 0)

    # Neueste zuerst -- beim Nachlesen interessiert der juengste Tag zuerst.
    geordnet = sorted(tage, key=lambda e: e.get("day", 0), reverse=True)

    zeilen = [
        "---",
        "tags: [imkopfhaben/420track]",
        f"richtwert: {ziel_richtwert}",
        "---",
        "",
        "# 420-Track",
        "",
        f"Stand: {datetime.now():%d.%m.%Y %H:%M} · heute {heute} · "
        f"Tagesrichtwert {ziel_richtwert}",
        "",
        "> Erzeugt vom Geraet ueber `/api/420track`. Ein erneuter Lauf",
        "> **ueberschreibt** diese Datei. Eigene Vermerke gehoeren in",
        f"> `{TRACK_VERMERKE_DATEI}` — der Export haengt sie hier nach Datum an.",
        "",
        "## Verlauf",
        "",
    ]
    protokolliert = 0
    for eintrag in geordnet:
        datum = track_tag_als_datum(eintrag.get("day", 0))
        if datum is None:
            continue
        protokolliert += 1
        anzahl = int(eintrag.get("count", 0))
        ueber = " ⚑" if ziel_richtwert and anzahl > ziel_richtwert else ""
        punkte = "●" * max(0, anzahl)
        zeilen.append(f"### {datum:%Y-%m-%d} — {anzahl}{ueber}")
        if punkte:
            zeilen.append("")
            zeilen.append(punkte)
        vermerk = vermerke.get(datum)
        if vermerk:
            zeilen.append("")
            zeilen.append(vermerk)
        zeilen.append("")

    schreiben(ziel / TRACK_DATEI, "\n".join(zeilen))
    return protokolliert


def uebersicht_schreiben(ziel: Path, eintraege, anzahl_tage: int, quelle: str) -> None:
    jetzt = datetime.now()
    arten = defaultdict(int)
    for eintrag in eintraege:
        arten[eintrag["art"]] += 1

    zeilen = [
        "---",
        "tags: [imkopfhaben/start]",
        "---",
        "",
        "# imkopfhaben — Notizen",
        "",
        f"Stand: {jetzt:%d.%m.%Y %H:%M} · {len(eintraege)} Aufnahmen · Quelle: {quelle}",
        "",
        "## Was hier liegt",
        "",
        f"- `01-Tagebuch/` — je Tag eine Datei, {anzahl_tage} insgesamt",
        "- `02-Aufgaben.md` — alle Aufgaben, offen und erledigt getrennt",
        "- `03-Ideen.md` — Ideen und Notizen",
        "- `04-Zusammenfassungen/` — die Fassungen, die das Geraet erzeugt hat",
        "- `05-Eigene-Notizen/` — deins. Der Export fasst dieses Verzeichnis nie an",
        "- `06-420Track.md` — der 420-Track vom Geraet, mit deinen Vermerken",
        "- `06-420Track-Vermerke.md` — deins. Vermerke je Tag; der Export liest nur",
        "",
        "## Verteilung",
        "",
    ]
    for art, anzahl in sorted(arten.items(), key=lambda p: -p[1]):
        zeilen.append(f"- {art}: {anzahl}")
    zeilen += [
        "",
        "## Wie das hier hereinkommt",
        "",
        "Erzeugt von `brain/notizen-exportieren.py` auf dem Pi. Ein erneuter",
        "Lauf frischt den Stand auf und **ueberschreibt** die Dateien oben —",
        "eigene Gedanken gehoeren deshalb nach `05-Eigene-Notizen/`.",
        "",
        "Der Export geht nur in eine Richtung. Was du hier aenderst, bleibt",
        "hier: das Geraet ist und bleibt die Quelle.",
        "",
    ]
    schreiben(ziel / "00-Uebersicht.md", "\n".join(zeilen))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--host", default=STANDARD_HOST, help="Adresse des Geraets")
    parser.add_argument("--ziel", type=Path, default=STANDARD_ZIEL, help="Zielverzeichnis")
    argumente = parser.parse_args()

    aufnahmen, zusammenfassungen = geraet_lesen(argumente.host)
    track = track_lesen(argumente.host)
    eintraege = eintraege_sammeln(aufnahmen, mitschrift.lesen())

    # Der 420-Track ist eine eigene Quelle -- ein Lauf lohnt auch dann, wenn es
    # keine Notizen gibt, aber das Geraet den Track liefert.
    if not eintraege and track is None:
        print("Nichts zu exportieren: weder Geraet erreichbar noch Mitschrift gefuellt.")
        return 1

    ziel = argumente.ziel
    try:
        ziel.mkdir(parents=True, exist_ok=True)
        # Deins, und der Export fasst es nie an -- deshalb hier nur anlegen.
        (ziel / "05-Eigene-Notizen").mkdir(exist_ok=True)
    except OSError as fehler:
        print(f"Ziel {ziel} nicht beschreibbar: {fehler}")
        return 1

    # Die Vermerke-Datei des Besitzers einmalig als Vorlage anlegen (Weg 1); ist
    # sie schon da, bleibt sie unberuehrt.
    track_vermerke_vorlage_anlegen(ziel)

    quelle = "Geraet + Mitschrift" if aufnahmen else "nur Mitschrift"
    anzahl_tage = anzahl_aufgaben = anzahl_ideen = anzahl_fassungen = 0
    if eintraege:
        # Erst den alten Bestand raeumen, dann neu schreiben -- so faellt weg, was
        # auf dem Geraet geloescht wurde. "05-Eigene-Notizen" bleibt unberuehrt.
        ziel_aufraeumen(ziel)
        anzahl_tage = tagesdateien_schreiben(ziel, eintraege)
        anzahl_aufgaben = aufgaben_schreiben(ziel, eintraege)
        anzahl_ideen = ideen_schreiben(ziel, eintraege)
        anzahl_fassungen = zusammenfassungen_schreiben(ziel, zusammenfassungen)
        uebersicht_schreiben(ziel, eintraege, anzahl_tage, quelle)

    # 420-Track nur schreiben, wenn das Geraet geantwortet hat -- sonst bliebe
    # die vorhandene Kopie (einzige neben dem NVS) erhalten.
    anzahl_track = track_schreiben(ziel, track, track_vermerke_lesen(ziel)) if track is not None else None

    print(f"Nach {ziel} geschrieben:")
    if eintraege:
        print(f"  {len(eintraege)} Aufnahmen aus {quelle}")
        print(f"  {anzahl_tage} Tagesdateien, {anzahl_aufgaben} Aufgaben, {anzahl_ideen} Ideen")
        print(f"  {anzahl_fassungen} Zusammenfassungen")
    if anzahl_track is not None:
        print(f"  420-Track: {anzahl_track} Tage (heute {track.get('today_count', 0)})")
    else:
        print("  420-Track: Geraet aus -- 06-420Track.md unveraendert")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

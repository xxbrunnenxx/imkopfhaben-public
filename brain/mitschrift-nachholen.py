#!/usr/bin/env python3
"""Holt einmalig nach, was vor der Mitschrift entstanden ist.

Die Mitschrift greift jedes Transkript beim Entstehen ab -- aber erst,
seit es sie gibt. Alles, was davor aufgenommen wurde, liegt nur auf der
SD-Karte im Geraet. Dieses Skript holt genau diese Altbestaende einmal
ueber die Archiv-Route des Geraets und traegt sie nach.

Dafuer muss das Geraet an und im WLAN sein -- einmalig, genau das, was
die Mitschrift danach ueberfluessig macht.

Doppelte werden am Wortlaut erkannt, nicht an einer ID: das Geraet
nummeriert seine Aufnahmen anders als die Mitschrift, eine gemeinsame ID
gibt es nicht -- und soll es auch nicht geben, die Mitschrift kennt ja
auch Aufnahmen, die das Geraet zwischenzeitlich geloescht hat.

Warum nicht zusaetzlich auf die Sekunde verglichen wird: die beiden
Seiten stempeln verschiedene Ereignisse. Das Geraet haelt fest, wann die
Aufnahme begann; die Mitschrift, wann das Transkript fertig war. Dazwischen
liegen die Sprechdauer und die Whisper-Laufzeit, auf dem Pi gut eine halbe
Minute. Ein Vergleich auf den Zeitpunkt findet deshalb nie eine
Uebereinstimmung und traegt alles doppelt nach -- beim ersten Lauf am
19.09.2026 genau so passiert und hier behoben.

    brain/mitschrift-nachholen.py 192.168.178.75
"""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mitschrift  # noqa: E402

STANDARD_HOST = "192.168.178.75"


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else STANDARD_HOST

    try:
        with urllib.request.urlopen(
            f"http://{host}/api/archive/recordings", timeout=90
        ) as antwort:
            daten = json.load(antwort)
    except OSError as fehler:
        print(f"Geraet unter {host} nicht erreichbar: {fehler}")
        return 1

    if not daten.get("ok"):
        print(f"SD-Karte nicht lesbar: {daten.get('status')}")
        return 1

    # Nur der Wortlaut zaehlt (siehe Modul-Doku oben). Zwei verschiedene
    # Aufnahmen mit exakt gleichem Wortlaut werden dadurch als eine
    # behandelt -- hinnehmbar: eine Dublette in der Mitschrift stiftet mehr
    # Verwirrung als eine fehlende Wiederholung desselben Satzes.
    vorhanden = {e["transkript"].strip() for e in mitschrift.lesen()}

    nachgetragen = 0
    uebersprungen = 0
    for eintrag in sorted(daten["recordings"], key=lambda e: e["created_unix_seconds"]):
        text = (eintrag.get("transcript") or "").strip()
        if not text:
            continue

        if text in vorhanden:
            uebersprungen += 1
            continue
        vorhanden.add(text)

        mitschrift.mitschreiben(
            text,
            dauer_sekunden=eintrag["duration_ms"] / 1000,
            quelle=f"nachgeholt-vom-geraet:{eintrag['recording_id']}",
        )
        nachgetragen += 1

    print(f"{nachgetragen} nachgetragen, {uebersprungen} waren schon da.")
    print(f"Mitschrift liegt in {mitschrift.QUELLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

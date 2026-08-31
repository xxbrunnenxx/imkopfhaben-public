"""Der Akku-Lerner — schätzt, wie lange der Akku noch hält, rein aus
beobachteten Boot-zu-Stromausfall-Spannen. Läuft als EIGENER, von
`app.py` unabhängiger Dienst (siehe imkopfhaben-notebook-akku-lerner.service)
— bewusst nur mit Python-Standardbibliothek gebaut, damit er auch dann noch
läuft, wenn am Notebook selbst gerade etwas kaputt ist.

Uebernommen aus barthalomeus (barthal/akku_lernen.py) — gleiche Mechanik,
gleiches Geraet (Whisplay-Board), nur der Standardpfad angepasst.

**Ein "Zyklus" zählt nur, wenn er mit einem echten Stromausfall endete**
(Akku leer) — nicht bei einem bewussten `sudo reboot`. Unterschieden über
eine Markierung (`sauber_beendet`), die nur beim sauberen Herunterfahren
(SIGTERM/SIGINT abgefangen) gesetzt wird: fehlt sie beim nächsten Start, ist
die Stromversorgung abgerissen, und der zuletzt geschriebene Uptime-Wert ist
die Dauer dieses Zyklus.

Geschrieben wird alle `INTERVALL` Sekunden (Vorgabe: 1-2 Minuten reichen an
Genauigkeit) — bricht der Strom irgendwann dazwischen ab, ist der zuletzt
geschriebene Stand höchstens so alt.

Aufruf (über systemd, siehe imkopfhaben-notebook-akku-lerner.service):
    python3 akku_lernen.py [--datei PFAD] [--intervall SEKUNDEN]
"""

import argparse
import json
import os
import signal
import sys
import time

MAX_ZYKLEN = 7
INTERVALL = 90.0
STANDARD_DATEI = os.path.expanduser("~/akku_lernen.json")


def _uptime() -> float:
    with open("/proc/uptime") as f:
        return float(f.read().split()[0])


def _leerer_stand() -> dict:
    return {"uptime_zuletzt": 0.0, "sauber_beendet": True, "zyklen": []}


def _laden(pfad: str) -> dict:
    """Fehlt die Datei, ist das kein Fehler (erster Start überhaupt) — ist
    sie kaputt, wird das gemeldet, aber ein frischer Stand reicht als
    Rückfallebene."""
    try:
        with open(pfad, encoding="utf-8") as f:
            stand = json.load(f)
    except FileNotFoundError:
        return _leerer_stand()
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"⚠ {pfad} ist beschädigt ({e}) — Zyklen-Historie beginnt neu.",
              file=sys.stderr)
        return _leerer_stand()
    stand.setdefault("uptime_zuletzt", 0.0)
    stand.setdefault("sauber_beendet", True)
    stand.setdefault("zyklen", [])
    return stand


def _fsync_verzeichnis(pfad: str) -> None:
    fd = os.open(os.path.dirname(os.path.abspath(pfad)), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _schreiben(pfad: str, stand: dict) -> None:
    """Atomar — der ganze Zweck ist, den letzten Stand über einen abrupten
    Stromausfall zu retten. Wirft nicht, ein Schreibfehler soll den Lerner
    nicht sterben lassen."""
    tmp = pfad + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(stand, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, pfad)
        _fsync_verzeichnis(pfad)
    except OSError as e:
        print(f"⚠ Akku-Lerner konnte nicht schreiben: {e}", file=sys.stderr)
        try:
            os.remove(tmp)
        except OSError:
            pass


def geschaetzte_energie(pfad: str = STANDARD_DATEI) -> float | None:
    """0..100 aus den gelernten Zyklen, oder `None` ohne jede Historie —
    dann zeigt die Anzeige "Baked!" statt eines (erfundenen) Prozentwerts.
    """
    zyklen = _laden(pfad).get("zyklen") or []
    if not zyklen:
        return None
    erwartet = sum(zyklen) / len(zyklen)
    if erwartet <= 0:
        return None
    jetzt = _uptime()
    anteil = 1.0 - (jetzt / erwartet)
    return max(0.0, min(100.0, anteil * 100.0))


def _zyklus_abschliessen(stand: dict) -> dict:
    """Beim Start aufgerufen, bevor der neue Zyklus losgeht: ist der vorige
    Lauf ohne sauberes Runterfahren geendet (echter Stromausfall), wandert
    sein letzter Uptime-Wert in die Zyklen-Historie (höchstens `MAX_ZYKLEN`,
    ältester fliegt raus)."""
    if stand["sauber_beendet"]:
        print("Sauber beendeter letzter Lauf — kein Zyklus für die Historie.")
        return stand

    zyklen = stand["zyklen"] + [stand["uptime_zuletzt"]]
    stand["zyklen"] = zyklen[-MAX_ZYKLEN:]
    print(f"Stromausfall erkannt — Zyklus mit {stand['uptime_zuletzt']:.0f}s "
          f"in die Historie aufgenommen ({len(stand['zyklen'])}/{MAX_ZYKLEN}).")

    if len(zyklen) >= 2:
        neuester, rest = zyklen[-1], zyklen[:-1]
        durchschnitt_rest = sum(rest) / len(rest)
        if durchschnitt_rest > 0:
            if neuester > durchschnitt_rest * 1.05:
                print(f"Trend: Kapazität steigt ({neuester:.0f}s vs. "
                      f"Ø {durchschnitt_rest:.0f}s zuvor — neuer Akku?)")
            elif neuester < durchschnitt_rest * 0.95:
                print(f"Trend: Kapazität sinkt ({neuester:.0f}s vs. "
                      f"Ø {durchschnitt_rest:.0f}s zuvor)")
    return stand


def _main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--datei", default=STANDARD_DATEI,
                   help=f"Wo der Stand liegt (Standard: {STANDARD_DATEI})")
    p.add_argument("--intervall", type=float, default=INTERVALL,
                   help=f"Sekunden zwischen zwei Schreibvorgängen (Standard: {INTERVALL})")
    a = p.parse_args()

    stand = _zyklus_abschliessen(_laden(a.datei))
    stand["uptime_zuletzt"] = 0.0
    stand["sauber_beendet"] = False
    _schreiben(a.datei, stand)

    laeuft = True

    def _anhalten(signum, rahmen):
        nonlocal laeuft
        laeuft = False

    signal.signal(signal.SIGTERM, _anhalten)
    signal.signal(signal.SIGINT, _anhalten)

    print(f"Läuft — schreibt alle {a.intervall:.0f}s nach {a.datei}.")
    try:
        naechste_schreibung = time.monotonic()
        while laeuft:
            jetzt = time.monotonic()
            if jetzt >= naechste_schreibung:
                stand["uptime_zuletzt"] = _uptime()
                _schreiben(a.datei, stand)
                naechste_schreibung = jetzt + a.intervall
            time.sleep(1.0)
    finally:
        # Sauberes Ende: Markierung setzen, damit der nächste Start diesen
        # Lauf nicht fälschlich als Stromausfall zählt.
        stand["uptime_zuletzt"] = _uptime()
        stand["sauber_beendet"] = True
        _schreiben(a.datei, stand)
        print("Sauber beendet.")

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

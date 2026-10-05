"""kopffrei-Archiv auf dem Pi: Aufnahme und Text nebeneinander, je Aera ein Ordner.

Ablauf (Besitzer-Vorgabe 02.10.2026):

  1. Das Geraet schickt eine Aufnahme mit Kennung und Aera (POST /api/aufnahme).
     Der Pi legt die WAV sofort ab und bestaetigt -- das Geraet wartet NICHT am
     offenen Draht auf den Text. (Vorher ging der fertige Text verloren, wenn das
     Geraet waehrenddessen einschlief, und es schickte dieselbe Aufnahme spaeter
     noch einmal: doppelt gerechnet, doppelt in der Mitschrift.)
  2. Ein Hintergrund-Arbeiter transkribiert der Reihe nach und legt
     <kennung>.txt neben die WAV. Der brain bleibt dabei ansprechbar.
  3. Der Text wird ans Geraet geschickt (POST /api/transkript), so lange, bis es
     "gespeichert" meldet. Im Nickerchen oder gesperrt ist dessen Funk aus; dann
     klappt es beim naechsten Wachsein -- das Geraet meldet sich per /api/health.
  4. Kommt dieselbe Kennung noch einmal: keine zweite Transkription, nur erneute
     Zustellung.
  5. Jede Formatierung des Geraets beginnt eine neue Aera = neuer Ordner. Die
     Aera vergibt das Geraet (Datum_Uhrzeit-Zufall), so entsteht eine Historie.

Ablage:  ~/kopffrei-archiv/<aera>/<kennung>.wav   die Aufnahme
                                 <kennung>.txt   der Text
                                 <kennung>.json  der Stand (angenommen,
                                                 transkribiert, zugestellt ...)

Die Mitschrift (mitschrift.py) wird weiter mitgeschrieben -- der Stick-Export
und alles andere, was daraus liest, laeuft unveraendert.
"""

import json
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import ai_service
import mitschrift

ARCHIV = Path(os.environ.get("KOPFFREI_ARCHIV", str(Path.home() / "kopffrei-archiv")))
GERAET_DATEI = ARCHIV / "geraet.json"

# SaveTranscript auf dem Geraet lehnt leeren Text ab -- und "nichts" waere auch
# nicht ehrlich. Stille bekommt diesen sichtbaren Hinweis.
KEIN_TEXT = "[keine Sprache erkannt]"

GERAET_PORT = 80            # Weboberflaeche des Geraets laeuft im WLAN-Betrieb mit
ZUSTELL_TAKT_S = 30         # so oft wird ohne Anstoss nach Ausstehendem geschaut
ZUSTELL_TIMEOUT_S = 8

_KENNUNG = re.compile(r"^rec_[A-Za-z0-9_]{1,64}$")
_AERA = re.compile(r"^[A-Za-z0-9_-]{1,48}$")

_lock = threading.Lock()          # Stand-Dateien und Geraete-Adresse
_arbeit: "queue.Queue[tuple[str, str]]" = queue.Queue()
_anstoss = threading.Event()      # Zustellung jetzt versuchen
_gestartet = False
_geraet_ip: "str | None" = None


def _jetzt() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _pfade(aera: str, kennung: str) -> tuple[Path, Path, Path]:
    ordner = ARCHIV / aera
    return ordner / f"{kennung}.wav", ordner / f"{kennung}.txt", ordner / f"{kennung}.json"


def _schreibe_atomar(pfad: Path, daten: bytes) -> None:
    tmp = pfad.with_name(pfad.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(daten)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, pfad)


def _lese_stand(pfad: Path) -> dict:
    try:
        return json.loads(pfad.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return {}


def _schreibe_stand(pfad: Path, stand: dict) -> None:
    _schreibe_atomar(pfad, json.dumps(stand, ensure_ascii=False, indent=1).encode("utf8"))


def _ist_lokal(ip: "str | None") -> bool:
    return not ip or ip.startswith("127.") or ip == "::1"


def _merke_geraet(ip: "str | None") -> None:
    """Merkt sich die Adresse des Geraets (fuer die Zustellung), auch ueber Neustarts."""
    global _geraet_ip
    if _ist_lokal(ip) or ip == _geraet_ip:
        return
    _geraet_ip = ip
    try:
        ARCHIV.mkdir(parents=True, exist_ok=True)
        _schreibe_stand(GERAET_DATEI, {"ip": ip, "seit": _jetzt()})
    except OSError as e:
        print(f"[kopffrei-archiv] Geraete-Adresse nicht gespeichert: {e}", flush=True)
    print(f"[kopffrei-archiv] Geraet erreichbar unter {ip}", flush=True)


def _wav_dauer_s(daten_bytes: int, wav: Path) -> float:
    """Dauer aus dem 44-Byte-Kopf (16 Bit mono, wie das Geraet sie schickt)."""
    try:
        with open(wav, "rb") as f:
            kopf = f.read(44)
        rate = int.from_bytes(kopf[24:28], "little")
        kanaele = int.from_bytes(kopf[22:24], "little") or 1
        bits = int.from_bytes(kopf[34:36], "little") or 16
        if rate:
            return max(0, daten_bytes - 44) / (rate * kanaele * bits / 8)
    except OSError:
        pass
    return 0.0


# ---------------------------------------------------------------------------
# 1. Annehmen
# ---------------------------------------------------------------------------

def annehmen(kennung: str, aera: str, daten: bytes, absender_ip: "str | None") -> tuple[int, dict]:
    """Legt die Aufnahme ab und bestaetigt sofort. Rueckgabe: (HTTP-Status, Antwort)."""
    if not _KENNUNG.match(kennung or ""):
        return 400, {"fehler": "kennung_ungueltig"}
    if not _AERA.match(aera or ""):
        return 400, {"fehler": "aera_ungueltig"}
    if len(daten) <= 44:
        return 400, {"fehler": "keine_aufnahme"}

    wav, txt, js = _pfade(aera, kennung)
    with _lock:
        _merke_geraet(absender_ip)
        wav.parent.mkdir(parents=True, exist_ok=True)
        if wav.exists():
            # Dieselbe Aufnahme noch einmal (das Geraet hat die Bestaetigung nicht
            # bekommen): nicht neu rechnen. Liegt der Text schon da, gleich zustellen.
            if txt.exists():
                _anstoss.set()
            else:
                _arbeit.put((aera, kennung))  # falls die Arbeit verloren ging; der Arbeiter prueft
            print(f"[kopffrei-archiv] {aera}/{kennung}: schon da (Text bereit: {txt.exists()})",
                  flush=True)
            return 200, {"status": "bekannt", "text_bereit": txt.exists()}
        _schreibe_atomar(wav, daten)
        _schreibe_stand(js, {
            "kennung": kennung,
            "aera": aera,
            "bytes": len(daten),
            "angenommen": _jetzt(),
            "transkribiert": None,
            "zugestellt": None,
            "verworfen": None,
            "zustellversuche": 0,
            "letzter_fehler": None,
        })
    _arbeit.put((aera, kennung))
    print(f"[kopffrei-archiv] {aera}/{kennung}: angenommen ({len(daten)} Bytes)", flush=True)
    return 202, {"status": "angenommen"}


# ---------------------------------------------------------------------------
# 2. Transkribieren (ein Arbeiter, der Reihe nach)
# ---------------------------------------------------------------------------

def _arbeiter() -> None:
    while True:
        aera, kennung = _arbeit.get()
        try:
            wav, txt, js = _pfade(aera, kennung)
            if txt.exists() or not wav.exists():
                continue  # schon erledigt (doppelt eingereiht) oder weggeraeumt
            beginn = time.monotonic()
            text = (ai_service.transcribe_audio(str(wav)) or "").strip()
            daten_bytes = wav.stat().st_size
            dauer = _wav_dauer_s(daten_bytes, wav)
            if text:
                mitschrift.mitschreiben(text, dauer_sekunden=dauer,
                                        bytes_empfangen=daten_bytes, quelle="kopffrei-archiv")
            _schreibe_atomar(txt, (text or KEIN_TEXT).encode("utf8"))
            with _lock:
                stand = _lese_stand(js)
                stand["transkribiert"] = _jetzt()
                stand["rechenzeit_s"] = round(time.monotonic() - beginn, 1)
                _schreibe_stand(js, stand)
            print(f"[kopffrei-archiv] {aera}/{kennung}: transkribiert, {dauer:.1f}s Audio, "
                  f"{len(text)} Zeichen, {time.monotonic() - beginn:.1f}s gerechnet", flush=True)
            _anstoss.set()
        except Exception as e:  # der Arbeiter darf nie sterben
            print(f"[kopffrei-archiv] Fehler beim Transkribieren {aera}/{kennung}: {e}", flush=True)
        finally:
            _arbeit.task_done()


# ---------------------------------------------------------------------------
# 3. Zustellen (bis das Geraet "gespeichert" meldet)
# ---------------------------------------------------------------------------

def _ausstehend() -> list[tuple[str, str, Path, Path]]:
    """Alle Texte, die fertig, aber noch nicht zugestellt und nicht verworfen sind."""
    offen = []
    if not ARCHIV.exists():
        return offen
    for js in sorted(ARCHIV.glob("*/rec_*.json")):
        stand = _lese_stand(js)
        if stand.get("zugestellt") or stand.get("verworfen"):
            continue
        txt = js.with_suffix(".txt")
        if txt.exists():
            offen.append((js.parent.name, js.stem, txt, js))
    return offen


def _stelle_zu(ip: str, aera: str, kennung: str, text: str) -> int:
    """Ein Zustellversuch. Rueckgabe: HTTP-Status oder 0, wenn das Geraet nicht antwortet."""
    abfrage = urllib.parse.urlencode({"id": kennung, "aera": aera})
    anfrage = urllib.request.Request(
        f"http://{ip}:{GERAET_PORT}/api/transkript?{abfrage}",
        data=text.encode("utf8"),
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=ZUSTELL_TIMEOUT_S) as antwort:
            return antwort.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError):
        return 0


def _zusteller() -> None:
    while True:
        _anstoss.wait(timeout=ZUSTELL_TAKT_S)
        _anstoss.clear()
        ip = _geraet_ip
        if not ip:
            continue
        for aera, kennung, txt, js in _ausstehend():
            try:
                text = txt.read_text(encoding="utf8")
            except OSError:
                continue
            status = _stelle_zu(ip, aera, kennung, text)
            with _lock:
                stand = _lese_stand(js)
                stand["zustellversuche"] = int(stand.get("zustellversuche") or 0) + 1
                if status == 200:
                    stand["zugestellt"] = _jetzt()
                    stand["letzter_fehler"] = None
                elif status == 404:
                    stand["verworfen"] = _jetzt()
                    stand["letzter_fehler"] = "auf dem Geraet nicht (mehr) vorhanden"
                elif status == 409:
                    stand["verworfen"] = _jetzt()
                    stand["letzter_fehler"] = "Geraet ist inzwischen in einer anderen Aera"
                else:
                    stand["letzter_fehler"] = f"HTTP {status}" if status else "Geraet nicht erreichbar"
                _schreibe_stand(js, stand)
            print(f"[kopffrei-archiv] Zustellung {aera}/{kennung} -> "
                  f"{status or 'nicht erreichbar'}", flush=True)
            if status == 0:
                break  # Funk aus (Nickerchen/gesperrt): naechster Anlauf beim Wachsein


def geraet_meldet_sich(ip: "str | None", kennzeichen: "str | None") -> None:
    """Aufruf aus /api/health: das Geraet ist wach und im WLAN -> jetzt zustellen.

    Das Geraet fragt mit dem Standard-Kennzeichen des ESP-HTTP-Clients
    ("ESP32 HTTP Client/..."), beim Hochladen mit "folloup-sticky". So wird auch
    eine neue DHCP-Adresse sofort uebernommen.
    """
    kz = kennzeichen or ""
    if _ist_lokal(ip) or not ("ESP32" in kz or "folloup-sticky" in kz):
        return
    with _lock:
        _merke_geraet(ip)
    _anstoss.set()


# ---------------------------------------------------------------------------
# Stand und Start
# ---------------------------------------------------------------------------

def stand() -> dict:
    """Wie steht es um die Nachrichten -- je Aera gezaehlt."""
    je_aera: dict = {}
    if ARCHIV.exists():
        for js in ARCHIV.glob("*/rec_*.json"):
            s = _lese_stand(js)
            z = je_aera.setdefault(js.parent.name, {
                "angenommen": 0, "transkribiert": 0, "zugestellt": 0, "verworfen": 0, "offen": 0})
            z["angenommen"] += 1
            if s.get("transkribiert"):
                z["transkribiert"] += 1
            if s.get("zugestellt"):
                z["zugestellt"] += 1
            elif s.get("verworfen"):
                z["verworfen"] += 1
            else:
                z["offen"] += 1
    return {"geraet": _geraet_ip, "warteschlange": _arbeit.qsize(), "aeren": je_aera}


def starten() -> None:
    """Einmal beim Start des brain: Liegengebliebenes wieder aufnehmen, Arbeiter starten."""
    global _gestartet, _geraet_ip
    if _gestartet:
        return
    _gestartet = True
    ARCHIV.mkdir(parents=True, exist_ok=True)
    gespeichert = _lese_stand(GERAET_DATEI).get("ip")
    if gespeichert and not _ist_lokal(gespeichert):
        _geraet_ip = gespeichert
    liegengeblieben = 0
    for wav in sorted(ARCHIV.glob("*/rec_*.wav")):
        if not wav.with_suffix(".txt").exists():
            _arbeit.put((wav.parent.name, wav.stem))
            liegengeblieben += 1
    threading.Thread(target=_arbeiter, name="kopffrei-transkription", daemon=True).start()
    threading.Thread(target=_zusteller, name="kopffrei-zustellung", daemon=True).start()
    _anstoss.set()
    print(f"[kopffrei-archiv] bereit: {ARCHIV}, Geraet {_geraet_ip or 'noch unbekannt'}, "
          f"{liegengeblieben} zum Transkribieren wieder eingereiht", flush=True)

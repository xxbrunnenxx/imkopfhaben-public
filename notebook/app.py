#!/usr/bin/env python3
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

import akku_lernen

# Whisplay Runtime einbinden
RUNTIME_DIR = os.path.expanduser("~/Whisplay/runtime")
if RUNTIME_DIR not in sys.path:
    sys.path.append(RUNTIME_DIR)

from whisplay_client import create_whisplay_hardware  # noqa: E402

logging.basicConfig(
    filename=os.path.expanduser("~/app_error.log"),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
log = logging.getLogger("imkopfhaben-app")

SERVER_URL = "http://kraken.local:8000/process"
RECORD_PATH = Path("/tmp/note.wav")
ARCHIVE_PATH = Path.home() / "imkopfhaben_archive.json"
QUEUE_DIR = Path.home() / "notiz_warteschlange"
QUEUE_RETRY_SEC = 60.0

FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_PATH_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# 48000 Hz am WM8960 Codec verhindert Knackser
RECORD_CMD = [
    "arecord",
    "-D", "whisplaysound",
    "-c", "2",
    "-f", "S16_LE",
    "-r", "48000",
    str(RECORD_PATH),
]

RESULT_DISPLAY_SEC = 5.0
LONG_PRESS_SEC = 0.6

TAG_COLORS = {
    "Todo": (255, 120, 0),
    "Aufgabe": (255, 120, 0),
    "Idee": (0, 180, 255),
    "Notiz": (0, 230, 100),
    "Termin": (255, 0, 200),
    "Wichtig": (255, 0, 0),
    "Tagebuch": (176, 136, 245),
    "Unklar": (130, 130, 130),
}


def _load_fonts():
    try:
        return (
            ImageFont.truetype(FONT_PATH_BOLD, 18),
            ImageFont.truetype(FONT_PATH_REGULAR, 14),
            ImageFont.truetype(FONT_PATH_REGULAR, 11),
        )
    except OSError:
        default = ImageFont.load_default()
        return default, default, default


def rgb565_bytes(image: Image.Image) -> bytes:
    """Konvertiert PIL Image in das vom Whisplay LCD erwartete RGB565 Format."""
    rgb = image.convert("RGB")
    output = bytearray()
    for y in range(rgb.height):
        for x in range(rgb.width):
            r, g, b = rgb.getpixel((x, y))
            value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            output.append((value >> 8) & 0xFF)
            output.append(value & 0xFF)
    return bytes(output)


class Archive:
    def __init__(self, path: Path):
        self.path = path
        self.items = []
        self.load()

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception as e:
                log.error(f"Fehler beim Laden des Archivs: {e}")
                self.items = []

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Fehler beim Speichern des Archivs: {e}")

    def add(self, tag: str, note: str, transcript: str):
        item = {
            "tag": tag,
            "note": note,
            "transcript": transcript,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.items.insert(0, item)
        self.save()

    def counts(self) -> dict:
        counts = {"Idee": 0, "Aufgabe": 0, "Notiz": 0, "Todo": 0, "Termin": 0, "Wichtig": 0}
        for item in self.items:
            tag = item.get("tag", "Notiz")
            counts[tag] = counts.get(tag, 0) + 1
        return counts


class App:
    def __init__(self):
        QUEUE_DIR.mkdir(exist_ok=True)
        self.board = create_whisplay_hardware()
        self.board.set_backlight(70)
        self.archive = Archive(ARCHIVE_PATH)
        
        self.title_font, self.body_font, self.small_font = _load_fonts()

        self.mode = "dashboard"  # "dashboard", "browse"
        self.browse_index = 0
        self.press_started_at = 0.0
        self.record_proc = None
        # Schuetzt die Warteschlange: Tastendruck-Callback (eigener Thread des
        # Whisplay-Daemons) und der periodische Hintergrund-Retry in run()
        # koennen sonst gleichzeitig dieselbe Datei verarbeiten/loeschen -
        # live beobachtet als "No such file or directory" beim Oeffnen.
        self._warteschlangen_lock = threading.Lock()

        # Callbacks registrieren
        self.board.on_button_press(self._on_press)
        self.board.on_button_release(self._on_release)
        if hasattr(self.board, "on_exit_request"):
            self.board.on_exit_request(self._on_exit_request)
        if hasattr(self.board, "on_focus_revoked"):
            self.board.on_focus_revoked(self._on_focus_revoked)

    def _on_exit_request(self):
        pass

    def _on_focus_revoked(self):
        pass

    def _push(self, image: Image.Image, rgb=(0, 0, 0)) -> None:
        try:
            self.board.set_rgb(*rgb)
            self.board.draw_image(0, 0, self.board.LCD_WIDTH, self.board.LCD_HEIGHT, rgb565_bytes(image))
        except Exception as e:
            log.error(f"Display Push Fehler: {e}")

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> list:
        """Bricht Text anhand der tatsächlichen Pixelbreite sauber um."""
        lines = []
        for paragraph in text.splitlines():
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current_line = []
            for word in words:
                test_line = " ".join(current_line + [word])
                try:
                    w = font.getlength(test_line)
                except AttributeError:
                    try:
                        w = font.getbbox(test_line)[2]
                    except Exception:
                        w = len(test_line) * 8
                
                if w <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
        return lines

    def show_message(self, title: str, body: str, rgb=(0, 0, 0)) -> None:
        image = Image.new("RGB", (self.board.LCD_WIDTH, self.board.LCD_HEIGHT), "white")
        draw = ImageDraw.Draw(image)
        
        pad_x = 6
        max_text_width = self.board.LCD_WIDTH - (2 * pad_x)

        # 1. Titel
        draw.text((pad_x, 4), title[:22], font=self.title_font, fill="black")
        
        # 2. Dezente Trennlinie
        draw.line([(pad_x, 26), (self.board.LCD_WIDTH - pad_x, 26)], fill=(200, 200, 200), width=1)

        # 3. Body Text mit automatischem Zeilenumbruch
        wrapped_lines = self._wrap_text(body, self.body_font, max_text_width)
        
        y = 30
        line_height = 18
        for line in wrapped_lines:
            if y + line_height > self.board.LCD_HEIGHT - 4:
                draw.text((pad_x, y), "...", font=self.body_font, fill=(120, 120, 120))
                break
            draw.text((pad_x, y), line, font=self.body_font, fill="black")
            y += line_height

        self._push(image, rgb)

    def show_dashboard(self) -> None:
        c = self.archive.counts()
        energie = akku_lernen.geschaetzte_energie()
        akku_text = f"{energie:.0f}%" if energie is not None else "Baked!"
        wartend = len(list(QUEUE_DIR.glob("*.wav")))
        body = (
            f"Todos: {c.get('Todo', 0) + c.get('Aufgabe', 0)}\n"
            f"Ideen: {c.get('Idee', 0)}\n"
            f"Notizen: {c.get('Notiz', 0) + c.get('Wichtig', 0) + c.get('Tagebuch', 0)}\n"
            f"Akku: {akku_text}\n"
        )
        if wartend:
            body += f"Warten auf Kraken: {wartend}\n"
        body += (
            "\nKurz druecken: Aufnehmen\n"
            "Nochmal druecken: Senden\n"
            "Lang halten: Blaettern"
        )
        self.show_message("imkopfhaben", body, rgb=(0, 0, 0))

    def show_browse_item(self) -> None:
        if not self.archive.items:
            self.show_message("Durchblaettern", "Noch keine Eintraege vorhanden.\nKurz druecken zum Aufnehmen.", rgb=(80, 80, 80))
            return
        
        idx = self.browse_index % len(self.archive.items)
        item = self.archive.items[idx]
        tag = item.get("tag", "Notiz")
        time_text = item.get("created_at", "")[11:16]
        position = f"{idx + 1}/{len(self.archive.items)}"
        title = f"{tag} {time_text} ({position})"
        
        self.show_message(title, item.get("note", ""), rgb=TAG_COLORS.get(tag, (0, 200, 100)))

    def _start_recording(self) -> None:
        self.mode = "recording"
        self.show_message("Hoere zu...", "Nochmal druecken zum\nBeenden & Senden.", rgb=(255, 0, 0))
        if RECORD_PATH.exists():
            RECORD_PATH.unlink()
        self.record_proc = subprocess.Popen(RECORD_CMD, stderr=subprocess.PIPE)

    def _stop_and_send(self) -> None:
        try:
            self.record_proc.terminate()
            _, stderr = self.record_proc.communicate(timeout=2)
        except Exception as e:
            stderr = None
            log.error(f"arecord konnte nicht sauber beendet werden: {e}")
        finally:
            self.record_proc = None

        if not RECORD_PATH.exists():
            details = stderr.decode(errors="ignore")[:150] if stderr else "keine Aufnahmedatei erzeugt"
            log.error(f"Aufnahme fehlgeschlagen: {details}")
            self.show_message("Fehler", f"Aufnahme fehlgeschlagen:\n{details}", rgb=(255, 0, 0))
            time.sleep(RESULT_DISPLAY_SEC)
            self.mode = "dashboard"
            self.show_dashboard()
            return

        # In die Warteschlange verschieben statt direkt zu senden - so geht bei
        # nicht erreichbarem Brain nichts verloren, siehe OFFENE_PUNKTE.md.
        # shutil.move statt Path.rename: /tmp ist tmpfs, das Home-Verzeichnis
        # liegt auf der SD-Karte - ein reines rename() ueber Geraetegrenzen
        # hinweg scheitert mit "Invalid cross-device link".
        ziel = QUEUE_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S_%f')}.wav"
        shutil.move(str(RECORD_PATH), str(ziel))

        self.show_message("Sende...", "Warte auf Pi 5 Brain...", rgb=(0, 180, 255))
        self._verarbeite_warteschlange(frisch=ziel)

        self.mode = "dashboard"
        self.show_dashboard()

    def _verarbeite_warteschlange(self, frisch: Path | None = None, blockierend: bool = True) -> None:
        """Arbeitet die Warteschlange aeltestenzuerst ab (Dateiname beginnt mit
        Zeitstempel, sortiert also richtig). Bricht beim ersten Fehlschlag ab -
        damit bleibt die Reihenfolge erhalten und Kraken wird nicht mit
        Wiederholungsversuchen fuer laengst faellige Dateien geflutet, sobald
        er wieder da ist. `frisch` ist die Datei aus dem gerade laufenden
        Tastendruck, falls es einer war - nur dafuer wird ein Ergebnis auf dem
        Display gezeigt, der Rest laeuft still im Hintergrund.

        `blockierend=False` (Hintergrund-Retry) laesst den Aufruf ausfallen,
        statt zu warten, wenn der Tastendruck-Thread gerade selbst mitten in
        der Warteschlange steckt - der naechste Zyklus in 60s holt es nach."""
        if not self._warteschlangen_lock.acquire(blocking=blockierend):
            return
        try:
            dateien = sorted(QUEUE_DIR.glob("*.wav"))
            for index, pfad in enumerate(dateien):
                try:
                    with open(pfad, "rb") as f:
                        resp = requests.post(SERVER_URL, files={"file": f}, timeout=60)
                    resp.raise_for_status()
                    data = resp.json()
                except requests.RequestException as e:
                    log.error(f"Warteschlange: {pfad.name} nicht gesendet: {e}")
                    if pfad == frisch:
                        verbleibend = len(dateien) - index
                        self.show_message(
                            "Gespeichert",
                            f"Kraken nicht erreichbar,\nwird spaeter gesendet.\n({verbleibend} in der Warteschlange)",
                            rgb=(255, 150, 0),
                        )
                        time.sleep(RESULT_DISPLAY_SEC)
                    return

                tag = data.get("tag", "Notiz")
                note = data.get("note", "").strip() or "(leere Antwort)"
                transcript = data.get("transcript", "")
                self.archive.add(tag, note, transcript)
                pfad.unlink()

                if pfad == frisch:
                    self.show_message(tag, note, rgb=TAG_COLORS.get(tag, (0, 255, 0)))
                    time.sleep(RESULT_DISPLAY_SEC)
        finally:
            self._warteschlangen_lock.release()

    def _on_press(self) -> None:
        self.press_started_at = time.monotonic()

    def _on_release(self) -> None:
        # Alles ab hier abgesichert: der Whisplay-Daemon (whisplay_client.py:_event_loop)
        # schluckt jede Exception aus diesem Callback lautlos und ohne Log - ohne dieses
        # try/except bleibt das Display bei einem Fehler fuer immer im aktuellen Zustand haengen.
        try:
            self._handle_release()
        except Exception as e:
            log.error(f"Fehler bei Tasterauswertung: {e}")
            self.mode = "dashboard"
            self.show_message("Fehler", f"Unerwarteter Fehler:\n{str(e)[:120]}", rgb=(255, 0, 0))
            time.sleep(RESULT_DISPLAY_SEC)
            self.show_dashboard()

    def _handle_release(self) -> None:
        duration = time.monotonic() - self.press_started_at

        # Aufnahme laeuft -> jeder Tastendruck beendet sie und sendet, egal wie lang
        if self.mode == "recording":
            self._stop_and_send()
            return

        if self.mode == "dashboard":
            if duration >= LONG_PRESS_SEC:
                self.mode = "browse"
                self.browse_index = 0
                self.show_browse_item()
            else:
                self._start_recording()
            return

        # Durchblättern: kurz = einen weiter (am Ende wieder von vorn), lang = zurueck nach Home
        if self.mode == "browse":
            if duration >= LONG_PRESS_SEC:
                self.mode = "dashboard"
                self.show_dashboard()
            else:
                self.browse_index += 1
                self.show_browse_item()

    def run(self):
        self.show_dashboard()
        naechster_versuch = time.monotonic() + QUEUE_RETRY_SEC
        while True:
            time.sleep(1.0)
            if time.monotonic() < naechster_versuch:
                continue
            naechster_versuch = time.monotonic() + QUEUE_RETRY_SEC
            # Nur im Ruhezustand nachsenden - waehrend einer Aufnahme oder im
            # Blaettern soll die Warteschlange das Display nicht dazwischenfunken.
            if self.mode != "dashboard" or not any(QUEUE_DIR.glob("*.wav")):
                continue
            try:
                self._verarbeite_warteschlange(blockierend=False)
            except Exception as e:
                log.error(f"Warteschlange (Hintergrund): {e}")
            if self.mode == "dashboard":
                self.show_dashboard()


if __name__ == "__main__":
    app = App()
    try:
        app.run()
    except KeyboardInterrupt:
        app.board.set_rgb(0, 0, 0)
        sys.exit(0)

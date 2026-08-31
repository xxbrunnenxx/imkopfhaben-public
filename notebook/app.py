#!/usr/bin/env python3
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

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

TAG_COLORS = {
    "Todo": (255, 120, 0),
    "Aufgabe": (255, 120, 0),
    "Idee": (0, 180, 255),
    "Notiz": (0, 230, 100),
    "Termin": (255, 0, 200),
    "Wichtig": (255, 0, 0),
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
        self.board = create_whisplay_hardware()
        self.board.set_backlight(70)
        self.archive = Archive(ARCHIVE_PATH)
        
        self.title_font, self.body_font, self.small_font = _load_fonts()

        self.mode = "dashboard"  # "dashboard", "browse"
        self.browse_index = 0
        self.press_started_at = 0.0
        self.record_proc = None

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
        body = (
            f"Todos: {c.get('Todo', 0) + c.get('Aufgabe', 0)}\n"
            f"Ideen: {c.get('Idee', 0)}\n"
            f"Notizen: {c.get('Notiz', 0)}\n\n"
            "Kurz halten: Sprechen\n"
            "Loslassen: Senden\n"
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

    def _on_press(self) -> None:
        self.press_started_at = time.monotonic()
        if self.mode == "dashboard":
            self.show_message("Hoere zu...", "Spreche deine Notiz ein...\nLasse los zum Senden.", rgb=(255, 0, 0))
            if RECORD_PATH.exists():
                RECORD_PATH.unlink()
            self.record_proc = subprocess.Popen(RECORD_CMD, stderr=subprocess.PIPE)

    def _on_release(self) -> None:
        duration = time.monotonic() - self.press_started_at

        # Aufnahme läuft -> Beenden und an Pi 5 senden
        if self.record_proc:
            try:
                self.record_proc.terminate()
                _, stderr = self.record_proc.communicate(timeout=2)
            except Exception:
                pass
            self.record_proc = None

            if duration < 0.5:
                self.show_dashboard()
                return

            self.show_message("Sende...", "Warte auf Pi 5 Brain...", rgb=(0, 180, 255))
            try:
                with open(RECORD_PATH, "rb") as f:
                    resp = requests.post(SERVER_URL, files={"file": f}, timeout=60)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                self.show_message("Fehler", f"Kraken nicht erreichbar:\n{str(e)[:120]}", rgb=(255, 0, 0))
                time.sleep(RESULT_DISPLAY_SEC)
                self.show_dashboard()
                return

            tag = data.get("tag", "Notiz")
            note = data.get("note", "").strip() or "(leere Antwort)"
            transcript = data.get("transcript", "")
            self.archive.add(tag, note, transcript)

            self.show_message(tag, note, rgb=TAG_COLORS.get(tag, (0, 255, 0)))
            time.sleep(RESULT_DISPLAY_SEC)
            self.show_dashboard()
            return

        # Durchblättern
        if self.mode == "browse":
            if duration > 1.5:
                self.mode = "dashboard"
                self.show_dashboard()
            else:
                self.browse_index += 1
                self.show_browse_item()
        elif self.mode == "dashboard" and duration > 1.5:
            self.mode = "browse"
            self.browse_index = 0
            self.show_browse_item()

    def run(self):
        self.show_dashboard()
        while True:
            time.sleep(0.1)


if __name__ == "__main__":
    app = App()
    try:
        app.run()
    except KeyboardInterrupt:
        app.board.set_rgb(0, 0, 0)
        sys.exit(0)

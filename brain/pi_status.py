"""Pi-5-Kennzahlen fuer die Geraete-Startseite.

Liest nur aus dem Kernel (/proc, /sys) und aus vcgencmd -- keine
Fremdpakete, im Sinne von "Nehmen, was es gibt". Jede Funktion faengt
ihren eigenen Fehler ab und gibt None zurueck, statt zu werfen: die
Statusroute darf nie am fehlenden Sensor scheitern.
"""

from __future__ import annotations

import subprocess
import time
from typing import Optional

# Wanduhr-Startzeitpunkt des Prozesses. time.monotonic() waere gegen
# Zeitspruenge robuster, laesst sich aber nicht in einen Zeitstempel
# umrechnen; fuer eine Uptime-Anzeige reicht die Wanduhr.
_PROZESS_START = time.time()


def brain_uptime_sekunden() -> float:
    """Laufzeit dieses Brain-Prozesses in Sekunden."""
    return max(0.0, time.time() - _PROZESS_START)


def pi_uptime_sekunden() -> Optional[float]:
    """Laufzeit des Pi seit dem Booten, aus /proc/uptime."""
    try:
        with open("/proc/uptime", "r", encoding="ascii") as f:
            return float(f.read().split()[0])
    except Exception:
        return None


def pi_temperatur_celsius() -> Optional[float]:
    """CPU-Temperatur des Pi. Erst der Kernel-Thermalzone-Weg (immer da),
    dann vcgencmd als Rueckfall."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="ascii") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        pass
    try:
        aus = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout
        # Form: "temp=48.3'C"
        wert = aus.split("=", 1)[1].split("'", 1)[0]
        return round(float(wert), 1)
    except Exception:
        return None


def cpu_last_prozent() -> Optional[float]:
    """Momentane CPU-Auslastung ueber ein kurzes /proc/stat-Delta (100 ms).
    Bewusst kurz, damit die Statusroute schnell antwortet."""
    try:
        erst = _lese_cpu_zeiten()
        time.sleep(0.1)
        zweit = _lese_cpu_zeiten()
        if erst is None or zweit is None:
            return None
        gesamt_delta = zweit[0] - erst[0]
        idle_delta = zweit[1] - erst[1]
        if gesamt_delta <= 0:
            return None
        return round(100.0 * (gesamt_delta - idle_delta) / gesamt_delta, 1)
    except Exception:
        return None


def _lese_cpu_zeiten():
    """(gesamt, idle) aus der ersten Zeile von /proc/stat."""
    with open("/proc/stat", "r", encoding="ascii") as f:
        felder = f.readline().split()
    if not felder or felder[0] != "cpu":
        return None
    werte = [int(x) for x in felder[1:]]
    idle = werte[3] + (werte[4] if len(werte) > 4 else 0)  # idle + iowait
    return sum(werte), idle


def ram_prozent() -> Optional[float]:
    """Belegter Arbeitsspeicher in Prozent, aus /proc/meminfo."""
    try:
        info = {}
        with open("/proc/meminfo", "r", encoding="ascii") as f:
            for zeile in f:
                teile = zeile.split(":")
                if len(teile) == 2:
                    info[teile[0].strip()] = int(teile[1].split()[0])  # kB
        gesamt = info.get("MemTotal")
        frei = info.get("MemAvailable")
        if not gesamt or frei is None:
            return None
        return round(100.0 * (gesamt - frei) / gesamt, 1)
    except Exception:
        return None


def status() -> dict:
    """Alle Kennzahlen fuer die Geraete-Startseite in einem Rutsch."""
    return {
        "backend": "Pi 5",
        "brain_uptime_sekunden": round(brain_uptime_sekunden(), 1),
        "pi_uptime_sekunden": pi_uptime_sekunden(),
        "pi_temperatur_celsius": pi_temperatur_celsius(),
        "cpu_last_prozent": cpu_last_prozent(),
        "ram_prozent": ram_prozent(),
    }

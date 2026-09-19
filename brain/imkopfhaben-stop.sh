#!/usr/bin/env bash
# imkopfhaben-stop.sh -- haelt die beiden Pi-Dienste wieder an, die
# imkopfhaben-start.sh hochgefahren hat. Danach ist der Kraken wieder
# lastfrei: kein Sprachmodell im Speicher, kein Whisper-Prozess.

set -u

BRAIN_VERZEICHNIS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LMS="$HOME/.lmstudio/bin/lms"
BRAIN_PORT=8000
PID_DATEI="$BRAIN_VERZEICHNIS/.brain.pid"

meldung() { printf '\n=== %s ===\n' "$1"; }

# ---------------------------------------------------------------------------
# 1. brain beenden
# ---------------------------------------------------------------------------
meldung "brain (Port $BRAIN_PORT) anhalten"

beendet=0
# Zuverlaessig ueber den Port: uvicorn koppelt sich beim Start per setsid
# ab, der eigentliche Serverprozess ist NICHT die im Start-Skript gemerkte
# PID (das ist nur der Wrapper). Deshalb wird hier der Prozess beendet, der
# wirklich auf Port 8000 lauscht -- das trifft immer den richtigen.
if command -v fuser >/dev/null 2>&1; then
    if fuser -k "${BRAIN_PORT}/tcp" 2>/dev/null; then
        echo "brain (Port $BRAIN_PORT) beendet."
        beendet=1
    fi
else
    # Kein fuser vorhanden: ueber das Kommando suchen.
    if pkill -f "uvicorn main:app --host 0.0.0.0 --port ${BRAIN_PORT}" 2>/dev/null; then
        echo "brain (ueber Prozessname) beendet."
        beendet=1
    fi
fi
rm -f "$PID_DATEI"

[ "$beendet" -eq 0 ] && echo "Kein laufender brain-Prozess gefunden (war wohl schon aus)."

# ---------------------------------------------------------------------------
# 2. LM Studio Server beenden
# ---------------------------------------------------------------------------
meldung "Stuendlichen Stick-Abgleich anhalten"

# Nur den Zeitgeber, nicht die Einheit selbst deaktivieren: beim naechsten
# imkopfhaben-start.sh soll er ohne weiteres Zutun wieder anspringen.
if systemctl list-unit-files imkopfhaben-stick.timer >/dev/null 2>&1; then
    sudo systemctl stop imkopfhaben-stick.timer 2>/dev/null \
        && echo "Zeitgeber gestoppt -- kein stuendliches Aufwachen mehr." \
        || echo "Zeitgeber war nicht aktiv."
else
    echo "Zeitgeber nicht installiert -- nichts zu stoppen."
fi

# ---------------------------------------------------------------------------
meldung "LM Studio Server anhalten"

if [ -x "$LMS" ]; then
    # Modell aus dem Speicher werfen, dann den Server stoppen.
    "$LMS" unload --all 2>/dev/null && echo "Modell(e) entladen."
    "$LMS" server stop 2>/dev/null && echo "LM Studio Server gestoppt." \
        || echo "LM Studio Server war nicht aktiv."
    # "server stop" beendet nur den HTTP-Server; der llmster-Unterbau bleibt
    # sonst im RAM haengen (bekanntes LM-Studio-Verhalten). Fuer echte
    # Lastfreiheit den Rest ebenfalls beenden.
    sleep 1
    if pkill -f 'llmster' 2>/dev/null; then
        echo "LM Studio Hintergrundprozess (llmster) beendet."
    fi
else
    echo "LM Studio (lms) nicht gefunden -- nichts zu stoppen."
fi

meldung "Fertig -- der Kraken ist wieder lastfrei"

#!/usr/bin/env bash
# imkopfhaben-start.sh -- faehrt die beiden Pi-Dienste hoch, die das
# ESP32-Notizbuch (folloup-waveshare) braucht. Bewusst KEIN Autostart und
# kein systemd-Dienst: der Kraken soll im Ruhezustand lastfrei bleiben. Du
# rufst das hier von Hand auf, wenn du das Geraet benutzen willst, und
# beendest es danach mit imkopfhaben-stop.sh.
#
# Zwei Dienste werden gestartet:
#   1. LM Studio Server auf Port 1234  -- das Sprachmodell (gemma-4-e2b),
#      das die "Zusammenfassen"-Knoepfe am Geraet bedient.
#   2. brain (dieses Verzeichnis) auf Port 8000 -- nimmt die Sprachdatei
#      vom Geraet entgegen und macht mit Whisper Text daraus.
#
# Beide binden auf 0.0.0.0, damit das ESP32 sie ueber "kraken.local"
# erreicht. Das Skript wartet, bis beide wirklich antworten, und meldet
# dann "bereit" -- oder bricht mit einer klaren Meldung ab, wenn etwas
# nicht hochkommt.

set -u

# -- Pfade, an einer Stelle, damit ein Umzug nur hier geaendert wird --
BRAIN_VERZEICHNIS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LMS="$HOME/.lmstudio/bin/lms"
MODELL="google/gemma-4-e2b"
LMS_PORT=1234
BRAIN_PORT=8000
BRAIN_LOG="$BRAIN_VERZEICHNIS/brain.log"

# Wie lange (Sekunden) hoechstens auf jeden Dienst gewartet wird.
WARTE_LMS=120     # Modell laden dauert auf dem Pi eine Weile
WARTE_BRAIN=120   # Whisper-Modell laden dauert ebenfalls

meldung() { printf '\n=== %s ===\n' "$1"; }
fehler()  { printf '\nFEHLER: %s\n' "$1" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. LM Studio Server + Modell
# ---------------------------------------------------------------------------
meldung "1/2  LM Studio (Sprachmodell) auf Port $LMS_PORT"

[ -x "$LMS" ] || fehler "LM Studio nicht gefunden unter $LMS -- ist LM Studio installiert?"

# Server hochfahren (bind auf 0.0.0.0, damit das Geraet drankommt). Der
# Befehl kehrt zurueck, sobald der Server laeuft.
"$LMS" server start --port "$LMS_PORT" --bind 0.0.0.0 \
    || fehler "LM Studio Server liess sich nicht starten."

# Modell laden, falls noch keins geladen ist. -y beantwortet Rueckfragen
# automatisch (Skriptbetrieb).
if "$LMS" ps 2>/dev/null | grep -q "$MODELL"; then
    echo "Modell $MODELL ist bereits geladen."
else
    echo "Lade Modell $MODELL (das dauert beim ersten Mal etwas) ..."
    # "Text file busy" kann direkt nach "lms server start" auftreten, weil
    # die lms-Binary dann noch vom gerade gestarteten Dienst gehalten wird
    # (live beobachtet 19.09.2026). Deshalb ein paar Versuche statt sofort
    # abzubrechen.
    geladen=0
    for versuch in 1 2 3 4 5; do
        if "$LMS" load "$MODELL" -y; then geladen=1; break; fi
        echo "Versuch $versuch fehlgeschlagen, warte 5s ..."
        sleep 5
    done
    [ "$geladen" -eq 1 ] || fehler "Modell $MODELL liess sich nicht laden."
fi

# Warten, bis der Server das Modell ueber die API wirklich meldet.
echo -n "Warte auf LM Studio"
for ((i = 0; i < WARTE_LMS; i++)); do
    if curl -s --max-time 3 "http://127.0.0.1:$LMS_PORT/v1/models" 2>/dev/null \
        | grep -q "$MODELL"; then
        echo " -- bereit."
        break
    fi
    echo -n "."
    sleep 1
    [ "$i" -eq $((WARTE_LMS - 1)) ] && fehler "LM Studio meldet das Modell nach ${WARTE_LMS}s nicht."
done

# ---------------------------------------------------------------------------
# 2. brain (Whisper-Transkription)
# ---------------------------------------------------------------------------
meldung "2/2  brain (Whisper-Transkription) auf Port $BRAIN_PORT"

[ -x "$BRAIN_VERZEICHNIS/venv/bin/uvicorn" ] \
    || fehler "brain-venv fehlt ($BRAIN_VERZEICHNIS/venv) -- einmal 'python3 -m venv venv && venv/bin/pip install -r requirements.txt' im brain-Ordner ausfuehren."

# Laeuft schon etwas auf dem Port?
if curl -s --max-time 3 "http://127.0.0.1:$BRAIN_PORT/api/health" 2>/dev/null | grep -q '"status"'; then
    echo "brain laeuft bereits auf Port $BRAIN_PORT."
else
    echo "Starte brain (Log: $BRAIN_LOG) ..."
    # Im Hintergrund, von der Konsole abgekoppelt, damit es weiterlaeuft,
    # auch wenn du das Terminal schliesst. PID merken fuers Stop-Skript.
    # Wichtig: die Subshell darf nicht auf uvicorn warten. Ohne das
    # abschliessende "exit" bleibt sie als Elternprozess haengen und das
    # Startskript kehrt nie zur Konsole zurueck (live beobachtet 19.09.2026),
    # obwohl beide Dienste laengst bereit sind.
    ( cd "$BRAIN_VERZEICHNIS" && \
      setsid nohup venv/bin/uvicorn main:app --host 0.0.0.0 --port "$BRAIN_PORT" \
        > "$BRAIN_LOG" 2>&1 & echo $! > "$BRAIN_VERZEICHNIS/.brain.pid"; exit 0 )
fi

echo -n "Warte auf brain (laedt das Whisper-Modell)"
for ((i = 0; i < WARTE_BRAIN; i++)); do
    if curl -s --max-time 3 "http://127.0.0.1:$BRAIN_PORT/api/health" 2>/dev/null | grep -q '"status"'; then
        echo " -- bereit."
        break
    fi
    echo -n "."
    sleep 1
    [ "$i" -eq $((WARTE_BRAIN - 1)) ] && fehler "brain antwortet nach ${WARTE_BRAIN}s nicht. Schau ins Log: $BRAIN_LOG"
done

# ---------------------------------------------------------------------------
meldung "Beide Dienste bereit"
cat <<MELDUNG
Das Geraet kann jetzt aufnehmen. Es spricht den Kraken unter "kraken.local"
an:
  Sprachmodell  ->  http://kraken.local:$LMS_PORT/v1/
  Transkription ->  http://kraken.local:$BRAIN_PORT/api/transcribe-raw

Wenn du fertig bist, alles wieder anhalten mit:
  ./imkopfhaben-stop.sh
MELDUNG

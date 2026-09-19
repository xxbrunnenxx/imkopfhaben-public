#!/usr/bin/env bash
# notizen-auf-stick.sh -- stuendlicher Abgleich der Notizen auf den USB-Stick.
#
# Der Sinn dieses Wrappers ist der Fall, dass der Stick NICHT steckt. Das ist
# der Normalfall, kein Fehler: der Besitzer nimmt ihn mit. Dann soll hier
# nichts blinken, nichts scheitern und nichts in ein Fehlerprotokoll laufen --
# das Skript geht still und zufrieden wieder schlafen. Steckt der Stick beim
# naechsten Lauf wieder, wird er erkannt, eingehaengt und der Rueckstand in
# einem Zug nachgezogen. Der Export schreibt ohnehin immer den vollen Stand,
# es gibt also keinen Rueckstand, der sich anhaeufen koennte.
#
# Erkannt wird der Stick an seiner UUID, nicht an /dev/sda1: die
# Geraetenamen vergibt der Kernel in der Reihenfolge des Einsteckens. Wer
# nach /dev/sda1 greift, greift frueher oder spaeter auf eine fremde Platte
# -- und dieses Skript haengt ein und schreibt.

set -u

STICK_UUID="B218B41F18B3E111"   # GigaStick, NTFS
EINHAENGEPUNKT="/mnt/gigastick"
BRAIN_VERZEICHNIS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Nach journalctl, deshalb ohne Zeitstempel -- den setzt systemd davor.
meldung() { printf '%s\n' "$1"; }

# --- 1. Steckt der Stick ueberhaupt? ---------------------------------------
GERAET="/dev/disk/by-uuid/$STICK_UUID"
if [ ! -e "$GERAET" ]; then
    meldung "Stick steckt nicht -- nichts zu tun. (Kein Fehler: er ist unterwegs.)"
    exit 0
fi

# --- 2. Haengt er schon? Sonst einhaengen -----------------------------------
# Selbst eingehaengt oder vorgefunden? Nur was dieses Skript selbst eingehaengt
# hat, haengt es hinterher auch wieder aus -- einen Einhaengepunkt
# wegzuziehen, den jemand anders gerade benutzt, waere ruecksichtslos.
SELBST_EINGEHAENGT=0
if ! findmnt -n --source "$(readlink -f "$GERAET")" >/dev/null 2>&1; then
    mkdir -p "$EINHAENGEPUNKT" 2>/dev/null || sudo mkdir -p "$EINHAENGEPUNKT"
    if ! sudo mount "$GERAET" "$EINHAENGEPUNKT" 2>/dev/null; then
        meldung "Stick steckt, laesst sich aber nicht einhaengen -- uebersprungen."
        exit 0
    fi
    SELBST_EINGEHAENGT=1
    meldung "Stick eingehaengt unter $EINHAENGEPUNKT."
fi

# Wo er wirklich haengt -- er koennte schon woanders eingehaengt sein.
ZIEL_BASIS="$(findmnt -n -o TARGET --source "$(readlink -f "$GERAET")" | head -1)"
ZIEL="$ZIEL_BASIS/Pi5Backup_old version/vault/07-imkopfhaben"

aufraeumen() {
    if [ "$SELBST_EINGEHAENGT" = "1" ]; then
        sync
        sudo umount "$EINHAENGEPUNKT" 2>/dev/null \
            && meldung "Stick wieder ausgehaengt (sicher zum Abziehen)." \
            || meldung "Aushaengen fehlgeschlagen -- Stick nicht einfach abziehen."
    else
        sync
    fi
}
# Auch bei Abbruch aushaengen: ein haengengebliebener Einhaengepunkt waere
# schlimmer als ein ausgelassener Lauf.
trap aufraeumen EXIT

# --- 3. Exportieren ---------------------------------------------------------
# Der Export holt sich das Geraet selbst, wenn es erreichbar ist, und faellt
# sonst auf die Mitschrift zurueck. Beides ist hier recht: Hauptsache, der
# Stick traegt den jeweils besten verfuegbaren Stand.
python3 "$BRAIN_VERZEICHNIS/notizen-exportieren.py" --ziel "$ZIEL"

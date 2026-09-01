# ESP32-S3-ePaper-3.97 — Hardware-Erkenntnisse

Stand: 2026-09-01. Begleitet `docs/design/tintendisplay.html` (reiner
Bildschirmentwurf) — hier stehen die Hardware-Fakten, die beim Erstellen
dieses Entwurfs geprüft wurden, nicht der Entwurf selbst.

## Akku-Füllstand: echter Fuel-Gauge vorhanden

Das Board (Waveshare ESP32-S3-ePaper-3.97) hat einen **AXP2101-PMIC**
(I2C-Adresse `0x34`) mit eingebautem Coulomb-Counter — die Prozentzahl
wird vom Chip selbst berechnet, nicht geschätzt.

Nachgewiesen an zwei Stellen:

- Im **offiziellen Waveshare-Repo** selbst (`waveshareteam/ESP32-S3-ePaper-3.97`):
  `components/i2c_bsp/i2c_bsp.c` registriert `AXP2101Addr 0x34`,
  `components/axpPower/axp_prot.cpp` initialisiert einen vollständigen
  AXP2101-Treiber mit den passenden Lade-Parametern — wird von der
  eigenen Demo-App aber nie aufgerufen. Deshalb der erste (falsche)
  Eindruck, das Board hätte keinen Fuel-Gauge: "Demo nutzt X nicht"
  beweist nicht "Hardware kann X nicht".
- **Live bewiesen** durch einen unabhängigen Fork für dieselbe Hardware,
  [`alxv2016/folloup-sticky`](https://github.com/alxv2016/folloup-sticky),
  Branch `folloup-waveshare`: `GetBatteryLevel()` liest das Register
  `XPOWERS_AXP2101_BAT_PERCENT_DATA` per I2C, Boot-Log bestätigt
  `"AXP2101 power hold established (batt=%d%% ...)"`.

**Konsequenz:** Ein Akku-Lerner (wie bei barthalomeus/5teve/dem
Whisplay-Notebook, wo echte Messung fehlt) ist für dieses Board **nicht
nötig** — der echte Prozentwert kommt per I2C vom Chip selbst, sobald der
AXP2101 verdrahtet wird. Der Bus wird ohnehin mit RTC (PCF85063) und IMU
(QMI8658) geteilt.

**Lizenz-Hinweis für die spätere Umsetzung:** `folloup-sticky` selbst
steht unter GPLv3 — dessen Treiber-Kopie nicht direkt übernehmen. Der
eigentliche AXP2101-Treiber ist erkennbar von lewisxhe's `XPowersLib`
abgeleitet (MIT-lizenziert, der verbreitete Standardweg für AXP192/
AXP202/AXP2101 auf ESP32-Boards) — die Bibliothek direkt verwenden statt
den GPL-Fork zu kopieren.

## Referenz-Projekt: `alxv2016/folloup-sticky`

Kein Teil von imkopfhaben, aber dieselbe Zielhardware (Branch
`folloup-waveshare`) und ein sehr ähnliches Grundkonzept (Sprachnotizen,
Kategorien Idea/To-do/Note, ePaper-Anzeige). Zwei Dinge daraus als
mögliche Ansatzpunkte für später vermerkt:

- **Nach Tag gruppierte, fensterbasierte Notizliste** statt endlosem
  Scrollen — Einträge werden unter Datums-Überschriften zusammengefasst,
  das sichtbare Fenster ist fest begrenzt, eine Zählleiste ("3 von 12")
  ersetzt eine Scrollbar. Sinnvoll, sobald unsere eigene Notizliste über
  eine Handvoll Einträge hinauswächst.
- Verdrahtung/Pin-Belegung (Board-Komponente unter
  `components/board/include/waveshare_board_config.h` im
  `folloup-waveshare`-Branch) als Referenz für Tasten-, I2C- und
  Audio-Pins auf exakt diesem Board.

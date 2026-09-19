# Graph Report - imkopfhaben-public  (2026-09-19)

## Corpus Check
- 19 files · ~17,923 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .service 4, (none) 1, .logrotate 1)

## Summary
- 282 nodes · 485 edges · 15 communities (14 shown, 1 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7bdbc090`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- App
- app.py
- akku_lernen.py
- get_counts
- database.py
- 📡 API-Spezifikation (`brain/`)
- json
- notizen-exportieren.py
- pi_status.py
- imkopfhaben-brain -- Anleitung zum Starten und Stoppen
- imkopfhaben-start.sh
- notizen-auf-stick.sh
- ESP32-S3-ePaper-3.97 — Hardware-Erkenntnisse
- imkopfhaben-stop.sh

## God Nodes (most connected - your core abstractions)
1. `App` - 17 edges
2. `📡 API-Spezifikation (`brain/`)` - 12 edges
3. `process_audio()` - 10 edges
4. `main()` - 9 edges
5. `🧠 imkopfhaben` - 9 edges
6. `status()` - 8 edges
7. `_veredele_einzelne_notiz()` - 8 edges
8. `schreiben()` - 7 edges
9. `fuehre_veredelung_schritt_aus()` - 7 edges
10. `Archive` - 7 edges

## Surprising Connections (you probably didn't know these)
- `process_audio()` --calls--> `transcribe_audio()`  [EXTRACTED]
  brain/main.py → brain/ai_service.py
- `list_notes()` --calls--> `get_all_notes()`  [EXTRACTED]
  brain/main.py → brain/database.py
- `_main()` --calls--> `get_all_notes()`  [EXTRACTED]
  brain/veredelung_test_iterativ.py → brain/database.py
- `_main()` --calls--> `get_all_notes()`  [EXTRACTED]
  brain/veredelung_test.py → brain/database.py
- `delete_note()` --calls--> `delete_note()`  [EXTRACTED]
  brain/main.py → brain/database.py

## Import Cycles
- None detected.

## Communities (15 total, 1 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.06
Nodes (50): asyncio, BaseModel, transcribe_audio(), get_buendel_vorschlaege(), init_db(), loesche_buendel_vorschlag(), Fuer die Web-UI (roh+veredelt/Vorschlaege nebeneinander) - die Veredelung…, delete_note() (+42 more)

### Community 1 - "App"
Cohesion: 0.19
Nodes (8): Image, ImageFont, App, Konvertiert PIL Image in das vom Whisplay LCD erwartete RGB565 Format., Bricht Text anhand der tatsächlichen Pixelbreite sauber um., Arbeitet die Warteschlange aeltestenzuerst ab (Dateiname beginnt mit…, rgb565_bytes(), Übrige Punkte

### Community 2 - "app.py"
Cohesion: 0.12
Nodes (14): logging, _aktualisiere_tag_colors(), Archive, _hex_zu_rgb(), _lade_sync_stand(), _load_fonts(), Path, Periodischer Abgleich mit dem Brain (Issue #11/#16), analog zum… (+6 more)

### Community 3 - "akku_lernen.py"
Cohesion: 0.18
Nodes (15): argparse, _fsync_verzeichnis(), geschaetzte_energie(), _laden(), _leerer_stand(), _main(), Der Akku-Lerner — schätzt, wie lange der Akku noch hält, rein aus beobachteten…, Beim Start aufgerufen, bevor der neue Zyklus losgeht: ist der vorige Lauf ohne… (+7 more)

### Community 4 - "get_counts"
Cohesion: 0.33
Nodes (6): get_category_counts(), get_hoechste_notiz_id(), get_hoechste_veredelung_id(), Fuer GET /api/counts - Notebook pollt das periodisch, um Server- seitige…, get_counts(), Fuers periodische Notebook-Polling (Issue #16/#11) - erkennt Server-seitige…

### Community 5 - "database.py"
Cohesion: 0.07
Nodes (54): Any, structure_with_llm(), add_category(), _aehnlichster_treffer(), append_to_diary(), delete_note(), diary_hat_aehnliches_segment(), find_similar_recent() (+46 more)

### Community 6 - "📡 API-Spezifikation (`brain/`)"
Cohesion: 0.08
Nodes (24): Notizen auf dem USB-Stick (19.09.2026), Offene Punkte, A. `brain/` (Pi 5 / Server), 📡 API-Spezifikation (`brain/`), 📐 Architektur, 📁 Aufbau, B. `notebook/` (Pi Zero 2 W / Client), 🎛️ Bedienung (`notebook/`) (+16 more)

### Community 7 - "json"
Cohesion: 0.18
Nodes (14): _frage_gemma(), _json_ausschneiden(), _kategorien(), _main(), Vergleichs-Testskript zu veredelung_test.py: statt alle Notizen in einem Rutsch…, _json_ausschneiden(), _kategorien(), _main() (+6 more)

### Community 8 - "notizen-exportieren.py"
Cohesion: 0.17
Nodes (20): Holt einmalig nach, was vor der Mitschrift entstanden ist. Die Mitschrift…, aufgaben_schreiben(), eintraege_sammeln(), geraet_lesen(), hole(), ideen_schreiben(), main(), Path (+12 more)

### Community 9 - "pi_status.py"
Cohesion: 0.15
Nodes (17): brain_uptime_sekunden(), cpu_last_prozent(), _lese_cpu_zeiten(), pi_temperatur_celsius(), pi_uptime_sekunden(), ram_prozent(), Pi-5-Kennzahlen fuer die Geraete-Startseite. Liest nur aus dem Kernel (/proc,…, Alle Kennzahlen fuer die Geraete-Startseite in einem Rutsch. (+9 more)

### Community 10 - "imkopfhaben-brain -- Anleitung zum Starten und Stoppen"
Cohesion: 0.22
Nodes (8): Haeufige Fragen, imkopfhaben-brain -- Anleitung zum Starten und Stoppen, Notizen auf den USB-Stick legen (offline weiterarbeiten), So startest du (Schritt fuer Schritt), So stoppst du (wenn du fertig bist), Stündlich von selbst, solange die Dienste laufen (19.09.2026), Was da technisch laeuft (Kurzfassung), Wichtig: das laeuft NICHT von allein

### Community 11 - "imkopfhaben-start.sh"
Cohesion: 0.83
Nodes (3): fehler(), meldung(), imkopfhaben-start.sh script

### Community 12 - "notizen-auf-stick.sh"
Cohesion: 0.83
Nodes (3): aufraeumen(), meldung(), notizen-auf-stick.sh script

### Community 13 - "ESP32-S3-ePaper-3.97 — Hardware-Erkenntnisse"
Cohesion: 0.50
Nodes (3): Akku-Füllstand: echter Fuel-Gauge vorhanden, ESP32-S3-ePaper-3.97 — Hardware-Erkenntnisse, Referenz-Projekt: `alxv2016/folloup-sticky`

## Knowledge Gaps
- **28 isolated node(s):** `Notizen auf dem USB-Stick (19.09.2026)`, `📐 Architektur`, `🎛️ Bedienung (`notebook/`)`, `🛠️ Hardware`, `⚙️ Technische Besonderheiten` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 107 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `App` to `app.py`?**
  _High betweenness centrality (0.242) - this node is a cross-community bridge._
- **Why does `Übrige Punkte` connect `App` to `📡 API-Spezifikation (`brain/`)`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Why does `Offene Punkte` connect `📡 API-Spezifikation (`brain/`)` to `App`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **What connects `Notizen auf dem USB-Stick (19.09.2026)`, `📐 Architektur`, `🎛️ Bedienung (`notebook/`)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05505279034690799 - nodes in this community are weakly interconnected._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11688311688311688 - nodes in this community are weakly interconnected._
- **Should `database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06623376623376623 - nodes in this community are weakly interconnected._
# Graph Report - imkopfhaben-public  (2026-10-05)

## Corpus Check
- 20 files · ~20,480 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .service 4, (none) 1, .logrotate 1)

## Summary
- 331 nodes · 599 edges · 15 communities (14 shown, 1 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 7 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b82fb741`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- App
- app.py
- kopffrei_archiv.py
- mitschrift.py
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
2. `main()` - 14 edges
3. `📡 API-Spezifikation (`brain/`)` - 12 edges
4. `_arbeiter()` - 10 edges
5. `process_audio()` - 10 edges
6. `schreiben()` - 9 edges
7. `🧠 imkopfhaben` - 9 edges
8. `status()` - 8 edges
9. `_veredele_einzelne_notiz()` - 8 edges
10. `_lese_stand()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `_arbeiter()` --calls--> `transcribe_audio()`  [EXTRACTED]
  brain/kopffrei_archiv.py → brain/ai_service.py
- `process_audio()` --calls--> `transcribe_audio()`  [EXTRACTED]
  brain/main.py → brain/ai_service.py
- `lifespan()` --calls--> `init_db()`  [EXTRACTED]
  brain/main.py → brain/database.py
- `list_notes()` --calls--> `get_all_notes()`  [EXTRACTED]
  brain/main.py → brain/database.py
- `_main()` --calls--> `get_all_notes()`  [EXTRACTED]
  brain/veredelung_test_iterativ.py → brain/database.py

## Import Cycles
- None detected.

## Communities (15 total, 1 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.06
Nodes (46): asyncio, BaseModel, transcribe_audio(), get_buendel_vorschlaege(), get_category_counts(), get_hoechste_notiz_id(), get_hoechste_veredelung_id(), init_db() (+38 more)

### Community 1 - "App"
Cohesion: 0.15
Nodes (11): Image, ImageFont, App, _lade_sync_stand(), Konvertiert PIL Image in das vom Whisplay LCD erwartete RGB565 Format., Bricht Text anhand der tatsächlichen Pixelbreite sauber um., Arbeitet die Warteschlange aeltestenzuerst ab (Dateiname beginnt mit…, Periodischer Abgleich mit dem Brain (Issue #11/#16), analog zum… (+3 more)

### Community 2 - "app.py"
Cohesion: 0.08
Nodes (27): argparse, logging, _fsync_verzeichnis(), geschaetzte_energie(), _laden(), _leerer_stand(), _main(), Der Akku-Lerner — schätzt, wie lange der Akku noch hält, rein aus beobachteten… (+19 more)

### Community 3 - "kopffrei_archiv.py"
Cohesion: 0.14
Nodes (30): annehmen(), _arbeiter(), _ausstehend(), geraet_meldet_sich(), _ist_lokal(), _jetzt(), _lese_stand(), _merke_geraet() (+22 more)

### Community 4 - "mitschrift.py"
Cohesion: 0.16
Nodes (16): _anhaengen_atomar(), lesen(), mitschreiben(), main(), Holt einmalig nach, was vor der Mitschrift entstanden ist. Die Mitschrift…, Path, Mitschrift: jedes Transkript beim Entstehen wegschreiben. Warum es das gibt…, Anhaengen und auf die Platte zwingen. Ohne flush/fsync steht bei einem… (+8 more)

### Community 5 - "database.py"
Cohesion: 0.07
Nodes (54): Any, structure_with_llm(), add_category(), _aehnlichster_treffer(), append_to_diary(), delete_note(), diary_hat_aehnliches_segment(), find_similar_recent() (+46 more)

### Community 6 - "📡 API-Spezifikation (`brain/`)"
Cohesion: 0.07
Nodes (25): 420-Track in den Vault-Export (20.09.2026), Notizen auf dem USB-Stick (19.09.2026), Offene Punkte, A. `brain/` (Pi 5 / Server), 📡 API-Spezifikation (`brain/`), 📐 Architektur, 📁 Aufbau, B. `notebook/` (Pi Zero 2 W / Client) (+17 more)

### Community 7 - "json"
Cohesion: 0.18
Nodes (14): _frage_gemma(), _json_ausschneiden(), _kategorien(), _main(), Vergleichs-Testskript zu veredelung_test.py: statt alle Notizen in einem Rutsch…, _json_ausschneiden(), _kategorien(), _main() (+6 more)

### Community 8 - "notizen-exportieren.py"
Cohesion: 0.13
Nodes (29): aufgaben_schreiben(), eintraege_sammeln(), geraet_lesen(), hole(), ideen_schreiben(), main(), Path, Beide Quellen zu einer Liste zusammenfuehren. Das Geraet hat Vorrang, weil nur… (+21 more)

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
- **29 isolated node(s):** `Notizen auf dem USB-Stick (19.09.2026)`, `420-Track in den Vault-Export (20.09.2026)`, `📐 Architektur`, `🎛️ Bedienung (`notebook/`)`, `🛠️ Hardware` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 128 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `App` to `app.py`?**
  _High betweenness centrality (0.220) - this node is a cross-community bridge._
- **Why does `Übrige Punkte` connect `App` to `📡 API-Spezifikation (`brain/`)`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Why does `Offene Punkte` connect `📡 API-Spezifikation (`brain/`)` to `App`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **What connects `Notizen auf dem USB-Stick (19.09.2026)`, `420-Track in den Vault-Export (20.09.2026)`, `📐 Architektur` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.056429232192414434 - nodes in this community are weakly interconnected._
- **Should `App` be split into smaller, more focused modules?**
  _Cohesion score 0.1476923076923077 - nodes in this community are weakly interconnected._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07777777777777778 - nodes in this community are weakly interconnected._
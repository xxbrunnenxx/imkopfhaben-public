# Graph Report - imkopfhaben-public  (2026-10-05)

## Corpus Check
- 5 files · ~6,515 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: .service 2, (none) 1)

## Summary
- 116 nodes · 143 edges · 24 communities (7 shown, 17 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8d5382fb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- asyncio
- App
- akku_lernen.py
- queue
- app.py
- difflib
- 🧠 imkopfhaben
- faster_whisper
- collections
- 📡 API-Spezifikation (`brain/`)
- Archive
- ._push
- contextlib
- ESP32-S3-ePaper-3.97 — Hardware-Erkenntnisse
- fastapi_middleware_cors
- fastapi_responses
- pydantic
- re
- sqlite3
- tempfile
- typing
- urllib_error
- urllib_parse
- urllib_request

## God Nodes (most connected - your core abstractions)
1. `App` - 17 edges
2. `📡 API-Spezifikation (`brain/`)` - 12 edges
3. `🧠 imkopfhaben` - 9 edges
4. `Archive` - 7 edges
5. `_main()` - 6 edges
6. `_laden()` - 5 edges
7. `Übrige Punkte` - 5 edges
8. `_schreiben()` - 4 edges
9. `geschaetzte_energie()` - 4 edges
10. `_aktualisiere_tag_colors()` - 4 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (24 total, 17 thin omitted)

### Community 1 - "App"
Cohesion: 0.24
Nodes (5): ImageFont, App, Bricht Text anhand der tatsächlichen Pixelbreite sauber um., Arbeitet die Warteschlange aeltestenzuerst ab (Dateiname beginnt mit…, Übrige Punkte

### Community 2 - "akku_lernen.py"
Cohesion: 0.13
Nodes (19): argparse, json, _fsync_verzeichnis(), geschaetzte_energie(), _laden(), _leerer_stand(), _main(), Der Akku-Lerner — schätzt, wie lange der Akku noch hält, rein aus beobachteten… (+11 more)

### Community 4 - "app.py"
Cohesion: 0.12
Nodes (16): datetime, logging, _aktualisiere_tag_colors(), _hex_zu_rgb(), _lade_sync_stand(), _load_fonts(), Periodischer Abgleich mit dem Brain (Issue #11/#16), analog zum…, Holt die Kategorie-Farben vom Brain (GET /api/config) und ergaenzt/… (+8 more)

### Community 6 - "🧠 imkopfhaben"
Cohesion: 0.13
Nodes (13): 420-Track in den Vault-Export (20.09.2026), Notizen auf dem USB-Stick (19.09.2026), Offene Punkte, A. `brain/` (Pi 5 / Server), 📐 Architektur, 📁 Aufbau, B. `notebook/` (Pi Zero 2 W / Client), 🎛️ Bedienung (`notebook/`) (+5 more)

### Community 9 - "📡 API-Spezifikation (`brain/`)"
Cohesion: 0.17
Nodes (12): 📡 API-Spezifikation (`brain/`), `DELETE /api/notes/{note_id}`, `GET /`, `GET /api/buendel-vorschlaege` / `DELETE /api/buendel-vorschlaege/{id}`, `GET /api/config`, `GET /api/counts`, `GET /api/health` (Alias: `GET /health`), `GET /api/notes` (+4 more)

### Community 11 - "._push"
Cohesion: 0.67
Nodes (3): Image, Konvertiert PIL Image in das vom Whisplay LCD erwartete RGB565 Format., rgb565_bytes()

### Community 13 - "ESP32-S3-ePaper-3.97 — Hardware-Erkenntnisse"
Cohesion: 0.50
Nodes (3): Akku-Füllstand: echter Fuel-Gauge vorhanden, ESP32-S3-ePaper-3.97 — Hardware-Erkenntnisse, Referenz-Projekt: `alxv2016/folloup-sticky`

## Knowledge Gaps
- **23 isolated node(s):** `Notizen auf dem USB-Stick (19.09.2026)`, `420-Track in den Vault-Export (20.09.2026)`, `📐 Architektur`, `🎛️ Bedienung (`notebook/`)`, `🛠️ Hardware` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 66 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `App` to `._push`, `app.py`?**
  _High betweenness centrality (0.345) - this node is a cross-community bridge._
- **Why does `Offene Punkte` connect `🧠 imkopfhaben` to `App`?**
  _High betweenness centrality (0.281) - this node is a cross-community bridge._
- **Why does `Übrige Punkte` connect `App` to `🧠 imkopfhaben`?**
  _High betweenness centrality (0.281) - this node is a cross-community bridge._
- **What connects `Notizen auf dem USB-Stick (19.09.2026)`, `420-Track in den Vault-Export (20.09.2026)`, `📐 Architektur` to the rest of the system?**
  _23 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `akku_lernen.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12280701754385964 - nodes in this community are weakly interconnected._
- **Should `🧠 imkopfhaben` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
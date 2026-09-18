# Graph Report - imkopfhaben-public  (2026-09-18)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 152 nodes · 238 edges · 17 communities (10 shown, 7 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `090f585c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- App
- app.py
- akku_lernen.py
- database.py
- veredelung_service.py
- Any
- veredelung_test.py
- _aehnlichster_treffer
- veredelung_test_iterativ.py
- get_alte_tagebuch_eintraege
- get_buendel_vorschlaege
- get_diary_entry_for_date
- get_notes_ohne_veredelung
- get_veredelte_seit
- get_veredelung_for_note
- zaehle_kategorie_vorschlag

## God Nodes (most connected - your core abstractions)
1. `App` - 17 edges
2. `Archive` - 7 edges
3. `_laden()` - 5 edges
4. `_main()` - 5 edges
5. `_frage_gemma()` - 5 edges
6. `fuehre_veredelung_schritt_aus()` - 5 edges
7. `get_note_by_id()` - 5 edges
8. `transcribe_raw()` - 4 edges
9. `rgb565_bytes()` - 4 edges
10. `_aktualisiere_tag_colors()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `LM Studio haelt sich nicht immer strikt an 'nur JSON antworten' - schneidet…` --rationale_for--> `_json_ausschneiden()`  [EXTRACTED]
  brain/veredelung_test.py → brain/veredelung_service.py

## Import Cycles
- None detected.

## Communities (17 total, 7 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.09
Nodes (29): BaseModel, delete_note(), get_buendel_vorschlaege(), get_config(), get_counts(), health_check(), lifespan(), list_notes() (+21 more)

### Community 1 - "App"
Cohesion: 0.19
Nodes (7): Image, ImageFont, App, Konvertiert PIL Image in das vom Whisplay LCD erwartete RGB565 Format., Bricht Text anhand der tatsächlichen Pixelbreite sauber um., Arbeitet die Warteschlange aeltestenzuerst ab (Dateiname beginnt mit…, rgb565_bytes()

### Community 2 - "app.py"
Cohesion: 0.16
Nodes (9): _aktualisiere_tag_colors(), Archive, _hex_zu_rgb(), _lade_sync_stand(), _load_fonts(), Periodischer Abgleich mit dem Brain (Issue #11/#16), analog zum…, Holt die Kategorie-Farben vom Brain (GET /api/config) und ergaenzt/…, _speichere_sync_stand() (+1 more)

### Community 3 - "akku_lernen.py"
Cohesion: 0.23
Nodes (13): _fsync_verzeichnis(), geschaetzte_energie(), _laden(), _leerer_stand(), _main(), Der Akku-Lerner — schätzt, wie lange der Akku noch hält, rein aus beobachteten…, Beim Start aufgerufen, bevor der neue Zyklus losgeht: ist der vorige Lauf ohne…, Fehlt die Datei, ist das kein Fehler (erster Start überhaupt) — ist sie kaputt,… (+5 more)

### Community 4 - "database.py"
Cohesion: 0.15
Nodes (6): get_categories(), get_category_counts(), loesche_leere_kategorien(), Name -> Farbe, sortiert nach Anlagedatum. Einzige Quelle der Wahrheit fuer…, Entfernt echt (nicht nur ausgeblendet) alle Kategorien ohne zugehoerige Notiz -…, Fuer GET /api/counts - Notebook pollt das periodisch, um Server- seitige…

### Community 5 - "veredelung_service.py"
Cohesion: 0.33
Nodes (10): _buendel_erkennen(), _farbe_fuer_neue_kategorie(), _frage_gemma(), fuehre_veredelung_schritt_aus(), _json_ausschneiden(), Idle-Zeit-Veredelung der Notizen (Issue #16) - Produktionsmodul, aus den…, Deterministisch aus der Anzahl bestehender Kategorien abgeleitet, damit neue…, Fuehrt GENAU EINEN Veredelungsschritt aus (ein LLM-Call oder eine reine DB-… (+2 more)

### Community 6 - "Any"
Cohesion: 0.27
Nodes (10): Any, append_to_diary(), get_all_notes(), get_note_by_id(), Titel wird beim Speichern immer auf die Kategorie gesetzt (wie beim…, Haengt einen weiteren Eintrag mit Uhrzeit-Praefix an einen bestehenden…, save_note(), save_veredelung() (+2 more)

### Community 7 - "veredelung_test.py"
Cohesion: 0.43
Nodes (6): _json_ausschneiden(), _kategorien(), _main(), Eigenstaendiges Testskript fuer die Idle-Zeit-Veredelung (Issue #16). Bewusst…, LM Studio haelt sich nicht immer strikt an 'nur JSON antworten' - schneidet…, veredele()

### Community 8 - "_aehnlichster_treffer"
Cohesion: 0.33
Nodes (6): _aehnlichster_treffer(), diary_hat_aehnliches_segment(), find_similar_recent(), Vergleicht `text` per difflib.SequenceMatcher (Groß-/Kleinschreibung ignoriert)…, Prueft, ob der neue Transkript-Text einem bereits im Tageseintrag enthaltenen…, Sucht in den letzten `minutes` Minuten nach einer Notiz mit sehr aehnlichem…

### Community 9 - "veredelung_test_iterativ.py"
Cohesion: 0.53
Nodes (5): _frage_gemma(), _json_ausschneiden(), _kategorien(), _main(), Vergleichs-Testskript zu veredelung_test.py: statt alle Notizen in einem Rutsch…

## Knowledge Gaps
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `App` to `app.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08712121212121213 - nodes in this community are weakly interconnected._
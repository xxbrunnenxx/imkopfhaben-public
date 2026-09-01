"""Idle-Zeit-Veredelung der Notizen (Issue #16) - Produktionsmodul, aus den
Testskripten veredelung_test.py/veredelung_test_iterativ.py hervorgegangen.

Fuehrt bei jedem Aufruf von fuehre_veredelung_schritt_aus() GENAU EINEN
kleinen Arbeitsschritt aus (ein LLM-Call, oder eine reine DB-Operation ohne
LLM) und kehrt dann zurueck - der Aufrufer (main.py) entscheidet ueber den
Pausen-Trigger, wie oft das passiert, und kann zwischen zwei Aufrufen jederzeit
abbrechen, ohne mitten in einer Modell-Generierung zu unterbrechen.

Nutzt bewusst ein anderes, kleineres Modell (google/gemma-4-e2b ueber LM
Studio) als der Live-Pfad (qwen2.5:7b ueber Ollama) - Ergebnis eines
Vergleichstests (siehe Issue #16, Kommentare): e2b war schneller,
zuverlaessiger UND qualitativ mindestens gleichauf. e4b ist an den zwei
anspruchsvollsten Aufgaben (grosser Tagebuch-Text, Buendel-Erkennung ueber
alle Notizen) wiederholt gescheitert.
"""

import json
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

import requests

import database

LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
VEREDELUNGS_MODELL = "google/gemma-4-e2b"

# Wie lange ein Tagebuch-Tageseintrag zurueckliegen muss, bevor er in die
# mehrtaegige Verdichtung einfliesst (Punkt 4) - nicht der aktuelle Tag oder
# die letzten Tage, die man noch im Kopf hat.
TAGEBUCH_VERDICHTUNGS_ALTER_TAGE = 7

# Ab wie vielen gleichlautenden Kategorie-Vorschlaegen (fuer eine bislang
# nicht existierende Kategorie) die Veredelung sie tatsaechlich anlegt.
# Kein aus der Diskussion abgeleiteter fester Wert (die sagt "haengt vom
# Kontext ab") - 2 ist die niedrigste Schwelle, die noch ein Muster von
# einem Einzelfall unterscheidet.
NEUE_KATEGORIE_SCHWELLE = 2

EINZEL_PROMPT = """Notiz [{kategorie}] ({zeit}): "{text}"

Aufgabe:
1. Glaette den Text sprachlich - klare, kurze Saetze statt rohem
   Transkript-Stil, ohne Inhalt zu veraendern oder zu erfinden.
2. Pruefe die Kategorie - waehle aus [{kategorien}] die passendste
   (kann die bestehende bestaetigen). Falls wirklich keine der
   bestehenden Kategorien passt, kannst du stattdessen einen kurzen,
   neuen Kategorienamen vorschlagen (ein Wort, groß geschrieben).

Antworte AUSSCHLIESSLICH als JSON:
{{"geglaettet": "<Text>", "kategorie_vorschlag": "<Kategorie>", "kategorie_geaendert": <true/false>}}"""

BUENDEL_PROMPT = """Notizen:
{notizen}

Erkenne inhaltlich redundante/sehr aehnliche Notizen (auch sinngemaess,
nicht nur wortgleich) und gruppiere ihre IDs. Nutze NUR die IDs, die oben
tatsaechlich aufgelistet sind - erfinde keine.

Antworte AUSSCHLIESSLICH als JSON:
{{"buendel_vorschlaege": [{{"ids": [<ID>, ...], "begruendung": "<kurz>"}}]}}"""

TAGEBUCH_VERDICHTUNGS_PROMPT = """Tagebuch-Eintraege mehrerer Tage:
{eintraege}

Fasse diese Tage zu EINER kompakten Zusammenfassung zusammen - die
wichtigsten Ereignisse/Stimmungen, ohne jeden Einzelsatz zu wiederholen.

Antworte AUSSCHLIESSLICH als JSON:
{{"zusammenfassung": "<Text>"}}"""


def _json_ausschneiden(text: str) -> str:
    """LM Studio haelt sich nicht immer strikt an 'nur JSON antworten' -
    schneidet ggf. Markdown-Codebloecke oder Text drumherum weg."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    ende = text.rfind("}")
    return text[start:ende + 1] if start != -1 and ende != -1 else text


def _frage_gemma(prompt: str, max_tokens: int = 1500) -> dict:
    payload = {
        "model": VEREDELUNGS_MODELL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    resp = requests.post(LMSTUDIO_URL, json=payload, timeout=400)
    resp.raise_for_status()
    inhalt = resp.json()["choices"][0]["message"]["content"]
    return json.loads(_json_ausschneiden(inhalt))


def _veredele_einzelne_notiz(notiz: dict) -> str:
    kategorien = list(database.get_categories().keys())
    prompt = EINZEL_PROMPT.format(
        kategorie=notiz["category"], zeit=notiz["created_at"], text=notiz["body"],
        kategorien=", ".join(kategorien),
    )
    ergebnis = _frage_gemma(prompt)
    geglaettet = ergebnis.get("geglaettet") or notiz["body"]
    kategorie_vorschlag = ergebnis.get("kategorie_vorschlag")

    database.save_veredelung(notiz["id"], geglaettet, kategorie_vorschlag)

    # Neue, bislang unbekannte Kategorie: nur anlegen, wenn sie wiederholt
    # vorgeschlagen wurde (Issue #16, Punkt 5) - ein einzelner Vorschlag ist
    # kein Muster.
    if kategorie_vorschlag and kategorie_vorschlag not in kategorien:
        haeufigkeit = database.zaehle_kategorie_vorschlag(kategorie_vorschlag)
        if haeufigkeit >= NEUE_KATEGORIE_SCHWELLE:
            database.add_category(kategorie_vorschlag, _farbe_fuer_neue_kategorie())
            return f"Notiz #{notiz['id']} veredelt, neue Kategorie '{kategorie_vorschlag}' angelegt (x{haeufigkeit})"

    return f"Notiz #{notiz['id']} veredelt"


def _farbe_fuer_neue_kategorie() -> str:
    """Deterministisch aus der Anzahl bestehender Kategorien abgeleitet,
    damit neue Kategorien nicht alle dieselbe Farbe wie die zuletzt
    manuell vergebene haben."""
    palette = ["#f59e0b", "#10b981", "#6366f1", "#ec4899", "#14b8a6", "#f97316", "#8b5cf6"]
    return palette[len(database.get_categories()) % len(palette)]


def _buendel_erkennen() -> Optional[str]:
    notizen = database.get_all_notes(limit=200)
    if len(notizen) < 2:
        return None
    gueltige_ids = {n["id"] for n in notizen}
    notizen_text = "\n".join(f"- ID {n['id']}: {n['body']}" for n in notizen)

    ergebnis = _frage_gemma(BUENDEL_PROMPT.format(notizen=notizen_text), max_tokens=3000)
    vorschlaege = ergebnis.get("buendel_vorschlaege", [])

    # ID-Validierung gegen die tatsaechlich existierenden Notizen - beim
    # Testen halluzinierte Gemma wiederholt nicht existierende IDs oder
    # verwechselte im Text vorkommende Uhrzeiten mit echten Notiz-IDs
    # (siehe Issue #16). Nur Vorschlaege mit ausschliesslich echten,
    # numerischen IDs werden uebernommen.
    gueltige_vorschlaege = []
    for v in vorschlaege:
        ids = v.get("ids", [])
        bereinigt = [i for i in ids if isinstance(i, int) and i in gueltige_ids]
        if len(bereinigt) >= 2:
            gueltige_vorschlaege.append({"ids": bereinigt, "begruendung": v.get("begruendung", "")})

    if gueltige_vorschlaege:
        database.speichere_buendel_vorschlaege(gueltige_vorschlaege)
        return f"{len(gueltige_vorschlaege)} Bündel-Vorschläge gespeichert (von {len(vorschlaege)} roh, Rest ungültige IDs verworfen)"
    return "Bündel-Erkennung gelaufen, nichts Verwertbares gefunden"


def _tagebuch_verdichten() -> Optional[str]:
    grenze = (datetime.now() - timedelta(days=TAGEBUCH_VERDICHTUNGS_ALTER_TAGE)).strftime("%Y-%m-%d")
    alte_eintraege = database.get_alte_tagebuch_eintraege(vor_datum=grenze)
    if len(alte_eintraege) < 2:
        return None

    eintraege_text = "\n\n".join(f"[{e['created_at'][:10]}]\n{e['body']}" for e in alte_eintraege)
    ergebnis = _frage_gemma(TAGEBUCH_VERDICHTUNGS_PROMPT.format(eintraege=eintraege_text), max_tokens=1500)
    zusammenfassung = ergebnis.get("zusammenfassung")
    if not zusammenfassung:
        return None

    ids = [e["id"] for e in alte_eintraege]
    zeitraum = f"{alte_eintraege[0]['created_at'][:10]} bis {alte_eintraege[-1]['created_at'][:10]}"
    database.save_note(
        title="Tagebuch",
        body=f"Verdichtet ({zeitraum}):\n{zusammenfassung}",
        category="Tagebuch",
        priority="normal",
        raw_transcript=eintraege_text,
    )
    for i in ids:
        database.delete_note(i)
    return f"{len(ids)} Tagebuch-Einträge zu einer Zusammenfassung verdichtet ({zeitraum})"


def fuehre_veredelung_schritt_aus() -> Optional[str]:
    """Fuehrt GENAU EINEN Veredelungsschritt aus (ein LLM-Call oder eine
    reine DB-Operation) und gibt eine kurze Beschreibung zurueck, oder None
    wenn es aktuell nichts zu tun gibt. Reihenfolge: erst unveredelte
    Notizen einzeln abarbeiten, dann Buendel-Erkennung, dann Tagebuch-
    Verdichtung, dann leere Kategorien aufraeumen."""
    unveredelt = database.get_notes_ohne_veredelung(limit=1)
    if unveredelt:
        return _veredele_einzelne_notiz(unveredelt[0])

    buendel_ergebnis = _buendel_erkennen()
    if buendel_ergebnis:
        return buendel_ergebnis

    verdichtung_ergebnis = _tagebuch_verdichten()
    if verdichtung_ergebnis:
        return verdichtung_ergebnis

    geloescht = database.loesche_leere_kategorien()
    if geloescht:
        return f"Leere Kategorien entfernt: {', '.join(geloescht)}"

    return None

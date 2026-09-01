"""Vergleichs-Testskript zu veredelung_test.py: statt alle Notizen in
einem Rutsch zu schicken, wird jede einzeln an Gemma gegeben (glaetten +
Kategorie pruefen). Das Buendeln redundanter Notizen läuft als separater,
zweiter Schritt am Ende ueber alle (schon veredelten) Texte - iterativ
macht sonst wenig Sinn, Bündeln braucht zwangsläufig mehrere Notizen im
Blick.

Bewusst getrennt von veredelung_test.py, um Batch- vs. iterativen Ansatz
direkt zu vergleichen (Zeit pro Call, Qualitaet, Ausfallsicherheit).

Aufruf:
    cd brain && venv/bin/python3 -u veredelung_test_iterativ.py
"""

import json
import time

import requests

import database

LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
VEREDELUNGS_MODELL = "google/gemma-4-e4b"

EINZEL_PROMPT = """Notiz [{kategorie}] ({zeit}): "{text}"

Aufgabe:
1. Glaette den Text sprachlich - klare, kurze Saetze statt rohem
   Transkript-Stil, ohne Inhalt zu veraendern oder zu erfinden.
2. Pruefe die Kategorie - waehle aus [{kategorien}] die passendste
   (kann die bestehende bestaetigen).

Antworte AUSSCHLIESSLICH als JSON:
{{"geglaettet": "<Text>", "kategorie_vorschlag": "<Kategorie>", "kategorie_geaendert": <true/false>}}"""

BUENDEL_PROMPT = """Notizen:
{notizen}

Erkenne inhaltlich redundante/sehr aehnliche Notizen (auch sinngemaess,
nicht nur wortgleich) und gruppiere ihre IDs.

Antworte AUSSCHLIESSLICH als JSON:
{{"buendel_vorschlaege": [{{"ids": [<ID>, ...], "begruendung": "<kurz>"}}]}}"""


def _json_ausschneiden(text: str) -> str:
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
    data = resp.json()
    inhalt = data["choices"][0]["message"]["content"]
    finish_reason = data["choices"][0].get("finish_reason")
    ausgeschnitten = _json_ausschneiden(inhalt)
    try:
        return json.loads(ausgeschnitten)
    except json.JSONDecodeError as e:
        # Rohantwort mitloggen statt blind zu scheitern - beim letzten Lauf
        # war unklar, ob abgeschnitten (finish_reason=length) oder das
        # Modell hat schlicht fehlerhaftes JSON gebaut.
        print(f"  [JSON-Fehler] finish_reason={finish_reason}, Antwortlaenge={len(inhalt)} Zeichen")
        print(f"  [Rohantwort] {inhalt!r}")
        raise


def _kategorien() -> list:
    resp = requests.get("http://localhost:8000/api/config", timeout=5)
    resp.raise_for_status()
    return list(resp.json().get("categories", {}).keys())


def _main() -> None:
    notizen = database.get_all_notes(limit=500)
    kategorien = _kategorien()
    print(f"{len(notizen)} Notizen, iterativ, ein Call pro Notiz\n")

    veredelt = []
    gesamt_start = time.monotonic()
    for n in notizen:
        prompt = EINZEL_PROMPT.format(
            kategorie=n["category"], zeit=n["created_at"], text=n["body"],
            kategorien=", ".join(kategorien),
        )
        t0 = time.monotonic()
        try:
            ergebnis = _frage_gemma(prompt)
            dauer = time.monotonic() - t0
            print(f"#{n['id']} [{n['category']}] ({dauer:.1f}s)")
            print(f"  vorher:  {n['body']}")
            print(f"  nachher: {ergebnis.get('geglaettet')}")
            if ergebnis.get("kategorie_geaendert"):
                print(f"  Kategorie-Vorschlag: {ergebnis.get('kategorie_vorschlag')}")
            veredelt.append({"id": n["id"], **ergebnis})
        except Exception as e:
            dauer = time.monotonic() - t0
            print(f"#{n['id']} FEHLER nach {dauer:.1f}s: {e}")
        print()

    print(f"Gesamtzeit Einzel-Calls: {time.monotonic() - gesamt_start:.1f}s\n")

    print("=== Bündel-Erkennung (ein Call ueber alle) ===")
    notizen_text = "\n".join(f"- ID {n['id']}: {n['body']}" for n in notizen)
    t0 = time.monotonic()
    try:
        buendel_ergebnis = _frage_gemma(BUENDEL_PROMPT.format(notizen=notizen_text), max_tokens=3000)
        print(f"({time.monotonic() - t0:.1f}s)")
        for b in buendel_ergebnis.get("buendel_vorschlaege", []):
            print(f"  IDs {b.get('ids')}: {b.get('begruendung')}")
    except Exception as e:
        print(f"FEHLER nach {time.monotonic() - t0:.1f}s: {e}")


if __name__ == "__main__":
    _main()

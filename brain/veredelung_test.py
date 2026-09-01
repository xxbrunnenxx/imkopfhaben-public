"""Eigenstaendiges Testskript fuer die Idle-Zeit-Veredelung (Issue #16).

Bewusst NICHT in main.py verdrahtet - kein Pausen-Trigger, keine neue
DB-Tabelle, kein Notebook-Sync. Nimmt die bestehenden Notizen aus der DB,
schickt sie an Gemma-4-E4B ueber LM Studio (lokal, Port 1234, OpenAI-
kompatible API) und gibt das Ergebnis nur aus - schreibt nichts zurueck.

Reiner Probelauf, um zu sehen, ob das Modell brauchbare Ergebnisse liefert,
bevor der Rest der Architektur (Tabelle, Endpunkte, Sync) gebaut wird.

Aufruf:
    cd brain && venv/bin/python3 veredelung_test.py
"""

import json

import requests

import database

LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
VEREDELUNGS_MODELL = "google/gemma-4-e4b"

# Eigener Prompt, bewusst getrennt von ai_service.structure_with_llm() -
# die Veredelung ist eine andere Aufgabe (Nachbearbeitung mehrerer
# bestehender Notizen) als die Live-Kategorisierung einer einzelnen
# frischen Aufnahme (siehe Issue #16, Entscheidung "eigener neuer Prompt").
VEREDELUNGS_PROMPT = """Du bekommst eine Liste bereits gespeicherter Sprachnotizen (roh
transkribiert, teils holprig gesprochen). Deine Aufgabe:

1. Glaette jeden Text sprachlich - aus rohem Transkript-Stil klare, kurze
   Saetze machen, ohne den Inhalt zu veraendern oder etwas hinzuzuerfinden.
2. Pruefe die vergebene Kategorie nochmal - falls eine andere Kategorie aus
   [{kategorien}] besser passt, schlage sie vor, sonst die bestehende
   bestaetigen.
3. Erkenne inhaltlich redundante/sehr aehnliche Notizen untereinander
   (nicht nur wortgleich, auch sinngemaess) und gruppiere ihre IDs.

Notizen:
{notizen}

Antworte AUSSCHLIESSLICH als JSON in diesem Format:
{{
  "veredelt": [
    {{"id": <ID>, "geglaettet": "<glatter Text>", "kategorie_vorschlag": "<Kategorie>", "kategorie_geaendert": <true/false>}}
  ],
  "buendel_vorschlaege": [
    {{"ids": [<ID>, <ID>, ...], "begruendung": "<kurz, warum die zusammengehoeren>"}}
  ]
}}"""


def _kategorien() -> list:
    resp = requests.get("http://localhost:8000/api/config", timeout=5)
    resp.raise_for_status()
    return list(resp.json().get("categories", {}).keys())


def veredele(notizen: list, kategorien: list) -> dict:
    notizen_text = "\n".join(
        f"- ID {n['id']} [{n['category']}] ({n['created_at']}): {n['body']}"
        for n in notizen
    )
    prompt = VEREDELUNGS_PROMPT.format(
        kategorien=", ".join(kategorien),
        notizen=notizen_text,
    )

    payload = {
        "model": VEREDELUNGS_MODELL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    resp = requests.post(LMSTUDIO_URL, json=payload, timeout=300)
    resp.raise_for_status()
    inhalt = resp.json()["choices"][0]["message"]["content"]
    return json.loads(_json_ausschneiden(inhalt))


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


def _main() -> None:
    notizen = database.get_all_notes(limit=500)
    if not notizen:
        print("Keine Notizen in der DB - nichts zu veredeln.")
        return

    kategorien = _kategorien()
    print(f"{len(notizen)} Notizen, Kategorien: {kategorien}\n")
    print("Sende an Gemma-4-E4B (LM Studio)...\n")

    ergebnis = veredele(notizen, kategorien)

    print("=== Veredelte Texte ===")
    for eintrag in ergebnis.get("veredelt", []):
        original = next((n for n in notizen if n["id"] == eintrag.get("id")), None)
        print(f"\n#{eintrag.get('id')} [{original['category'] if original else '?'}]")
        print(f"  vorher: {original['body'] if original else '?'}")
        print(f"  nachher: {eintrag.get('geglaettet')}")
        if eintrag.get("kategorie_geaendert"):
            print(f"  Kategorie-Vorschlag: {eintrag.get('kategorie_vorschlag')}")

    print("\n=== Bündel-Vorschläge (redundante Notizen) ===")
    buendel = ergebnis.get("buendel_vorschlaege", [])
    if not buendel:
        print("Keine gefunden.")
    for b in buendel:
        print(f"  IDs {b.get('ids')}: {b.get('begruendung')}")


if __name__ == "__main__":
    _main()

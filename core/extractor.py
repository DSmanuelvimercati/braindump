"""
Estrae entità, fatti e struttura vault dalle trascrizioni, usando Gemma4.
"""

import json
import re
from core.model import think  # text-only via Ollama
from core import vault


SYSTEM_EXTRACT = """Sei un assistente che organizza ricordi e pensieri personali in un vault Obsidian.
Ricevi quello che l'utente ha detto e il contesto esistente nel vault.
Estrai informazioni strutturate e decidi come organizzarle in note markdown.
Rispondi SOLO con JSON valido, niente altro."""


def extract(transcript: str) -> list[dict]:
    """
    Analizza una trascrizione e ritorna una lista di operazioni vault da eseguire.
    Ogni operazione: {"action": "write"|"merge"|"journal", "folder": str, "title": str, "content": str, "tags": [str]}
    """
    context = vault.context_summary()

    prompt = f"""L'utente ha detto:
"{transcript}"

Contesto vault esistente:
{context}

Analizza e restituisci un JSON con questa struttura:
{{
  "operazioni": [
    {{
      "action": "merge",
      "folder": "Persone|Lavoro|Esperienze|Idee|Concetti|Journal",
      "title": "titolo della nota",
      "content": "testo markdown in prima persona, usa [[Nome]] per collegare persone/concetti menzionati",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

Regole:
- Scrivi SEMPRE in prima persona ("lavoro", "ho fatto", "mi piace", ecc.)
- Usa [[wikilinks]] per persone, luoghi, aziende, concetti chiave
- Se viene menzionata una persona → crea/aggiorna nota in Persone/
- Se viene menzionato il lavoro → Lavoro/
- Se è un'esperienza/ricordo → Esperienze/
- Se è un'idea/riflessione → Idee/
- Aggiungi sempre una operazione "journal" con il Journal del giorno
- Se il testo è troppo vago o non contiene informazioni utili, restituisci solo l'operazione journal
- Titoli brevi e chiari, max 5 parole"""

    raw = think(SYSTEM_EXTRACT, prompt)

    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return data.get("operazioni", [])
    except json.JSONDecodeError:
        pass

    # Fallback: salva almeno nel journal
    return [{"action": "journal", "folder": "Journal", "title": "", "content": transcript, "tags": ["journal"]}]


def apply(operazioni: list[dict]):
    """Esegue le operazioni sul vault."""
    for op in operazioni:
        action = op.get("action", "merge")
        folder = op.get("folder", "Idee")
        title = op.get("title", "")
        content = op.get("content", "")
        tags = op.get("tags", [])

        if action == "journal" or folder == "Journal":
            vault.append_to_daily(content)
        elif action == "write":
            vault.write(folder, title, content, tags)
        else:  # merge (default)
            vault.merge(folder, title, content, tags)

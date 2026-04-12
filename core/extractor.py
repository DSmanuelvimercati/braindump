"""
Estrae entità, fatti e struttura vault dalle trascrizioni, usando Gemma4.
"""

import json
import re
from core.model import think  # text-only via Ollama
from core import vault


def extract(transcript: str) -> list[dict]:
    """
    Analizza una trascrizione e ritorna una lista di operazioni vault da eseguire.
    Ogni operazione: {"action": "merge", "folder": str, "title": str, "content": str, "tags": [str]}
    """
    from core.prompts import get as get_prompt
    context = vault.context_summary()

    prompt = f"""Contesto vault esistente:
{context}

Trascrizione da elaborare:
{transcript}

Restituisci il JSON delle operazioni."""

    raw = think(get_prompt("extractor"), prompt)

    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return data.get("operazioni", [])
        print(f"  [extractor] nessun JSON trovato nella risposta: {raw[:200]!r}", flush=True)
    except json.JSONDecodeError as e:
        print(f"  [extractor] JSON non valido: {e} — risposta: {raw[:200]!r}", flush=True)

    return []


def apply(operazioni: list[dict]):
    """Esegue le operazioni sul vault."""
    for op in operazioni:
        folder = op.get("folder", "")
        title = op.get("title", "")
        content = op.get("content", "")
        tags = op.get("tags", [])
        if folder and title and content:
            vault.merge(folder, title, content, tags)

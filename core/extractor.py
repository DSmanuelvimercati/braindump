"""
Estrae entità, fatti e struttura vault dalle trascrizioni, usando Gemma4.
"""

import json
import re
from core.model import think  # text-only via Ollama
from core import vault


SYSTEM_EXTRACT = """Sei l'archivista di un vault Obsidian autobiografico. Ricevi trascrizioni di conversazioni e le trasformi in operazioni di scrittura sul vault.

IL TUO UNICO OUTPUT è un JSON valido, niente altro — niente spiegazioni, niente testo prima o dopo.

STRUTTURA OUTPUT:
{"operazioni": [ {"action": "merge", "folder": "...", "title": "...", "content": "...", "tags": [...]} ]}

CARTELLE — usa quelle esistenti o creane di nuove se nessuna è adatta:
- Persone/ → persone menzionate per nome
- Lavoro/ → lavoro, aziende, ruoli
- Esperienze/ → eventi, ricordi, periodi vissuti
- Idee/ → progetti, piani, idee concrete
- Concetti/ → concetti tecnici o culturali
- Opinioni/ → punti di vista personali, posizioni, interpretazioni
- (puoi usare altre cartelle se il contenuto non rientra in nessuna di queste)

FORMATO DEL CONTENUTO:
- Bullet point atomici, uno per riga, in prima persona
- "lavoro a", "ho studiato", "penso che", "secondo me", "ho conosciuto"
- [[wikilinks]] SOLO per nomi propri reali: persone, aziende, luoghi geografici
- MAI wikilinks per concetti astratti, idee, titoli di altre note

TITOLI:
- Max 4 parole, descrittivo del soggetto — MAI interpretativo
- Corretto: "Luca Bianchi", "Datapizza", "Bachata", "Bias in NLP"
- Sbagliato: "L'impatto dei mentori", "Riflessioni sul lavoro", "Come ho capito X"

QUANDO RESTITUIRE {"operazioni": []}:
- La risposta è negativa, evasiva, o un rifiuto ("no", "non lo so", "non ricordo")
- Non emergono informazioni nuove e concrete
- La risposta è già completamente coperta dal vault esistente

REGOLE ASSOLUTE:
- Solo ciò che è stato detto esplicitamente — zero inferenze, zero interpretazioni
- Se non è stato detto chiaramente, non scriverlo
- Non inventare dettagli per completare una nota"""


def extract(transcript: str) -> list[dict]:
    """
    Analizza una trascrizione e ritorna una lista di operazioni vault da eseguire.
    Ogni operazione: {"action": "merge", "folder": str, "title": str, "content": str, "tags": [str]}
    """
    context = vault.context_summary()

    prompt = f"""Contesto vault esistente:
{context}

Trascrizione da elaborare:
{transcript}

Restituisci il JSON delle operazioni."""

    raw = think(SYSTEM_EXTRACT, prompt)

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

"""
Tool del vault eseguiti in locale (laptop).
Gemma li "chiama" scrivendo JSON — Python li esegue e restituisce il risultato.
"""

import os
import re
from core import vault
from config import VAULT_PATH, VAULT_FOLDERS


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "vault_read",
        "description": "Leggi una nota specifica dal vault.",
        "args": {"folder": "cartella (Journal/Persone/Lavoro/Esperienze/Idee/Concetti)", "title": "titolo nota"},
        "example": '{"tool": "vault_read", "args": {"folder": "Persone", "title": "Lucrezia"}}'
    },
    {
        "name": "vault_search",
        "description": "Cerca nel vault per keyword. Ritorna le note rilevanti.",
        "args": {"query": "parola o frase da cercare"},
        "example": '{"tool": "vault_search", "args": {"query": "Datapizza"}}'
    },
    {
        "name": "vault_get_entity",
        "description": "Recupera tutto ciò che si sa su una persona o concetto specifico.",
        "args": {"name": "nome della persona o concetto"},
        "example": '{"tool": "vault_get_entity", "args": {"name": "Lucrezia"}}'
    },
    {
        "name": "vault_get_gaps",
        "description": "Trova aree del vault poco sviluppate: argomenti menzionati ma non approfonditi.",
        "args": {},
        "example": '{"tool": "vault_get_gaps", "args": {}}'
    },
    {
        "name": "ask_user",
        "description": "Fai UNA domanda specifica a Manuel. Usalo SOLO quando hai abbastanza contesto.",
        "args": {"question": "la domanda da fare"},
        "example": '{"tool": "ask_user", "args": {"question": "Da quanto tempo conosci Lucrezia?"}}'
    },
]

TOOL_NAMES = {t["name"] for t in TOOL_DEFINITIONS}


def tool_prompt_block() -> str:
    """Genera il blocco di testo con i tool da includere nel system prompt."""
    lines = ["TOOL DISPONIBILI (usa SOLO il JSON, nient'altro):"]
    for t in TOOL_DEFINITIONS:
        lines.append(f"\n- {t['name']}: {t['description']}")
        lines.append(f"  Esempio: {t['example']}")
    lines.append("\nSe vuoi usare un tool, scrivi SOLO il JSON. Nessun testo prima o dopo.")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Esecuzione tool
# ------------------------------------------------------------------

def execute(tool_name: str, args: dict) -> str:
    if tool_name == "vault_read":
        return _vault_read(args.get("folder", ""), args.get("title", ""))
    elif tool_name == "vault_search":
        return _vault_search(args.get("query", ""))
    elif tool_name == "vault_get_entity":
        return _vault_get_entity(args.get("name", ""))
    elif tool_name == "vault_get_gaps":
        return _vault_get_gaps()
    elif tool_name == "ask_user":
        # Speciale: non eseguito qui, gestito dall'agent loop
        return args.get("question", "")
    else:
        return f"Tool sconosciuto: {tool_name}"


def _vault_read(folder: str, title: str) -> str:
    content = vault.read(folder, title)
    if not content:
        return f"Nota '{folder}/{title}' non trovata nel vault."
    return f"[{folder}/{title}]\n{content}"


def _vault_search(query: str) -> str:
    query_lower = query.lower()
    results = []
    for folder in VAULT_FOLDERS:
        folder_path = os.path.join(VAULT_PATH, folder)
        if not os.path.exists(folder_path):
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(folder_path, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            if query_lower in content.lower() or query_lower in fname.lower():
                # Estrai body senza frontmatter
                body = re.sub(r"^---.*?---\n", "", content, flags=re.DOTALL).strip()
                preview = body[:300].replace("\n", " ")
                results.append(f"[{folder}/{fname[:-3]}]: {preview}")

    if not results:
        return f"Nessuna nota trovata per '{query}'."
    return "\n\n".join(results[:5])  # max 5 risultati


def _vault_get_entity(name: str) -> str:
    name_lower = name.lower()
    results = []
    for folder in VAULT_FOLDERS:
        folder_path = os.path.join(VAULT_PATH, folder)
        if not os.path.exists(folder_path):
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".md"):
                continue
            if name_lower in fname.lower():
                fpath = os.path.join(folder_path, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                body = re.sub(r"^---.*?---\n", "", content, flags=re.DOTALL).strip()
                results.append(f"[{folder}/{fname[:-3]}]\n{body}")

    if not results:
        # Cerca anche nelle note che menzionano il nome
        mention_results = _vault_search(name)
        if "Nessuna nota trovata" not in mention_results:
            return f"Nessuna nota dedicata a '{name}', ma viene menzionato in:\n{mention_results}"
        return f"'{name}' non è presente nel vault."
    return "\n\n---\n\n".join(results)


def _vault_get_gaps() -> str:
    """Trova entità nei wikilinks che non hanno una nota dedicata."""
    all_links = set()
    all_notes = set()

    for folder in VAULT_FOLDERS:
        folder_path = os.path.join(VAULT_PATH, folder)
        if not os.path.exists(folder_path):
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".md"):
                continue
            all_notes.add(fname[:-3].lower())
            fpath = os.path.join(folder_path, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            all_links.update(l.lower() for l in links)

    gaps = all_links - all_notes
    if not gaps:
        return "Nessun gap trovato: tutte le entità linkate hanno una nota dedicata."

    return "Entità menzionate ma senza nota dedicata:\n" + "\n".join(f"- {g}" for g in sorted(gaps))

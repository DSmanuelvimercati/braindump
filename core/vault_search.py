"""
Funzioni di ricerca e analisi del vault, condivise tra i mode.
"""

import os
import re
from difflib import SequenceMatcher
from core import vault
from config import VAULT_PATH, VAULT_FOLDERS


def search(query: str, max_results: int = 5) -> str:
    """Cerca nel vault per keyword. Ritorna preview delle note trovate."""
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
                body = re.sub(r"^---.*?---\n", "", content, flags=re.DOTALL).strip()
                preview = body[:300].replace("\n", " ")
                results.append(f"[{folder}/{fname[:-3]}]: {preview}")
    if not results:
        return f"Nessuna nota trovata per '{query}'."
    return "\n\n".join(results[:max_results])


def get_entity(name: str) -> str:
    """Recupera tutto ciò che si sa su un'entità (nota dedicata + menzioni)."""
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
        mention_results = search(name)
        if "Nessuna nota trovata" not in mention_results:
            return f"Nessuna nota dedicata a '{name}', ma viene menzionato in:\n{mention_results}"
        return f"'{name}' non è presente nel vault."
    return "\n\n---\n\n".join(results)


def get_gaps() -> str:
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


def find_duplicates(threshold: float = 0.75) -> list[dict]:
    """
    Trova coppie di note probabilmente duplicate (fuzzy match su titolo + contenuto).
    Ritorna lista di {"folder_a", "title_a", "folder_b", "title_b", "similarity"}.
    """
    notes = vault.list_all()
    dupes = []
    for i, a in enumerate(notes):
        for b in notes[i + 1:]:
            # Titoli simili?
            title_sim = SequenceMatcher(None, a["title"].lower(), b["title"].lower()).ratio()
            if title_sim < 0.5:
                continue
            # Contenuto simile?
            body_a = re.sub(r"^---.*?---\n", "", a["content"], flags=re.DOTALL).strip()
            body_b = re.sub(r"^---.*?---\n", "", b["content"], flags=re.DOTALL).strip()
            content_sim = SequenceMatcher(None, body_a[:500], body_b[:500]).ratio()
            combined = title_sim * 0.4 + content_sim * 0.6
            if combined >= threshold:
                dupes.append({
                    "folder_a": a["folder"], "title_a": a["title"],
                    "folder_b": b["folder"], "title_b": b["title"],
                    "similarity": round(combined, 2),
                })
    return dupes


def audit() -> str:
    """Genera un report di audit del vault: statistiche, gap, duplicati, note senza tag."""
    notes = vault.list_all()
    # Stats per cartella
    folder_counts = {}
    tagless = []
    small_notes = []
    for n in notes:
        folder_counts[n["folder"]] = folder_counts.get(n["folder"], 0) + 1
        # Check tag
        if "tags: []" in n["content"] or "tags: ['']" in n["content"]:
            tagless.append(f"{n['folder']}/{n['title']}")
        # Check note piccole (<30 char di body)
        body = re.sub(r"^---.*?---\n", "", n["content"], flags=re.DOTALL).strip()
        if len(body) < 30:
            small_notes.append(f"{n['folder']}/{n['title']}")

    lines = [f"VAULT AUDIT — {len(notes)} note totali"]
    lines.append("\nNote per cartella:")
    for f, c in sorted(folder_counts.items()):
        lines.append(f"  {f}: {c}")

    # Gap
    gaps_str = get_gaps()
    if "Nessun gap" not in gaps_str:
        lines.append(f"\n{gaps_str}")

    # Duplicati
    dupes = find_duplicates()
    if dupes:
        lines.append(f"\nPOSSIBILI DUPLICATI ({len(dupes)}):")
        for d in dupes[:10]:
            lines.append(f"  {d['folder_a']}/{d['title_a']} ~ {d['folder_b']}/{d['title_b']} ({d['similarity']})")

    # Note senza tag
    if tagless:
        lines.append(f"\nNOTE SENZA TAG ({len(tagless)}):")
        for t in tagless[:10]:
            lines.append(f"  {t}")

    # Note troppo piccole
    if small_notes:
        lines.append(f"\nNOTE TROPPO CORTE ({len(small_notes)}):")
        for s in small_notes[:10]:
            lines.append(f"  {s}")

    return "\n".join(lines)

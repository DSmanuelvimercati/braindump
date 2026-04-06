"""
Obsidian vault: lettura e scrittura di note markdown con frontmatter YAML e wikilinks.
"""

import os
import re
import json
from datetime import date
from config import VAULT_PATH, VAULT_FOLDERS


def init():
    os.makedirs(VAULT_PATH, exist_ok=True)
    for f in VAULT_FOLDERS:
        os.makedirs(os.path.join(VAULT_PATH, f), exist_ok=True)
    obsidian_dir = os.path.join(VAULT_PATH, ".obsidian")
    os.makedirs(obsidian_dir, exist_ok=True)
    app_json = os.path.join(obsidian_dir, "app.json")
    if not os.path.exists(app_json):
        with open(app_json, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _safe_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\n]', '', name).strip()


def path_for(folder: str, title: str) -> str:
    return os.path.join(VAULT_PATH, folder, f"{_safe_name(title)}.md")


def daily_journal_path() -> str:
    return path_for("Journal", date.today().isoformat())


def read(folder: str, title: str) -> str:
    p = path_for(folder, title)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def write(folder: str, title: str, content: str, tags: list[str] = None):
    """Crea o sovrascrive una nota."""
    tags = tags or []
    today = date.today().isoformat()
    frontmatter = (
        f"---\n"
        f"title: \"{_safe_name(title)}\"\n"
        f"tags: [{', '.join(repr(t) for t in tags)}]\n"
        f"date: {today}\n"
        f"updated: {today}\n"
        f"---\n\n"
    )
    p = path_for(folder, title)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(frontmatter + content)


def append_to_daily(text: str):
    """Aggiunge testo al journal del giorno, creandolo se necessario."""
    p = daily_journal_path()
    today = date.today().isoformat()
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(
                f"---\ntitle: \"Journal {today}\"\ntags: ['journal']\ndate: {today}\n---\n\n"
            )
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n\n" + text)


def merge(folder: str, title: str, new_content: str, tags: list[str] = None):
    """
    Aggiorna una nota esistente aggiungendo contenuto, oppure la crea.
    Se esiste già, appende sotto un separatore.
    """
    existing = read(folder, title)
    if existing:
        today = date.today().isoformat()
        # Aggiorna il campo 'updated' nel frontmatter
        updated = re.sub(r"updated: \d{4}-\d{2}-\d{2}", f"updated: {today}", existing)
        with open(path_for(folder, title), "w", encoding="utf-8") as f:
            f.write(updated + f"\n\n---\n\n{new_content}")
    else:
        write(folder, title, new_content, tags)


def context_summary(max_chars: int = 3000) -> str:
    """Restituisce un riassunto del vault esistente per dare contesto al modello."""
    lines = []
    for folder in VAULT_FOLDERS:
        folder_path = os.path.join(VAULT_PATH, folder)
        if not os.path.exists(folder_path):
            continue
        for fname in sorted(os.listdir(folder_path)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(folder_path, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            # Strip frontmatter per brevità
            body = re.sub(r"^---.*?---\n", "", content, flags=re.DOTALL).strip()
            preview = body[:300].replace("\n", " ")
            lines.append(f"[{folder}/{fname[:-3]}]: {preview}")
            if sum(len(l) for l in lines) > max_chars:
                break

    return "\n".join(lines) if lines else "Vault vuoto."

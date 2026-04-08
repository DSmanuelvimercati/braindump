"""
Backup del vault all'avvio del server.
Mantiene le ultime N copie nella cartella vault_backups/.
"""

import shutil
from pathlib import Path
from datetime import datetime

from config import VAULT_PATH

BACKUP_DIR = Path(VAULT_PATH).parent / "vault_backups"
MAX_BACKUPS = 3


def backup_vault() -> str:
    """
    Copia il vault in vault_backups/vault_YYYYMMDD_HHMMSS.
    Elimina le copie più vecchie oltre MAX_BACKUPS.
    Restituisce il path del backup creato.
    """
    vault_path = Path(VAULT_PATH)
    if not vault_path.exists():
        return ""

    BACKUP_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"vault_{timestamp}"
    shutil.copytree(vault_path, dest)

    # Tieni solo le ultime MAX_BACKUPS copie
    backups = sorted(BACKUP_DIR.iterdir(), key=lambda p: p.name)
    for old in backups[:-MAX_BACKUPS]:
        shutil.rmtree(old)

    return str(dest)

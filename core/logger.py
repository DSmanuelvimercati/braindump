"""
Session logger: scrive il pensiero grezzo di Gemma su file markdown.
Un file per sessione in logs/.
"""

import os
from datetime import datetime


class SessionLogger:
    def __init__(self, mode: str):
        os.makedirs("logs", exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = os.path.join("logs", f"{ts}_{mode}.md")
        self._f = open(self.path, "w", encoding="utf-8")
        self._write(f"# Session log — {mode} — {ts}\n\n")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _write(self, text: str):
        self._f.write(text)
        self._f.flush()

    def log_token(self, token: str, end: str = ""):
        """Chiamato per ogni token in streaming."""
        self._f.write(token)
        if end:
            self._f.write(end)
        self._f.flush()

    def log(self, text: str):
        """Log di una riga strutturata."""
        self._write(text + "\n")

    def section(self, title: str):
        self._write(f"\n## {title}\n\n")

    def close(self):
        self._write("\n\n---\n*fine sessione*\n")
        self._f.close()

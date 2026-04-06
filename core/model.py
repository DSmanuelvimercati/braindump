"""
Wrapper Ollama: text → text via API locale.
Il modello (gemma4 GGUF quantizzato) gira su CPU tramite Ollama.
"""

import requests
from config import OLLAMA_BASE, OLLAMA_MODEL


def think(system: str, user: str) -> str:
    """Chiamata chat a Ollama. Ritorna la risposta come stringa."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    try:
        r = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Ollama non raggiungibile. Avvia Ollama prima di eseguire il programma.")
    except Exception as e:
        raise RuntimeError(f"Errore Ollama: {e}")

"""
Wrapper Ollama: text → text via API locale.
Supporta sia modalità bloccante che streaming token-per-token.
"""

import json
import time
import requests
from config import OLLAMA_BASE, OLLAMA_MODEL, OLLAMA_NUM_CTX

_MAX_RETRIES = 3


def think(system: str, user: str, on_token=None) -> str:
    """
    Chiamata chat a Ollama con retry automatico su ConnectionError.

    Args:
        system:   system prompt
        user:     messaggio utente
        on_token: callback(token: str) chiamato per ogni token in streaming.
                  Se None, modalità bloccante classica.

    Returns:
        risposta completa come stringa
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": on_token is not None,
        "options": {"num_ctx": OLLAMA_NUM_CTX},
    }

    for attempt in range(_MAX_RETRIES):
        try:
            if on_token is None:
                # Modalità bloccante
                r = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
                r.raise_for_status()
                data = r.json()
                _log_tokens(data)
                return data["message"]["content"].strip()
            else:
                # Modalità streaming
                return _stream(payload, on_token)

        except requests.exceptions.ConnectionError:
            if attempt < _MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  [ollama] connessione fallita, retry in {wait}s...", flush=True)
                time.sleep(wait)
            else:
                raise RuntimeError(f"Ollama non raggiungibile dopo {_MAX_RETRIES} tentativi.")
        except Exception as e:
            raise RuntimeError(f"Errore Ollama: {e}")

    raise RuntimeError("Ollama non raggiungibile.")  # unreachable, soddisfa type checker


def _log_tokens(data: dict):
    prompt_tokens = data.get("prompt_eval_count", 0)
    gen_tokens = data.get("eval_count", 0)
    pct = round(prompt_tokens / OLLAMA_NUM_CTX * 100) if OLLAMA_NUM_CTX else 0
    warn = " ⚠ VICINO AL LIMITE" if pct > 80 else ""
    print(f"  [tokens] prompt={prompt_tokens}/{OLLAMA_NUM_CTX} ({pct}%) gen={gen_tokens}{warn}", flush=True)


def _stream(payload: dict, on_token) -> str:
    """Streaming SSE da Ollama: chiama on_token per ogni chunk, ritorna il testo completo."""
    full = []
    with requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json=payload,
        stream=True,
        timeout=120
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            token = chunk.get("message", {}).get("content", "")
            if token:
                full.append(token)
                on_token(token)
            if chunk.get("done"):
                _log_tokens(chunk)
                break
    return "".join(full).strip()

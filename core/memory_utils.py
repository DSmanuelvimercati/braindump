"""
Utility per gestione memory datapizza-ai con budget dinamico in token.
Stima token come len(text) / 4 (approssimazione per modelli multilingue).
"""

from config import OLLAMA_NUM_CTX

# Riserva per la risposta del modello
_RESPONSE_RESERVE = 512


def estimate_tokens(text: str) -> int:
    """Stima grezza del numero di token (chars / 4)."""
    return len(text) // 4


def trim_memory(memory, system_prompt: str, max_turns: int = 20):
    """
    Rimuove i turni più vecchi dalla memory finché il totale stimato
    (system_prompt + memory) rientra nel budget di contesto.

    Args:
        memory: datapizza Memory object (supporta len, del, iterazione)
        system_prompt: il system prompt corrente (per stimarne i token)
        max_turns: limite massimo di turni indipendente dal budget token
    """
    budget = OLLAMA_NUM_CTX - _RESPONSE_RESERVE
    system_tokens = estimate_tokens(system_prompt)

    # Prima: rispetta il limite di turni
    while len(memory) > max_turns:
        del memory[0]

    # Poi: taglia finché non stiamo nel budget token
    while len(memory) > 1:
        memory_text = _memory_to_text(memory)
        total = system_tokens + estimate_tokens(memory_text)
        if total <= budget:
            break
        del memory[0]


def _memory_to_text(memory) -> str:
    """Serializza la memory in testo per stimare i token."""
    parts = []
    for turn in memory:
        for block in turn:
            text = getattr(block, 'content', None) or getattr(block, 'result', '') or ''
            if text:
                parts.append(text[:500])  # tronca blocchi giganti per la stima
    return "\n".join(parts)

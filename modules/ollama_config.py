"""
Configurazione per l'integrazione con Ollama.
"""

# URL dell'endpoint Ollama
OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_API_BASE}/api/generate"
OLLAMA_CHAT_ENDPOINT = f"{OLLAMA_API_BASE}/api/chat"

# Nome del modello da utilizzare
# Puoi modificare questo valore con il nome di qualsiasi modello disponibile su Ollama
# Esempi: llama3, mistral, gemma, mixtral, phi, etc.
DEFAULT_MODEL = "gemma3:1b"

# Parametri di generazione predefiniti
DEFAULT_PARAMS = {
    "temperature": 0.7,
    "top_p": 0.95,
    "max_tokens": 1024
}

# Funzione per ottenere un elenco dei modelli disponibili
def get_available_models():
    """
    Restituisce un elenco dei modelli disponibili su Ollama.
    Richiede che il servizio Ollama sia attivo.
    """
    import requests
    try:
        response = requests.get(f"{OLLAMA_API_BASE}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [model.get("name") for model in models]
        return []
    except Exception:
        return [] 
import os

# Modello Ollama (gemma4 quantizzato GGUF, ottimizzato CPU)
OLLAMA_BASE = "http://localhost:11434"  # <- sostituisci con IP del PC 3060, es: "http://192.168.1.50:11434"
OLLAMA_MODEL = "gemma4:e2b"            # <- sul PC 3060 usa "gemma4:e4b"

# Whisper per STT (tiny = leggero su CPU, base = migliore accuratezza)
WHISPER_MODEL = "base"   # tiny | base | small
WHISPER_LANGUAGE = "it"

# Vault Obsidian
VAULT_PATH = os.path.join(os.path.dirname(__file__), "vault")

# Audio
AUDIO_SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.008    # ampiezza RMS minima per rilevare voce
SILENCE_TIMEOUT_SEC = 2.0    # secondi di silenzio per terminare utterance

# Cartelle vault
VAULT_FOLDERS = ["Journal", "Persone", "Lavoro", "Esperienze", "Idee", "Concetti"]

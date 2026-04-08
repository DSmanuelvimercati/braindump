import os

# Modello Ollama (gemma4 quantizzato GGUF, ottimizzato CPU)
OLLAMA_BASE = "http://100.107.20.71:11434"  # dellg15 via Tailscale
OLLAMA_MODEL = "gemma4:e4b"
OLLAMA_NUM_CTX = 4096   # token di contesto — 4k per evitare crash sulla 3060 12GB

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
VAULT_FOLDERS = ["Journal", "Persone", "Lavoro", "Esperienze", "Idee", "Concetti", "Opinioni"]

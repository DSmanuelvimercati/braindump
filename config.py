"""
Configurazione dell'applicazione Braindump.
"""

import os
import datetime

# Prompt di sistema
SYSTEM_PROMPT = """
Sei un agente intervistatore che deve generare domande concise per l'utente.

Il tuo compito è stimolare l'utente con domande pertinenti sul topic scelto, che siano:
1. Personali (rivolte alle esperienze/opinioni/preferenze dell'utente)
2. Non ripetitive
3. Interessanti e stimolanti
4. Facili da rispondere

NON devi MAI:
- Generare risposte per conto dell'utente
- Creare riassunti o sommari
- Dare consigli non richiesti
- Cambiare argomento senza che l'utente lo chieda
- Fare domande quiz o testare l'utente

Attendi pazientemente le risposte dell'utente e rispondi solo con domande pertinenti al topic.
"""

# Directory per i dati
BRAINDUMP_DIR = "braindump_data"
INFORMATION_DIR = os.path.join(BRAINDUMP_DIR, "informazioni")
CONCEPTS_DIR = os.path.join(BRAINDUMP_DIR, "concetti")
GUIDELINES_DIR = "guidelines"  # Directory per le linee guida
PERMANENT_GUIDELINES_FILE = os.path.join(GUIDELINES_DIR, "interviewer_guidelines.md")

# Cartella temporanea per la sessione
TEMP_FOLDER = "temp_session"

# Configurazione delle domande
MAX_QUESTIONS_PER_TOPIC = 10
TIME_LIMIT_SECONDS = 600  # 10 minuti

# Estensioni dei file supportate
SUPPORTED_EXTENSIONS = [".md", ".txt"]

# Chiavi di configurazione del LLM
LLM_CONFIG = {
    "temperature": 0.7,
    "max_tokens": 1024,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "timeout": 60  # secondi
}

# Topic predefiniti - utilizzati solo se non ci sono file concetti
DEFAULT_TOPICS = [
    "lavoro",
    "hobby",
    "famiglia",
    "relazioni",
    "persone",
    "esperienze",
    "convinzioni",
    "viaggi",
    "abitudini",
    "idee",
    "progetti",
    "formazione"
]

def create_temp_folder():
    """Crea una cartella temporanea per la sessione corrente."""
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    
    # Crea sottocartella per le informazioni e concetti
    temp_info_dir = os.path.join(TEMP_FOLDER, "informazioni")
    
    if not os.path.exists(temp_info_dir):
        os.makedirs(temp_info_dir)


def load_braindump_data():
    """
    Legge tutti i file Markdown presenti nella cartella BRAINDUMP_DIR (in tutte le sue sottocartelle).
    Restituisce un dizionario in cui le chiavi sono i nomi dei file e i valori il contenuto.
    """
    data = {}
    if not os.path.exists(BRAINDUMP_DIR):
        os.makedirs(BRAINDUMP_DIR)
    for root, _, files in os.walk(BRAINDUMP_DIR):
        for filename in files:
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                with open(filepath, "r", encoding="utf-8") as file:
                    data[filename] = file.read()
    return data

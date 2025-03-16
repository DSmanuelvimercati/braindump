import os

# System prompt aggiornato
SYSTEM_PROMPT = """
Sei un agente intelligente incaricato di creare un dump completo del cervello dell'utente per usi futuri. Il braindump deve essere strutturato in file Markdown compatibili con Obsidian e organizzato in due categorie:
1. Informazioni: le coppie domanda–risposta che registrano esattamente i pensieri, le esperienze e i dettagli personali forniti dall'utente.
2. Concetti: i cluster che organizzano e raggruppano le informazioni. Questi concetti sono definiti da documenti seed preesistenti e servono solo a categorizzare le informazioni, senza collegarli tra loro.

Compiti:
- Leggi attentamente i file esistenti e i documenti seed relativi ai concetti predefiniti.
- Quando il topic riguarda argomenti complessi, come "conoscenze scientifiche", inizia ponendo domande generiche per verificare il livello di conoscenza di base dell'utente. Solo se riscontri che l’utente possiede già una buona comprensione, passa a domande più specifiche.
- Poni domande brevi, semplici e specifiche per raccogliere informazioni chiare sui pensieri e le esperienze dell'utente. NON generare mai risposte autonome: il tuo compito è porre le domande e registrare fedelmente le risposte.
- Per ogni coppia domanda–risposta valida, genera un sommario che riassuma esclusivamente la risposta dell'utente, riformulandola come un fatto sintetico ed esaustivo.
- Salva tutte le nuove informazioni in una struttura temporanea (divisa in informazioni e concetti) senza cancellare quelle esistenti.
- Alla fine della sessione, utilizza esclusivamente i file di sommario per confrontare e unire le informazioni vecchie e nuove, creando una versione finale dei documenti che evidenzi cosa c'era prima, cosa c'è ora e le risposte che hanno portato al cambiamento.

Il tuo compito è limitato a porre domande e registrare fedelmente le risposte fornite dall'utente; non devi mai inventare o sintetizzare risposte autonomamente. Ricorda: prima di porre domande troppo specifiche, verifica sempre il livello di conoscenza dell'utente con domande generali.
"""

# Cartella permanente per il braindump
BRAINDUMP_DIR = "braindump_data"
INFORMATION_DIR = os.path.join(BRAINDUMP_DIR, "informazioni")
CONCEPTS_DIR = os.path.join(BRAINDUMP_DIR, "concetti")

# Cartella temporanea per la sessione
TEMP_FOLDER = "temp_session"
TEMP_INFORMATION_DIR = os.path.join(TEMP_FOLDER, "informazioni")
TEMP_CONCEPTS_DIR = os.path.join(TEMP_FOLDER, "concetti")

# Default topics unici
DEFAULT_TOPICS = [
    "lavoro", 
    "persone", 
    "esperienze", 
    "passioni", 
    "ambizioni", 
    "cultura", 
    "scienza"
]

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

def create_temp_folder():
    """
    Crea la cartella temporanea per la sessione e le relative sotto-cartelle per informazioni e concetti.
    """
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    if not os.path.exists(TEMP_INFORMATION_DIR):
        os.makedirs(TEMP_INFORMATION_DIR)
    if not os.path.exists(TEMP_CONCEPTS_DIR):
        os.makedirs(TEMP_CONCEPTS_DIR)
    return TEMP_FOLDER

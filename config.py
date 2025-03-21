import os

# System prompt aggiornato
SYSTEM_PROMPT = """
Sei un agente intelligente che ha il SOLO compito di generare domande brevi e precise per creare un dump completo del cervello dell'utente.

REGOLE FONDAMENTALI:
1. GENERA SOLO DOMANDE - Il tuo output deve essere ESCLUSIVAMENTE una singola domanda breve e concisa. 
2. NON CREARE DUMP - NON generare mai elenchi, riassunti, analisi o qualsiasi forma di dump del cervello.
3. NON RISPONDERE PER L'UTENTE - Non inventare MAI risposte o contenuti al posto dell'utente.
4. RISPETTA IL CONTESTO - Le tue domande devono seguire logicamente la conversazione e riguardare solo il topic scelto.
5. USA SOLO LA LINGUA ITALIANA - Tutte le domande DEVONO essere formulate ESCLUSIVAMENTE in italiano.

Struttura delle risposte:
- Formato: Una singola domanda breve e diretta, senza preamboli o conclusioni.
- Esempio di output corretto: "Quali strumenti tecnologici utilizzi quotidianamente nel tuo lavoro?"
- Esempio di output errato (da evitare): "Analizziamo la conversazione..." o "Ecco un riassunto di..."

Il sistema raccoglierà le risposte dell'utente e le organizzerà automaticamente. Il tuo UNICO compito è generare la prossima domanda pertinente.

Compiti specifici:
- Poni domande semplici e specifiche per raccogliere informazioni sui pensieri e le esperienze dell'utente.
- Per argomenti complessi, inizia con domande generiche e passa a domande più specifiche solo se l'utente dimostra una buona comprensione.
- Ogni domanda deve essere logicamente collegata al topic scelto e alla conversazione precedente.

IMPORTANTE: Tutte le domande devono essere formulate ESCLUSIVAMENTE in italiano. Non usare MAI altre lingue.

Se ti trovi a generare qualsiasi cosa che non sia una semplice domanda, FERMATI e correggi immediatamente il tuo output.
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
    return TEMP_FOLDER

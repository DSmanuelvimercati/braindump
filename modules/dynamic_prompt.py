import os
from config import SYSTEM_PROMPT, CONCEPTS_DIR, INFORMATION_DIR, TEMP_FOLDER, load_braindump_data
from modules.llm import generate_text

def get_topic_suggestions():
    """
    Restituisce solo i nomi dei file dalla cartella 'concetti'.
    Non include i file dalla cartella 'informazioni'.
    """
    # Leggi solo dalla cartella concetti
    topics = []
    if os.path.exists(CONCEPTS_DIR):
        for filename in os.listdir(CONCEPTS_DIR):
            if filename.endswith(".md"):
                topic_name = filename.replace(".md", "")
                topics.append(topic_name)
    
    return topics

def get_files_in_directory(directory):
    """Ritorna la lista dei file .md presenti nella directory."""
    files = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.endswith(".md"):
                files.append(filename)
    return files

def chunks(lst, n):
    """Divide la lista lst in sottoliste di lunghezza al massimo n."""
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def select_relevant_files(directory, chosen_topic):
    """
    Raggruppa in batch di 10 i file della directory e usa l'LLM per selezionare quelli rilevanti
    per il topic scelto. Ritorna un insieme dei nomi dei file ritenuti pertinenti.
    """
    all_files = get_files_in_directory(directory)
    relevant_files = set()
    for batch in chunks(all_files, 10):
        # Costruisci un prompt che elenca i file del batch
        batch_str = ", ".join(batch)
        prompt = (f"Considera la seguente lista di file: {batch_str}. "
                  f"Per il topic '{chosen_topic}', indica quali file sono rilevanti. "
                  "Rispondi con i nomi separati da virgola. Se nessuno è rilevante, rispondi 'Nessuno'.")
        response = generate_text(prompt).strip()
        # Se la risposta contiene 'nessuno', passa al batch successivo
        if "NESSUNO" in response.upper():
            continue
        # Altrimenti, estrai i nomi e aggiungili all'insieme
        for file_name in response.split(","):
            file_name = file_name.strip()
            if file_name and file_name in batch:
                relevant_files.add(file_name)
    return list(relevant_files)

def read_selected_context(directory, chosen_topic):
    """
    Usa select_relevant_files per determinare quali file includere e restituisce il loro contenuto concatenato.
    """
    relevant_files = select_relevant_files(directory, chosen_topic)
    context = ""
    for filename in relevant_files:
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            context += f"\n---\n{f.read()}\n"
    return context

def build_dynamic_prompt(chosen_topic=None, conversation_history="", relevant_files=None):
    """
    Costruisce un prompt dinamico per l'LLM, adattandolo in base a:
    - Se stiamo scegliendo il topic (chosen_topic è None) o generando domande
    - La cronologia della conversazione esistente
    - I file di contesto rilevanti per il topic attuale

    Args:
        chosen_topic (str, optional): Topic scelto per l'intervista. Se None, è richiesta la scelta del topic.
        conversation_history (str, optional): Cronologia della conversazione corrente.
        relevant_files (list, optional): Lista dei file MD rilevanti per fornire contesto.

    Returns:
        str: Prompt dinamico per l'LLM
    """
    # Base del prompt comune
    base_prompt = """Sei un agente intelligente che ha il SOLO compito di generare domande brevi e precise per creare un dump completo del cervello dell'utente.
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
Il sistema raccoglierà le risposte dell'utente e le organizzerà automaticamente. Il tuo UNICO compito è generare la prossima domanda pertinente."""

    # Se siamo nella fase di scelta del topic
    if chosen_topic is None:
        suggestions = get_topic_suggestions()
        suggestions_text = "\n".join([f"{i+1}. {topic}" for i, topic in enumerate(suggestions)])
        prompt = f"""{base_prompt}
Compiti specifici:
- Poni domande semplici e specifiche per raccogliere informazioni sui pensieri e le esperienze dell'utente.
- Per argomenti complessi, inizia con domande generiche e passa a domande più specifiche solo se l'utente dimostra una buona comprensione.
- Ogni domanda deve essere logicamente collegata al topic scelto e alla conversazione precedente.
IMPORTANTE: Tutte le domande devono essere formulate ESCLUSIVAMENTE in italiano. Non usare MAI altre lingue.
Se ti trovi a generare qualsiasi cosa che non sia una semplice domanda, FERMATI e correggi immediatamente il tuo output.
Topic suggeriti:
{suggestions_text}
Scegli un topic e indicamelo per iniziare l'intervista.
ATTENZIONE FINALE: Il tuo output deve essere esclusivamente una singola domanda breve e concisa. Non generare riassunti, analisi o spiegazioni aggiuntive."""
        return prompt
    
    # Prepara il contesto dai file rilevanti
    context_info = ""
    if relevant_files and len(relevant_files) > 0:
        context_info = "Informazioni dal contesto rilevante:\n"
        
        for file_path in relevant_files[:5]:  # Limitiamo a 5 file al massimo
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Estraiamo solo le prime 200 caratteri per non appesantire il prompt
                    short_content = content[:200] + "..." if len(content) > 200 else content
                    filename = os.path.basename(file_path)
                    context_info += f"\nDal file {filename}:\n{short_content}\n"
            except Exception as e:
                print(f"Errore nella lettura del file {file_path}: {e}")
        
        context_info += "\nUtilizza queste informazioni SOLO se pertinenti per generare una domanda rilevante e non ripetitiva.\n"
    
    # Quando abbiamo un topic scelto e stiamo generando domande
    prompt = f"""{base_prompt}
Topic attuale: {chosen_topic}

{context_info}

Storico della conversazione:
{conversation_history}

IMPORTANTE: Questa è un'intervista personale, NON un quiz di conoscenza. 
Le tue domande devono:
1. Concentrarsi sulle ESPERIENZE PERSONALI e OPINIONI dell'utente relative al topic "{chosen_topic}"
2. Essere formulate per estrarre informazioni dalla testa dell'utente (sia opinioni che fatti personali)
3. NON testare le conoscenze generali dell'utente come in un esame
4. Evitare domande accademiche o enciclopediche che richiedono conoscenze specialistiche
5. Usare un tono conversazionale, come se stessi facendo un'intervista amichevole

Esempi di buone domande:
- "Quale aspetto della {chosen_topic} ti appassiona di più?"
- "Come hai sviluppato il tuo interesse per {chosen_topic}?"
- "Quali esperienze personali hai avuto con {chosen_topic}?"
- "Qual è la tua opinione su {chosen_topic}?"

Esempi di domande da EVITARE:
- "Quali sono le principali caratteristiche del folklore latinoamericano?" (troppo accademica)
- "Elenca i cinque principali esponenti della letteratura romantica" (quiz di conoscenza)
- "In che anno è stata fondata l'Accademia della Crusca?" (test di nozioni)

Genera una NUOVA domanda singola, breve, diretta e PERSONALE che segua questi principi.

ATTENZIONE: La tua risposta deve contenere SOLO UNA DOMANDA, niente altro. Non aggiungere introduzioni o spiegazioni."""
    
    return prompt

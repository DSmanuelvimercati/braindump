import os
from config import SYSTEM_PROMPT, CONCEPTS_DIR, TEMP_CONCEPTS_DIR, INFORMATION_DIR, TEMP_INFORMATION_DIR, DEFAULT_TOPICS, load_braindump_data
from modules.llm import generate_text

def get_topic_suggestions():
    """
    Restituisce una lista di topic suggeriti basata sui file di braindump esistenti
    e sui DEFAULT_TOPICS. Se non sono presenti dati, ritorna DEFAULT_TOPICS.
    """
    data = load_braindump_data()
    if not data:
        return DEFAULT_TOPICS
    else:
        topics = [filename.replace(".md", "") for filename in data.keys()]
        for d in DEFAULT_TOPICS:
            if d not in topics:
                topics.append(d)
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

def build_dynamic_prompt(chosen_topic=None, conversation_history=""):
    """
    Costruisce un prompt dinamico combinando SYSTEM_PROMPT, il contesto selezionato dai file rilevanti
    (sia permanenti che temporanei) e la cronologia della conversazione.
    Se il topic non è stato scelto, invita l'utente a sceglierne uno elencando i suggerimenti.
    """
    base_prompt = SYSTEM_PROMPT + "\n\n"
    if chosen_topic:
        base_prompt += f"Topic selezionato: {chosen_topic}\n\n"
        base_prompt += "Genera una domanda breve, semplice e specifica per raccogliere informazioni chiare su questo argomento.\n"
    else:
        topics = get_topic_suggestions()
        base_prompt += "Topic suggeriti:\n"
        for idx, topic in enumerate(topics, 1):
            base_prompt += f"{idx}. {topic}\n"
        base_prompt += "\nScegli un topic e indicamelo per iniziare l'intervista.\n"
    
    # Leggi il contesto dai file permanenti (concetti e informazioni)
    perm_context_info = read_selected_context(INFORMATION_DIR, chosen_topic) if chosen_topic else ""
    perm_context_conc = read_selected_context(CONCEPTS_DIR, chosen_topic) if chosen_topic else ""
    temp_context_info = read_selected_context(TEMP_INFORMATION_DIR, chosen_topic) if chosen_topic else ""
    temp_context_conc = read_selected_context(TEMP_CONCEPTS_DIR, chosen_topic) if chosen_topic else ""
    
    if perm_context_info or perm_context_conc or temp_context_info or temp_context_conc:
        base_prompt += "\nContesto attuale (dai file rilevanti):\n"
        if perm_context_conc or temp_context_conc:
            base_prompt += "Concetti:\n" + perm_context_conc + temp_context_conc + "\n"
        if perm_context_info or temp_context_info:
            base_prompt += "Informazioni:\n" + perm_context_info + temp_context_info + "\n"
    
    if conversation_history:
        base_prompt += "\nCronologia della conversazione:\n" + conversation_history + "\n"
    
    return base_prompt

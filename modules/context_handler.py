import os
from modules.llm_handler import timed_generate_text, extract_json_from_response
from config import INFORMATION_DIR, CONCEPTS_DIR

def get_relevant_context(chosen_topic, conversation_history):
    """
    Seleziona solo i file MD pertinenti al topic e alla conversazione attuale.
    Analizza i file in blocchi di massimo 20 per evitare di sovraccaricare l'LLM.
    
    Args:
        chosen_topic (str): Il topic scelto per l'intervista
        conversation_history (str): La cronologia della conversazione
        
    Returns:
        list: Lista dei percorsi dei file rilevanti
    """
    # Raccogliamo tutti i potenziali file di contesto
    all_files = []
    for directory in [INFORMATION_DIR, CONCEPTS_DIR]:
        if os.path.exists(directory):
            all_files.extend([os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.md')])
    
    if not all_files:
        print("Nessun file di contesto disponibile.")
        return []
    
    # Cerchiamo esplicitamente il file di definizione del concetto per il topic scelto
    # Questo file deve essere sempre incluso nei risultati
    concept_file = None
    topic_lower = chosen_topic.lower()
    
    for f in all_files:
        basename = os.path.basename(f).replace('.md', '').lower()
        if basename == topic_lower and CONCEPTS_DIR in f:
            concept_file = f
            print(f"Trovato file di definizione del concetto per '{chosen_topic}': {os.path.basename(concept_file)}")
            break
    
    # Se abbiamo pochi file, possiamo analizzarli tutti insieme
    relevant_files = []
    if len(all_files) <= 20:
        relevant_files = evaluate_files_relevance(all_files, chosen_topic, conversation_history)
    else:
        # Altrimenti, li analizziamo a blocchi
        for i in range(0, len(all_files), 20):
            chunk = all_files[i:i+20]
            relevant_chunk = evaluate_files_relevance(chunk, chosen_topic, conversation_history)
            relevant_files.extend(relevant_chunk)
    
    # Assicuriamoci che il file di definizione del concetto sia incluso nei risultati
    if concept_file and concept_file not in relevant_files:
        relevant_files.append(concept_file)
        print(f"Aggiunto forzatamente il file di definizione del concetto '{os.path.basename(concept_file)}'")
    
    # Stampa debug dei file rilevanti selezionati
    if relevant_files:
        print(f"File di contesto rilevanti selezionati: {len(relevant_files)}")
        for f in relevant_files:
            print(f"  - {os.path.basename(f)}")
    else:
        print("Nessun file rilevante trovato per questo topic e conversazione.")
    
    return relevant_files

def evaluate_files_relevance(files, chosen_topic, conversation_history):
    """
    Valuta quali file sono pertinenti rispetto al topic e alla conversazione.
    Restituisce la lista dei percorsi dei file rilevanti.
    
    Args:
        files (list): Lista di percorsi di file da valutare
        chosen_topic (str): Il topic scelto per l'intervista
        conversation_history (str): La cronologia della conversazione
        
    Returns:
        list: Lista dei percorsi dei file rilevanti
    """
    # Estraiamo i nomi dei file (senza estensione) per l'analisi
    filenames = [os.path.basename(f).replace('.md', '') for f in files]
    
    # Prepariamo il contesto della conversazione (limitato per non appesantire troppo)
    conv_context = conversation_history
    if len(conv_context) > 500:
        # Prendiamo solo le ultime parti della conversazione se è troppo lunga
        conv_context = conv_context[-500:]
    
    prompt = f"""
    Dato il topic attuale "{chosen_topic}" e il seguente contesto di conversazione:
    {conv_context if conv_context else "Nuova conversazione"}
    
    Valuta quali dei seguenti documenti potrebbero contenere informazioni pertinenti:
    {', '.join(filenames)}
    
    Considera attentamente:
    1. Documenti il cui nome è semanticamente correlato al topic attuale
    2. Documenti che potrebbero contenere informazioni utili per le prossime domande
    3. Solo i documenti veramente rilevanti per questa specifica conversazione
    
    Restituisci un JSON array con i nomi dei file pertinenti (SOLO i nomi, senza estensione):
    ["nome1", "nome2", ...]
    
    Se nessun documento è rilevante, restituisci un array vuoto: []
    """
    
    result = timed_generate_text(prompt, "valutazione pertinenza file")
    
    # Estrazione del JSON dalla risposta
    relevant_names = extract_json_from_response(result)
    
    # Filtriamo la lista dei file per restituire solo quelli rilevanti
    return [f for f in files if os.path.basename(f).replace('.md', '') in relevant_names]

def choose_topic_manually(suggestions):
    """
    Sceglie automaticamente un topic tra quelli suggeriti quando l'utente non ne specifica uno.
    
    Args:
        suggestions (list): Lista di topic suggeriti
        
    Returns:
        str: Il topic scelto
    """
    suggestions_str = ", ".join(suggestions)
    prompt = f"L'utente non ha scelto un topic. Tra i seguenti topic: {suggestions_str}, scegli quello più pertinente."
    print("Chiamata LLM per scelta automatica del topic...")
    chosen = timed_generate_text(prompt, "choose topic").strip().lower()
    print(f"Topic scelto dall'LLM: {chosen}")
    
    for topic in suggestions:
        if topic.lower() in chosen:
            return topic
    return suggestions[0]

def change_topic(new_topic, suggestions, conversation_history):
    """
    Gestisce il cambio di topic durante l'intervista.
    
    Args:
        new_topic (str): Il nuovo topic richiesto
        suggestions (list): Lista di topic suggeriti
        conversation_history (str): La cronologia della conversazione
        
    Returns:
        tuple: (topic scelto, nuova domanda, messaggio)
    """
    # Check se il nuovo topic è nella lista dei suggeriti
    topic_match = None
    for topic in suggestions:
        if new_topic.lower() in topic.lower() or topic.lower() in new_topic.lower():
            topic_match = topic
            break
    
    # Se non troviamo un match esatto, chiediamo all'LLM di selezionare il più vicino
    if not topic_match:
        prompt = f"""
        L'utente vorrebbe cambiare topic a "{new_topic}".
        Tra i seguenti topic disponibili: {', '.join(suggestions)}
        Quale è il più vicino semanticamente a "{new_topic}"?
        Restituisci SOLO il nome del topic scelto, senza spiegazioni.
        """
        
        closest_match = timed_generate_text(prompt, "find closest topic").strip()
        
        # Verifichiamo che il match sia nella lista
        for topic in suggestions:
            if topic.lower() in closest_match.lower():
                topic_match = topic
                break
        
        # Se ancora non troviamo un match, usiamo il primo della lista
        if not topic_match:
            topic_match = suggestions[0]
            message = f"Non ho trovato un topic corrispondente a '{new_topic}'. Uso '{topic_match}' come fallback."
        else:
            message = f"Topic cambiato da '{new_topic}' a '{topic_match}' (il più simile disponibile)."
    else:
        message = f"Topic cambiato a: {topic_match}"
    
    # Generiamo una nuova domanda per il nuovo topic
    prompt = f"""
    L'utente ha cambiato topic da precedente a "{topic_match}".
    Genera una domanda introduttiva per iniziare l'esplorazione di questo nuovo topic.
    La domanda deve essere personale, rivolta all'utente, e focalizzata sulle sue esperienze e opinioni.
    IMPORTANTE: La domanda deve essere breve (massimo 15 parole) e in italiano.
    """
    
    new_question = timed_generate_text(prompt, "nuova domanda per nuovo topic")
    
    return topic_match, new_question, message 
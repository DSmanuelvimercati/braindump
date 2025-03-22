import os
from modules.llm_handler import timed_generate_text, filter_llm_response
from modules.dynamic_prompt import build_dynamic_prompt
from config import TEMP_FOLDER

def generate_new_question(chosen_topic, conversation_history, relevant_files=None, previous_questions=None):
    """
    Genera una nuova domanda basata sul topic e sulla cronologia della conversazione.
    
    Args:
        chosen_topic (str): Il topic selezionato
        conversation_history (str): La cronologia della conversazione
        relevant_files (list): I file rilevanti per il contesto
        previous_questions (list): Le domande poste in precedenza
        
    Returns:
        str: La nuova domanda generata
    """
    # Prepara il contesto dai file rilevanti
    context_content = ""
    if relevant_files:
        for file_path in relevant_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    file_name = os.path.basename(file_path)
                    file_dir = os.path.dirname(file_path)
                    
                    # Evidenzia particolarmente i file dalla cartella dei concetti
                    if "concetti" in file_dir.lower():
                        context_content += f"\n--- DEFINIZIONE DEL CONCETTO '{file_name}' ---\n{file_content}\n"
                    else:
                        context_content += f"\n--- Informazione da '{file_name}' ---\n{file_content}\n"
            except Exception as e:
                print(f"Errore nella lettura del file {file_path}: {e}")
    
    # Leggi le linee guida temporanee se esistono
    guidelines_content = ""
    temp_guidelines_file = os.path.join(TEMP_FOLDER, "temp_guidelines.md")
    
    if os.path.exists(temp_guidelines_file):
        try:
            with open(temp_guidelines_file, 'r', encoding='utf-8') as f:
                guidelines_content = f.read()
        except Exception as e:
            print(f"Errore nella lettura delle linee guida: {e}")
    
    # Genera una nuova domanda usando il contesto, le linee guida e il prompt dinamico
    prompt = f"""
    Genera una domanda sul topic '{chosen_topic}' basandoti sulle seguenti definizioni, linee guida e informazioni di contesto:
    
    {context_content if context_content else "Nessuna informazione di contesto disponibile."}
    
    LINEE GUIDA PER LA GENERAZIONE DELLE DOMANDE:
    {guidelines_content if guidelines_content else "Nessuna linea guida specifica disponibile."}
    
    La domanda deve essere:
    1. STRETTAMENTE ed ESCLUSIVAMENTE correlata al significato del topic '{chosen_topic}' come definito nel contesto
    2. COMPLETAMENTE focalizzata sul topic principale, evitando qualsiasi deviazione verso altri argomenti
    3. Basata sulla definizione del concetto fornita, NON su interpretazioni personali del concetto
    
    IMPORTANTE: 
    - Il topic '{chosen_topic}' deve essere inteso ESATTAMENTE come definito nei file di contesto
    - Se è presente una definizione esplicita del concetto, segui RIGOROSAMENTE quella definizione
    - NON interpretare il topic come un interesse o una passione dell'utente, a meno che non sia esplicitamente indicato
    - Formula la domanda in modo che sia pertinente alla vita personale dell'utente ma rispettando la definizione del concetto
    - Segui scrupolosamente le linee guida specifiche fornite dall'utente, se presenti
    
    Esempi di domande corrette:
    - Per il topic 'anagrafica' definito come "informazioni personali basilari": "Quali cambiamenti hai registrato nella tua anagrafica negli ultimi anni?"
    - Per il topic 'lavoro': "In che modo il tuo attuale lavoro riflette le tue aspirazioni professionali?"
    
    Basati anche sul contesto della conversazione: {conversation_history}
    
    Genera una SINGOLA domanda breve e diretta in italiano.
    """
    
    new_question = timed_generate_text(prompt, "nuova domanda con contesto")
    
    # Filtra e valida la risposta
    filtered_question = filter_llm_response(
        new_question, 
        chosen_topic=chosen_topic, 
        previous_questions=previous_questions
    )
    
    return filtered_question

def generate_new_question_after_skip(chosen_topic, conversation_history, previous_questions=None):
    """
    Genera una nuova domanda dopo che l'utente ha saltato quella corrente.
    
    Args:
        chosen_topic (str): Il topic selezionato
        conversation_history (str): La cronologia della conversazione
        previous_questions (list): Le domande poste in precedenza
        
    Returns:
        str: La nuova domanda generata
    """
    # Leggi le linee guida temporanee se esistono
    guidelines_content = ""
    temp_guidelines_file = os.path.join(TEMP_FOLDER, "temp_guidelines.md")
    
    if os.path.exists(temp_guidelines_file):
        try:
            with open(temp_guidelines_file, 'r', encoding='utf-8') as f:
                guidelines_content = f.read()
        except Exception as e:
            print(f"Errore nella lettura delle linee guida: {e}")
    
    prompt = f"""
    L'utente ha deciso di saltare questa domanda. 
    
    Genera una NUOVA domanda singola sul topic '{chosen_topic}', che sia:
    1. STRETTAMENTE correlata al significato principale del topic
    2. NON sovrapponibile con altri topic
    3. Diversa dalle precedenti e più interessante
    4. Focalizzata sulla vita personale dell'utente
    
    LINEE GUIDA PER LA GENERAZIONE DELLE DOMANDE:
    {guidelines_content if guidelines_content else "Nessuna linea guida specifica disponibile."}
    
    Il topic '{chosen_topic}' è il FOCUS PRINCIPALE della domanda, non deviare verso altri argomenti.
    Segui scrupolosamente le linee guida specifiche fornite dall'utente, se presenti.
    
    Basati su questo contesto di conversazione:
    {conversation_history}
    
    IMPORTANTE: La domanda deve essere ESCLUSIVAMENTE in italiano.
    """
    
    new_question = timed_generate_text(prompt, "nuova domanda dopo skip")
    
    # Filtra e valida la risposta
    filtered_question = filter_llm_response(
        new_question, 
        chosen_topic=chosen_topic, 
        previous_questions=previous_questions
    )
    
    return filtered_question

def generate_more_relevant_question(current_topic, conversation_history, previous_questions=None):
    """
    Genera una domanda più pertinente quando l'utente indica che la domanda corrente non è rilevante.
    
    Args:
        current_topic (str): Il topic corrente
        conversation_history (str): La cronologia della conversazione
        previous_questions (list): Le domande poste in precedenza
        
    Returns:
        str: Una domanda più pertinente
    """
    # Leggi le linee guida temporanee se esistono
    guidelines_content = ""
    temp_guidelines_file = os.path.join(TEMP_FOLDER, "temp_guidelines.md")
    
    if os.path.exists(temp_guidelines_file):
        try:
            with open(temp_guidelines_file, 'r', encoding='utf-8') as f:
                guidelines_content = f.read()
        except Exception as e:
            print(f"Errore nella lettura delle linee guida: {e}")
    
    prompt = f"""
    L'utente ha indicato che la domanda precedente non era rilevante o era troppo complessa.
    
    Per il topic '{current_topic}', genera una domanda più semplice e pertinente, che sia:
    1. STRETTAMENTE correlata al significato principale del topic '{current_topic}'
    2. Più concreta e specifica
    3. Basata sulle esperienze personali dell'utente
    4. Facilmente comprensibile
    5. Senza richiedere conoscenze specialistiche
    
    LINEE GUIDA PER LA GENERAZIONE DELLE DOMANDE:
    {guidelines_content if guidelines_content else "Nessuna linea guida specifica disponibile."}
    
    Il topic '{current_topic}' è il FOCUS PRINCIPALE della domanda, non deviare verso altri argomenti.
    Segui scrupolosamente le linee guida specifiche fornite dall'utente, se presenti.
    
    Ecco il contesto della conversazione fino ad ora:
    {conversation_history}

    ATTENZIONE: Genera SOLO UNA domanda breve e semplice in italiano. Non aggiungere altro testo.
    """
    
    new_question = timed_generate_text(prompt, "domanda più pertinente")
    
    # Filtra e valida la risposta
    filtered_question = filter_llm_response(
        new_question, 
        chosen_topic=current_topic, 
        previous_questions=previous_questions
    )
    
    return filtered_question

def similarity_score(question, previous_questions, threshold=0.8):
    """
    Calcola un punteggio di similarità tra una domanda e quelle precedenti.
    
    Args:
        question (str): La domanda da verificare
        previous_questions (list): Lista delle domande precedenti
        threshold (float): La soglia di similarità (0-1)
        
    Returns:
        float: Il punteggio di similarità (0-1)
    """
    if not previous_questions:
        return 0
        
    question = question.lower()
    
    # Rimuovi punteggiatura comune e converti tutto in minuscolo
    import re
    question_clean = re.sub(r'[.,?!;:]', '', question)
    question_words = set(question_clean.split())
    
    max_similarity = 0
    for prev_question in previous_questions:
        prev_clean = re.sub(r'[.,?!;:]', '', prev_question.lower())
        prev_words = set(prev_clean.split())
        
        # Usa l'indice di Jaccard per determinare la similarità
        if not question_words or not prev_words:
            continue
            
        intersection = question_words.intersection(prev_words)
        union = question_words.union(prev_words)
        
        similarity = len(intersection) / len(union) if union else 0
        max_similarity = max(max_similarity, similarity)
    
    return max_similarity

def is_similar_to_previous(question, previous_questions, threshold=0.8):
    """
    Verifica se una domanda è simile a quelle poste in precedenza.
    
    Args:
        question (str): La domanda da verificare
        previous_questions (list): Lista delle domande precedenti
        threshold (float): La soglia di similarità (0-1)
        
    Returns:
        bool: True se la domanda è simile a una precedente
    """
    return (question.strip().lower() in [q.lower() for q in previous_questions]) or \
           (similarity_score(question, previous_questions) > threshold) 
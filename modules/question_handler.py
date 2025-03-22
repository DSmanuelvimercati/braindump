import os
from modules.llm_handler import timed_generate_text, filter_llm_response
from modules.dynamic_prompt import build_dynamic_prompt

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
    # Genera una nuova domanda usando il prompt dinamico
    prompt = build_dynamic_prompt(
        chosen_topic=chosen_topic, 
        conversation_history=conversation_history, 
        relevant_files=relevant_files
    )
    
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
    prompt = f"L'utente ha deciso di saltare questa domanda. Genera una NUOVA domanda singola sul topic '{chosen_topic}', diversa dalle precedenti e più interessante. Basati su questo contesto di conversazione:\n\n{conversation_history}\n\nIMPORTANTE: La domanda deve essere ESCLUSIVAMENTE in italiano."
    
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
    prompt = f"""
    L'utente ha indicato che la domanda precedente non era rilevante o era troppo complessa.
    Per il topic '{current_topic}', genera una domanda più semplice e pertinente, che sia:
    1. Più concreta e specifica
    2. Basata sulle esperienze personali dell'utente
    3. Facilmente comprensibile
    4. Senza richiedere conoscenze specialistiche

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
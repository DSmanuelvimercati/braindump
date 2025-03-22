from modules.llm_handler import timed_generate_text

def interpret_user_answer(answer):
    """
    Interpreta la risposta dell'utente per comandi rapidi base.
    
    Args:
        answer (str): La risposta dell'utente
        
    Returns:
        str: Il tipo di risposta identificato
            - "NO_ANSWER" se l'utente scrive "skip" o è vuoto
            - "HELP" se l'utente chiede aiuto
            - "VALID_ANSWER" in tutti gli altri casi
    """
    if not answer or answer.strip().lower() in ["skip", "salta"]:
        return "NO_ANSWER"
    if answer.strip().lower() in ["aiuto", "help", "?"]:
        return "HELP"
    return "VALID_ANSWER"

def interpret_meta_response(answer, current_topic, current_question):
    """
    Analizza la risposta dell'utente per identificare comandi meta come cambiamenti di topic.
    
    Args:
        answer (str): La risposta dell'utente
        current_topic (str): Il topic corrente
        current_question (str): La domanda corrente
        
    Returns:
        dict: Un dizionario con i risultati dell'analisi:
            - "type": il tipo di risposta (DIRECT, CHANGE_TOPIC, IRRELEVANT, SUGGEST_QUESTION)
            - "content": il contenuto della risposta o il nuovo topic
            - "message": un messaggio per l'utente
    """
    # Normalizzazione dell'input
    answer_lower = answer.strip().lower()
    
    # Analisi delle risposte irrilevanti o "non so"
    irrelevant_responses = [
        "non so", "non lo so", "irrilevante", "non capisco", "non pertinente",
        "troppo complesso", "troppo difficile", "non è pertinente", "non è rilevante",
        "troppo ampia", "domanda troppo ampia", "non ho capito"
    ]
    
    # Check per "cambia topic a X" o "parliamo di X" o simili
    if "cambia topic" in answer_lower or "cambia argomento" in answer_lower or "parliamo di" in answer_lower:
        prompt = f"""
        Analizza il seguente messaggio dell'utente per estrarre un nuovo topic richiesto:
        "{answer}"
        
        L'utente sembra voler cambiare topic durante l'intervista. Estrai il nuovo topic menzionato.
        Restituisci solo il nome del nuovo topic. Se non viene menzionato chiaramente un nuovo topic, rispondi con "Nessun topic trovato".
        """
        
        new_topic = timed_generate_text(prompt, "extract new topic").strip()
        
        if "nessun topic" in new_topic.lower():
            return {
                "type": "DIRECT",
                "content": answer,
                "message": "DEBUG - Tipo di risposta rilevato: DIRECT\nDEBUG - Richiesta di cambio topic ma nessun topic specificato."
            }
            
        return {
            "type": "CHANGE_TOPIC",
            "content": new_topic,
            "message": f"DEBUG - Tipo di risposta rilevato: CHANGE_TOPIC\nDEBUG - Nuovo topic richiesto: {new_topic}"
        }
    
    # Check per risposte irrilevanti
    for phrase in irrelevant_responses:
        if phrase in answer_lower:
            prompt = f"""
            Analizza la seguente risposta dell'utente:
            "{answer}"
            
            Domanda: {current_question}
            Topic: {current_topic}
            
            L'utente ha indicato che la domanda non è rilevante o è troppo complessa.
            Determina il motivo esatto della risposta dell'utente. Descrivi in una frase.
            """
            
            reason = timed_generate_text(prompt, "interpretazione risposta").strip()
            
            return {
                "type": "IRRELEVANT",
                "content": answer,
                "message": f"DEBUG - Tipo di risposta rilevato: IRRELEVANT\nDEBUG - Motivazione: {reason}"
            }
    
    # Check per suggerimenti di domande
    if "?" in answer:
        prompt = f"""
        Analizza la seguente risposta dell'utente:
        "{answer}"
        
        Domanda originale: {current_question}
        Topic: {current_topic}
        
        L'utente sembra aver suggerito una propria domanda invece di rispondere. 
        È (a) una semplice richiesta di chiarimento della domanda, o
        (b) sta chiedendo di cambiare completamente la domanda?
        Rispondi solo con "A" o "B".
        """
        
        suggestion_type = timed_generate_text(prompt, "analisi suggerimento domanda").strip().upper()
        
        if suggestion_type == "B":
            return {
                "type": "SUGGEST_QUESTION",
                "content": answer,
                "message": f"DEBUG - Tipo di risposta rilevato: SUGGEST_QUESTION\nDEBUG - L'utente ha suggerito una domanda alternativa."
            }
    
    # Se nessuna delle condizioni precedenti è vera, la risposta è diretta
    prompt = f"""
    Analizza la seguente risposta dell'utente:
    "{answer}"
    
    Domanda: {current_question}
    Topic: {current_topic}
    
    Verifica se la risposta dell'utente è pertinente alla domanda e al topic.
    Rispondi solo con "PERTINENTE" o "NON PERTINENTE".
    """
    
    relevance_check = timed_generate_text(prompt, "controllo pertinenza").strip().upper()
    
    if "NON PERTINENTE" in relevance_check:
        prompt = f"""
        Analizza la seguente risposta dell'utente:
        "{answer}"
        
        Domanda: {current_question}
        Topic: {current_topic}
        
        La risposta non sembra pertinente. Spiega brevemente perché.
        """
        
        reason = timed_generate_text(prompt, "analisi non pertinenza").strip()
        
        return {
            "type": "IRRELEVANT",
            "content": answer,
            "message": f"DEBUG - Tipo di risposta rilevato: IRRELEVANT\nDEBUG - Motivazione: {reason}\nDEBUG - Correzione automatica: riclassificazione come DIRECT"
        }
    
    return {
        "type": "DIRECT",
        "content": answer,
        "message": "DEBUG - Tipo di risposta rilevato: DIRECT"
    }

def provide_help_info():
    """
    Fornisce informazioni di aiuto all'utente.
    
    Returns:
        str: Il messaggio di aiuto
    """
    help_text = """
    === COMANDI DISPONIBILI ===
    
    Durante l'intervista puoi usare i seguenti comandi:
    
    - "skip" o (vuoto): salta la domanda attuale
    - "fine" o "exit": termina l'intervista e salva i risultati
    - "help", "aiuto" o "?": mostra questo messaggio di aiuto
    - "cambia topic a [NOME]": cambia l'argomento dell'intervista
    - "irrilevante": indica che la domanda non è pertinente
    
    Puoi sempre rispondere normalmente per fornire informazioni sul topic.
    """
    return help_text 
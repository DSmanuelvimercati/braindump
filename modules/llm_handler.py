import time
from modules.llm import generate_text

def timed_generate_text(prompt, description=""):
    """
    Esegue una chiamata all'LLM e misura il tempo impiegato.
    
    Args:
        prompt (str): Il prompt da inviare all'LLM
        description (str): Descrizione della chiamata per il logging
        
    Returns:
        str: La risposta generata dall'LLM
    """
    start_time = time.time()
    result = generate_text(prompt)
    duration = time.time() - start_time
    print(f"[{description}] LLM call took {duration:.2f} seconds")
    return result

def filter_llm_response(response, chosen_topic="", max_length=150, previous_questions=None):
    """
    Filtra e valida la risposta dell'LLM per assicurarsi che sia una domanda valida.
    
    Args:
        response (str): La risposta dell'LLM da filtrare
        chosen_topic (str): Il topic corrente
        max_length (int): La lunghezza massima consentita per la risposta
        previous_questions (list): Lista delle domande precedenti per evitare ripetizioni
        
    Returns:
        str: La risposta filtrata e validata
    """
    # Verifica se il risultato è una domanda valida
    if (len(response) > max_length or 
        "**" in response or 
        "# " in response or 
        ":" in response.split("?")[0]):
        
        print("ATTENZIONE: Rilevata risposta non valida dall'LLM. Riprovo con una richiesta più semplice...")
        
        # Genera una richiesta più semplice
        avoid_questions = ""
        if previous_questions and len(previous_questions) > 0:
            questions_to_avoid = previous_questions[-5:] if len(previous_questions) > 5 else previous_questions
            avoid_questions = f"NON ripetere queste domande che sono già state poste: {', '.join(questions_to_avoid)}"
        
        simplified_prompt = (
            f"Genera SOLO UNA domanda breve (massimo 15 parole) sul topic '{chosen_topic}' in italiano. "
            "NON aggiungere altri testi o spiegazioni. Usa solo la lingua italiana. "
            f"{avoid_questions}"
        )
        
        response = timed_generate_text(simplified_prompt, "retry question")
    
    return response.strip()

def extract_json_from_response(response):
    """
    Estrae un array JSON da una risposta testuale dell'LLM.
    
    Args:
        response (str): La risposta dell'LLM
        
    Returns:
        list: L'array JSON estratto o una lista vuota in caso di errore
    """
    try:
        import re
        import json
        
        # Cerca per pattern di array JSON
        json_match = re.search(r'\[.*\]', response)
        if json_match:
            json_text = json_match.group(0)
            return json.loads(json_text)
        else:
            print("Nessun formato JSON valido trovato nella risposta")
            return []
    except Exception as e:
        print(f"Errore nell'analisi JSON: {e}")
        print(f"Risposta ricevuta: {response}")
        return [] 
import time
from modules.llm import generate_text
from modules.logger import ColoredLogger

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

def filter_llm_response(response, topic):
    """
    Filtra la risposta dell'LLM per garantire che sia valida.
    
    Args:
        response (str): La risposta dell'LLM
        topic (str): Il topic corrente
        
    Returns:
        str: La risposta filtrata
    """
    # Controlla se la risposta contiene placeholder
    if "[topic]" in response or "[argomento]" in response:
        ColoredLogger.warning(f"La risposta contiene placeholder: {response}")
        response = response.replace("[topic]", topic).replace("[argomento]", topic)
    
    # Verifica se la risposta è una domanda valida
    if not is_valid_question(response) or len(response.split()) > 20:
        ColoredLogger.warning(f"Risposta non valida: {response}")
        
        # Prova a generare una risposta più semplice
        prompt = f"""
        Genera UNA sola domanda personale riguardante il topic "{topic}".
        
        LINEE GUIDA:
        - La domanda deve essere in italiano
        - La domanda deve essere specifica e personale, NON generica
        - Evita domande generiche come "Cosa ne pensi di {topic}?"
        - Non usare MAI placeholder come [topic] o [argomento]
        - Usa direttamente il termine "{topic}" nella domanda se necessario
        - La domanda deve essere breve (15-20 parole massimo)
        - La domanda deve richiedere una risposta basata su esperienze o opinioni personali
        
        Esempi di domande VALIDE:
        - "Come hai sviluppato la tua passione per la filosofia durante gli anni universitari?"
        - "Quali progetti lavorativi ti hanno dato maggiore soddisfazione nell'ultimo anno?"
        
        Esempi di domande NON VALIDE:
        - "Cosa ne pensi di [topic]?" (troppo generica e usa placeholder)
        - "Parlami di anagrafica." (non è una vera domanda)
        - "Quali sono gli aspetti più interessanti dell'argomento che stiamo trattando?" (troppo vaga)
        
        Rispondi SOLO con la domanda, senza altre spiegazioni.
        """
        
        new_response = generate_text(prompt)
        
        # Verifica la nuova risposta
        if is_valid_question(new_response) and "[topic]" not in new_response and "[argomento]" not in new_response:
            return new_response
        
        # Se anche il secondo tentativo fallisce, usa una domanda generica di backup
        ColoredLogger.warning("Secondo tentativo fallito, uso domanda di backup")
        backup_questions = [
            f"Qual è la tua esperienza personale con {topic}?",
            f"Cosa ti ha portato ad interessarti a {topic}?",
            f"Come hai sviluppato le tue conoscenze su {topic}?",
            f"Quali aspetti di {topic} ti interessano maggiormente?",
            f"Come si collega {topic} alla tua vita quotidiana?"
        ]
        import random
        return random.choice(backup_questions)
    
    return response

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

def is_valid_question(text):
    """
    Verifica se il testo è una domanda valida.
    
    Args:
        text (str): Il testo da verificare
        
    Returns:
        bool: True se è una domanda valida, False altrimenti
    """
    if not text:
        return False
    
    # Pulisci la risposta
    text = text.strip()
    
    # Verifica se termina con un punto interrogativo
    if not text.endswith("?"):
        return False
    
    # Controlla la lunghezza
    words = text.split()
    if len(words) < 3 or len(words) > 30:
        return False
    
    # Controlla elementi indesiderati
    unwanted_elements = [
        "**", "# ", 
        "la tua richiesta", "come vedrai", "ecco", "ho capito",
        "secondo le informazioni", "restituisci", "genera"
    ]
    
    for element in unwanted_elements:
        if element in text.lower():
            return False
    
    return True 
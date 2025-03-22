"""
Gestore delle risposte utente: interpreta e classifica le risposte dell'utente con analisi semantica LLM.
"""

from modules.llm_handler import timed_generate_text, filter_llm_response
from modules.logger import ColoredLogger
import re
import json

def interpret_user_answer(user_input):
    """
    Interpreta la risposta base dell'utente usando l'LLM per un'analisi semantica.
    
    Args:
        user_input (str): L'input dell'utente
        
    Returns:
        str: Il tipo di risposta rilevato
    """
    # Per risposte semplici e comuni, usa ancora l'approccio basato su regole per efficienza
    # Normalizza l'input
    user_input_lower = user_input.strip().lower()
    
    # Risposte vuote o skip
    if not user_input_lower or user_input_lower in ["skip", "passa", "salta", "s", "next", "n"]:
        return "NO_ANSWER"
    
    # Richieste di aiuto
    if user_input_lower in ["help", "aiuto", "?", "aiutami"]:
        return "HELP"
    
    # Per risposte più complesse, utilizza l'LLM per l'analisi semantica
    prompt = f"""
    Analizza la seguente risposta dell'utente e classifica il tipo di richiesta:
    
    Risposta: "{user_input}"
    
    Considera le seguenti categorie:
    1. NO_ANSWER - L'utente vuole saltare la domanda o non fornisce una risposta
    2. HELP - L'utente chiede aiuto o assistenza
    3. STANDARD - L'utente fornisce una risposta standard alla domanda
    
    Restituisci SOLO UNA di queste parole chiave: "NO_ANSWER", "HELP" o "STANDARD"
    """
    
    response = timed_generate_text(prompt, "classificazione risposta base").strip().upper()
    
    # Verifica che la risposta sia una delle categorie previste
    if response in ["NO_ANSWER", "HELP", "STANDARD"]:
        return response
    
    # Fallback in caso di risposta non riconosciuta
    return "STANDARD"

def interpret_meta_response(user_input, current_topic, current_question):
    """
    Analizza la risposta dell'utente per capire se è una meta-richiesta utilizzando l'LLM.
    
    Args:
        user_input (str): L'input dell'utente
        current_topic (str): Il topic corrente
        current_question (str): La domanda corrente
        
    Returns:
        dict: Un dizionario con il tipo di risposta e il contenuto
    """
    ColoredLogger.system("Analisi della risposta dell'utente...")
    
    # Prompt migliorato per l'analisi semantica della risposta
    prompt = f"""
    Analizza semanticamente la seguente risposta dell'utente alla domanda: "{current_question}" (topic: {current_topic})
    
    Risposta utente: "{user_input}"
    
    Scegli UNA SOLA tra queste classificazioni:
    1. DIRECT - Risposta diretta alla domanda (l'utente sta effettivamente rispondendo alla domanda)
    2. CHANGE_TOPIC - Richiesta di cambiare topic (es. "parliamo di lavoro", "cambiamo argomento")
    3. IRRELEVANT - Indicazione che la domanda è irrilevante o fuori contesto (es. "questa domanda non mi interessa", "non è pertinente")
    4. SUGGEST_QUESTION - L'utente suggerisce una domanda alternativa (es. "chiedimi piuttosto...", "sarebbe meglio chiedere...")
    
    Se la classificazione è CHANGE_TOPIC, identifica il nuovo topic richiesto.
    Se la classificazione è SUGGEST_QUESTION, estrai la domanda suggerita.
    
    IMPORTANTE: Prima di classificare una risposta come IRRELEVANT, verifica che l'utente stia effettivamente dicendo che la domanda è irrilevante, non che stia semplicemente rispondendo in modo negativo.
    
    Restituisci il risultato in formato JSON:
    {{
      "type": "DIRECT|CHANGE_TOPIC|IRRELEVANT|SUGGEST_QUESTION",
      "content": "contenuto rilevante o domanda suggerita o nuovo topic",
      "confidence": 0-100
    }}
    """
    
    # Genera la classificazione
    response = timed_generate_text(prompt, "classificazione semantica risposta")
    
    # Estrai il risultato JSON
    try:
        # Cerca un pattern JSON nella risposta
        json_match = re.search(r'{.*}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)
            
            response_type = result.get("type", "DIRECT")
            content = result.get("content", user_input)
            confidence = result.get("confidence", 80)
            
            message = f"Risposta classificata come: {response_type} (confidenza: {confidence}%)"
            
            return {
                "type": response_type,
                "content": content,
                "confidence": confidence,
                "message": message
            }
    except Exception as e:
        ColoredLogger.error(f"Errore nell'analisi della risposta JSON: {e}")
    
    # Fallback
    return {
        "type": "DIRECT",
        "content": user_input,
        "confidence": 50,
        "message": "Risposta classificata come: DIRECT (fallback)"
    }

def evaluate_question_compliance(question, guidelines):
    """
    Valuta se una domanda rispetta le linee guida utilizzando l'LLM.
    
    Args:
        question (str): La domanda da valutare
        guidelines (str): Le linee guida da rispettare
        
    Returns:
        dict: Risultato della valutazione con conformità, spiegazione e suggerimenti
    """
    ColoredLogger.system("Valutazione della conformità della domanda...")
    
    prompt = f"""
    Valuta se la seguente domanda rispetta le linee guida fornite.
    
    Domanda: "{question}"
    
    Linee guida:
    {guidelines}
    
    Analizza attentamente e determina:
    1. Se la domanda è conforme alle linee guida
    2. Quali aspetti rispetta e quali eventualmente viola
    3. Come potrebbe essere migliorata per rispettare meglio le linee guida
    
    Restituisci il risultato in formato JSON:
    {{
      "compliant": true/false,
      "explanation": "Spiegazione dettagliata del perché la domanda rispetta o non rispetta le linee guida",
      "improvement_suggestions": "Suggerimenti specifici per migliorare la domanda (se necessario)"
    }}
    """
    
    response = timed_generate_text(prompt, "valutazione conformità domanda")
    
    try:
        json_match = re.search(r'{.*}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)
            
            return {
                "compliant": result.get("compliant", True),
                "explanation": result.get("explanation", "Nessuna spiegazione fornita"),
                "improvement_suggestions": result.get("improvement_suggestions", "")
            }
    except Exception as e:
        ColoredLogger.error(f"Errore nell'analisi della valutazione: {e}")
    
    # Fallback
    return {
        "compliant": True,
        "explanation": "Non è stato possibile valutare la conformità della domanda",
        "improvement_suggestions": ""
    }

def provide_help_info():
    """
    Fornisce informazioni di aiuto all'utente.
    
    Returns:
        str: Il messaggio di aiuto formattato
    """
    help_message = """
Comandi disponibili:
- fine/exit: Termina l'intervista
- skip/passa: Salta la domanda corrente
- help/aiuto: Mostra questo messaggio di aiuto
- cambia topic X: Cambia il topic corrente a X
- "Non mi interessa questa domanda": Indica che la domanda non è rilevante
- "Chiedimi invece X": Suggerisci una domanda alternativa
- "inseriamo nelle guideline che X": Aggiungi X alle linee guida
- "mostra guideline": Visualizza le linee guida attuali

Per valutare una domanda:
- "questa domanda rispetta le linee guida": Conferma che la domanda è adeguata
- "questa domanda non rispetta le linee guida": Segnala che la domanda non è conforme

Quando ti viene mostrata una risposta suggerita:
- Conferma con "sì", "va bene", etc.
- Modifica con "no, in realtà..." o fornendo una risposta differente
- Rifiuta con "no", "non è corretto", etc.
    """
    
    return help_message

def summarize_conversation(conversation_history, current_topic):
    """
    Genera un riassunto della conversazione.
    
    Args:
        conversation_history (str): La cronologia della conversazione
        current_topic (str): Il topic corrente
        
    Returns:
        str: Il riassunto generato
    """
    if not conversation_history.strip():
        return f"Nessuna conversazione registrata sul topic '{current_topic}'."
    
    ColoredLogger.system("Generazione del riassunto della conversazione...")
    
    prompt = f"""
    Genera un riassunto conciso della seguente conversazione sul topic '{current_topic}'.
    
    {conversation_history}
    
    Il riassunto deve:
    1. Evidenziare i punti principali trattati
    2. Essere in forma di paragrafi (non elenchi puntati)
    3. Essere in terza persona
    4. Non superare i 3-4 paragrafi
    5. Essere in italiano
    
    Inizia direttamente con il riassunto, senza introduzioni.
    """
    
    summary = timed_generate_text(prompt, "riassunto conversazione")
    
    # Filtra la risposta
    summary = filter_llm_response(summary, current_topic)
    
    return summary

def extract_key_insights(conversation_history, current_topic):
    """
    Estrae le intuizioni chiave dalla conversazione.
    
    Args:
        conversation_history (str): La cronologia della conversazione
        current_topic (str): Il topic corrente
        
    Returns:
        list: Lista delle intuizioni chiave
    """
    if not conversation_history.strip():
        return []
    
    ColoredLogger.system("Estrazione degli insight principali...")
    
    prompt = f"""
    Estrai 3-5 insight chiave dalla seguente conversazione sul topic '{current_topic}'.
    
    {conversation_history}
    
    Gli insight devono:
    1. Essere specifici e significativi
    2. Riflettere il contenuto della conversazione
    3. Essere espressi come affermazioni concise (max 15 parole)
    4. Essere in italiano
    
    Restituisci SOLO un array JSON con gli insight:
    ["Insight 1", "Insight 2", ...]
    """
    
    response = timed_generate_text(prompt, "estrazione insight")
    
    # Estrai gli insight
    try:
        # Cerca pattern JSON nella risposta
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            insights = json.loads(json_str)
            
            # Filtra gli insight
            filtered_insights = [filter_llm_response(insight, current_topic) for insight in insights]
            return filtered_insights
    except Exception as e:
        ColoredLogger.error(f"Errore nell'estrazione degli insight: {e}")
    
    # Fallback
    return [] 
import os
from modules.dynamic_prompt import build_dynamic_prompt, get_topic_suggestions
from modules.storage import save_braindump_entry
from modules.llm_handler import timed_generate_text, filter_llm_response
from modules.question_handler import (
    generate_new_question, 
    generate_new_question_after_skip, 
    generate_more_relevant_question,
    is_similar_to_previous
)
from modules.response_handler import interpret_user_answer, interpret_meta_response, provide_help_info
from modules.context_handler import get_relevant_context, choose_topic_manually, change_topic
from modules.consolidation import finalize_session
from config import create_temp_folder

VERBOSE = True

def log(msg):
    """Log un messaggio se il verbose è attivo"""
    if VERBOSE:
        print(msg)

def start_interview():
    """
    Funzione principale che gestisce l'intero flusso dell'intervista.
    """
    # Inizializzazione
    create_temp_folder()
    print(f"Cartella temporanea creata: {os.path.abspath(os.path.join(os.getcwd(), 'temp_session'))}")
    
    # Proposta dei topic
    prompt = build_dynamic_prompt(chosen_topic=None, conversation_history="")
    print("Prompt per la selezione del topic:")
    print(prompt)
    
    # Selezione del topic
    topic_input = input("Inserisci il numero del topic scelto o il nome (lascia vuoto per scelta automatica): ").strip()
    suggestions = get_topic_suggestions()
    
    if topic_input == "":
        chosen_topic = choose_topic_manually(suggestions)
    elif topic_input.isdigit():
        idx = int(topic_input) - 1
        if idx < len(suggestions):
            chosen_topic = suggestions[idx]
        else:
            print("Scelta non valida, verrà usato 'Generale'.")
            chosen_topic = "Generale"
    else:
        chosen_topic = topic_input
    
    print(f"\nTopic selezionato: {chosen_topic}")
    
    # Inizializzazione della conversazione
    conversation_history = ""
    previous_questions = []
    
    # Otteniamo i file di contesto rilevanti per il topic scelto
    relevant_files = get_relevant_context(chosen_topic, conversation_history)
    
    # Generazione della prima domanda
    print("Chiamata LLM per generare la prima domanda...")
    current_question = generate_new_question(
        chosen_topic=chosen_topic,
        conversation_history=conversation_history,
        relevant_files=relevant_files
    )
    
    print(f"Domanda generata: {current_question}")
    previous_questions.append(current_question.strip().lower())
    
    # Loop principale dell'intervista
    while True:
        print("\nDomanda:", current_question)
        user_input = input("Risposta (digita 'fine' per terminare): ").strip()
        
        # Gestione uscita
        if user_input.lower() in ["fine", "exit"]:
            finalize_session(chosen_topic)
            break
        
        # Gestione comandi base
        basic_interpretation = interpret_user_answer(user_input)
        
        # Gestione Skip
        if basic_interpretation == "NO_ANSWER":
            print("Risposta ignorata (skip).")
            conversation_history += f"Domanda: {current_question}\n\nRisposta: [SKIPPED]\n\n"
            
            current_question = generate_new_question_after_skip(
                chosen_topic=chosen_topic,
                conversation_history=conversation_history,
                previous_questions=previous_questions
            )
            
            # Evita domande ripetute
            attempts = 0
            while is_similar_to_previous(current_question, previous_questions) and attempts < 3:
                print("Rilevata domanda simile a una precedente, rigenerando...")
                current_question = generate_new_question_after_skip(
                    chosen_topic=chosen_topic,
                    conversation_history=conversation_history,
                    previous_questions=previous_questions
                )
                attempts += 1
            
            previous_questions.append(current_question.strip().lower())
            print(f"Domanda generata: {current_question}")
            continue
        
        # Gestione richiesta di aiuto rapida
        if basic_interpretation == "HELP":
            help_info = provide_help_info()
            print(help_info)
            continue
        
        # Analisi meta-risposte
        meta_analysis = interpret_meta_response(user_input, chosen_topic, current_question)
        print(meta_analysis["message"])
        
        # Gestione in base al tipo di risposta
        if meta_analysis["type"] == "DIRECT":
            # Risposta diretta - salva e procedi
            pair_text = f"Domanda: {current_question}\n\nRisposta: {meta_analysis['content']}"
            print("Salvataggio delle informazioni temporanee...")
            info_file_path = save_braindump_entry(pair_text, chosen_topic)
            print(f"Informazioni salvate in: {info_file_path}")
            
            conversation_history += pair_text + "\n\n"
            
            # Ottieni nuovamente i file di contesto rilevanti dopo la risposta
            relevant_files = get_relevant_context(chosen_topic, conversation_history)
            
            # Genera nuova domanda
            new_question = generate_new_question(
                chosen_topic=chosen_topic,
                conversation_history=conversation_history,
                relevant_files=relevant_files,
                previous_questions=previous_questions
            )
            
            # Evita domande ripetute
            attempts = 0
            while is_similar_to_previous(new_question, previous_questions) and attempts < 3:
                print("Rilevata domanda simile a una precedente, rigenerando...")
                new_question = generate_new_question_after_skip(
                    chosen_topic=chosen_topic,
                    conversation_history=conversation_history,
                    previous_questions=previous_questions
                )
                attempts += 1
            
            current_question = new_question
            previous_questions.append(current_question.strip().lower())
            
        elif meta_analysis["type"] == "CHANGE_TOPIC":
            # Cambio topic
            new_topic = meta_analysis.get("content", "").strip()
            if not new_topic:
                print("Non ho capito a quale topic vuoi cambiare. Continuiamo con il topic attuale.")
                continue
                
            # Registra la richiesta di cambio topic nella cronologia
            pair_text = f"Domanda: {current_question}\n\nRisposta: [CAMBIO TOPIC a {new_topic}]"
            conversation_history += pair_text + "\n\n"
            
            # Cambia effettivamente topic
            chosen_topic, current_question, topic_message = change_topic(new_topic, suggestions, conversation_history)
            print(topic_message)
            
            # Reset degli array per il nuovo topic
            previous_questions = [current_question.strip().lower()]
            
        elif meta_analysis["type"] == "IRRELEVANT":
            # Risposta che indica che la domanda non è rilevante
            print("La domanda precedente verrà ignorata. Genererò una domanda più pertinente.")
            
            # Registra che la domanda è stata ignorata
            pair_text = f"Domanda: {current_question}\n\nRisposta: [DOMANDA IRRILEVANTE: {meta_analysis['content']}]"
            conversation_history += pair_text + "\n\n"
            
            # Genera una domanda più pertinente
            current_question = generate_more_relevant_question(
                current_topic=chosen_topic,
                conversation_history=conversation_history,
                previous_questions=previous_questions
            )
            
            previous_questions.append(current_question.strip().lower())
            print(f"Domanda generata: {current_question}")
            
        elif meta_analysis["type"] == "SUGGEST_QUESTION":
            # L'utente ha suggerito una domanda alternativa
            print("Utilizzerò la tua domanda suggerita come base per la prossima.")
            
            # Registra il suggerimento nella cronologia
            pair_text = f"Domanda: {current_question}\n\nRisposta: [SUGGERIMENTO DOMANDA: {meta_analysis['content']}]"
            conversation_history += pair_text + "\n\n"
            
            # Estrai la domanda suggerita
            suggested_question = meta_analysis['content']
            
            # Genera una nuova domanda basata sul suggerimento
            prompt = f"""
            L'utente ha suggerito questa domanda: "{suggested_question}"
            
            Genera una domanda simile ma migliorata che:
            1. Mantenga l'intento originale dell'utente
            2. Sia in formato interrogativo diretto
            3. Sia pertinente al topic '{chosen_topic}'
            4. Sia breve e concisa
            
            IMPORTANTE: Restituisci SOLO la domanda, in italiano, senza testo aggiuntivo.
            """
            
            improved_question = timed_generate_text(prompt, "migliora domanda suggerita")
            
            # Filtra la risposta
            current_question = filter_llm_response(improved_question, chosen_topic)
            previous_questions.append(current_question.strip().lower())
            print(f"Domanda generata: {current_question}")

if __name__ == "__main__":
    start_interview() 
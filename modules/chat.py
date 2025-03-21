import os
import shutil
import time
import json
from tqdm import tqdm
from modules.dynamic_prompt import build_dynamic_prompt, get_topic_suggestions
from modules.llm import generate_text
from modules.storage import save_braindump_entry
from config import INFORMATION_DIR, TEMP_INFORMATION_DIR, create_temp_folder, CONCEPTS_DIR

VERBOSE = True

def log(msg):
    if VERBOSE:
        print(msg)

def timed_generate_text(prompt, description=""):
    start_time = time.time()
    result = generate_text(prompt)
    duration = time.time() - start_time
    print(f"[{description}] LLM call took {duration:.2f} seconds")
    return result

def get_relevant_context(chosen_topic, conversation_history):
    """
    Seleziona solo i file MD pertinenti al topic e alla conversazione attuale.
    Analizza i file in blocchi di massimo 20 per evitare di sovraccaricare l'LLM.
    """
    from config import INFORMATION_DIR, CONCEPTS_DIR
    import os
    
    # Raccogliamo tutti i potenziali file di contesto
    all_files = []
    for directory in [INFORMATION_DIR, CONCEPTS_DIR]:
        if os.path.exists(directory):
            all_files.extend([os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.md')])
    
    if not all_files:
        print("Nessun file di contesto disponibile.")
        return []
    
    # Se abbiamo pochi file, possiamo analizzarli tutti insieme
    if len(all_files) <= 20:
        return evaluate_files_relevance(all_files, chosen_topic, conversation_history)
    
    # Altrimenti, li analizziamo a blocchi
    relevant_files = []
    for i in range(0, len(all_files), 20):
        chunk = all_files[i:i+20]
        relevant_chunk = evaluate_files_relevance(chunk, chosen_topic, conversation_history)
        relevant_files.extend(relevant_chunk)
    
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
    
    try:
        # Estrai l'array JSON
        import re
        import json
        
        # Cerca per pattern di array JSON
        json_match = re.search(r'\[.*\]', result)
        if json_match:
            json_text = json_match.group(0)
            relevant_names = json.loads(json_text)
            
            # Filtriamo la lista dei file per restituire solo quelli rilevanti
            return [f for f in files if os.path.basename(f).replace('.md', '') in relevant_names]
        else:
            print("Nessun formato JSON valido trovato nella risposta")
            return []
    except Exception as e:
        print(f"Errore nell'analisi della pertinenza: {e}")
        print(f"Risposta ricevuta: {result}")
        return []

def interpret_user_answer(answer):
    """
    Interpreta la risposta dell'utente per comandi rapidi base.
    Restituisce:
    - "NO_ANSWER" se l'utente scrive "skip" o è vuoto
    - "HELP" se l'utente chiede aiuto
    - "VALID_ANSWER" in tutti gli altri casi
    """
    if not answer or answer.strip().lower() == "skip":
        return "NO_ANSWER"
    if answer.strip().lower() in ["aiuto", "help", "?"]:
        return "HELP"
    return "VALID_ANSWER"

def choose_topic_manually(suggestions):
    suggestions_str = ", ".join(suggestions)
    prompt = f"L'utente non ha scelto un topic. Tra i seguenti topic: {suggestions_str}, scegli quello più pertinente."
    log("Chiamata LLM per scelta automatica del topic...")
    chosen = timed_generate_text(prompt, "choose topic").strip().lower()
    log(f"Topic scelto dall'LLM: {chosen}")
    for topic in suggestions:
        if topic.lower() in chosen:
            return topic
    return suggestions[0]

def generate_new_question_after_skip(chosen_topic, conversation_history):
    """Genera una nuova domanda dopo che l'utente ha saltato quella corrente"""
    # Ottieni i file di contesto rilevanti
    relevant_files = get_relevant_context(chosen_topic, conversation_history)
    
    prompt = f"L'utente ha deciso di saltare questa domanda. Genera una NUOVA domanda singola sul topic '{chosen_topic}', diversa dalle precedenti e più interessante. Basati su questo contesto di conversazione:\n\n{conversation_history}\n\nIMPORTANTE: La domanda deve essere ESCLUSIVAMENTE in italiano."
    
    new_question = timed_generate_text(prompt, "nuova domanda dopo skip")
    
    # Filtro di sicurezza: verifica se il risultato è una domanda valida
    if len(new_question) > 150 or "**" in new_question or "# " in new_question or ":" in new_question.split("?")[0]:
        print("ATTENZIONE: Rilevata risposta non valida dall'LLM. Riprovo con una richiesta più semplice...")
        new_question = timed_generate_text(
            f"Genera SOLO UNA domanda breve (massimo 15 parole) sul topic '{chosen_topic}' in italiano. "
            "NON aggiungere altri testi o spiegazioni. Usa solo la lingua italiana.",
            "retry question"
        )
    
    return new_question

def start_interview():
    create_temp_folder()
    print(f"Cartella temporanea creata: {os.path.abspath(os.path.join(os.getcwd(), 'temp_session'))}")
    
    # Proposta dei topic
    prompt = build_dynamic_prompt(chosen_topic=None, conversation_history="")
    print("Prompt per la selezione del topic:")
    print(prompt)
    
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
    
    conversation_history = ""
    previous_questions = []  # Aggiungo un array per tenere traccia delle domande precedenti
    
    # Otteniamo i file di contesto rilevanti per il topic scelto
    relevant_files = get_relevant_context(chosen_topic, conversation_history)
    
    print("Chiamata LLM per generare la prima domanda...")
    current_question = timed_generate_text(build_dynamic_prompt(chosen_topic=chosen_topic, conversation_history=conversation_history, relevant_files=relevant_files), "prima domanda")
    
    # Filtro di sicurezza: verifica se il risultato è una domanda valida
    if len(current_question) > 150 or "**" in current_question or "# " in current_question:
        print("ATTENZIONE: Rilevata risposta non valida dall'LLM. Riprovo con una richiesta più semplice...")
        current_question = timed_generate_text(
            f"Genera SOLO UNA domanda breve (massimo 15 parole) sul topic '{chosen_topic}' in italiano. "
            "NON aggiungere altri testi o spiegazioni. Usa solo la lingua italiana.",
            "retry first question"
        )
    
    print(f"Domanda generata: {current_question.strip()}")
    previous_questions.append(current_question.strip().lower())  # Aggiungo la domanda all'elenco
    
    last_question = current_question.strip().lower()
    while True:
        print("\nDomanda:", current_question)
        user_input = input("Risposta (digita 'fine' per terminare): ").strip()
        if user_input.lower() in ["fine", "exit"]:
            print("Intervista terminata.")
            break
        
        # Gestione comandi base
        basic_interpretation = interpret_user_answer(user_input)
        
        # Gestione Skip
        if basic_interpretation == "NO_ANSWER":
            print("Risposta ignorata (skip).")
            conversation_history += f"Domanda: {current_question}\n\nRisposta: [SKIPPED]\n\n"
            current_question = generate_new_question_after_skip(chosen_topic, conversation_history)
            
            # Evita domande ripetute
            attempts = 0
            while (current_question.strip().lower() in previous_questions or similarity_score(current_question, previous_questions) > 0.8) and attempts < 3:
                print("Rilevata domanda simile a una precedente, rigenerando...")
                current_question = generate_new_question_after_skip(chosen_topic, conversation_history)
                attempts += 1
            
            previous_questions.append(current_question.strip().lower())
            last_question = current_question.strip().lower()
            print(f"Domanda generata: {current_question.strip()}")
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
            # Risposta diretta - salva e procedi come prima
            pair_text = f"Domanda: {current_question}\n\nRisposta: {meta_analysis['content']}"
            print("Salvataggio delle informazioni temporanee...")
            info_file_path = save_braindump_entry(pair_text, chosen_topic)
            print(f"Informazioni salvate in: {info_file_path}")
            
            conversation_history += pair_text + "\n\n"
            
            # Ottieni nuovamente i file di contesto rilevanti dopo la risposta
            relevant_files = get_relevant_context(chosen_topic, conversation_history)
            
            new_question = timed_generate_text(build_dynamic_prompt(chosen_topic=chosen_topic, conversation_history=conversation_history, relevant_files=relevant_files), "nuova domanda con contesto")
            
            # Filtro di sicurezza
            if len(new_question) > 150 or "**" in new_question or "# " in new_question or ":" in new_question.split("?")[0]:
                print("ATTENZIONE: Rilevata risposta non valida dall'LLM. Riprovo con una richiesta più semplice...")
                new_question = timed_generate_text(
                    f"Genera SOLO UNA domanda breve (massimo 15 parole) sul topic '{chosen_topic}' in italiano. "
                    "NON aggiungere altri testi o spiegazioni. Usa solo la lingua italiana. "
                    f"NON ripetere queste domande che sono già state poste: {', '.join(previous_questions[-5:] if len(previous_questions) > 5 else previous_questions)}",
                    "retry question"
                )
            
            # Evita domande ripetute
            attempts = 0
            while (new_question.strip().lower() in previous_questions or similarity_score(new_question, previous_questions) > 0.8) and attempts < 3:
                print("Rilevata domanda simile a una precedente, rigenerando...")
                new_question = generate_new_question_after_skip(chosen_topic, conversation_history)
                attempts += 1
            
            current_question = new_question
            previous_questions.append(current_question.strip().lower())
            last_question = current_question.strip().lower()
            
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
            last_question = current_question.strip().lower()
            
            # Reset della cronologia per il nuovo topic
            conversation_history = ""
            
            # Ottieni file rilevanti per il nuovo topic
            relevant_files = get_relevant_context(chosen_topic, conversation_history)
            
        elif meta_analysis["type"] == "SUGGEST_QUESTION":
            # Suggerimento di domanda
            suggested = meta_analysis.get("content", "").strip()
            if not suggested:
                print("Non ho capito quale domanda vorresti che ti facessi. Continuo con le mie domande.")
                current_question = generate_new_question_after_skip(chosen_topic, conversation_history)
            else:
                current_question = generate_suggested_question(suggested, chosen_topic, conversation_history)
            
            # Registra il suggerimento nella cronologia
            pair_text = f"Domanda: {last_question}\n\nRisposta: [SUGGERIMENTO DI DOMANDA: {suggested}]"
            conversation_history += pair_text + "\n\n"
            previous_questions.append(current_question.strip().lower())
            last_question = current_question.strip().lower()
            
        elif meta_analysis["type"] == "IRRELEVANT":
            # Domanda non pertinente
            # Registra il feedback nella cronologia
            pair_text = f"Domanda: {current_question}\n\nRisposta: [DOMANDA NON PERTINENTE]"
            conversation_history += pair_text + "\n\n"
            
            # Genera una domanda più pertinente
            current_question = generate_more_relevant_question(chosen_topic, conversation_history)
            previous_questions.append(current_question.strip().lower())
            last_question = current_question.strip().lower()
            
        elif meta_analysis["type"] == "HELP":
            # Richiesta di aiuto dettagliata (già gestita con il messaggio)
            help_info = provide_help_info()
            print(help_info)
            continue
            
        print(f"Domanda generata: {current_question.strip()}")
    
    finalize_session(chosen_topic)

def finalize_session(chosen_topic):
    """
    Alla fine dell'intervista, consolida le informazioni raccolte per il topic in uno o più documenti finali.
    L'LLM decide dinamicamente quanti documenti creare, i titoli e il contenuto basandosi sulla coerenza
    tra le coppie domanda–risposta raccolte. L'output deve essere in formato JSON, per esempio:
    [
      {"title": "Titolo1", "content": "Contenuto1"},
      {"title": "Titolo2", "content": "Contenuto2"}
    ]
    Il sistema presenterà i documenti generati per revisione. Se accettati, li salverà nei file permanenti.
    Alla fine, chiederà se si vogliono pulire le cartelle temporanee.
    """
    import json
    new_tree = "new_tree"
    if not os.path.exists(new_tree):
        os.makedirs(new_tree)
    
    file_name = f"{chosen_topic.replace(' ', '_')}.md"
    from config import TEMP_INFORMATION_DIR, INFORMATION_DIR
    temp_file_path = os.path.join(TEMP_INFORMATION_DIR, file_name)
    if not os.path.exists(temp_file_path):
        print("Nessuna nuova informazione trovata per questo topic.")
        return
    
    with open(temp_file_path, "r", encoding="utf-8") as f:
        qa_content = f.read()
    
    # Filtriamo le coppie domanda-risposta rimuovendo quelle irrilevanti o saltate
    cleaned_qa_pairs = []
    qa_pairs = qa_content.split("\n\n")
    
    # Ogni coppia dovrebbe avere il formato "Domanda: X\n\nRisposta: Y"
    for i in range(0, len(qa_pairs), 2):
        if i+1 < len(qa_pairs):
            question = qa_pairs[i]
            answer = qa_pairs[i+1]
            
            # Verifico se la risposta è stata segnalata come irrilevante o è stata saltata
            if "[DOMANDA NON PERTINENTE]" in answer or "[SKIPPED]" in answer or "[CAMBIO TOPIC" in answer:
                print(f"Ignorata coppia domanda-risposta irrilevante o saltata: {question}")
                continue
            
            # Verifico anche se la risposta contiene testo che indica irrilevanza
            answer_text = answer.lower() if isinstance(answer, str) else ""
            if "irrilevante" in answer_text or "non pertinente" in answer_text or "troppo ampia" in answer_text:
                print(f"Ignorata coppia domanda-risposta con feedback di irrilevanza: {question}")
                continue
                
            cleaned_qa_pairs.append(question)
            cleaned_qa_pairs.append(answer)
    
    # Ricostruisco il contenuto con solo le coppie valide
    cleaned_qa_content = "\n\n".join(cleaned_qa_pairs)
    
    if not cleaned_qa_content.strip():
        print("Nessuna informazione valida da elaborare dopo la pulizia delle risposte irrilevanti.")
        return
    
    print("Utilizzando le seguenti coppie domanda-risposta per generare documenti:")
    print(cleaned_qa_content)
    
    merge_prompt = (
        f"Ho raccolto le seguenti coppie domanda–risposta per il topic '{chosen_topic}':\n\n"
        f"{cleaned_qa_content}\n\n"
        "Organizza queste informazioni in uno o più documenti finali, basandoti SOLO sulle informazioni fornite. "
        "Per ciascun documento, genera un titolo sintetico (max 4 parole) e il relativo contenuto. "
        "\n\nIMPORTANTE: NON descrivere la conversazione! NON usare frasi come 'L'utente ha risposto...' o 'L'utente chiede...'. "
        "Scrivi DIRETTAMENTE le informazioni in prima persona, come se fossero scritte dall'utente. "
        "Riformula le risposte in modo che siano comprensibili anche senza conoscere le domande. "
        "\n\nESEMPIO di riformulazione corretta:\n"
        "Domanda: 'Quali sono le tue aree di specializzazione?'\n"
        "Risposta: 'NLP, GenAI'\n"
        "Riformulazione corretta: 'Sono specializzato in Natural Language Processing (NLP) e Intelligenza Artificiale Generativa (GenAI).'\n\n"
        "Riformulazione ERRATA: 'L'utente indica che le sue aree di specializzazione sono NLP e GenAI.'\n\n"
        "\n\nREGOLE CRITICHE:\n"
        "1. NON AGGIUNGERE INFORMAZIONI che l'utente non ha fornito\n"
        "2. NON INVENTARE contenuti anche se sembrano logicamente collegati\n"
        "3. NON RIEMPIRE LACUNE o COLLEGAMENTI tra le informazioni\n"
        "4. INCLUDI SOLO informazioni che appaiono esplicitamente nelle risposte\n"
        "5. Se hai dubbi su un'informazione, NON includerla\n\n"
        "Produci l'output in formato JSON, ad esempio:\n"
        "[{\"title\": \"Titolo1\", \"content\": \"Sono specializzato in...\"}]\n"
    )
    print("Chiamata LLM per consolidare le informazioni (raggruppamento in documenti finali)...")
    consolidated_output = timed_generate_text(merge_prompt, "consolidate QA to JSON")
    print("LLM ha restituito il seguente output JSON:")
    print(consolidated_output)
    
    try:
        # Pulisco l'output da eventuali delimitatori Markdown e problemi di formato
        json_text = consolidated_output
        
        # Debug
        print("\nJSON originale ricevuto:")
        print(json_text)
        
        # Metodo 1: Se il testo contiene ```json, estrai il contenuto
        if "```json" in json_text:
            # Prendo il testo dopo ```json
            json_text = json_text.split("```json", 1)[1]
            # E prima del prossimo ```
            if "```" in json_text:
                json_text = json_text.split("```", 1)[0].strip()
        # Metodo 2: Se il testo contiene solo ```, estrai il contenuto del primo blocco di codice
        elif "```" in json_text:
            parts = json_text.split("```")
            if len(parts) >= 3:  # almeno un blocco di codice completo
                json_text = parts[1].strip()
        
        # Pulizia addizionale per rimuovere testo prima o dopo il JSON
        start_bracket = json_text.find("[")
        end_bracket = json_text.rfind("]")
        if start_bracket != -1 and end_bracket != -1:
            json_text = json_text[start_bracket:end_bracket+1]
        
        # Debug
        print("\nJSON dopo la pulizia:")
        print(json_text)
        
        # Eseguo il parsing del JSON
        docs = json.loads(json_text)
        print(f"Documenti rilevati: {len(docs)}")
        
        # Verifica che i documenti non contengano descrizioni in terza persona
        for doc in docs:
            content = doc.get("content", "")
            if "l'utente" in content.lower() or "l'intervistato" in content.lower():
                print("ATTENZIONE: Rilevate descrizioni in terza persona. Correggo...")
                # Rigenerazione con enfasi maggiore sulla prima persona
                doc["content"] = fix_third_person_content(content, chosen_topic)
        
    except Exception as e:
        print("Errore nel parsing del JSON generato dall'LLM:", e)
        print("Output ricevuto:", consolidated_output)
        return
    
    for doc in docs:
        title = doc.get("title", f"{chosen_topic.replace(' ', '_')}_consolidato").replace(" ", "_")
        content = doc.get("content", "")
        new_file_path = os.path.join(new_tree, f"{title}.md")
        with open(new_file_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"title: {title}\n")
            f.write(f"date: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            f.write("---\n\n")
            f.write(content)
        print(f"\nDocumento consolidato creato: {new_file_path}")
        user_confirm = input(f"Digita 'OK' per aggiornare il file permanente per '{title}', oppure altro per saltare: ").strip()
        if user_confirm.lower() == "ok":
            # Salvo i documenti consolidati nella cartella 'informazioni'
            permanent_file_path = os.path.join(INFORMATION_DIR, f"{title}.md")
            os.makedirs(os.path.dirname(permanent_file_path), exist_ok=True)
            shutil.copy(new_file_path, permanent_file_path)
            print(f"Il file permanente per '{title}' è stato aggiornato in: {permanent_file_path}")
        else:
            print(f"Aggiornamento per '{title}' annullato.")
    
    # Dopo aver completato la revisione, chiedi se pulire le cartelle temporanee
    clean_confirm = input("\nVuoi pulire le cartelle temporanee 'new_tree' e 'temp_session'? (s/N): ").strip()
    if clean_confirm.lower() == 's':
        # Pulisci le cartelle temporanee
        folders_to_clean = ["new_tree", "temp_session"]
        
        for folder in folders_to_clean:
            if os.path.exists(folder):
                print(f"Pulizia della cartella '{folder}'...")
                try:
                    # Rimuove tutti i contenuti della cartella
                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as e:
                            print(f"Errore durante la rimozione di {file_path}: {e}")
                    print(f"Cartella '{folder}' pulita con successo.")
                except Exception as e:
                    print(f"Errore durante la pulizia della cartella '{folder}': {e}")
            else:
                print(f"La cartella '{folder}' non esiste.")
        
        print("Pulizia completata.")
    else:
        print("Le cartelle temporanee non sono state pulite.")

def fix_third_person_content(content, topic):
    """
    Corregge il contenuto scritto in terza persona trasformandolo in prima persona.
    """
    prompt = f"""
    Riscrivi il seguente testo in prima persona, eliminando tutte le riferimenti all'utente in terza persona.
    
    Testo originale:
    {content}
    
    Esempio di trasformazione:
    "L'utente indica che le sue aree di specializzazione sono NLP e GenAI" -> "Sono specializzato in NLP e GenAI"
    "L'intervistato ha risposto che lavora come sviluppatore" -> "Lavoro come sviluppatore"
    
    Riscrivi il testo completo in modo da sembrare scritto direttamente dalla persona, NON menzionare mai "l'utente" o "l'intervistato".
    Mantieni tutte le informazioni ma cambia solo la forma. Il testo deve essere fluido e naturale.
    """
    
    corrected = timed_generate_text(prompt, "correzione prima persona")
    return corrected

def interpret_meta_response(answer, current_topic, current_question):
    """
    Analizza la risposta dell'utente per determinare se è una risposta diretta
    alla domanda o una meta-risposta (istruzioni, feedback, richieste di cambio topic).
    
    Restituisce un dizionario con:
    - 'type': il tipo di risposta ('DIRECT', 'CHANGE_TOPIC', 'SUGGEST_QUESTION', 'IRRELEVANT', 'HELP')
    - 'content': contenuto aggiuntivo rilevante per il tipo (es. nuovo topic, suggerimento di domanda)
    - 'message': messaggio da mostrare all'utente
    """
    prompt = f"""
    Analizza la seguente risposta dell'utente alla domanda "{current_question}" sul topic "{current_topic}".
    
    Determina se la risposta è:
    1. Una risposta diretta alla domanda (la normale risposta che fornisce l'informazione richiesta)
    2. Una richiesta di cambio topic (es. "parliamo di altro", "cambiamo argomento a X")
    3. Un suggerimento su cosa chiedere (es. "dovresti chiedermi X", "chiedimi di Y")
    4. Un'indicazione che la domanda non è pertinente (es. "questa domanda non c'entra", "non è rilevante")
    5. Una richiesta di spiegazioni o aiuto (solo richieste esplicite come "aiuto", "help", "come funziona")
    
    IMPORTANTE: La maggior parte delle risposte sono DIRECT (risposte dirette). Risposte come "migliorare, essere felice" 
    o "non lo so", "forse", "dipende", "non ci ho pensato", "ho vari obiettivi", sono tutte risposte dirette.
    
    Classifica come HELP solo quando l'utente chiede esplicitamente aiuto o spiegazioni sul funzionamento.
    Classifica come IRRELEVANT solo quando l'utente indica chiaramente che la domanda non è pertinente.
    
    Restituisci solo un oggetto JSON nel seguente formato:
    {{
      "type": "DIRECT" o "CHANGE_TOPIC" o "SUGGEST_QUESTION" o "IRRELEVANT" o "HELP",
      "content": "eventuale nuovo topic/domanda suggerita/etc.",
      "reason": "breve spiegazione del perché hai classificato così"
    }}
    
    Se è una richiesta di cambio topic, estrai il nuovo topic. Se è un suggerimento di domanda, estrai la domanda suggerita.
    """
    
    # Gestione diretta dei comandi espliciti di aiuto
    if answer.strip().lower() in ["aiuto", "help", "?"]:
        return {
            "type": "HELP",
            "content": answer,
            "message": "Ti spiegherò meglio come funziona l'intervista."
        }
    
    # Usiamo sempre l'LLM per analizzare la risposta, indipendentemente dalla lunghezza
    interpretation = timed_generate_text(prompt + "\nRisposta utente: " + answer, "interpretazione risposta")
    
    # Cerco di estrarre il JSON
    try:
        # Estrazione del JSON dalla risposta
        json_text = interpretation
        
        # Se il testo contiene ```json, estrai il contenuto
        if "```json" in json_text:
            json_text = json_text.split("```json", 1)[1]
            if "```" in json_text:
                json_text = json_text.split("```", 1)[0].strip()
        # Altrimenti se contiene solo ```, estrai il contenuto del primo blocco
        elif "```" in json_text:
            parts = json_text.split("```")
            if len(parts) >= 3:
                json_text = parts[1].strip()
        
        # Pulizia per rimuovere testo prima o dopo il JSON
        start_bracket = json_text.find("{")
        end_bracket = json_text.rfind("}")
        if start_bracket != -1 and end_bracket != -1:
            json_text = json_text[start_bracket:end_bracket+1]
        
        result = json.loads(json_text)
        
        # Debug output per verificare il tipo rilevato
        print(f"DEBUG - Tipo di risposta rilevato: {result['type']}")
        if 'reason' in result:
            print(f"DEBUG - Motivazione: {result['reason']}")
        
        # Verifica euristica aggiuntiva - se la risposta non contiene parole chiave di meta-risposte,
        # ma viene classificata come non diretta, la riclassifichiamo come diretta
        if result["type"] != "DIRECT":
            user_answer_lower = answer.strip().lower()
            
            # Liste di parole chiave per ciascun tipo di meta-risposta
            help_keywords = ["aiuto", "help", "come funziona", "spiegami", "non capisco", "?"]
            change_topic_keywords = ["cambia", "cambiamo", "parliamo di", "altro argomento", "altro topic"]
            irrelevant_keywords = ["non c'entra", "non centra", "irrilevante", "non pertinente", "fuori tema"]
            suggest_keywords = ["chiedi", "dovresti chiedere", "domandami", "chiedimi", "perché non mi chiedi"]
            
            # Se non ci sono parole chiave ma è classificata come meta-risposta, trattiamola come diretta
            is_help = any(keyword in user_answer_lower for keyword in help_keywords)
            is_change = any(keyword in user_answer_lower for keyword in change_topic_keywords)
            is_irrelevant = any(keyword in user_answer_lower for keyword in irrelevant_keywords)
            is_suggest = any(keyword in user_answer_lower for keyword in suggest_keywords)
            
            # Se non contiene nessuna parola chiave ma è classificata come meta-risposta, correggiamo
            if not (is_help or is_change or is_irrelevant or is_suggest):
                print("DEBUG - Correzione automatica: riclassificazione come DIRECT")
                result["type"] = "DIRECT"
                result["content"] = answer
                result["message"] = "Risposta registrata (correzione automatica)."
        
        # Genero il messaggio in base al tipo rilevato
        if result["type"] == "DIRECT":
            result["message"] = "Risposta registrata."
            result["content"] = answer
        elif result["type"] == "CHANGE_TOPIC":
            result["message"] = f"Cambio topic a '{result['content']}'."
        elif result["type"] == "SUGGEST_QUESTION":
            result["message"] = f"Seguendo il tuo suggerimento di domanda."
        elif result["type"] == "IRRELEVANT":
            result["message"] = "La domanda precedente verrà ignorata. Genererò una domanda più pertinente."
        elif result["type"] == "HELP":
            result["message"] = "Ti spiegherò meglio come funziona l'intervista."
            result["content"] = answer
        
        return result
        
    except Exception as e:
        # In caso di errore, trattiamo come risposta diretta
        print(f"Errore nell'interpretazione della risposta: {e}")
        return {
            "type": "DIRECT",
            "content": answer,
            "message": "Risposta registrata (fallback per errore di interpretazione)."
        }

def change_topic(new_topic, suggestions, conversation_history):
    """
    Gestisce il cambio di topic durante l'intervista.
    
    Args:
        new_topic: Il nuovo topic richiesto dall'utente
        suggestions: Lista dei topic suggeriti/disponibili
        conversation_history: Cronologia della conversazione attuale
    
    Returns:
        tuple: (topic_valido, nuova_domanda, messaggio)
    """
    # Verifico se il nuovo topic è nella lista dei suggeriti o è un custom
    valid_topic = new_topic
    found = False
    
    # Controllo se il topic è tra quelli suggeriti (ignorando case)
    for topic in suggestions:
        if topic.lower() == new_topic.lower():
            valid_topic = topic  # Uso il caso corretto dal sistema
            found = True
            break
    
    # Se non ho trovato corrispondenze esatte, chiedo all'LLM di verificare somiglianze
    if not found:
        prompt = f"L'utente vuole cambiare topic a '{new_topic}'. Tra i seguenti topic disponibili: {', '.join(suggestions)}, quale è il più simile? Se non c'è nessuna corrispondenza, rispondi 'CUSTOM'."
        response = timed_generate_text(prompt, "verifica topic simile")
        if any(topic.lower() in response.lower() for topic in suggestions):
            for topic in suggestions:
                if topic.lower() in response.lower():
                    valid_topic = topic
                    found = True
                    break
    
    # Genero una domanda appropriata per il nuovo topic
    prompt_domanda = build_dynamic_prompt(chosen_topic=valid_topic, conversation_history="")
    new_question = timed_generate_text(prompt_domanda, "prima domanda nuovo topic")
    
    if found:
        message = f"Topic cambiato a '{valid_topic}'. Iniziamo con una nuova domanda."
    else:
        message = f"Ho creato un nuovo topic personalizzato: '{valid_topic}'. Iniziamo con una nuova domanda."
    
    return valid_topic, new_question, message

def generate_suggested_question(suggested_question, current_topic, conversation_history):
    """
    Genera una domanda basata sul suggerimento dell'utente.
    
    Args:
        suggested_question: Il suggerimento o l'idea di domanda proposta dall'utente
        current_topic: Il topic corrente
        conversation_history: Cronologia della conversazione
    
    Returns:
        str: La domanda generata
    """
    prompt = f"""
    L'utente ha suggerito di chiedergli: "{suggested_question}".
    
    Formula una domanda breve, diretta e in italiano che catturi l'essenza di questo suggerimento, 
    mantenendola pertinente al topic '{current_topic}'.
    
    Rispondi SOLO con la domanda formulata, niente altro.
    """
    
    question = timed_generate_text(prompt, "genera domanda suggerita")
    
    # Filtro di sicurezza
    if len(question) > 150 or "**" in question or "# " in question:
        question = timed_generate_text(
            f"Genera UNA SOLA domanda BREVE in italiano basata su questo suggerimento: '{suggested_question}'.",
            "riforma domanda suggerita"
        )
    
    return question

def generate_more_relevant_question(current_topic, conversation_history):
    """
    Genera una domanda più pertinente quando l'utente indica che la domanda corrente non è rilevante.
    
    Args:
        current_topic: Il topic corrente
        conversation_history: Cronologia della conversazione
        
    Returns:
        str: Una nuova domanda più pertinente
    """
    prompt = f"""
    L'utente ha indicato che la tua ultima domanda non era pertinente al topic '{current_topic}'.
    
    Genera una NUOVA domanda più focalizzata e rilevante per questo topic, tenendo conto della 
    conversazione precedente.
    
    Contesto della conversazione:
    {conversation_history}
    
    Rispondi SOLO con la nuova domanda, niente altro.
    """
    
    new_question = timed_generate_text(prompt, "domanda più pertinente")
    
    # Filtro di sicurezza
    if len(new_question) > 150 or "**" in new_question or "# " in new_question:
        new_question = timed_generate_text(
            f"Genera UNA SOLA domanda BREVE in italiano sul topic '{current_topic}', assicurandoti che sia veramente pertinente.",
            "riforma domanda pertinente"
        )
    
    return new_question

def provide_help_info():
    """
    Fornisce informazioni di aiuto all'utente su come funziona l'intervista.
    
    Returns:
        str: Messaggio informativo per l'utente
    """
    help_text = """
    Come funziona l'intervista:
    
    1. Puoi rispondere normalmente alle domande per fornire informazioni.
    2. Puoi digitare 'skip' per saltare una domanda.
    3. Puoi digitare 'fine' o 'exit' per terminare l'intervista.
    
    Puoi anche:
    - Chiedere di cambiare topic (es. "Cambiamo topic a lavoro")
    - Suggerire domande (es. "Dovresti chiedermi dei miei hobby")
    - Indicare che una domanda non è pertinente (es. "Questa domanda non c'entra con l'argomento")
    - Chiedere aiuto digitando "aiuto" o "help"
    
    Tutte le informazioni che fornisci verranno organizzate in documenti che potrai rivedere alla fine.
    """
    return help_text

def similarity_score(question, previous_questions):
    """
    Calcola un punteggio di similarità tra una domanda e un elenco di domande precedenti.
    Restituisce il punteggio più alto di similarità trovato.
    """
    if not previous_questions:
        return 0
    
    # Versione semplificata che conta le parole in comune
    question_words = set(question.lower().strip().split())
    
    highest_score = 0
    for prev_q in previous_questions:
        prev_words = set(prev_q.lower().strip().split())
        
        if not question_words or not prev_words:
            continue
            
        intersection = question_words.intersection(prev_words)
        score = len(intersection) / min(len(question_words), len(prev_words))
        
        if score > highest_score:
            highest_score = score
    
    return highest_score

if __name__ == '__main__':
    start_interview()

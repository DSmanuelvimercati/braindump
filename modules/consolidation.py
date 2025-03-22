import os
import json
import shutil
from modules.llm_handler import timed_generate_text
from config import INFORMATION_DIR, TEMP_INFORMATION_DIR

def finalize_session(chosen_topic):
    """
    Finalizza la sessione di intervista, consolidando le informazioni raccolte.
    
    Args:
        chosen_topic (str): Il topic trattato durante l'intervista
        
    Returns:
        None
    """
    print("Intervista terminata.")
    
    # Verifica se ci sono informazioni nella cartella temporanea
    temp_topic_dir = os.path.join(TEMP_INFORMATION_DIR, chosen_topic.lower())
    if not os.path.exists(temp_topic_dir):
        print(f"Nessuna informazione salvata per il topic '{chosen_topic}'.")
        return
    
    # Legge il contenuto delle risposte salvate temporaneamente
    qa_pairs = []
    for filename in os.listdir(temp_topic_dir):
        if filename.endswith(".md"):
            file_path = os.path.join(temp_topic_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                qa_pairs.append(content)
    
    if not qa_pairs:
        print(f"Nessuna informazione salvata per il topic '{chosen_topic}'.")
        return
    
    print(f"Chiamata LLM per consolidare le informazioni (raggruppamento in documenti finali)...")
    documents = consolidate_qa_to_documents(qa_pairs, chosen_topic)
    
    # Salvataggio dei documenti consolidati
    save_consolidated_documents(documents)

def consolidate_qa_to_documents(qa_pairs, topic):
    """
    Consolida le coppie domanda-risposta in documenti strutturati.
    
    Args:
        qa_pairs (list): Lista di stringhe contenenti coppie domanda-risposta
        topic (str): Il topic trattato durante l'intervista
        
    Returns:
        list: Lista di dizionari con i documenti consolidati
    """
    prompt = f"""
    Consolida le seguenti informazioni in forma di documenti coerenti.
    Le informazioni sono state raccolte da un'intervista sul topic '{topic}'.
    
    INFORMAZIONI RACCOLTE:
    {os.linesep.join(qa_pairs)}
    
    Le informazioni devono essere:
    1. Riorganizzate in 2-5 documenti con titoli chiari
    2. Espresse in prima persona ("Io penso...", "Mi piace...", ecc.)
    3. Senza ripetizioni o contraddizioni
    4. Fluide e ben strutturate, non in formato domanda-risposta
    5. Senza aggiungere informazioni che non sono presenti nelle risposte originali
    
    Restituisci l'output come un JSON array di oggetti, ognuno con campi "title" e "content":
    [
        {
            "title": "Titolo del documento 1",
            "content": "Contenuto coerente e ben strutturato..."
        },
        {
            "title": "Titolo del documento 2",
            "content": "Contenuto coerente e ben strutturato..."
        }
    ]
    """
    
    response = timed_generate_text(prompt, "consolidate QA to JSON")
    
    try:
        # Cerca il testo JSON nella risposta
        import re
        json_match = re.search(r'\[\s*{.*}\s*\]', response, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            documents = json.loads(json_text)
            print(f"LLM ha restituito il seguente output JSON:\n```json\n{json.dumps(documents, indent=2, ensure_ascii=False)}\n```")
            
            # Stampa le versioni originali e pulite
            print(f"JSON originale ricevuto:\n```json\n{json.dumps(documents, indent=2, ensure_ascii=False)}\n```")
            
            # Pulizia dei documenti
            for doc in documents:
                doc["content"] = fix_third_person_content(doc["content"], topic)
            
            print(f"JSON dopo la pulizia:\n{json.dumps(documents, indent=2, ensure_ascii=False)}")
            
            return documents
        else:
            print("Nessun JSON valido trovato nella risposta dell'LLM.")
            print(f"Risposta ricevuta: {response}")
            return []
    except Exception as e:
        print(f"Errore nell'analisi JSON: {e}")
        print(f"Risposta ricevuta: {response}")
        return []

def fix_third_person_content(content, topic):
    """
    Corregge il contenuto se formulato in terza persona.
    
    Args:
        content (str): Il contenuto da verificare
        topic (str): Il topic trattato durante l'intervista
        
    Returns:
        str: Il contenuto corretto in prima persona
    """
    # Verificare se il contenuto è già in prima persona
    first_person_indicators = ["io ", "mi ", "mio ", "mia ", "miei ", "mie ", "sono ", "ho ", "penso ", "credo "]
    for indicator in first_person_indicators:
        if indicator in content.lower():
            return content
    
    # Se il contenuto non è in prima persona, lo correggiamo
    prompt = f"""
    Riformula il seguente testo in prima persona, come se fosse l'utente stesso a parlare.
    Mantieni ESATTAMENTE le stesse informazioni, non aggiungere o rimuovere nulla.
    Usa "io", "mi", "mio", ecc. invece di "l'utente", "lui/lei", ecc.
    
    TESTO DA RIFORMULARE:
    {content}
    """
    
    response = timed_generate_text(prompt, "fix third person")
    return response.strip()

def save_consolidated_documents(documents):
    """
    Salva i documenti consolidati in una nuova cartella.
    
    Args:
        documents (list): Lista di dizionari con titoli e contenuti
        
    Returns:
        None
    """
    # Crea directory per i nuovi documenti se non esiste
    new_tree_dir = "new_tree"
    if not os.path.exists(new_tree_dir):
        os.makedirs(new_tree_dir)
    
    print(f"Documenti rilevati: {len(documents)}")
    
    # Per ogni documento consolidato
    for doc in documents:
        title = doc["title"]
        content = doc["content"]
        
        # Crea un nome file valido dal titolo
        filename = title.replace(" ", "_").replace("/", "_").replace("\\", "_")
        filename = ''.join(c for c in filename if c.isalnum() or c == '_')
        filepath = os.path.join(new_tree_dir, f"{filename}.md")
        
        # Scrive il contenuto nel file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Documento consolidato creato: {filepath}")
        
        # Chiedi conferma per sostituire il file permanente
        permanent_dir = INFORMATION_DIR
        if not os.path.exists(permanent_dir):
            os.makedirs(permanent_dir)
        
        permanent_path = os.path.join(permanent_dir, f"{filename}.md")
        user_input = input(f"Digita 'OK' per aggiornare il file permanente per '{filename}', oppure altro per saltare: ")
        
        if user_input.strip().upper() == "OK":
            shutil.copy(filepath, permanent_path)
            print(f"Il file permanente per '{filename}' è stato aggiornato in: {permanent_path}")
        else:
            print(f"Aggiornamento per '{filename}' annullato.")
    
    # Chiedi se pulire le cartelle temporanee
    user_input = input("Vuoi pulire le cartelle temporanee 'new_tree' e 'temp_session'? (s/N): ")
    if user_input.strip().lower() == "s":
        cleanup_temp_folders()

def cleanup_temp_folders():
    """
    Pulisce le cartelle temporanee del sistema.
    
    Returns:
        None
    """
    # Pulisci la cartella new_tree
    try:
        new_tree_dir = "new_tree"
        print(f"Pulizia della cartella '{new_tree_dir}'...")
        if os.path.exists(new_tree_dir):
            for item in os.listdir(new_tree_dir):
                item_path = os.path.join(new_tree_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            print(f"Cartella '{new_tree_dir}' pulita con successo.")
        else:
            print(f"La cartella '{new_tree_dir}' non esiste.")
    except Exception as e:
        print(f"Errore durante la pulizia di '{new_tree_dir}': {e}")
    
    # Pulisci la cartella temp_session
    try:
        temp_dir = "temp_session"
        print(f"Pulizia della cartella '{temp_dir}'...")
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            print(f"Cartella '{temp_dir}' pulita con successo.")
        else:
            print(f"La cartella '{temp_dir}' non esiste.")
    except Exception as e:
        print(f"Errore durante la pulizia di '{temp_dir}': {e}")
    
    print("Pulizia completata.") 
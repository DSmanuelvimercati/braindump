import os
import shutil
import time
import json
from tqdm import tqdm
from modules.dynamic_prompt import build_dynamic_prompt, get_topic_suggestions
from modules.llm import generate_text
from modules.storage import save_braindump_entry
from config import INFORMATION_DIR, TEMP_INFORMATION_DIR, create_temp_folder

VERBOSE = False

def log(msg):
    if VERBOSE:
        print(msg)

def timed_generate_text(prompt, description=""):
    start_time = time.time()
    result = generate_text(prompt)
    duration = time.time() - start_time
    print(f"[{description}] LLM call took {duration:.2f} seconds")
    return result

def interpret_user_answer(answer):
    """
    Restituisce "NO_ANSWER" se l'utente scrive esattamente "skip" o è vuoto, altrimenti "VALID_ANSWER".
    """
    if answer.strip().lower() == "skip" or answer.strip() == "":
        return "NO_ANSWER"
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
    skip_question_prompt = (
        f"Genera una nuova domanda breve e concisa per il topic '{chosen_topic}' "
        "basandoti sul seguente contesto, evitando di ripetere domande già poste:\n\n"
        f"{conversation_history}\n\n"
        "Domanda:"
    )
    return timed_generate_text(skip_question_prompt, "new question after skip")

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
    print("Chiamata LLM per generare la prima domanda...")
    current_question = timed_generate_text(build_dynamic_prompt(chosen_topic=chosen_topic, conversation_history=conversation_history), "prima domanda")
    print(f"Domanda generata: {current_question.strip()}")
    
    last_question = current_question.strip().lower()
    while True:
        print("\nDomanda:", current_question)
        user_input = input("Risposta (digita 'fine' per terminare): ").strip()
        if user_input.lower() in ["fine", "exit"]:
            print("Intervista terminata.")
            break
        
        if interpret_user_answer(user_input) == "NO_ANSWER":
            print("Risposta ignorata (skip).")
            conversation_history += f"Domanda: {current_question}\n\nRisposta: [SKIPPED]\n\n"
            current_question = generate_new_question_after_skip(chosen_topic, conversation_history)
            while current_question.strip().lower() == last_question:
                current_question = generate_new_question_after_skip(chosen_topic, conversation_history)
            last_question = current_question.strip().lower()
            print(f"Domanda generata: {current_question.strip()}")
            continue
        
        pair_text = f"Domanda: {current_question}\n\nRisposta: {user_input}"
        print("Salvataggio delle informazioni temporanee...")
        info_file_path = save_braindump_entry(pair_text, chosen_topic)
        print(f"Informazioni salvate in: {info_file_path}")
        
        conversation_history += pair_text + "\n\n"
        new_question = timed_generate_text(build_dynamic_prompt(chosen_topic=chosen_topic, conversation_history=conversation_history), "nuova domanda con contesto")
        while new_question.strip().lower() == last_question:
            new_question = generate_new_question_after_skip(chosen_topic, conversation_history)
        current_question = new_question
        last_question = current_question.strip().lower()
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
    
    merge_prompt = (
        f"Ho raccolto le seguenti coppie domanda–risposta per il topic '{chosen_topic}':\n\n"
        f"{qa_content}\n\n"
        "Organizza queste informazioni in uno o più documenti finali, basandoti sulla coerenza tra le domande e le risposte. "
        "Per ciascun documento, genera un titolo sintetico (max 4 parole) e il relativo contenuto, "
        "in modo che il documento sia comprensibile anche senza conoscere l'intera sequenza delle domande. "
        "Produci l'output in formato JSON, ad esempio:\n"
        "[{\"title\": \"Titolo1\", \"content\": \"Contenuto1\"}, {\"title\": \"Titolo2\", \"content\": \"Contenuto2\"}]\n"
        "Non aggiungere informazioni extra."
    )
    print("Chiamata LLM per consolidare le informazioni (raggruppamento in documenti finali)...")
    consolidated_output = timed_generate_text(merge_prompt, "consolidate QA to JSON")
    print("LLM ha restituito il seguente output JSON:")
    print(consolidated_output)
    
    try:
        docs = json.loads(consolidated_output)
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
            permanent_file_path = os.path.join(INFORMATION_DIR, f"{title}.md")
            os.makedirs(os.path.dirname(permanent_file_path), exist_ok=True)
            shutil.copy(new_file_path, permanent_file_path)
            print(f"Il file permanente per '{title}' è stato aggiornato.")
        else:
            print(f"Aggiornamento per '{title}' annullato.")

if __name__ == '__main__':
    start_interview()

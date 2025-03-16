import os
import time
from config import TEMP_INFORMATION_DIR, TEMP_CONCEPTS_DIR

def save_braindump_entry(content, topic):
    """
    Salva (o aggiunge) una coppia domanda–risposta nel file Markdown relativo al topic,
    salvandolo nella cartella temporanea delle informazioni.
    """
    file_name = f"{topic.replace(' ', '_')}.md"
    file_path = os.path.join(TEMP_INFORMATION_DIR, file_name)
    
    if os.path.exists(file_path):
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + content)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"title: {topic}\n")
            f.write(f"date: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            f.write("---\n\n")
            f.write(content)
    
    return file_path

def update_summary(pair_text, topic, llm_function):
    """
    Estrae la domanda e la risposta dalla coppia domanda–risposta e usa il LLM per riformularle
    in un fatto sintetico ed esaustivo. Il sommario deve includere le informazioni chiave della domanda
    e della risposta, in modo che risulti comprensibile anche senza conoscere la sequenza completa.
    
    Esempio:
      - Domanda: "Qual è il tuo obiettivo principale?"
      - Risposta: "Voglio essere felice."
      - Sommario desiderato: "L'utente afferma che il suo obiettivo principale è essere felice."
      
    Il prompt non deve aggiungere informazioni non presenti nella coppia.
    """
    # Estrai la domanda e la risposta separatamente
    parts = pair_text.split("Risposta:")
    if len(parts) < 2:
        question_text = pair_text.strip()
        answer_text = ""
    else:
        question_text = parts[0].replace("Domanda:", "").strip()
        answer_text = parts[1].strip()
    
    summary_prompt = (
        "Riformula la seguente coppia domanda–risposta in un fatto sintetico ed esaustivo, includendo le parole chiave "
        "della domanda per dare contesto e la risposta dell'utente. Non aggiungere informazioni non presenti.\n\n"
        "Esempio:\n"
        "Domanda: 'Qual è il tuo obiettivo principale?'\n"
        "Risposta: 'Voglio essere felice.'\n"
        "Sommario: 'L'utente afferma che il suo obiettivo principale è essere felice.'\n\n"
        "Ora, riformula la seguente coppia:\n\n"
        f"Domanda: {question_text}\n"
        f"Risposta: {answer_text}\n\n"
        "Sommario:"
    )
    
    summary = llm_function(summary_prompt)
    file_name = f"{topic.replace(' ', '_')}_sommario.md"
    from config import TEMP_CONCEPTS_DIR
    file_path = os.path.join(TEMP_CONCEPTS_DIR, file_name)
    
    if os.path.exists(file_path):
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + summary)
    else:
        import time
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"title: Sommario - {topic}\n")
            f.write(f"date: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            f.write("---\n\n")
            f.write(summary)
    return file_path

from modules.processor import identify_gaps, generate_question
from modules.dashboard import display_dashboard
from modules.storage import save_package
from modules.dynamic_prompt import determine_next_question  # Importa la funzione dal nuovo file
from modules.llm import generate_text

from modules.llm import generate_text
from modules.storage import save_package
from modules.dashboard import display_dashboard
from modules.dynamic_prompt import determine_next_question

def start_interview():
    print("Intervista iniziata. Rispondi alle domande che ti verranno poste.")
    print("Digita 'fine', 'interrompi' o 'exit' per terminare l'intervista.")
    
    # Domanda iniziale di default, se non ci sono dati ancora
    current_question = "Raccontami qualcosa su di te. Qual è la tua esperienza professionale?"
    
    while True:
        print("\nAgente:", current_question)
        user_answer = input("Tu: ")
        
        if user_answer.lower() in ["fine", "interrompi", "exit"]:
            print("Intervista terminata.")
            break
        
        # Crea il pacchetto temporaneo con la domanda corrente e la risposta fornita
        package = {
            'gap': "N/A",  # Puoi aggiornare questo campo se implementi un'analisi del gap
            'question': current_question,
            'answer': user_answer,
            'status': ''  # Stato da definire in base alla scelta
        }
        
        # Visualizza il pacchetto per la revisione
        print("\nPacchetto:")
        print("  Domanda:", package['question'])
        print("  Risposta:", package['answer'])
        
        decision = input("Accetta (a) o Rigetta (r)? ")
        if decision.lower() == 'a':
            package['status'] = 'accettato'
            display_dashboard([package])
            if not save_package(package):
                print("Errore nel salvataggio del pacchetto.")
        else:
            package['status'] = 'rigettato'
            print("Pacchetto rigettato, non salvato.")
        
        # Genera la prossima domanda in base al contesto attuale del braindump
        dynamic_prompt = determine_next_question()
        next_question = generate_text(dynamic_prompt, max_new_tokens=100, temperature=0.7, top_p=0.95)
        
        # Aggiorna current_question per il prossimo turno
        current_question = next_question


def start_chat():
    print("Chat inizializzata. Scrivi 'exit' per terminare.")
    print("Comandi aggiuntivi: 'analizza', 'backup', 'grafo', 'intervista'")
    
    while True:
        user_input = input("Tu: ")
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == "backup":
            from modules.backup import backup_data
            backup_data()
            print("Backup eseguito.")
        elif user_input.lower() == "grafo":
            from modules.graph import build_graph_from_data
            G = build_graph_from_data()
            print(f"Grafo creato: {len(G.nodes())} nodi, {len(G.edges())} archi.")
        elif user_input.lower() == "intervista":
            start_interview()
        else:
            response = generate_response(user_input)
            print("Agente:", response)


def generate_response(user_input):
    if user_input.lower() == 'analizza':
        # Utilizza un testo di esempio o il contenuto da analizzare
        dummy_text = "Questo è un esempio di testo da analizzare per identificare lacune informative."
        gap = identify_gaps(dummy_text)
        question = generate_question(gap)
        answer = "Risposta generata in base alla domanda."  # Placeholder o generazione avanzata
        package = {
            'gap': gap,
            'question': question,
            'answer': answer,
            'status': 'accettato'  # Per ora assumiamo l'accettazione per semplificare
        }
        display_dashboard([package])
        save_package(package)
        return "Analisi completata, pacchetto salvato e dashboard visualizzata."
    else:
        from modules.llm import generate_text
        return generate_text(f"Rispondi in modo conciso: {user_input}")

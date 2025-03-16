from modules.processor import identify_gaps, generate_question
from modules.dashboard import display_dashboard

def start_chat():
    print("Chat inizializzata. Scrivi 'exit' per terminare.")
    while True:
        user_input = input("Tu: ")
        if user_input.lower() == 'exit':
            break
        response = generate_response(user_input)
        print("Agente:", response)

def generate_response(user_input):
    # Per esempio, se l'input dell'utente è "analizza", esegui l'analisi
    if user_input.lower() == 'analizza':
        # Esegui una simulazione di analisi
        dummy_text = "Questo è un esempio di testo da analizzare per lacune informative."
        gap = identify_gaps(dummy_text)
        question = generate_question(gap)
        answer = "Risposta placeholder per la domanda generata."
        package = {
            'gap': gap,
            'question': question,
            'answer': answer,
            'status': 'in attesa'
        }
        display_dashboard([package])
        return "Analisi completata, vedi dashboard."
    else:
        # Risposta generica per altri input
        return f"Risposta generata per: {user_input}"
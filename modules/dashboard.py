def display_dashboard(packages):
    """
    Mostra in console l'elenco dei pacchetti e permette all'utente di accettare o rigettare.
    """
    for idx, package in enumerate(packages, start=1):
        print(f"\nPacchetto {idx}:")
        print(f"  Lacuna: {package['gap']}")
        print(f"  Domanda: {package['question']}")
        print(f"  Risposta: {package['answer']}")
        decision = input("Accetta (a) o Rigetta (r)? ")
        if decision.lower() == 'a':
            package['status'] = 'accettato'
        else:
            package['status'] = 'rigettato'
        print(f"Stato: {package['status']}")

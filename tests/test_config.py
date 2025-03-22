"""
Configurazione per l'esecuzione dei test unitari.
Questo file contiene le impostazioni per decidere quali test eseguire
e mantiene uno storico dei tempi di esecuzione.
"""

import os
import json
from datetime import datetime

# Percorso del file di configurazione e dello storico dei tempi
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'test_config.json')
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'test_history.json')

# Impostazioni predefinite
DEFAULT_CONFIG = {
    # Se True, esegue tutti i test disponibili
    "run_all_tests": True,
    
    # Se run_all_tests è False, esegue solo i test in questa lista
    # Formato: "NomeClasse.nome_metodo_test"
    "tests_to_run": [],
    
    # Se True, esegue tutti i test della classe specificata
    # Formato: ["NomeClasse1", "NomeClasse2"]
    "test_classes": [],
    
    # Numero massimo di esecuzioni da salvare nello storico per ogni test
    "max_history_entries": 5,
    
    # Mostra la stima del tempo prima di eseguire i test
    "show_time_estimates": True,
    
    # Livello di verbosità per il logger (0=minimo, 1=normale, 2=dettagliato)
    "verbosity": 1
}


def load_config():
    """Carica la configurazione dal file o crea una configurazione predefinita."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Assicurati che tutte le chiavi necessarie esistano
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"Errore nel caricamento della configurazione: {e}")
            return DEFAULT_CONFIG
    else:
        # Crea il file di configurazione predefinito
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config):
    """Salva la configurazione nel file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Errore nel salvataggio della configurazione: {e}")


def load_history():
    """Carica lo storico dei tempi di esecuzione."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore nel caricamento dello storico: {e}")
            return {}
    else:
        return {}


def save_history(history):
    """Salva lo storico dei tempi di esecuzione."""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        print(f"Errore nel salvataggio dello storico: {e}")


def update_test_history(test_name, execution_time):
    """
    Aggiorna lo storico dei tempi di esecuzione per un test.
    
    Args:
        test_name (str): Nome del test (NomeClasse.nome_metodo_test)
        execution_time (float): Tempo di esecuzione in secondi
    """
    config = load_config()
    history = load_history()
    max_entries = config['max_history_entries']
    
    # Crea una nuova voce per questo test se non esiste
    if test_name not in history:
        history[test_name] = []
    
    # Aggiungi la nuova esecuzione con timestamp
    history[test_name].append({
        "time": execution_time,
        "timestamp": datetime.now().isoformat()
    })
    
    # Mantieni solo le ultime max_entries
    if len(history[test_name]) > max_entries:
        history[test_name] = history[test_name][-max_entries:]
    
    save_history(history)


def get_test_time_estimate(test_name):
    """
    Calcola una stima del tempo di esecuzione per un test basandosi sullo storico.
    
    Args:
        test_name (str): Nome del test (NomeClasse.nome_metodo_test)
    
    Returns:
        tuple: (tempo medio, tempo minimo, tempo massimo, numero di esecuzioni)
    """
    history = load_history()
    
    if test_name not in history or not history[test_name]:
        return None, None, None, 0
    
    times = [entry["time"] for entry in history[test_name]]
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    count = len(times)
    
    return avg_time, min_time, max_time, count


def should_run_test(test_name):
    """
    Determina se un test dovrebbe essere eseguito in base alla configurazione.
    
    Args:
        test_name (str): Nome del test (NomeClasse.nome_metodo_test)
    
    Returns:
        bool: True se il test deve essere eseguito, False altrimenti
    """
    config = load_config()
    
    # Se run_all_tests è True, esegui tutti i test
    if config["run_all_tests"]:
        return True
    
    # Controlla se il test è nella lista tests_to_run
    if test_name in config["tests_to_run"]:
        return True
    
    # Controlla se la classe del test è nella lista test_classes
    class_name = test_name.split('.')[0]
    if class_name in config["test_classes"]:
        return True
    
    return False


def get_total_time_estimate():
    """
    Calcola la stima del tempo totale per tutti i test che saranno eseguiti.
    
    Returns:
        float: Stima del tempo totale in secondi
    """
    history = load_history()
    config = load_config()
    total_time = 0
    
    for test_name in history:
        if should_run_test(test_name):
            avg_time, _, _, _ = get_test_time_estimate(test_name)
            if avg_time is not None:
                total_time += avg_time
    
    return total_time 
"""
Analisi dei tempi di esecuzione dei test.
Questo modulo fornisce strumenti per visualizzare e analizzare lo storico
dei tempi di esecuzione dei test.
"""

import os
import sys
import json
from datetime import datetime
import statistics
from colorama import init, Fore, Style
from tabulate import tabulate

# Aggiungo la directory principale al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importo le utility per la configurazione e il logging
from tests.test_config import load_history, load_config
from tests.test_logger import TestLogger

def print_execution_statistics():
    """
    Stampa statistiche dettagliate sui tempi di esecuzione.
    """
    history = load_history()
    if not history:
        TestLogger.warning("Nessuno storico dei tempi di esecuzione trovato.")
        return
    
    TestLogger.section("STATISTICHE DI ESECUZIONE DEI TEST")
    
    # Prepara i dati per la tabella
    rows = []
    for test_name, executions in history.items():
        if not executions:
            continue
        
        # Estrae i tempi di esecuzione
        times = [entry["time"] for entry in executions]
        
        # Calcola le statistiche
        avg_time = statistics.mean(times) if times else 0
        median_time = statistics.median(times) if times else 0
        min_time = min(times) if times else 0
        max_time = max(times) if times else 0
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        
        # Calcola la tendenza rispetto all'ultima esecuzione
        trend = ""
        if len(times) >= 2:
            last_time = times[-1]
            previous_time = times[-2]
            diff_percent = ((last_time - previous_time) / previous_time) * 100 if previous_time > 0 else 0
            
            if diff_percent > 10:
                trend = f"{Fore.RED}↑ {diff_percent:.1f}%{Style.RESET_ALL}"
            elif diff_percent < -10:
                trend = f"{Fore.GREEN}↓ {diff_percent:.1f}%{Style.RESET_ALL}"
            else:
                trend = f"{Fore.YELLOW}↔ {diff_percent:.1f}%{Style.RESET_ALL}"
        
        # Formatta il nome del test per maggiore leggibilità
        test_parts = test_name.split('.')
        short_name = f"{test_parts[-2]}.{test_parts[-1]}"
        
        rows.append([
            short_name,
            f"{avg_time:.3f}s",
            f"{median_time:.3f}s",
            f"{min_time:.3f}s",
            f"{max_time:.3f}s",
            f"{std_dev:.3f}s",
            len(times),
            trend
        ])
    
    # Ordina per tempo medio (dal più lento al più veloce)
    rows.sort(key=lambda x: float(x[1][:-1]), reverse=True)
    
    # Aggiungi le intestazioni della tabella
    headers = ["Test", "Media", "Mediana", "Min", "Max", "StdDev", "Esecuzioni", "Trend"]
    
    # Stampa la tabella
    TestLogger.info(tabulate(rows, headers=headers, tablefmt="grid"))
    
    # Totali
    total_tests = len(rows)
    total_avg_time = sum([float(row[1][:-1]) for row in rows])
    
    TestLogger.info(f"Totale test: {total_tests}")
    TestLogger.info(f"Tempo medio totale stimato: {total_avg_time:.3f}s")

def plot_test_history():
    """
    Visualizza un grafico dello storico dei tempi di esecuzione.
    Se matplotlib non è disponibile, stampa un messaggio di avviso.
    """
    try:
        import matplotlib.pyplot as plt
        
        history = load_history()
        if not history:
            TestLogger.warning("Nessuno storico dei tempi di esecuzione trovato.")
            return
        
        plt.figure(figsize=(12, 8))
        
        for test_name, executions in history.items():
            if not executions:
                continue
            
            # Estrae i tempi e i timestamp
            times = [entry["time"] for entry in executions]
            timestamps = [datetime.fromisoformat(entry["timestamp"]) for entry in executions]
            
            # Formatta il nome del test per maggiore leggibilità
            test_parts = test_name.split('.')
            short_name = f"{test_parts[-2]}.{test_parts[-1]}"
            
            # Aggiunge la serie al grafico
            plt.plot(timestamps, times, marker='o', label=short_name)
        
        plt.title("Storico dei tempi di esecuzione dei test")
        plt.xlabel("Data e ora")
        plt.ylabel("Tempo (secondi)")
        plt.grid(True)
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
        plt.tight_layout()
        
        # Salva il grafico
        output_file = os.path.join(os.path.dirname(__file__), 'test_history_plot.png')
        plt.savefig(output_file)
        TestLogger.info(f"Grafico salvato in: {output_file}")
        
        # Mostra il grafico (opzionale)
        plt.show()
    
    except ImportError:
        TestLogger.warning("Matplotlib non è installato. Non è possibile creare il grafico.")
        TestLogger.info("Installa matplotlib con 'pip install matplotlib' per utilizzare questa funzionalità.")

def identify_slowdowns():
    """
    Identifica i test che hanno subito un rallentamento significativo.
    """
    history = load_history()
    if not history:
        TestLogger.warning("Nessuno storico dei tempi di esecuzione trovato.")
        return
    
    slowdowns = []
    
    for test_name, executions in history.items():
        if len(executions) < 2:
            continue
        
        # Ordina le esecuzioni per timestamp
        sorted_executions = sorted(executions, key=lambda x: datetime.fromisoformat(x["timestamp"]))
        
        # Controlla se c'è stato un rallentamento negli ultimi due run
        last_time = sorted_executions[-1]["time"]
        prev_time = sorted_executions[-2]["time"]
        
        if last_time > prev_time * 1.2:  # Rallentamento del 20% o più
            diff_percent = ((last_time - prev_time) / prev_time) * 100
            
            # Formatta il nome del test per maggiore leggibilità
            test_parts = test_name.split('.')
            short_name = f"{test_parts[-2]}.{test_parts[-1]}"
            
            slowdowns.append((short_name, prev_time, last_time, diff_percent))
    
    if slowdowns:
        TestLogger.section("RALLENTAMENTI SIGNIFICATIVI")
        
        # Ordina per percentuale di rallentamento (dal maggiore al minore)
        slowdowns.sort(key=lambda x: x[3], reverse=True)
        
        for test_name, prev_time, last_time, diff_percent in slowdowns:
            TestLogger.warning(
                f"{test_name}: {prev_time:.3f}s → {last_time:.3f}s "
                f"({Fore.RED}+{diff_percent:.1f}%{Style.RESET_ALL})"
            )
    else:
        TestLogger.info("Nessun rallentamento significativo rilevato.")

if __name__ == "__main__":
    # Esegue l'analisi quando il file viene eseguito direttamente
    print_execution_statistics()
    identify_slowdowns()
    
    # Chiede se visualizzare il grafico
    response = input("Vuoi generare il grafico dei tempi? (s/n): ")
    if response.lower() in ['s', 'si', 'sì', 'y', 'yes']:
        plot_test_history() 
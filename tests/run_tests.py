import unittest
import time
import sys
import os
import importlib
import argparse
from colorama import init, Fore, Style

# Inizializzo colorama per i colori
init()

# Aggiungo la directory principale al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importo le utility per la configurazione e il logging
from tests.test_config import (
    load_config, save_config, load_history, update_test_history, 
    get_test_time_estimate, should_run_test, get_total_time_estimate
)
from tests.test_logger import TestLogger

class TestFilterResult(unittest.TextTestResult):
    """Risultato di test che esegue solo i test selezionati e misura i tempi."""
    
    def __init__(self, *args, **kwargs):
        super(TestFilterResult, self).__init__(*args, **kwargs)
        self.test_timings = {}
        self.skipped_tests = []
    
    def startTest(self, test):
        """Inizia a misurare il tempo del test."""
        test_name = test.id()
        
        # Verifica se il test deve essere eseguito
        if not should_run_test(test_name):
            self.skipped_tests.append(test_name)
            return
        
        # Ottieni la stima del tempo
        avg_time, min_time, max_time, count = get_test_time_estimate(test_name)
        
        # Registra l'inizio del test
        if avg_time is not None:
            TestLogger.test_start(test_name, avg_time)
        else:
            TestLogger.test_start(test_name)
        
        self._start_time = time.time()
        super(TestFilterResult, self).startTest(test)
    
    def stopTest(self, test):
        """Ferma la misurazione del tempo e salva il risultato."""
        test_name = test.id()
        
        # Salta i test che non devono essere eseguiti
        if test_name in self.skipped_tests:
            TestLogger.test_skipped(test_name, "Non selezionato nella configurazione")
            return
        
        elapsed_time = time.time() - self._start_time
        self.test_timings[test_name] = elapsed_time
        
        # Aggiorna lo storico dei tempi di esecuzione
        update_test_history(test_name, elapsed_time)
        
        super(TestFilterResult, self).stopTest(test)
    
    def addSuccess(self, test):
        """Registra un test completato con successo."""
        test_name = test.id()
        if test_name in self.test_timings:
            TestLogger.test_success(test_name, self.test_timings[test_name])
        super(TestFilterResult, self).addSuccess(test)
    
    def addError(self, test, err):
        """Registra un test fallito con errore."""
        test_name = test.id()
        if test_name in self.test_timings:
            error_message = self._exc_info_to_string(err, test)
            TestLogger.test_failure(test_name, self.test_timings[test_name], error_message)
        super(TestFilterResult, self).addError(test, err)
    
    def addFailure(self, test, err):
        """Registra un test fallito con assertion."""
        test_name = test.id()
        if test_name in self.test_timings:
            error_message = self._exc_info_to_string(err, test)
            TestLogger.test_failure(test_name, self.test_timings[test_name], error_message)
        super(TestFilterResult, self).addFailure(test, err)


class FilteredTestRunner(unittest.TextTestRunner):
    """Runner di test che esegue solo i test selezionati."""
    
    def __init__(self, *args, **kwargs):
        super(FilteredTestRunner, self).__init__(*args, **kwargs)
        self.resultclass = TestFilterResult
    
    def run(self, test):
        """Esegue i test e mostra i risultati."""
        TestLogger.section("AVVIO DEI TEST")
        
        # Stima il tempo totale
        total_estimated_time = get_total_time_estimate()
        if total_estimated_time > 0:
            TestLogger.info(f"Tempo totale stimato: {total_estimated_time:.2f} secondi")
        
        # Esegui i test
        start_time = time.time()
        result = super(FilteredTestRunner, self).run(test)
        total_time = time.time() - start_time
        
        # Mostra il riepilogo
        TestLogger.section("STATISTICHE SUI TEMPI DI ESECUZIONE")
        
        # Ordina i test per tempo di esecuzione (dal più lento al più veloce)
        sorted_times = sorted(result.test_timings.items(), key=lambda x: x[1], reverse=True)
        
        # Stampa tutti i tempi di esecuzione ordinati
        if sorted_times:
            total_measured_time = sum(elapsed for _, elapsed in sorted_times)
            for test_name, elapsed_time in sorted_times:
                # Colora in rosso i test che impiegano più di 1 secondo
                if elapsed_time > 1.0:
                    color = Fore.RED
                # Colora in giallo i test che impiegano più di 0.2 secondi
                elif elapsed_time > 0.2:
                    color = Fore.YELLOW
                # Colora in verde tutti gli altri
                else:
                    color = Fore.GREEN
                
                # Abbrevia il nome del test per una migliore visualizzazione
                test_parts = test_name.split('.')
                abbreviated_name = f"{test_parts[-2]}.{test_parts[-1]}"
                
                # Stampa la linea
                TestLogger.info(f"{color}{abbreviated_name:<50} {elapsed_time:.6f}s{Style.RESET_ALL}")
            
            TestLogger.section("RIEPILOGO")
            TestLogger.info(f"Tempo totale di esecuzione: {Fore.CYAN}{total_time:.6f}s{Style.RESET_ALL}")
            TestLogger.info(f"Media per test: {Fore.CYAN}{total_measured_time / len(sorted_times):.6f}s{Style.RESET_ALL}")
            
            # Test più lento e più veloce
            if len(sorted_times) > 0:
                slowest = sorted_times[0]
                TestLogger.info(f"Test più lento: {Fore.RED}{slowest[0].split('.')[-1]} ({slowest[1]:.6f}s){Style.RESET_ALL}")
            if len(sorted_times) > 1:
                fastest = sorted_times[-1]
                TestLogger.info(f"Test più veloce: {Fore.GREEN}{fastest[0].split('.')[-1]} ({fastest[1]:.6f}s){Style.RESET_ALL}")
        else:
            TestLogger.warning("Nessun test è stato eseguito.")
        
        return result


def discover_and_run_tests():
    """Scopre tutti i test e li esegue."""
    # Scopre tutti i test nella directory corrente
    start_dir = os.path.dirname(os.path.abspath(__file__))
    test_suite = unittest.defaultTestLoader.discover(start_dir, pattern="test_*.py")
    
    # Esegue i test con il runner personalizzato
    runner = FilteredTestRunner(verbosity=0)  # Ridotto perché usiamo il nostro logger
    return runner.run(test_suite)


def parse_arguments():
    """Analizza gli argomenti da riga di comando."""
    parser = argparse.ArgumentParser(description='Esegue i test unitari con configurazione e logging avanzati')
    
    # Opzioni per la configurazione
    parser.add_argument('--all', action='store_true', help='Esegue tutti i test disponibili')
    parser.add_argument('--test', action='append', help='Specifica un test da eseguire (formato: TestClass.test_method)')
    parser.add_argument('--class', dest='test_class', action='append', help='Esegue tutti i test di una classe specifica')
    parser.add_argument('--verbosity', type=int, choices=[0, 1, 2], help='Imposta il livello di verbosità (0=minimo, 1=normale, 2=dettagliato)')
    
    # Opzioni per il logging
    parser.add_argument('--no-estimates', action='store_true', help='Non mostrare le stime dei tempi di esecuzione')
    
    # Opzioni per salvare la configurazione
    parser.add_argument('--save-config', action='store_true', help='Salva la configurazione corrente come predefinita')
    
    return parser.parse_args()


def update_config_from_args(args):
    """Aggiorna la configurazione in base agli argomenti da riga di comando."""
    config = load_config()
    
    # Aggiorna le opzioni di configurazione
    if args.all:
        config['run_all_tests'] = True
    elif args.test or args.test_class:
        config['run_all_tests'] = False
        
        if args.test:
            config['tests_to_run'] = args.test
        
        if args.test_class:
            config['test_classes'] = args.test_class
    
    if args.verbosity is not None:
        config['verbosity'] = args.verbosity
    
    if args.no_estimates:
        config['show_time_estimates'] = False
    
    # Salva la configurazione se richiesto
    if args.save_config:
        save_config(config)
    
    return config


if __name__ == "__main__":
    # Analizza gli argomenti da riga di comando
    args = parse_arguments()
    
    # Aggiorna la configurazione
    config = update_config_from_args(args)
    
    # Se la verbosità è elevata, mostra la configurazione
    if config['verbosity'] >= 2:
        TestLogger.section("CONFIGURAZIONE")
        for key, value in config.items():
            TestLogger.debug(f"{key}: {value}")
    
    # Esegui i test
    result = discover_and_run_tests()
    
    # Uscita con codice di stato in base ai risultati
    sys.exit(not result.wasSuccessful()) 
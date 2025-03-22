import unittest
import sys
import os
import logging
from datetime import datetime
from colorama import init, Fore, Style, Back

# Inizializzo colorama
init()

# Aggiungo alla PYTHONPATH il percorso della directory principale
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_config import load_config

class TestLogger:
    """
    Logger specifico per l'esecuzione dei test.
    Gestisce diversi livelli di verbosità e colorazione dell'output.
    """
    
    # Livelli di log
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    
    @staticmethod
    def _should_log(level):
        """Controlla se il messaggio dovrebbe essere loggato in base alla verbosità configurata."""
        config = load_config()
        verbosity = config.get('verbosity', 1)
        
        # In caso di errori o critici, logga sempre
        if level >= TestLogger.WARNING:
            return True
        
        # Altrimenti, controlla il livello di verbosità
        if level == TestLogger.INFO and verbosity >= 1:
            return True
        if level == TestLogger.DEBUG and verbosity >= 2:
            return True
        
        return False
    
    @staticmethod
    def _log(level, message, color=None, highlight=False):
        """Metodo base per il logging."""
        if not TestLogger._should_log(level):
            return
        
        # Formatta il timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Applica colori se specificati
        if color:
            prefix = color
            suffix = Style.RESET_ALL
        else:
            prefix = ""
            suffix = ""
        
        # Applica evidenziazione se richiesta
        if highlight:
            prefix += Back.WHITE + Fore.BLACK
        
        # Stampa il messaggio
        print(f"{prefix}[{timestamp}] {message}{suffix}")
    
    @staticmethod
    def debug(message):
        """Log a livello debug (verbosità alta)."""
        TestLogger._log(TestLogger.DEBUG, message, Fore.CYAN)
    
    @staticmethod
    def info(message):
        """Log a livello info (verbosità normale)."""
        TestLogger._log(TestLogger.INFO, message)
    
    @staticmethod
    def warning(message):
        """Log a livello warning."""
        TestLogger._log(TestLogger.WARNING, message, Fore.YELLOW)
    
    @staticmethod
    def error(message):
        """Log a livello error."""
        TestLogger._log(TestLogger.ERROR, message, Fore.RED)
    
    @staticmethod
    def critical(message):
        """Log a livello critical."""
        TestLogger._log(TestLogger.CRITICAL, message, Fore.RED, highlight=True)
    
    @staticmethod
    def test_start(test_name, estimated_time=None):
        """Logga l'inizio di un test."""
        if estimated_time:
            TestLogger._log(TestLogger.INFO, f"▶️ Avvio test: {test_name} (tempo stimato: {estimated_time:.3f}s)", Fore.BLUE)
        else:
            TestLogger._log(TestLogger.INFO, f"▶️ Avvio test: {test_name}", Fore.BLUE)
    
    @staticmethod
    def test_success(test_name, execution_time):
        """Logga il successo di un test."""
        TestLogger._log(TestLogger.INFO, f"✅ Test completato: {test_name} in {execution_time:.3f}s", Fore.GREEN)
    
    @staticmethod
    def test_failure(test_name, execution_time, error_message):
        """Logga il fallimento di un test."""
        TestLogger._log(TestLogger.ERROR, f"❌ Test fallito: {test_name} in {execution_time:.3f}s", Fore.RED)
        TestLogger._log(TestLogger.ERROR, f"   Errore: {error_message}", Fore.RED)
    
    @staticmethod
    def test_skipped(test_name, reason=""):
        """Logga un test saltato."""
        if reason:
            TestLogger._log(TestLogger.INFO, f"⏭️ Test saltato: {test_name} - {reason}", Fore.YELLOW)
        else:
            TestLogger._log(TestLogger.INFO, f"⏭️ Test saltato: {test_name}", Fore.YELLOW)
    
    @staticmethod
    def section(title):
        """Logga un'intestazione di sezione."""
        TestLogger._log(TestLogger.INFO, f"\n{'-' * 70}", Fore.CYAN)
        TestLogger._log(TestLogger.INFO, f"📋 {title}", Fore.CYAN)
        TestLogger._log(TestLogger.INFO, f"{'-' * 70}", Fore.CYAN)


# Classe di test per il logger ColoredLogger del sistema principale
class TestColoredLogger(unittest.TestCase):
    """Test per la classe ColoredLogger del sistema principale."""
    
    def test_log_method(self):
        """Test per il metodo log."""
        # Importa la classe ColoredLogger dal modulo principale
        from modules.logger import ColoredLogger
        
        # Patch della funzione print per catturare l'output
        original_print = print
        printed_messages = []
        
        def mock_print(message):
            printed_messages.append(message)
        
        try:
            # Sostituisce temporaneamente la funzione print
            __builtins__['print'] = mock_print
            
            # Chiama il metodo log
            ColoredLogger.log("Test message", "TEST")
            
            # Verifica che sia stato stampato un messaggio
            self.assertEqual(len(printed_messages), 1)
            self.assertIn("TEST", printed_messages[0])
            self.assertIn("Test message", printed_messages[0])
        finally:
            # Ripristina la funzione print originale
            __builtins__['print'] = original_print
    
    def test_specialized_methods(self):
        """Test per i metodi specializzati."""
        # Importa la classe ColoredLogger dal modulo principale
        from modules.logger import ColoredLogger
        
        # Patch della funzione print per catturare l'output
        original_print = print
        printed_messages = []
        
        def mock_print(message):
            printed_messages.append(message)
        
        try:
            # Sostituisce temporaneamente la funzione print
            __builtins__['print'] = mock_print
            
            # Chiama i metodi specializzati
            ColoredLogger.interview("Interviewer message")
            ColoredLogger.synthetic("Synthetic message")
            ColoredLogger.moderator("Moderator message")
            
            # Verifica che siano stati stampati tre messaggi
            self.assertEqual(len(printed_messages), 3)
            self.assertIn("INTERVIEWER", printed_messages[0])
            self.assertIn("SYNTHETIC", printed_messages[1])
            self.assertIn("MODERATOR", printed_messages[2])
        finally:
            # Ripristina la funzione print originale
            __builtins__['print'] = original_print
    
    def test_method_calls_log(self):
        """Verifica che i metodi specializzati chiamino log."""
        # Importa la classe ColoredLogger dal modulo principale
        from modules.logger import ColoredLogger
        
        # Salva il metodo log originale
        original_log = ColoredLogger.log
        
        # Contatore per le chiamate a log
        call_count = 0
        
        def mock_log(message, prefix=None):
            nonlocal call_count
            call_count += 1
        
        try:
            # Sostituisce temporaneamente il metodo log
            ColoredLogger.log = mock_log
            
            # Chiama i metodi specializzati
            ColoredLogger.interview("Test")
            ColoredLogger.synthetic("Test")
            ColoredLogger.moderator("Test")
            
            # Verifica che log sia stato chiamato tre volte
            self.assertEqual(call_count, 3)
        finally:
            # Ripristina il metodo log originale
            ColoredLogger.log = original_log


if __name__ == "__main__":
    # Test semplice del TestLogger
    TestLogger.section("Test del TestLogger")
    TestLogger.debug("Questo è un messaggio di debug")
    TestLogger.info("Questo è un messaggio informativo")
    TestLogger.warning("Questo è un avviso")
    TestLogger.error("Questo è un errore")
    TestLogger.critical("Questo è un errore critico")
    TestLogger.test_start("test_example")
    TestLogger.test_success("test_example", 0.123)
    TestLogger.test_failure("test_failed", 0.456, "Qualcosa è andato storto")
    TestLogger.test_skipped("test_skipped", "Non necessario") 
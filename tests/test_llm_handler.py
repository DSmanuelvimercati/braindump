import unittest
import sys
import os

# Aggiungo alla PYTHONPATH il percorso della directory principale
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.llm_handler import is_valid_question

class TestLlmHandler(unittest.TestCase):
    """Test per le funzioni del modulo llm_handler."""
    
    def test_is_valid_question(self):
        """Test per la funzione is_valid_question."""
        # Test per domande valide
        self.assertTrue(is_valid_question("Qual è il tuo nome?"))
        self.assertTrue(is_valid_question("Come ti chiami?"))
        self.assertTrue(is_valid_question("Quali sono i tuoi hobby preferiti?"))
        
        # Test per domande non valide
        self.assertFalse(is_valid_question(""))  # Stringa vuota
        self.assertFalse(is_valid_question("Ciao"))  # Nessun punto interrogativo
        self.assertFalse(is_valid_question("A?"))  # Troppo corta
        self.assertFalse(is_valid_question("**Qual è il tuo nome?**"))  # Contiene **
        self.assertFalse(is_valid_question("# Domanda: come stai?"))  # Contiene #
        self.assertFalse(is_valid_question("Ecco una domanda: come stai?"))  # Contiene "ecco"
        self.assertFalse(is_valid_question("Questa è la tua richiesta di informazioni"))  # Contiene "la tua richiesta"
        
    def test_is_valid_question_with_unwanted_elements(self):
        """Test per la funzione is_valid_question con elementi indesiderati."""
        # Test per domande con elementi indesiderati
        self.assertFalse(is_valid_question("Secondo le informazioni fornite, qual è il tuo nome?"))
        self.assertFalse(is_valid_question("Ho capito che vuoi parlarmi di te. Qual è il tuo hobby?"))
        self.assertFalse(is_valid_question("Genera una risposta alla domanda: chi sei?"))
        self.assertFalse(is_valid_question("Restituisci il tuo nome e cognome?"))
        
        # Test per domande troppo lunghe
        long_question = "Questa è una domanda molto molto lunga che supera il limite di parole consentito e quindi dovrebbe essere considerata non valida perché contiene troppe parole e non rispetta le linee guida stabilite per le domande che devono essere brevi e concise in modo da essere facilmente comprensibili?"
        self.assertFalse(is_valid_question(long_question))

if __name__ == "__main__":
    unittest.main() 
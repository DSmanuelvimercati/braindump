import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Aggiungo alla PYTHONPATH il percorso della directory principale
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.agents.moderator import Moderator

class TestModerator(unittest.TestCase):
    """Test per la classe Moderator."""
    
    def setUp(self):
        """Setup per i test."""
        self.mock_interviewer = MagicMock()
        self.mock_synthetic = MagicMock()
        # Inizializzo il moderatore con mock per gli altri agenti
        self.moderator = Moderator(self.mock_interviewer, self.mock_synthetic)
    
    def test_present_suggestion_with_numeric_confidence(self):
        """Test per il metodo present_suggestion con confidenza numerica."""
        # Creo una risposta simulata con confidence come numero
        synthetic_response = {
            "response": "Questa è una risposta di test.",
            "confidence": 80,  # Valore numerico
            "sources": ["file1.md", "file2.md"]
        }
        
        # Chiamo il metodo da testare
        result = self.moderator.present_suggestion("Qual è la domanda di test?", synthetic_response)
        
        # Verifico che il risultato contenga la confidenza come "alto" (>=70)
        self.assertIn("confidenza: alto", result)
        self.assertIn("Questa è una risposta di test.", result)
        self.assertIn("Fonti: file1.md, file2.md", result)
    
    def test_present_suggestion_with_string_confidence(self):
        """Test per il metodo present_suggestion con confidenza come stringa."""
        # Creo una risposta simulata con confidence come stringa
        synthetic_response = {
            "response": "Questa è una risposta di test con confidenza come stringa.",
            "confidence": "medio",  # Stringa
            "sources": ["file3.md"]
        }
        
        # Chiamo il metodo da testare
        result = self.moderator.present_suggestion("Qual è la domanda di test?", synthetic_response)
        
        # Verifico che il risultato contenga la confidenza come "medio"
        self.assertIn("confidenza: medio", result)
        self.assertIn("Questa è una risposta di test con confidenza come stringa.", result)
        self.assertIn("Fonti: file3.md", result)
    
    def test_present_suggestion_without_sources(self):
        """Test per il metodo present_suggestion senza fonti."""
        # Creo una risposta simulata senza fonti
        synthetic_response = {
            "response": "Questa è una risposta senza fonti.",
            "confidence": 50,
            "sources": []
        }
        
        # Chiamo il metodo da testare
        result = self.moderator.present_suggestion("Qual è la domanda di test?", synthetic_response)
        
        # Verifico che il risultato indichi "nessuna fonte specifica"
        self.assertIn("Fonti: nessuna fonte specifica", result)
    
    @patch('modules.llm_handler.timed_generate_text')
    def test_process_user_input_with_valid_json(self, mock_generate_text):
        """Test per il metodo process_user_input con JSON valido."""
        # Configuro il mock per restituire un JSON valido
        mock_generate_text.return_value = """
        {
            "intent": "RISPOSTA_DIRETTA",
            "content": "Questa è la mia risposta diretta",
            "explanation": "L'utente sta rispondendo alla domanda"
        }
        """
        
        # Preparo i parametri
        user_input = "Questa è la mia risposta"
        current_question = "Qual è la domanda di test?"
        
        # Eseguo il metodo da testare
        try:
            result = self.moderator.process_user_input(user_input, current_question, None)
            
            # Verifico che il risultato sia un dizionario con i campi attesi
            self.assertIsInstance(result, dict)
            self.assertIn("action", result)
        except Exception as e:
            self.fail(f"process_user_input ha sollevato un'eccezione: {e}")
    
    @patch('modules.llm_handler.timed_generate_text')
    def test_process_user_input_with_invalid_json(self, mock_generate_text):
        """Test per il metodo process_user_input con JSON non valido."""
        # Configuro il mock per restituire una stringa non JSON
        mock_generate_text.return_value = "Questa non è una risposta JSON valida"
        
        # Preparo i parametri
        user_input = "Questa è la mia risposta"
        current_question = "Qual è la domanda di test?"
        
        # Eseguo il metodo da testare - dovrebbe gestire l'errore senza eccezioni
        try:
            result = self.moderator.process_user_input(user_input, current_question, None)
            
            # Verifico che sia stata gestita correttamente restituendo un dizionario
            self.assertIsInstance(result, dict)
        except Exception as e:
            self.fail(f"process_user_input non ha gestito correttamente JSON non valido: {e}")

if __name__ == "__main__":
    unittest.main() 
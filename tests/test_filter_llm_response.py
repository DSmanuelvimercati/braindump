import unittest
import sys
import os
from unittest.mock import patch

# Aggiungo alla PYTHONPATH il percorso della directory principale
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.llm_handler import filter_llm_response

class TestFilterLlmResponse(unittest.TestCase):
    """Test per la funzione filter_llm_response."""
    
    @patch('modules.llm_handler.generate_text')
    def test_filter_llm_response_valid(self, mock_generate_text):
        """Test per filter_llm_response con risposta valida."""
        # Mocking della risposta generata dall'LLM
        mock_generate_text.return_value = "Qual è la tua esperienza con il topic?"
        
        # Test con risposta valida
        topic = "Lavoro"
        response = "Quali sono le tue esperienze lavorative più formative?"
        
        filtered = filter_llm_response(response, topic)
        
        # Il risultato dovrebbe essere la risposta originale perché è valida
        self.assertEqual(filtered, response)
        
        # Verifico che generate_text non sia stato chiamato
        mock_generate_text.assert_not_called()
    
    @patch('modules.llm_handler.generate_text')
    def test_filter_llm_response_placeholder(self, mock_generate_text):
        """Test per filter_llm_response con placeholder."""
        # Test con risposta che contiene placeholder
        topic = "Lavoro"
        response = "Qual è la tua esperienza con [topic]?"
        
        filtered = filter_llm_response(response, topic)
        
        # Il risultato dovrebbe sostituire [topic] con "Lavoro"
        self.assertEqual(filtered, "Qual è la tua esperienza con Lavoro?")
        
    @patch('modules.llm_handler.generate_text')
    def test_filter_llm_response_invalid(self, mock_generate_text):
        """Test per filter_llm_response con risposta non valida."""
        # Configuro il mock per ritornare una risposta valida
        mock_generate_text.return_value = "Quali progetti lavorativi ti hanno dato più soddisfazione?"
        
        # Test con risposta non valida (manca il punto interrogativo)
        topic = "Lavoro"
        response = "Parlami delle tue esperienze di lavoro"
        
        filtered = filter_llm_response(response, topic)
        
        # Il risultato dovrebbe essere la risposta generata dal mock
        self.assertEqual(filtered, "Quali progetti lavorativi ti hanno dato più soddisfazione?")
        
        # Verifico che generate_text sia stato chiamato una volta
        mock_generate_text.assert_called_once()
    
    @patch('modules.llm_handler.generate_text')
    def test_filter_llm_response_fallback(self, mock_generate_text):
        """Test per filter_llm_response con fallback alle domande predefinite."""
        # Configuro il mock per ritornare una risposta ancora non valida
        mock_generate_text.return_value = "Restituisci informazioni sul [topic]"
        
        # Test con risposta non valida e fallback richiesto
        topic = "Lavoro"
        response = "# Domanda sul lavoro"
        
        filtered = filter_llm_response(response, topic)
        
        # Il risultato dovrebbe essere una delle domande di backup
        # Non possiamo prevedere quale esattamente perché è scelta casualmente
        self.assertIn("Lavoro", filtered)
        self.assertIn("?", filtered)
        
        # Verifico che generate_text sia stato chiamato una volta
        mock_generate_text.assert_called_once()

if __name__ == "__main__":
    unittest.main() 
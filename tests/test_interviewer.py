import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Aggiungo alla PYTHONPATH il percorso della directory principale
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.agents.interviewer import Interviewer

class TestInterviewer(unittest.TestCase):
    """Test per la classe Interviewer."""
    
    def test_interviewer_initialization(self):
        """Test per verificare che l'Interviewer sia inizializzato correttamente."""
        interviewer = Interviewer()
        
        # Verifica che tutti gli attributi necessari siano presenti
        self.assertTrue(hasattr(interviewer, 'previous_questions'), "Manca l'attributo previous_questions")
        self.assertTrue(hasattr(interviewer, 'questions_asked'), "Manca l'attributo questions_asked")
        self.assertTrue(hasattr(interviewer, 'last_question'), "Manca l'attributo last_question")
        self.assertTrue(hasattr(interviewer, 'available_topics'), "Manca l'attributo available_topics")
        
        # Verifica che le liste siano inizializzate vuote
        self.assertEqual(len(interviewer.previous_questions), 0, "previous_questions dovrebbe essere vuoto")
        self.assertEqual(len(interviewer.questions_asked), 0, "questions_asked dovrebbe essere vuoto")
        self.assertEqual(interviewer.last_question, "", "last_question dovrebbe essere una stringa vuota")
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="- Linea guida di test\n- Seconda linea guida")
    def test_get_current_guidelines_from_temp_file(self, mock_open, mock_exists):
        """Test per verificare il caricamento delle linee guida da file temporaneo."""
        # Configuro i mock per simulare l'esistenza del file temporaneo
        mock_exists.side_effect = lambda path: 'temp' in path
        
        interviewer = Interviewer()
        result = interviewer.get_current_guidelines()
        
        # Verifico che il risultato contenga il contenuto del file mock
        self.assertIn("Linea guida di test", result)
        self.assertIn("Seconda linea guida", result)
        
        # Verifico che sia stato tentato di aprire il file temporaneo
        mock_open.assert_called_once()
        
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="- Linea guida permanente\n- Seconda linea permanente")
    def test_get_current_guidelines_from_permanent_file(self, mock_open, mock_exists):
        """Test per verificare il caricamento delle linee guida da file permanente."""
        # Configuro i mock per simulare l'esistenza solo del file permanente
        def exists_side_effect(path):
            return 'guidelines' in path and 'temp' not in path
        mock_exists.side_effect = exists_side_effect
        
        interviewer = Interviewer()
        result = interviewer.get_current_guidelines()
        
        # Verifico che il risultato contenga il contenuto del file mock
        self.assertIn("Linea guida permanente", result)
        self.assertIn("Seconda linea permanente", result)
        
        # Verifico che sia stato tentato di aprire il file permanente
        mock_open.assert_called_once()
    
    @patch('os.path.exists')
    def test_get_current_guidelines_fallback(self, mock_exists):
        """Test per verificare il fallback alle linee guida predefinite."""
        # Configuro il mock per simulare che nessun file esista
        mock_exists.return_value = False
        
        interviewer = Interviewer()
        result = interviewer.get_current_guidelines()
        
        # Verifico che il risultato contenga le linee guida predefinite
        self.assertIn("Fai domande personali e specifiche sul topic", result)
        self.assertIn("Evita domande generiche o troppo vaghe", result)
    
    @patch('modules.llm_handler.filter_llm_response')
    @patch('modules.llm_handler.timed_generate_text')
    def test_generate_first_question(self, mock_timed_generate, mock_filter):
        """Test per verificare la generazione della prima domanda."""
        # Configuro i mock
        mock_timed_generate.return_value = "Domanda generata dall'LLM?"
        mock_filter.return_value = "Domanda filtrata e migliorata?"
        
        interviewer = Interviewer()
        
        # Sostituisco il metodo get_current_guidelines con un mock
        interviewer.get_current_guidelines = MagicMock(return_value="- Linea guida di test")
        
        # Chiamo il metodo da testare
        result = interviewer.generate_first_question("Topic Test")
        
        # Verifico che il risultato sia la domanda filtrata
        self.assertEqual(result, "Domanda filtrata e migliorata?")
        
        # Verifico che la domanda sia stata salvata come ultima domanda
        self.assertEqual(interviewer.last_question, "Domanda filtrata e migliorata?")
        
        # Verifico che la domanda sia stata aggiunta alla lista delle domande poste
        self.assertIn("Domanda filtrata e migliorata?", interviewer.questions_asked)
        
        # Verifico che gli altri metodi siano stati chiamati correttamente
        mock_timed_generate.assert_called_once()
        mock_filter.assert_called_once_with("Domanda generata dall'LLM?", "Topic Test")

if __name__ == "__main__":
    unittest.main() 
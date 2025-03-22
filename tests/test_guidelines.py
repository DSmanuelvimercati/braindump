import unittest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

# Aggiungo alla PYTHONPATH il percorso della directory principale
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.agents.moderator import Moderator

class TestGuidelines(unittest.TestCase):
    """Test per la gestione delle linee guida."""
    
    def setUp(self):
        """Setup per i test."""
        self.mock_interviewer = MagicMock()
        self.mock_synthetic = MagicMock()
        self.moderator = Moderator(self.mock_interviewer, self.mock_synthetic)
        # Imposto il percorso del file temporaneo delle linee guida
        self.moderator.temp_guidelines_file = "temp_test_guidelines.md"
        self.moderator.permanent_guidelines_file = "permanent_test_guidelines.md"
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="# Linee guida esistenti\n\n## Principi fondamentali\n- Linea guida 1\n- Linea guida 2\n")
    def test_initialize_temp_guidelines_from_permanent(self, mock_file, mock_exists):
        """Test dell'inizializzazione delle linee guida temporanee da file permanente."""
        # Configuro il mock per simulare che esista solo il file permanente
        mock_exists.side_effect = lambda path: path == self.moderator.permanent_guidelines_file
        
        # Chiamo il metodo da testare
        self.moderator.initialize_temp_guidelines()
        
        # Verifico che il file permanente sia stato letto
        mock_file.assert_called_with(self.moderator.permanent_guidelines_file, 'r', encoding='utf-8')
        
        # Verifico che il file temporaneo sia stato scritto
        mock_file.assert_called_with(self.moderator.temp_guidelines_file, 'w', encoding='utf-8')
        
        # Verifico che il contenuto del file permanente sia stato scritto nel file temporaneo
        handle = mock_file()
        handle.write.assert_called_with("# Linee guida esistenti\n\n## Principi fondamentali\n- Linea guida 1\n- Linea guida 2\n")
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_initialize_temp_guidelines_new(self, mock_file, mock_exists):
        """Test dell'inizializzazione di nuove linee guida temporanee."""
        # Configuro il mock per simulare che non esista nessun file
        mock_exists.return_value = False
        
        # Chiamo il metodo da testare
        self.moderator.initialize_temp_guidelines()
        
        # Verifico che il file temporaneo sia stato scritto
        mock_file.assert_called_with(self.moderator.temp_guidelines_file, 'w', encoding='utf-8')
        
        # Verifico che sia stato scritto un contenuto di base
        handle = mock_file()
        handle.write.assert_called()
        # Verifico che la scrittura contenga almeno un header
        args, _ = handle.write.call_args
        self.assertIn("# Linee guida", args[0])
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="# Linee guida\n\n## Principi fondamentali\n- Linea guida 1\n- Linea guida 2\n")
    @patch('modules.llm_handler.timed_generate_text')
    def test_add_to_guidelines(self, mock_generate_text, mock_file, mock_exists):
        """Test dell'aggiunta di una nuova linea guida."""
        # Configuro il mock per simulare che il file temporaneo esista
        mock_exists.return_value = True
        
        # Configuro il mock per simulare la risposta dell'LLM
        mock_generate_text.return_value = "- Nuova linea guida di test formattata"
        
        # Chiamo il metodo da testare
        result = self.moderator.add_to_guidelines("Nuova linea guida di test")
        
        # Verifico che l'operazione sia stata completata con successo
        self.assertTrue(result)
        
        # Verifico che il file sia stato aperto in lettura
        mock_file.assert_called_with(self.moderator.temp_guidelines_file, 'r', encoding='utf-8')
        
        # Verifico che il file sia stato poi aperto in scrittura
        mock_file.assert_called_with(self.moderator.temp_guidelines_file, 'w', encoding='utf-8')
        
        # Verifico che il mock dell'LLM sia stato chiamato
        mock_generate_text.assert_called_once()
        
        # Verifico che il contenuto aggiornato sia stato scritto nel file
        handle = mock_file()
        handle.write.assert_called()
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="# Linee guida\n\n## Principi fondamentali\n- Linea guida 1\n- Linea guida 2\n")
    def test_get_guidelines(self, mock_file, mock_exists):
        """Test del recupero delle linee guida correnti."""
        # Configuro il mock per simulare che il file temporaneo esista
        mock_exists.side_effect = lambda path: path == self.moderator.temp_guidelines_file
        
        # Chiamo il metodo da testare
        result = self.moderator.get_current_guidelines()
        
        # Verifico che il risultato non sia vuoto
        self.assertTrue(result)
        
        # Verifico che il file sia stato aperto in lettura
        mock_file.assert_called_with(self.moderator.temp_guidelines_file, 'r', encoding='utf-8')
        
        # Verifico che il contenuto delle linee guida sia stato restituito
        self.assertEqual(result, "# Linee guida\n\n## Principi fondamentali\n- Linea guida 1\n- Linea guida 2\n")
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="# Linee guida temporanee")
    @patch('os.makedirs')
    def test_save_permanent_guidelines(self, mock_makedirs, mock_file, mock_exists):
        """Test del salvataggio delle linee guida permanenti."""
        # Configuro il mock per simulare che il file temporaneo esista
        mock_exists.side_effect = lambda path: path == self.moderator.temp_guidelines_file
        
        # Chiamo il metodo da testare
        result = self.moderator.save_permanent_guidelines()
        
        # Verifico che l'operazione sia stata completata con successo
        self.assertTrue(result)
        
        # Verifico che la directory sia stata creata
        mock_makedirs.assert_called_once()
        
        # Verifico che il file temporaneo sia stato aperto in lettura
        mock_file.assert_called_with(self.moderator.temp_guidelines_file, 'r', encoding='utf-8')
        
        # Verifico che il file permanente sia stato aperto in scrittura
        mock_file.assert_called_with(self.moderator.permanent_guidelines_file, 'w', encoding='utf-8')
        
        # Verifico che il contenuto sia stato scritto
        handle = mock_file()
        handle.write.assert_called_with("# Linee guida temporanee")

if __name__ == "__main__":
    unittest.main() 
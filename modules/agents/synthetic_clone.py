"""
Agente Clone Sintetico: risponde alle domande consultando il braindump esistente.
"""

import os
import glob
from modules.llm_handler import timed_generate_text
from config import INFORMATION_DIR, CONCEPTS_DIR
from modules.logger import ColoredLogger

class SyntheticClone:
    """
    Agente che si occupa di rispondere alle domande consultando 
    il braindump esistente, simulando l'utente.
    """
    
    def __init__(self):
        """Inizializza l'agente clone sintetico."""
        self.information_dir = INFORMATION_DIR
        self.concepts_dir = CONCEPTS_DIR
    
    def find_relevant_files(self, question, topic):
        """
        Trova i file rilevanti per rispondere alla domanda.
        
        Args:
            question (str): La domanda a cui rispondere
            topic (str): Il topic corrente
            
        Returns:
            list: Lista dei percorsi dei file rilevanti
        """
        # Raccoglie tutti i file MD nelle cartelle di informazioni e concetti
        all_files = []
        for directory in [self.information_dir, self.concepts_dir]:
            if os.path.exists(directory):
                all_files.extend(glob.glob(os.path.join(directory, "*.md")))
        
        if not all_files:
            ColoredLogger.synthetic("Nessun file nel braindump da consultare.")
            return []
        
        # Crea un prompt per l'LLM per selezionare i file rilevanti
        file_names = [os.path.basename(f).replace(".md", "") for f in all_files]
        
        prompt = f"""
        Data questa domanda: "{question}" sul topic "{topic}", 
        quali tra i seguenti file potrebbero contenere informazioni rilevanti?
        
        File disponibili: {', '.join(file_names)}
        
        Considera:
        1. La semantica della domanda e il suo tema centrale
        2. Possibili collegamenti indiretti tra la domanda e i contenuti dei file
        3. La pertinenza al topic corrente
        
        Restituisci SOLO un array JSON con i nomi dei file (senza estensione):
        ["file1", "file2", ...]
        
        Se nessun file sembra rilevante, restituisci un array vuoto: []
        """
        
        result = timed_generate_text(prompt, "ricerca file per clone sintetico")
        
        # Estrai i nomi dei file dalla risposta JSON
        try:
            import re
            import json
            
            # Cerca pattern JSON nella risposta
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                file_list = json.loads(json_text)
                
                # Converte i nomi dei file in percorsi completi
                relevant_files = []
                for file_name in file_list:
                    matches = [f for f in all_files if os.path.basename(f).replace(".md", "") == file_name]
                    relevant_files.extend(matches)
                
                ColoredLogger.synthetic(f"Trovati {len(relevant_files)} file rilevanti.")
                return relevant_files
            else:
                ColoredLogger.synthetic("Nessun formato JSON valido trovato nella risposta.")
                return []
        except Exception as e:
            ColoredLogger.error(f"Errore nell'analisi della risposta: {e}")
            return []
    
    def extract_content_from_files(self, files):
        """
        Estrae il contenuto dai file rilevanti.
        
        Args:
            files (list): Lista dei percorsi dei file
            
        Returns:
            str: Il contenuto estratto
        """
        content = ""
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                    filename = os.path.basename(file_path)
                    content += f"\n--- Da {filename} ---\n{file_content}\n"
            except Exception as e:
                ColoredLogger.error(f"Errore nella lettura del file {file_path}: {e}")
        
        return content
    
    def generate_response(self, question, topic):
        """
        Genera una risposta basata sui dati del Braindump.
        
        Args:
            question (str): La domanda posta
            topic (str): Il topic corrente
            
        Returns:
            dict: Un dizionario con la risposta e i metadati
        """
        # Cerca file rilevanti per la domanda
        ColoredLogger.synthetic("[ricerca file per clone sintetico]")
        relevant_files = self.find_relevant_files(question, topic)
        
        if not relevant_files:
            ColoredLogger.synthetic("Nessun file rilevante trovato.")
            return {
                "found_relevant_info": False,
                "response": "",
                "confidence": 0,
                "sources": []
            }
        
        # Leggi i file rilevanti e crea il contesto
        context_text = ""
        file_names = []
        
        for file_path in relevant_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    file_name = os.path.basename(file_path)
                    context_text += f"\n--- {file_name} ---\n{content}\n"
                    file_names.append(file_name)
            except Exception as e:
                ColoredLogger.error(f"Errore nella lettura del file {file_path}: {e}")
        
        ColoredLogger.synthetic(f"Trovati {len(relevant_files)} file rilevanti.")
        
        # Genera una risposta basata sul contesto
        prompt = f"""
        Genera una risposta alla seguente domanda basandoti ESCLUSIVAMENTE sulle informazioni fornite nel contesto. 
        La risposta deve essere in prima persona, come se fossi tu a rispondere direttamente.
        
        Domanda: "{question}"
        
        Contesto (informazioni esistenti dell'utente sul topic '{topic}'):
        {context_text}
        
        LINEE GUIDA PER LA RISPOSTA:
        1. Rispondi SOLO se puoi trovare informazioni rilevanti nel contesto fornito
        2. La risposta deve essere in prima persona (usa "io", "mi", "mio", ecc.)
        3. Sii conciso ma completo
        4. Non inventare o aggiungere informazioni non presenti nel contesto
        5. Non usare espressioni come "Secondo le informazioni nel contesto..."
        6. Non usare placeholder come [topic] o [argomento] - utilizza direttamente i termini corretti
        7. Non aggiungere riferimenti espliciti ai file o alle fonti nella risposta stessa
        
        Restituisci un JSON con questo formato:
        {{
          "response": "La tua risposta completa in prima persona",
          "confidence": un numero da 0 a 100 che rappresenta quanto sei sicuro che la risposta sia basata sul contesto e pertinente alla domanda,
          "sources": ["nome_file1.md", "nome_file2.md"] (solo i nomi dei file che hai effettivamente utilizzato per la risposta)
        }}
        
        Se non trovi informazioni rilevanti nel contesto, restituisci:
        {{
          "response": "",
          "confidence": 0,
          "sources": []
        }}
        """
        
        response_text = timed_generate_text(prompt, "generazione risposta sintetica")
        
        # Estrai il JSON dalla risposta
        try:
            import json
            import re
            
            # Cerca un pattern JSON nella risposta
            json_match = re.search(r'{.*}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                response = result.get("response", "")
                confidence = result.get("confidence", 0)
                sources = result.get("sources", [])
                
                # Se ci sono state fonti trovate e la confidenza è ragionevole
                if response and confidence > 30:
                    # Assicurati che non ci siano placeholder rimasti nella risposta
                    if "[topic]" in response or "[argomento]" in response:
                        response = response.replace("[topic]", topic).replace("[argomento]", topic)
                    
                    confidence_level = "basso"
                    if confidence >= 70:
                        confidence_level = "alto"
                    elif confidence >= 40:
                        confidence_level = "medio"
                    
                    return {
                        "found_relevant_info": True,
                        "response": response,
                        "confidence": confidence_level,
                        "sources": sources
                    }
        except Exception as e:
            ColoredLogger.error(f"Errore nell'analisi della risposta JSON: {e}")
        
        return {
            "found_relevant_info": False,
            "response": "",
            "confidence": 0,
            "sources": []
        } 
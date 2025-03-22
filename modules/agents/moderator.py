"""
Agente Moderatore: coordina gli altri agenti e gestisce l'interazione con l'utente.
"""

import os
import re
from modules.storage import save_braindump_entry
from modules.response_handler import interpret_user_answer, interpret_meta_response, provide_help_info
from modules.llm_handler import timed_generate_text
from modules.context_handler import change_topic, choose_topic_manually
from modules.consolidation import finalize_session
from config import create_temp_folder, TEMP_FOLDER
from modules.logger import ColoredLogger

class Moderator:
    """
    Agente che si occupa di coordinare gli altri agenti e gestire l'interazione con l'utente.
    """
    
    def __init__(self, interviewer, synthetic_clone):
        """
        Inizializza l'agente moderatore.
        
        Args:
            interviewer: L'agente intervistatore
            synthetic_clone: L'agente clone sintetico
        """
        self.interviewer = interviewer
        self.synthetic_clone = synthetic_clone
        self.current_topic = None
        self.conversation_history = ""
        self.debug_mode = True
        self.temp_guidelines_file = os.path.join(TEMP_FOLDER, "temp_guidelines.md")
        self.permanent_guidelines_file = os.path.join("guidelines", "interviewer_guidelines.md")
        self.initialize_temp_guidelines()
    
    def initialize_temp_guidelines(self):
        """Inizializza il file temporaneo delle linee guida copiando il contenuto del file permanente."""
        # Assicurati che la directory guidelines esista
        if not os.path.exists("guidelines"):
            os.makedirs("guidelines")
        
        # Crea la cartella temporanea se non esiste
        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)
        
        # Se il file permanente esiste, copialo nel file temporaneo
        if os.path.exists(self.permanent_guidelines_file):
            try:
                with open(self.permanent_guidelines_file, "r", encoding="utf-8") as source:
                    content = source.read()
                
                with open(self.temp_guidelines_file, "w", encoding="utf-8") as target:
                    target.write(content)
                
                ColoredLogger.moderator(f"Linee guida caricate da: {self.permanent_guidelines_file}")
            except Exception as e:
                ColoredLogger.error(f"Errore nel copiare il file delle linee guida: {e}")
        else:
            # Se il file permanente non esiste, crea un file temporaneo vuoto con un'intestazione di base
            with open(self.temp_guidelines_file, "w", encoding="utf-8") as f:
                f.write("# Linee guida per l'agente Intervistatore\n\n")
                f.write("## Principi fondamentali\n")
                f.write("1. **Domande personali** - Focalizzate su esperienze ed opinioni dell'utente\n")
                f.write("2. **Domande specifiche** - Concrete e non generiche\n")
                f.write("3. **Rispetto del contesto** - Aderenti alla definizione del topic\n")
            
            ColoredLogger.moderator("Create nuove linee guida temporanee")
    
    def add_to_guidelines(self, new_guideline):
        """
        Aggiunge una nuova linea guida al file temporaneo.
        
        Args:
            new_guideline (str): La nuova linea guida da aggiungere
        
        Returns:
            bool: True se l'operazione è riuscita, False altrimenti
        """
        try:
            # Migliora la formattazione della linea guida
            prompt = f"""
            Formatta la seguente linea guida in modo chiaro e strutturato:
            
            "{new_guideline}"
            
            Assicurati che:
            1. Sia chiara e concisa
            2. Utilizzi punti elenco o numerazione se appropriato
            3. Sia coerente con lo stile di una linea guida per la generazione di domande
            
            Restituisci solo la linea guida formattata, senza introduzioni o commenti.
            """
            
            formatted_guideline = timed_generate_text(prompt, "formattazione guideline")
            
            # Determina in quale sezione aggiungere la linea guida
            with open(self.temp_guidelines_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Cerca la sezione appropriata o creane una nuova
            section_match = re.search(r'## (Principi|Esempi|Tipologie|Da evitare)', formatted_guideline, re.IGNORECASE)
            
            if section_match:
                section_name = section_match.group(1)
                # Cerca se questa sezione esiste già nel file
                existing_section = re.search(fr'## {section_name}', content, re.IGNORECASE)
                
                if existing_section:
                    # Sezione trovata, aggiungi la guideline sotto questa sezione
                    section_start = existing_section.start()
                    next_section = re.search(r'##', content[section_start+3:])
                    
                    if next_section:
                        insert_pos = section_start + 3 + next_section.start()
                        new_content = content[:insert_pos] + "\n\n" + formatted_guideline + "\n" + content[insert_pos:]
                    else:
                        new_content = content + "\n\n" + formatted_guideline + "\n"
                else:
                    # Sezione non trovata, aggiungi la nuova sezione alla fine
                    new_content = content + "\n\n## " + section_name + "\n\n" + formatted_guideline + "\n"
            else:
                # Nessuna sezione specificata, aggiungi alla fine sotto "Altri suggerimenti"
                if "## Altri suggerimenti" in content:
                    # Aggiunge sotto la sezione esistente
                    insert_pos = content.find("## Altri suggerimenti") + len("## Altri suggerimenti")
                    new_content = content[:insert_pos] + "\n\n" + formatted_guideline + "\n" + content[insert_pos:]
                else:
                    # Crea una nuova sezione
                    new_content = content + "\n\n## Altri suggerimenti\n\n" + formatted_guideline + "\n"
            
            # Scrivi il contenuto aggiornato
            with open(self.temp_guidelines_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            ColoredLogger.moderator(f"Aggiunta nuova linea guida: {formatted_guideline.strip()[:80]}...")
            return True
        
        except Exception as e:
            ColoredLogger.error(f"Errore nell'aggiunta della linea guida: {e}")
            return False
    
    def save_permanent_guidelines(self):
        """
        Salva le linee guida temporanee nel file permanente.
        
        Returns:
            bool: True se l'operazione è riuscita, False altrimenti
        """
        try:
            if os.path.exists(self.temp_guidelines_file):
                with open(self.temp_guidelines_file, "r", encoding="utf-8") as source:
                    content = source.read()
                
                with open(self.permanent_guidelines_file, "w", encoding="utf-8") as target:
                    target.write(content)
                
                ColoredLogger.moderator(f"Linee guida salvate permanentemente in: {self.permanent_guidelines_file}")
                return True
            else:
                ColoredLogger.warning("Nessun file di linee guida temporanee da salvare")
                return False
        except Exception as e:
            ColoredLogger.error(f"Errore nel salvare le linee guida permanenti: {e}")
            return False
    
    def get_current_guidelines(self):
        """
        Recupera il contenuto attuale delle linee guida temporanee.
        
        Returns:
            str: Il contenuto delle linee guida
        """
        try:
            if os.path.exists(self.temp_guidelines_file):
                with open(self.temp_guidelines_file, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                return "Nessuna linea guida presente."
        except Exception as e:
            ColoredLogger.error(f"Errore nella lettura delle linee guida: {e}")
            return "Errore nella lettura delle linee guida."
    
    def initialize_session(self):
        """Inizializza una nuova sessione di intervista."""
        create_temp_folder()
        self.initialize_temp_guidelines()
        ColoredLogger.moderator("Sessione inizializzata.")
        ColoredLogger.moderator(f"Cartella temporanea creata: {os.path.abspath(os.path.join(os.getcwd(), 'temp_session'))}")
    
    def select_topic(self, topic_input):
        """
        Seleziona il topic per l'intervista.
        
        Args:
            topic_input (str): Input dell'utente per la selezione del topic
            
        Returns:
            str: Il topic selezionato
        """
        available_topics = self.interviewer.available_topics
        
        # Gestisci l'input vuoto
        if not topic_input.strip():
            ColoredLogger.moderator("Nessun topic selezionato, utilizzo il topic predefinito 'Generale'")
            return "Generale"
        
        # Se l'input è un numero, seleziona il topic corrispondente dalla lista
        if topic_input.isdigit():
            idx = int(topic_input) - 1  # Converti da 1-based a 0-based
            if 0 <= idx < len(available_topics):
                selected_topic = available_topics[idx]
                ColoredLogger.moderator(f"Topic selezionato: {selected_topic} (opzione {topic_input})")
                self.current_topic = selected_topic
                return selected_topic
            else:
                ColoredLogger.warning(f"Indice {topic_input} non valido, utilizzo il topic 'Generale'")
                self.current_topic = "Generale"
                return "Generale"
        
        # Altrimenti, utilizza l'input come nome del topic
        self.current_topic = topic_input.strip()
        ColoredLogger.moderator(f"Topic selezionato: {self.current_topic}")
        return self.current_topic
    
    def process_user_input(self, user_input, current_question, suggestion_response=None):
        """
        Processa l'input dell'utente e determina l'azione successiva.
        
        Args:
            user_input (str): Input dell'utente
            current_question (str): La domanda corrente
            suggestion_response (dict, optional): Risposta suggerita dal clone sintetico
            
        Returns:
            dict: Risultato dell'elaborazione con le seguenti chiavi:
                - action: L'azione da eseguire (CONTINUE, EXIT, HELP, SKIP, etc.)
                - message: Messaggio da mostrare all'utente
                - data: Dati aggiuntivi specifici dell'azione
        """
        # Memorizza la domanda e la risposta suggerita correnti
        self.current_question = current_question
        self.current_suggestion = suggestion_response
        
        # Utilizziamo l'LLM per analizzare semanticamente l'input dell'utente
        intent_prompt = f"""
        Analizza l'input dell'utente e determina la sua intenzione principale.
        
        Input dell'utente: "{user_input}"
        Domanda corrente: "{current_question}"
        Topic attuale: "{self.current_topic}"
        
        Classifica l'intenzione dell'utente in UNA delle seguenti categorie:
        1. FEEDBACK_NEGATIVO_DOMANDA - L'utente indica che la domanda non rispetta le linee guida o non è adeguata
        2. FEEDBACK_POSITIVO_DOMANDA - L'utente conferma che la domanda rispetta le linee guida
        3. AGGIUNGI_GUIDELINE - L'utente vuole aggiungere una nuova linea guida (es. "inseriamo nelle guideline che...")
        4. AGGIUNGI_GUIDELINE_E_RISPONDI - L'utente vuole aggiungere una linea guida e poi rispondere alla domanda
        5. AGGIUNGI_GUIDELINE_E_CAMBIA - L'utente vuole aggiungere una linea guida e poi cambiare domanda
        6. MOSTRA_GUIDELINE - L'utente vuole vedere le linee guida attuali
        7. CAMBIA_DOMANDA - L'utente vuole cambiare domanda senza rispondere
        8. CAMBIA_DOMANDA_CON_FEEDBACK - L'utente vuole una nuova domanda con un feedback specifico
        9. EXIT - L'utente vuole terminare l'intervista
        10. SKIP - L'utente vuole saltare la domanda attuale
        11. HELP - L'utente chiede aiuto sui comandi disponibili
        12. RISPOSTA_DIRETTA - L'utente sta rispondendo direttamente alla domanda
        13. CAMBIA_TOPIC - L'utente vuole cambiare topic
        14. SUGGERISCI_DOMANDA - L'utente suggerisce una domanda alternativa
        15. IRRELEVANTE - L'utente indica che la domanda non è rilevante
        
        Restituisci un JSON con i seguenti campi:
        - "intent": la categoria identificata (usa ESATTAMENTE uno dei valori sopra)
        - "content": il contenuto rilevante (es. la linea guida da aggiungere, il feedback, ecc.)
        - "explanation": una breve spiegazione della classificazione
        
        Esempio di output:
        {
            "intent": "AGGIUNGI_GUIDELINE",
            "content": "le domande devono essere più personali",
            "explanation": "L'utente vuole aggiungere una nuova linea guida sulle domande personali"
        }
        """
        
        intent_analysis = timed_generate_text(intent_prompt, "analisi intento utente")
        
        # Estrai il JSON dalla risposta
        try:
            import json
            import re
            # Cerca di trovare il blocco JSON nella risposta
            json_match = re.search(r'{.*}', intent_analysis, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                analysis = json.loads(json_str)
                
                intent = analysis.get("intent", "RISPOSTA_DIRETTA")
                content = analysis.get("content", user_input)
                explanation = analysis.get("explanation", "")
                
                ColoredLogger.moderator(f"Intento rilevato: {intent} - {explanation}")
                
                # Gestione dei diversi intenti
                if intent == "FEEDBACK_NEGATIVO_DOMANDA":
                    self.in_feedback_mode = True
                    return {
                        "action": "FEEDBACK_MODE",
                        "message": "Hai indicato che la domanda non rispetta le linee guida. Vuoi:\n1. Rigenerare una nuova domanda\n2. Aggiungere una linea guida specifica\n3. Rispondere comunque a questa domanda",
                        "data": {"feedback_type": "negative"}
                    }
                    
                elif intent == "FEEDBACK_POSITIVO_DOMANDA":
                    self.in_feedback_mode = True
                    return {
                        "action": "FEEDBACK_MODE",
                        "message": "Hai confermato che la domanda rispetta le linee guida. Vuoi rispondere ora?",
                        "data": {"feedback_type": "positive"}
                    }
                    
                elif intent == "AGGIUNGI_GUIDELINE":
                    success = self.add_to_guidelines(content)
                    if success:
                        return {
                            "action": "GUIDELINE_ADDED",
                            "message": f"Linea guida aggiunta: '{content[:50]}...'. Vuoi continuare con la domanda attuale o generarne una nuova?",
                            "data": {"guideline": content}
                        }
                    else:
                        return {
                            "action": "ERROR",
                            "message": "Si è verificato un errore nell'aggiunta della linea guida.",
                            "data": {}
                        }
                        
                elif intent == "AGGIUNGI_GUIDELINE_E_RISPONDI":
                    success = self.add_to_guidelines(content)
                    if success:
                        return {
                            "action": "GUIDELINE_ADDED_CONTINUE",
                            "message": f"Linea guida aggiunta: '{content[:50]}...'. Procediamo con la domanda: {self.current_question}",
                            "data": {"guideline": content}
                        }
                    else:
                        return {
                            "action": "ERROR",
                            "message": "Si è verificato un errore nell'aggiunta della linea guida.",
                            "data": {}
                        }
                        
                elif intent == "AGGIUNGI_GUIDELINE_E_CAMBIA":
                    success = self.add_to_guidelines(content)
                    if success:
                        # Memorizza il feedback
                        self.user_feedback = content
                        return {
                            "action": "GUIDELINE_ADDED_REGENERATE",
                            "message": f"Linea guida aggiunta: '{content[:50]}...'. Genererò una nuova domanda che rispetti questa indicazione.",
                            "data": {"guideline": content}
                        }
                    else:
                        return {
                            "action": "ERROR",
                            "message": "Si è verificato un errore nell'aggiunta della linea guida.",
                            "data": {}
                        }
                        
                elif intent == "MOSTRA_GUIDELINE":
                    guidelines = self.get_current_guidelines()
                    return {
                        "action": "SHOW_GUIDELINES",
                        "message": f"Ecco le linee guida attuali:\n\n{guidelines}",
                        "data": {"guidelines": guidelines}
                    }
                    
                elif intent == "CAMBIA_DOMANDA":
                    return {
                        "action": "SKIP",
                        "message": "Genererò una nuova domanda...",
                        "data": {}
                    }
                    
                elif intent == "CAMBIA_DOMANDA_CON_FEEDBACK":
                    self.user_feedback = content
                    return {
                        "action": "REGENERATE_WITH_FEEDBACK",
                        "message": f"Genererò una nuova domanda tenendo in considerazione: '{self.user_feedback}'",
                        "data": {"feedback": self.user_feedback}
                    }
                    
                elif intent == "EXIT":
                    return {
                        "action": "CONFIRM_EXIT",
                        "message": "Vuoi salvare le modifiche alle linee guida prima di uscire? (sì/no)",
                        "data": {}
                    }
                    
                elif intent == "SKIP":
                    ColoredLogger.moderator("Risposta ignorata (skip).")
                    self.conversation_history += f"Domanda: {current_question}\n\nRisposta: [SKIPPED]\n\n"
                    return {
                        "action": "SKIP",
                        "message": "Domanda saltata. Generando una nuova domanda...",
                        "data": {}
                    }
                    
                elif intent == "HELP":
                    help_info = provide_help_info()
                    return {
                        "action": "HELP",
                        "message": help_info,
                        "data": {}
                    }
                    
                elif intent == "CAMBIA_TOPIC":
                    new_topic = content.strip()
                    if not new_topic:
                        return {
                            "action": "INFORM",
                            "message": "Non ho capito a quale topic vuoi cambiare. Continuiamo con il topic attuale.",
                            "data": {}
                        }
                        
                    # Registra la richiesta di cambio topic nella cronologia
                    pair_text = f"Domanda: {current_question}\n\nRisposta: [CAMBIO TOPIC a {new_topic}]"
                    self.conversation_history += pair_text + "\n\n"
                    
                    return {
                        "action": "CHANGE_TOPIC",
                        "message": f"Cambio topic a {new_topic}.",
                        "data": {"new_topic": new_topic}
                    }
                    
                elif intent == "SUGGERISCI_DOMANDA":
                    suggested_question = content
                    
                    # Registra il suggerimento nella cronologia
                    pair_text = f"Domanda: {current_question}\n\nRisposta: [SUGGERIMENTO DOMANDA: {suggested_question}]"
                    self.conversation_history += pair_text + "\n\n"
                    
                    return {
                        "action": "SUGGEST_QUESTION",
                        "message": "Utilizzerò la tua domanda suggerita come base per la prossima.",
                        "data": {"suggestion": suggested_question}
                    }
                    
                elif intent == "IRRELEVANTE":
                    # Registra che la domanda è stata ignorata
                    pair_text = f"Domanda: {current_question}\n\nRisposta: [DOMANDA IRRILEVANTE: {user_input}]"
                    self.conversation_history += pair_text + "\n\n"
                    
                    return {
                        "action": "IRRELEVANT",
                        "message": "La domanda era irrilevante. Generando una domanda più pertinente...",
                        "data": {}
                    }
            
            # Caso speciale: l'utente sta già in modalità feedback e risponde a una domanda di feedback
            if self.in_feedback_mode:
                # Reset della modalità feedback
                self.in_feedback_mode = False
                
                # Gestione delle risposte alla modalità feedback basate sull'input dell'utente
                feedback_intent_prompt = f"""
                L'utente è in modalità feedback per la domanda e ha risposto: "{user_input}"
                Determina quale azione vuole intraprendere:
                1. RIGENERA - Vuole rigenerare una nuova domanda
                2. AGGIUNGI_LINEA_GUIDA - Vuole aggiungere una linea guida
                3. RISPONDI - Vuole rispondere alla domanda originale
                4. NON_CHIARO - Non è chiaro cosa voglia fare
                
                Restituisci SOLO una di queste parole: "RIGENERA", "AGGIUNGI_LINEA_GUIDA", "RISPONDI", "NON_CHIARO"
                """
                
                feedback_intent = timed_generate_text(feedback_intent_prompt, "analisi risposta feedback").strip().upper()
                
                if "RIGENERA" in feedback_intent:
                    # Rigenerazione della domanda
                    self.regenerate_after_feedback = True
                    return {
                        "action": "REGENERATE_QUESTION",
                        "message": "Genererò una nuova domanda rispettando le linee guida...",
                        "data": {}
                    }
                elif "AGGIUNGI_LINEA_GUIDA" in feedback_intent:
                    # Aggiungi linea guida
                    return {
                        "action": "ASK_GUIDELINE",
                        "message": "Inserisci la nuova linea guida che vuoi aggiungere:",
                        "data": {}
                    }
                elif "RISPONDI" in feedback_intent:
                    # Risposta alla domanda originale
                    return {
                        "action": "CONTINUE_WITH_CURRENT",
                        "message": f"Procediamo con la domanda attuale: {self.current_question}",
                        "data": {}
                    }
                else:
                    # Risposta non riconosciuta
                    return {
                        "action": "FEEDBACK_MODE",
                        "message": "Non ho capito la tua risposta. Vuoi:\n1. Rigenerare una nuova domanda\n2. Aggiungere una linea guida specifica\n3. Rispondere comunque a questa domanda",
                        "data": {"feedback_type": "retry"}
                    }
                
        except Exception as e:
            ColoredLogger.error(f"Errore nell'analisi dell'intento: {e}")
        
        # Se abbiamo una risposta suggerita, analizziamo la risposta dell'utente
        # per capire se l'accetta, la modifica o la rifiuta
        if suggestion_response and suggestion_response["found_relevant_info"]:
            return self.process_response_feedback(user_input, current_question, suggestion_response)
        
        # Fallback: tratta come risposta diretta
        pair_text = f"Domanda: {current_question}\n\nRisposta: {user_input}"
        ColoredLogger.moderator("Salvataggio delle informazioni temporanee...")
        info_file_path = save_braindump_entry(pair_text, self.current_topic)
        ColoredLogger.moderator(f"Informazioni salvate in: {info_file_path}")
        
        self.conversation_history += pair_text + "\n\n"
        
        return {
            "action": "CONTINUE",
            "message": "Risposta salvata. Generando una nuova domanda...",
            "data": {"content": user_input}
        }
    
    def process_response_feedback(self, user_input, current_question, suggestion_response):
        """
        Analizza il feedback dell'utente sulla risposta suggerita.
        
        Args:
            user_input (str): Input dell'utente
            current_question (str): La domanda corrente
            suggestion_response (dict): Risposta suggerita dal clone sintetico
            
        Returns:
            dict: Risultato dell'elaborazione
        """
        suggested_response = suggestion_response["response"]
        
        # Determina se l'utente ha accettato, modificato o rifiutato la risposta
        prompt = f"""
        Analizza la reazione dell'utente alla risposta suggerita.
        
        Domanda originale: "{current_question}"
        
        Risposta suggerita: "{suggested_response}"
        
        Reazione dell'utente: "{user_input}"
        
        Determina se l'utente ha:
        1. ACCETTATO la risposta suggerita (es. "sì", "ok", "corretto", "va bene")
        2. MODIFICATO la risposta suggerita (aggiunto/corretto informazioni)
        3. RIFIUTATO la risposta suggerita (es. "no", "non è corretto", "questa non è la mia opinione")
        
        Restituisci solo una di queste parole: "ACCETTATO", "MODIFICATO", o "RIFIUTATO".
        """
        
        reaction = timed_generate_text(prompt, "analisi reazione utente").strip().upper()
        
        if "ACCETTATO" in reaction:
            # L'utente ha accettato la risposta
            pair_text = f"Domanda: {current_question}\n\nRisposta: {suggested_response}"
            ColoredLogger.moderator("L'utente ha accettato la risposta suggerita.")
            save_braindump_entry(pair_text, self.current_topic)
            
            self.conversation_history += pair_text + "\n\n"
            
            return {
                "action": "CONTINUE",
                "message": "Risposta accettata e salvata. Generando una nuova domanda...",
                "data": {"content": suggested_response}
            }
            
        elif "MODIFICATO" in reaction:
            # L'utente ha modificato la risposta
            ColoredLogger.moderator("L'utente ha modificato la risposta suggerita.")
            
            # Genera una risposta combinata
            combined_prompt = f"""
            Combina la risposta suggerita con la modifica dell'utente.
            
            Risposta suggerita: "{suggested_response}"
            
            Modifica dell'utente: "{user_input}"
            
            Genera una risposta finale che incorpori entrambe, mantenendo il formato in prima persona.
            """
            
            combined_response = timed_generate_text(combined_prompt, "combinazione risposte")
            
            # Salva la risposta combinata
            pair_text = f"Domanda: {current_question}\n\nRisposta: {combined_response}"
            save_braindump_entry(pair_text, self.current_topic)
            
            self.conversation_history += pair_text + "\n\n"
            
            return {
                "action": "CONTINUE",
                "message": "Risposta modificata e salvata. Generando una nuova domanda...",
                "data": {"content": combined_response}
            }
            
        else:  # RIFIUTATO
            # L'utente ha rifiutato la risposta
            ColoredLogger.moderator("L'utente ha rifiutato la risposta suggerita.")
            
            # Registra che la risposta suggerita è stata rifiutata
            pair_text = f"Domanda: {current_question}\n\nRisposta: {user_input}"
            save_braindump_entry(pair_text, self.current_topic)
            
            self.conversation_history += pair_text + "\n\n"
            
            return {
                "action": "CONTINUE",
                "message": "La tua risposta è stata salvata. Generando una nuova domanda...",
                "data": {"content": user_input}
            }
    
    def present_suggestion(self, question, synthetic_response):
        """
        Presenta una risposta suggerita all'utente.
        
        Args:
            question (str): La domanda posta
            synthetic_response (dict): La risposta generata dal clone sintetico
            
        Returns:
            str: Il messaggio formattato da presentare all'utente
        """
        response_text = synthetic_response["response"]
        confidence = synthetic_response["confidence"]
        sources = synthetic_response["sources"]
        
        # Formatta la presentazione in base al livello di confidenza
        # Gestisci sia il caso in cui confidence è una stringa che quando è un numero
        if isinstance(confidence, str):
            confidence_text = confidence  # Già nel formato "alto", "medio", "basso"
        else:
            # Converti il valore numerico in testo
            if confidence >= 70:
                confidence_text = "alto"
            elif confidence >= 40:
                confidence_text = "medio"
            else:
                confidence_text = "basso"
        
        sources_text = ", ".join(sources) if sources else "nessuna fonte specifica"
        
        message = f"""Ho trovato una possibile risposta nel tuo braindump (confidenza: {confidence_text}):

{response_text}

Fonti: {sources_text}

Confermi questa risposta? Puoi accettarla, modificarla o fornire una risposta completamente diversa."""
        
        return message
    
    def run_interview(self, selected_topic=None):
        """
        Esegue l'intervista completa, gestendo il flusso di domande e risposte.
        
        Args:
            selected_topic (str, optional): Il topic preselezionato per l'intervista
        """
        # Inizializza la sessione
        self.initialize_session()
        
        # Se non è stato preselezionato un topic, chiedi all'utente di selezionarlo
        if not selected_topic:
            print("\n" + "=" * 50)
            topic_input = input("Seleziona un topic per iniziare l'intervista: ")
            self.current_topic = self.select_topic(topic_input)
        else:
            self.current_topic = selected_topic
            ColoredLogger.moderator(f"Utilizzo il topic preselezionato: {self.current_topic}")
        
        # Genera la prima domanda
        current_question = self.interviewer.generate_first_question(self.current_topic)
        
        # Loop principale dell'intervista
        exit_confirmed = False
        while not exit_confirmed:
            print("\n" + "=" * 50)
            print(f"Domanda: {current_question}")
            
            # Verifica se il clone sintetico ha una risposta da suggerire
            synthetic_response = self.synthetic_clone.generate_response(current_question, self.current_topic)
            
            if synthetic_response["found_relevant_info"]:
                # Presenta la risposta suggerita
                suggestion_message = self.present_suggestion(current_question, synthetic_response)
                print("\n" + "-" * 50)
                print(suggestion_message)
                print("-" * 50)
            
            # Attendi l'input dell'utente
            user_input = input("\nRisposta: ")
            
            # Processa l'input dell'utente
            result = self.process_user_input(user_input, current_question, 
                                            synthetic_response if synthetic_response["found_relevant_info"] else None)
            
            print("\n" + result["message"])
            
            # Gestisci l'azione risultante
            if result["action"] == "CONFIRM_EXIT":
                save_response = input("").lower()
                if save_response in ["sì", "si", "yes", "y", "s"]:
                    self.save_permanent_guidelines()
                    print("Linee guida salvate. Sessione terminata.")
                    exit_confirmed = True
                elif save_response in ["no", "n"]:
                    print("Linee guida non salvate. Sessione terminata.")
                    exit_confirmed = True
                else:
                    print("Risposta non riconosciuta. Continuiamo con l'intervista.")
                    continue
            elif result["action"] == "GUIDELINE_ADDED" or result["action"] == "SHOW_GUIDELINES":
                # Mantieni la stessa domanda dopo aver aggiunto o mostrato le linee guida
                continue
            elif result["action"] == "EXIT":
                break
            elif result["action"] == "HELP":
                # Mostra l'help e riproponi la stessa domanda
                continue
            elif result["action"] == "SKIP":
                # Salta la domanda corrente e genera una nuova
                current_question = self.interviewer.generate_next_question(self.current_topic, self.conversation_history)
            elif result["action"] == "IRRELEVANT":
                # La domanda è stata considerata irrilevante, genera una più pertinente
                current_question = self.interviewer.generate_next_question(self.current_topic, self.conversation_history, irrelevant=True)
            elif result["action"] == "CHANGE_TOPIC":
                # Cambio topic
                self.current_topic = result["data"]["new_topic"]
                print(f"Topic cambiato a: {self.current_topic}")
                current_question = self.interviewer.generate_question_on_topic_change(self.current_topic, self.conversation_history)
            elif result["action"] == "SUGGEST_QUESTION":
                # L'utente ha suggerito una domanda
                suggested_question = result["data"]["suggestion"]
                current_question = self.interviewer.generate_question_from_suggestion(suggested_question, self.current_topic)
            else:  # CONTINUE e INFORM
                # Genera la prossima domanda
                current_question = self.interviewer.generate_next_question(self.current_topic, self.conversation_history)
        
        # Finalizza la sessione
        finalize_session(self.conversation_history) 
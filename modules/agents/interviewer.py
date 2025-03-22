"""
Agente Intervistatore: genera domande pertinenti per l'intervista.
"""

import os
import re
from modules.dynamic_prompt import build_dynamic_prompt
from modules.question_handler import (
    generate_new_question, 
    generate_new_question_after_skip, 
    generate_more_relevant_question,
    is_similar_to_previous
)
from modules.context_handler import get_relevant_context
from modules.llm_handler import timed_generate_text, filter_llm_response
from modules.logger import ColoredLogger
from config import INFORMATION_DIR, CONCEPTS_DIR, TEMP_FOLDER

class ContextHandler:
    """
    Gestisce il recupero di informazioni contestuali dai file di Braindump.
    """
    
    def __init__(self):
        """Inizializza il gestore di contesto."""
        self.concept_dir = CONCEPTS_DIR
        self.information_dir = INFORMATION_DIR
    
    def fetch_concept_definition(self, topic):
        """
        Recupera i file di definizione del concetto per un topic specifico.
        
        Args:
            topic (str): Il topic su cui cercare definizioni
            
        Returns:
            list: Lista di percorsi dei file pertinenti
        """
        topic_lower = topic.lower()
        result_files = []
        
        # Cerca file nella directory dei concetti che contengono il topic nel nome
        if os.path.exists(self.concept_dir):
            for filename in os.listdir(self.concept_dir):
                if filename.lower().endswith('.md') and topic_lower in filename.lower():
                    file_path = os.path.join(self.concept_dir, filename)
                    result_files.append(file_path)
                    ColoredLogger.interviewer(f"Trovato file definizione concetto: {filename}")
        
        return result_files
    
    def fetch_relevant_context(self, topic, conversation_history=""):
        """
        Cerca file di contesto rilevanti in base al topic e alla conversazione.
        
        Args:
            topic (str): Il topic principale
            conversation_history (str, optional): Storia della conversazione 
            
        Returns:
            list: Lista di percorsi dei file pertinenti
        """
        relevant_files = []
        
        # Prima cerca file direttamente correlati al topic
        topic_files = self.fetch_concept_definition(topic)
        relevant_files.extend(topic_files)
        
        # Estrae parole chiave dalla storia della conversazione recente
        if conversation_history:
            recent_keywords = self._extract_keywords(conversation_history)
            ColoredLogger.interviewer(f"Parole chiave estratte: {', '.join(recent_keywords[:5])}...")
            
            # Cerca file che contengono queste parole chiave
            for keyword in recent_keywords[:3]:  # Limita a 3 parole chiave per efficienza
                if len(keyword) > 3:  # Ignora parole troppo brevi
                    keyword_files = self._find_files_with_keyword(keyword)
                    for file in keyword_files:
                        if file not in relevant_files:
                            relevant_files.append(file)
        
        ColoredLogger.interviewer(f"Trovati {len(relevant_files)} file di contesto rilevanti")
        return relevant_files
    
    def _extract_keywords(self, text):
        """
        Estrae parole chiave significative dal testo.
        
        Args:
            text (str): Il testo da analizzare
            
        Returns:
            list: Lista di parole chiave
        """
        # Semplice implementazione che estrae parole non comuni
        common_words = {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una", 
                       "e", "o", "ma", "se", "per", "con", "su", "in", "da", "a", 
                       "che", "chi", "come", "dove", "quando", "perché", "cosa",
                       "del", "della", "dei", "degli", "delle", "questo", "questa",
                       "questi", "queste", "quello", "quella", "quelli", "quelle"}
        
        # Estrae tutte le parole dal testo
        words = re.findall(r'\b\w{3,}\b', text.lower())
        
        # Filtra parole comuni e ordina per lunghezza (presupponendo che parole più lunghe siano più specifiche)
        keywords = [word for word in words if word not in common_words]
        keywords.sort(key=len, reverse=True)
        
        # Rimuove duplicati mantenendo l'ordine
        unique_keywords = []
        seen = set()
        for word in keywords:
            if word not in seen:
                unique_keywords.append(word)
                seen.add(word)
        
        return unique_keywords
    
    def _find_files_with_keyword(self, keyword):
        """
        Trova file che contengono una parola chiave.
        
        Args:
            keyword (str): La parola chiave da cercare
            
        Returns:
            list: Lista di percorsi di file che contengono la parola chiave
        """
        matching_files = []
        
        # Cerca nei file dei concetti
        if os.path.exists(self.concept_dir):
            for filename in os.listdir(self.concept_dir):
                if filename.endswith('.md'):
                    file_path = os.path.join(self.concept_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if keyword.lower() in content.lower():
                                matching_files.append(file_path)
                    except Exception as e:
                        ColoredLogger.error(f"Errore nella lettura del file {file_path}: {e}")
        
        # Cerca nei file delle informazioni
        if os.path.exists(self.information_dir):
            for filename in os.listdir(self.information_dir):
                if filename.endswith('.md'):
                    file_path = os.path.join(self.information_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if keyword.lower() in content.lower():
                                matching_files.append(file_path)
                    except Exception as e:
                        ColoredLogger.error(f"Errore nella lettura del file {file_path}: {e}")
        
        return matching_files

class Interviewer:
    """
    Agente che si occupa di generare domande pertinenti basate sul topic
    e sulla conversazione precedente.
    """
    
    def __init__(self):
        """Inizializza l'agente intervistatore."""
        self.previous_questions = []
        self.questions_asked = []
        self.last_question = ""
        self.available_topics = self._load_available_topics()
        self.temp_guidelines_file = os.path.join(TEMP_FOLDER, "temp_guidelines.md")
        self.context_handler = ContextHandler()  # Aggiunto il gestore di contesto
    
    def _load_available_topics(self):
        """Carica i topic disponibili esclusivamente dalle directory dei dati."""
        topics = set()  # Inizia con un set vuoto senza topic predefiniti
        
        # Cartella dei concetti
        if os.path.exists(CONCEPTS_DIR):
            ColoredLogger.interviewer(f"Cerco topic nella cartella {CONCEPTS_DIR}")
            for filename in os.listdir(CONCEPTS_DIR):
                if filename.endswith(".md"):
                    # Estrai il nome del topic dal nome del file
                    topic = filename.replace(".md", "").replace("_", " ").title()
                    topics.add(topic)
                    ColoredLogger.interviewer(f"Aggiunto topic: {topic}")
        
        if not topics:
            ColoredLogger.warning("Nessun topic trovato nei file. Crea file .md nelle cartelle dei dati.")
        else:
            ColoredLogger.interviewer(f"Trovati {len(topics)} topic: {', '.join(topics)}")
        
        return sorted(list(topics))
    
    def get_topics_presentation(self):
        """Restituisce una presentazione formattata dei topic disponibili."""
        if not self.available_topics:
            return "Nessun topic disponibile. Aggiungi file .md nelle cartelle dei dati."
        
        topics_text = "\n".join([f"{i+1}. {topic}" for i, topic in enumerate(self.available_topics)])
        return f"""Ecco i topic disponibili su cui posso intervistarti:

{topics_text}

Scegli un topic digitando il numero corrispondente o suggeriscine uno nuovo. 
Puoi anche digitare 'cambia topic' in qualsiasi momento."""
    
    def get_current_guidelines(self):
        """
        Ottiene le linee guida correnti dal file temporaneo o permanente.
        
        Returns:
            str: Le linee guida per la generazione di domande
        """
        try:
            import os
            from config import TEMP_FOLDER
            
            # Path del file temporaneo delle linee guida
            temp_guidelines_path = os.path.join(TEMP_FOLDER, "interviewer_guidelines.md")
            
            # Path del file permanente delle linee guida
            permanent_guidelines_path = os.path.join("guidelines", "interviewer_guidelines.md")
            
            if os.path.exists(temp_guidelines_path):
                # Usa il file temporaneo se esiste
                with open(temp_guidelines_path, "r", encoding="utf-8") as f:
                    return f.read()
            elif os.path.exists(permanent_guidelines_path):
                # Usa il file permanente se quello temporaneo non esiste
                ColoredLogger.interviewer(f"Usando il file permanente delle linee guida: {permanent_guidelines_path}")
                with open(permanent_guidelines_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                ColoredLogger.warning("Nessun file di linee guida trovato, usando linee guida predefinite")
                return """
                - Fai domande personali e specifiche sul topic
                - Evita domande generiche o troppo vaghe
                - Le domande devono essere pertinenti alle esperienze dell'utente
                - Non chiedere informazioni troppo sensibili o private
                """
        except Exception as e:
            ColoredLogger.error(f"Errore nel recupero delle linee guida: {e}")
            return "Fai domande personali e specifiche sul topic scelto"
    
    def generate_first_question(self, topic):
        """
        Genera la prima domanda per iniziare l'intervista.
        
        Args:
            topic (str): Il topic scelto
            
        Returns:
            str: La domanda generata
        """
        ColoredLogger.interviewer(f"Generazione della prima domanda sul topic '{topic}'...")
        
        # Ottieni le linee guida per la generazione di domande
        guidelines = self.get_current_guidelines()
        
        # Costruzione del prompt con più dettagli sul topic e sulle linee guida
        prompt = f"""
        Genera una domanda introduttiva e aperta in italiano sul topic '{topic}'.
        
        LINEE GUIDA:
        {guidelines}
        
        REGOLE SPECIFICHE:
        - La domanda deve essere in italiano
        - La domanda deve essere personale e diretta all'utente
        - Deve essere specifica sul topic '{topic}' e non generale
        - Evita domande generiche come "Cosa ne pensi di {topic}?"
        - Non usare MAI placeholder come [topic] o [argomento]
        - Usa direttamente il termine "{topic}" nella domanda se necessario
        - La domanda deve invitare a una risposta elaborata (non sì/no)
        - La domanda deve sembrare naturale e conversazionale
        
        IMPORTANTE: Rispondi SOLO con la domanda, senza introduzioni o spiegazioni.
        """
        
        # Genera la domanda
        question = timed_generate_text(prompt, "generazione prima domanda")
        
        # Filtra e migliora il risultato
        filtered_question = filter_llm_response(question, topic)
        
        # Salva la domanda come ultima domanda posta
        self.last_question = filtered_question
        self.questions_asked.append(filtered_question)
        
        return filtered_question
    
    def generate_next_question(self, topic, conversation_history, irrelevant=False):
        """
        Genera la prossima domanda in base alla conversazione precedente.
        
        Args:
            topic (str): Il topic dell'intervista
            conversation_history (str): La storia della conversazione
            irrelevant (bool): Indica se la risposta precedente è stata irrilevante
            
        Returns:
            str: La domanda generata
        """
        ColoredLogger.interviewer(f"Generazione della prossima domanda sul topic '{topic}'...")
        
        # Ottieni le linee guida attuali
        guidelines = self.get_current_guidelines()
        
        if irrelevant:
            prompt = f"""
            La persona ha indicato che la domanda precedente non era rilevante.
            
            Genera una nuova domanda in italiano sul topic '{topic}' che sia:
            1. Più specifica e rilevante
            2. Personale e diretta all'utente
            
            LINEE GUIDA:
            {guidelines}
            
            Conversazione precedente:
            {conversation_history}
            
            REGOLE SPECIFICHE:
            - La domanda deve essere in italiano
            - Non usare MAI placeholder come [topic] o [argomento]
            - Usa direttamente il termine "{topic}" se necessario
            - La domanda deve essere DIVERSA dalle precedenti
            - Focalizzati su un aspetto specifico del topic
            - Assicurati che la domanda sia rilevante per la vita personale dell'utente
            
            IMPORTANTE: Rispondi SOLO con la domanda, senza introduzioni o spiegazioni.
            """
        else:
            prompt = f"""
            Analizza la conversazione precedente e genera una domanda di approfondimento in italiano sul topic '{topic}'.
            
            LINEE GUIDA:
            {guidelines}
            
            Conversazione precedente:
            {conversation_history}
            
            REGOLE SPECIFICHE:
            - La domanda deve seguire naturalmente dalla conversazione e approfondire elementi emersi
            - La domanda deve essere in italiano
            - La domanda deve essere personale e diretta all'utente
            - Non usare MAI placeholder come [topic] o [argomento]
            - Usa direttamente il termine "{topic}" se necessario
            - La domanda deve invitare a una risposta elaborata (non sì/no)
            - La domanda deve essere diversa dalle precedenti
            
            IMPORTANTE: Rispondi SOLO con la domanda, senza introduzioni o spiegazioni.
            """
        
        # Genera la domanda
        question = timed_generate_text(prompt, "generazione domanda successiva")
        
        # Filtra e migliora il risultato
        filtered_question = filter_llm_response(question, topic)
        
        # Salva la domanda come ultima domanda posta
        self.last_question = filtered_question
        self.questions_asked.append(filtered_question)
        
        return filtered_question
    
    def generate_question_on_topic_change(self, new_topic, conversation_history):
        """
        Genera una domanda quando l'utente cambia topic.
        
        Args:
            new_topic (str): Il nuovo topic scelto
            conversation_history (str): La storia della conversazione
            
        Returns:
            str: La nuova domanda sul nuovo topic
        """
        ColoredLogger.interviewer(f"Generazione domanda per nuovo topic '{new_topic}'...")
        
        # Ottieni le linee guida per il nuovo topic
        guidelines = self.get_current_guidelines()
        
        prompt = f"""
        L'utente ha cambiato l'argomento della conversazione al topic '{new_topic}'.
        
        Genera una domanda introduttiva in italiano sul nuovo topic '{new_topic}' che sia:
        1. Personale e diretta all'utente
        2. Specifica e rilevante per il topic '{new_topic}'
        
        LINEE GUIDA:
        {guidelines}
        
        REGOLE SPECIFICHE:
        - La domanda deve essere in italiano
        - Non usare MAI placeholder come [topic] o [argomento]
        - Usa direttamente il termine "{new_topic}" se necessario
        - La domanda deve invitare a una risposta elaborata (non sì/no)
        - Deve essere una domanda aperta e coinvolgente
        
        IMPORTANTE: Rispondi SOLO con la domanda, senza introduzioni o spiegazioni.
        """
        
        # Genera la domanda
        question = timed_generate_text(prompt, "generazione domanda per nuovo topic")
        
        # Filtra e migliora il risultato
        filtered_question = filter_llm_response(question, new_topic)
        
        # Salva la domanda come ultima domanda posta
        self.last_question = filtered_question
        self.questions_asked.append(filtered_question)
        
        return filtered_question
    
    def generate_question_from_suggestion(self, topic, suggestion, conversation_history):
        """
        Genera una domanda basata su un suggerimento dell'utente.
        
        Args:
            topic (str): Il topic dell'intervista
            suggestion (str): Il suggerimento dell'utente
            conversation_history (str): La storia della conversazione
            
        Returns:
            str: La domanda generata
        """
        ColoredLogger.interviewer(f"Generazione domanda basata sul suggerimento: '{suggestion}'...")
        
        # Ottieni le linee guida attuali
        guidelines = self.get_current_guidelines()
        
        prompt = f"""
        L'utente ha suggerito di parlare di: "{suggestion}"
        
        Genera una domanda in italiano che:
        1. Si basi direttamente su questo suggerimento
        2. Sia collegata al topic principale '{topic}'
        3. Sia personale e diretta all'utente
        
        LINEE GUIDA:
        {guidelines}
        
        Conversazione precedente:
        {conversation_history}
        
        REGOLE SPECIFICHE:
        - La domanda deve essere in italiano
        - Non usare MAI placeholder come [topic] o [argomento]
        - Usa direttamente i termini esatti dal suggerimento dell'utente
        - La domanda deve invitare a una risposta elaborata
        - Deve essere specifica e non generica
        
        IMPORTANTE: Rispondi SOLO con la domanda, senza introduzioni o spiegazioni.
        """
        
        # Genera la domanda
        question = timed_generate_text(prompt, "generazione domanda da suggerimento")
        
        # Filtra e migliora il risultato
        filtered_question = filter_llm_response(question, topic)
        
        # Salva la domanda come ultima domanda posta
        self.last_question = filtered_question
        self.questions_asked.append(filtered_question)
        
        return filtered_question
    
    def generate_question_by_type(self, question_type, topic, conversation_history=""):
        """
        Genera una domanda di tipo specifico utilizzando le linee guida.
        
        Args:
            question_type (str): Il tipo di domanda da generare
            topic (str): Il topic su cui generare la domanda
            conversation_history (str, optional): Storia della conversazione per contesto
            
        Returns:
            str: La domanda generata
        """
        ColoredLogger.interviewer(f"Genero una domanda di tipo '{question_type}' sul topic '{topic}'...")
        
        # Ottieni le linee guida attuali
        guidelines = self.get_current_guidelines()
        
        # Semplifica il contesto/storico della conversazione se troppo lungo
        if len(conversation_history) > 2000:
            # Estrai solo le ultime 3-5 domande/risposte
            conversation_pairs = re.findall(r"Domanda: (.*?)\n\nRisposta: (.*?)(?=\n\nDomanda:|$)", 
                                           conversation_history, re.DOTALL)
            simplified_history = ""
            for i in range(max(0, len(conversation_pairs) - 5), len(conversation_pairs)):
                q, a = conversation_pairs[i]
                simplified_history += f"Domanda: {q}\n\nRisposta: {a}\n\n"
            conversation_history = simplified_history
        
        # Prepara il prompt con le linee guida e i dettagli specifici del tipo di domanda
        prompt = f"""
        Genera una domanda di tipo '{question_type}' sul topic '{topic}' rispettando le seguenti linee guida:
        
        {guidelines}
        
        Dettagli specifici per questo tipo di domanda:
        """
        
        # Aggiungi dettagli specifici in base al tipo di domanda
        if question_type == "esperienza_personale":
            prompt += """
            - Chiedi di un'esperienza personale specifica
            - La domanda deve invitare a raccontare una storia o aneddoto
            - Usa parole come "quando", "racconta", "descrivi un momento in cui"
            """
        elif question_type == "opinione":
            prompt += """
            - Chiedi un'opinione o punto di vista personale
            - La domanda deve stimolare riflessione
            - Usa frasi come "cosa pensi di", "qual è la tua opinione su"
            """
        elif question_type == "preferenza":
            prompt += """
            - Chiedi una preferenza personale
            - La domanda deve far emergere gusti e inclinazioni
            - Usa frasi come "preferisci", "cosa ti piace di più", "tra X e Y"
            """
        elif question_type == "comportamento":
            prompt += """
            - Chiedi informazioni su abitudini o comportamenti ricorrenti
            - La domanda deve far emergere pattern quotidiani
            - Usa frasi come "come ti comporti quando", "quale è la tua routine"
            """
        else:  # Domanda generica
            prompt += """
            - Crea una domanda aperta e personale
            - La domanda deve stimolare una risposta articolata
            - Evita domande a cui si può rispondere con sì/no
            """
        
        # Aggiungi contesto della conversazione se disponibile
        if conversation_history:
            prompt += f"""
            
            Considera la conversazione avvenuta finora:
            {conversation_history}
            
            - Evita di ripetere domande simili a quelle già poste
            - Costruisci su informazioni già emerse
            - Mantieni coerenza con il flusso della conversazione
            """
        
        prompt += """
        
        IMPORTANTE:
        - La domanda deve essere singola e diretta (non porre più domande insieme)
        - Deve essere personale e rivolta all'interlocutore in seconda persona
        - Non includere premesse o introduzioni lunghe
        - La domanda dovrebbe essere specifica, non generica
        - Essere adatta a un'intervista personale, non a un quiz o esame
        
        Restituisci SOLO la domanda, senza introduzioni o spiegazioni.
        """
        
        # Genera la domanda
        new_question = timed_generate_text(prompt, "generazione domanda per tipo")
        
        # Verifica la conformità della domanda alle linee guida
        from modules.response_handler import evaluate_question_compliance
        
        compliance_result = evaluate_question_compliance(new_question, guidelines)
        
        # Se la domanda non è conforme, rigenera con feedback
        if not compliance_result["compliant"]:
            ColoredLogger.warning(f"Domanda non conforme: {compliance_result['explanation']}")
            
            # Rigenera con le indicazioni di miglioramento
            improvement_prompt = f"""
            La domanda generata non rispetta le linee guida. Ecco il feedback:
            
            Domanda originale: "{new_question}"
            
            Problemi: {compliance_result['explanation']}
            
            Suggerimenti: {compliance_result['improvement_suggestions']}
            
            Genera una nuova domanda di tipo '{question_type}' sul topic '{topic}' che risolva questi problemi.
            Restituisci SOLO la domanda, senza introduzioni o spiegazioni.
            """
            
            # Rigenera la domanda
            new_question = timed_generate_text(improvement_prompt, "rigenerazione domanda conforme")
        
        return new_question.strip()
    
    def generate_question_with_context(self, topic, context_files, conversation_history="", more_relevant=False):
        """
        Genera una domanda utilizzando file di contesto specifici.
        
        Args:
            topic (str): Il topic su cui generare la domanda
            context_files (list): Lista di file di contesto rilevanti
            conversation_history (str, optional): Storia della conversazione
            more_relevant (bool, optional): Se True, genera una domanda più rilevante
            
        Returns:
            str: La domanda generata
        """
        # Prepara il contesto dai file
        context_text = ""
        for file_path in context_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                file_name = os.path.basename(file_path)
                context_text += f"\n--- {file_name} ---\n{file_content}\n"
            except Exception as e:
                ColoredLogger.error(f"Errore nella lettura del file {file_path}: {e}")
        
        # Ottiene le linee guida attuali
        guidelines = self.get_current_guidelines()
        
        # Crea il prompt per la generazione della domanda
        if more_relevant:
            prompt = f"""
            Genera una domanda ESTREMAMENTE RILEVANTE sul topic '{topic}' utilizzando il seguente contesto.
            
            CONTESTO:
            {context_text}
            
            LINEE GUIDA:
            {guidelines}
            
            La domanda precedente è stata considerata non rilevante dall'utente.
            Genera una domanda che sia:
            1. Strettamente connessa al significato principale del topic '{topic}'
            2. Chiaramente rilevante per l'utente
            3. Specifica e personale, non generica
            4. Basata sulle informazioni nei file di contesto forniti
            
            Non menzionare che stai generando una domanda più rilevante.
            Restituisci SOLO la domanda, senza introduzioni o spiegazioni.
            """
        else:
            prompt = f"""
            Genera una domanda interessante sul topic '{topic}' utilizzando il seguente contesto.
            
            CONTESTO:
            {context_text}
            
            LINEE GUIDA:
            {guidelines}
            
            """
            
            # Aggiungi il contesto della conversazione se disponibile
            if conversation_history:
                prompt += f"""
                CONVERSAZIONE FINORA:
                {conversation_history}
                
                Considera la conversazione precedente per:
                - Evitare di ripetere domande simili
                - Costruire su informazioni già condivise
                - Mantenere un flusso di conversazione naturale
                """
            
            prompt += """
            La domanda deve essere:
            1. Personale e specifica all'utente
            2. Chiaramente collegata al topic e al contesto fornito
            3. Aperta e stimolante per una risposta articolata
            4. Formulata in modo diretto e conversazionale
            
            Restituisci SOLO la domanda, senza introduzioni o spiegazioni.
            """
        
        # Genera la domanda
        question = timed_generate_text(prompt, "generazione domanda con contesto")
        
        # Verifica la conformità della domanda alle linee guida
        from modules.response_handler import evaluate_question_compliance
        
        compliance_result = evaluate_question_compliance(question, guidelines)
        
        # Se la domanda non è conforme, rigenera con feedback
        if not compliance_result["compliant"]:
            ColoredLogger.warning(f"Domanda non conforme: {compliance_result['explanation']}")
            
            # Rigenera con le indicazioni di miglioramento
            improvement_prompt = f"""
            La domanda generata non rispetta le linee guida. Ecco il feedback:
            
            Domanda originale: "{question}"
            
            Problemi: {compliance_result['explanation']}
            
            Suggerimenti: {compliance_result['improvement_suggestions']}
            
            Topic: '{topic}'
            
            CONTESTO:
            {context_text[:500]}... [troncato]
            
            Genera una nuova domanda che risolva questi problemi e sia più conforme alle linee guida.
            Restituisci SOLO la domanda, senza introduzioni o spiegazioni.
            """
            
            # Rigenera la domanda
            question = timed_generate_text(improvement_prompt, "rigenerazione domanda conforme con contesto")
        
        return question.strip() 
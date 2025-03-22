"""
Sistema multi-agente per l'intervista Braindump.

Questo modulo coordina i tre agenti:
1. Intervistatore: genera domande pertinenti
2. Clone Sintetico: consulta il braindump esistente
3. Moderatore: coordina l'interazione
"""

import os
from modules.agents.interviewer import Interviewer
from modules.agents.synthetic_clone import SyntheticClone
from modules.agents.moderator import Moderator
from modules.logger import ColoredLogger

class MultiAgentSystem:
    """
    Classe che coordina i tre agenti e inizializza il sistema di intervista.
    """
    
    def __init__(self):
        """Inizializza il sistema multi-agente con i tre agenti principali."""
        self.interviewer = Interviewer()
        self.synthetic_clone = SyntheticClone()
        self.moderator = Moderator(self.interviewer, self.synthetic_clone)
    
    def start(self):
        """Avvia il sistema di intervista multi-agente."""
        ColoredLogger.system("Avvio del sistema multi-agente Braindump...")
        
        # Inizializza la sessione
        self.moderator.initialize_session()
        
        # Mostra introduzione
        print("\n" + "=" * 80)
        print(" 🤖 SISTEMA MULTI-AGENTE BRAINDUMP")
        print("=" * 80)
        print("""
Questo sistema utilizza tre agenti per supportare la tua intervista:

📝 Intervistatore: genera domande rilevanti sul topic scelto
🧠 Clone Sintetico: consulta il tuo braindump esistente per supportare le risposte
🎯 Moderatore: gestisce l'interazione tra gli agenti e coordina il processo

Quando possibile, il sistema cercherà di recuperare informazioni dal tuo braindump
esistente e ti offrirà la possibilità di confermare o modificare la risposta.
Per domande nuove, puoi rispondere normalmente.
        """)
        
        # Mostra la presentazione dei topic disponibili
        topics_presentation = self.interviewer.get_topics_presentation()
        print("\n" + "-" * 60)
        print(" TOPIC DISPONIBILI")
        print("-" * 60)
        print(topics_presentation)
        print("-" * 60 + "\n")
        
        # Chiedi all'utente di selezionare un topic
        topic_input = input("Inserisci il numero o il nome del topic desiderato: ")
        selected_topic = self.moderator.select_topic(topic_input)
        
        # Avvia l'intervista
        self.moderator.run_interview(selected_topic)


def start_multiagent_interview():
    """Avvia il sistema di intervista multi-agente."""
    system = MultiAgentSystem()
    system.start()


if __name__ == "__main__":
    start_multiagent_interview() 
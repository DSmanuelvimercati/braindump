import os
import yaml

def determine_next_question(data_directory='data', max_files=3):
    """
    Legge i file Markdown salvati nel braindump, estrae solo i campi 'question' e 'answer'
    se presenti e non vuoti, e costruisce un prompt di sistema pulito.
    """
    files = sorted([f for f in os.listdir(data_directory) if f.endswith('.md')])
    recent_files = files[-max_files:] if len(files) > max_files else files
    
    context_parts = []
    for filename in recent_files:
        filepath = os.path.join(data_directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Rimuovi i delimitatori '---'
            content = content.replace('---', '')
            try:
                frontmatter = yaml.safe_load(content)
                q = frontmatter.get('question', '').strip() if frontmatter.get('question') else ""
                a = frontmatter.get('answer', '').strip() if frontmatter.get('answer') else ""
                if q:  # includi solo se c'è una domanda
                    context_parts.append(f"Domanda: {q}\nRisposta: {a}")
            except Exception:
                continue
    
    context = "\n\n".join(context_parts)
    system_prompt = (
        "Sei un agente intervistatore intelligente e conciso. Di seguito trovi un riepilogo dei dati raccolti (solo domande e risposte rilevanti):\n\n"
        f"{context}\n\n"
        "Basandoti su queste informazioni, formula una nuova domanda di follow-up che approfondisca ulteriormente la conversazione. "
        "Assicurati di non ripetere la domanda già formulata e di porre una domanda che espanda il tema in maniera innovativa. "
        "Rispondi solo con la nuova domanda."
    )
    
    return system_prompt

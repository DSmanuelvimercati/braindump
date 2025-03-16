import os
import yaml
from datetime import datetime

def save_package(package, directory='data'):
    """
    Salva il pacchetto in un file Markdown con frontmatter YAML contenente:
    - date (timestamp)
    - question
    - answer
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Crea un timestamp per generare un nome file unico
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"package-{timestamp}.md"
    filepath = os.path.join(directory, filename)
    
    # Costruisci il frontmatter con i dati essenziali
    frontmatter = {
        'date': datetime.now().isoformat(),
        'question': package.get('question', ''),
        'answer': package.get('answer', '')
    }
    
    # Il contenuto del file sarà costituito solo dal frontmatter
    content = "---\n" + yaml.dump(frontmatter) + "---\n"
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Pacchetto salvato in {filepath}")
        return True
    except Exception as e:
        print(f"Errore durante il salvataggio: {e}")
        return False

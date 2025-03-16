import os
import yaml
import markdown

def read_markdown_file(filepath):
    """
    Legge un file Markdown e ne estrae il frontmatter YAML (se presente) e il contenuto.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Supponiamo che il frontmatter sia racchiuso tra '---'
    if lines[0].strip() == '---':
        end_index = lines[1:].index('---\n') + 1
        frontmatter = yaml.safe_load("".join(lines[1:end_index]))
        content = "".join(lines[end_index+1:])
    else:
        frontmatter = {}
        content = "".join(lines)
    
    return frontmatter, content

def index_markdown_files(directory='data'):
    """
    Scansiona la directory 'data' e legge tutti i file Markdown.
    """
    indexed_data = {}
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            path = os.path.join(directory, filename)
            frontmatter, content = read_markdown_file(path)
            indexed_data[filename] = {
                'metadata': frontmatter,
                'content': content
            }
    return indexed_data

def identify_gaps(text):
    """
    Utilizza il LLM locale per analizzare il testo e identificare lacune.
    Per ora restituisce una placeholder.
    """
    # In futuro qui integrerai il tuo modello di LLM (es. HuggingFace pipeline)
    return f"Lacuna individuata in: {text[:30]}..."

def generate_question(gap_description):
    """
    Utilizza il LLM per generare una domanda mirata a colmare la lacuna.
    Per ora restituisce una placeholder.
    """
    return f"Domanda per colmare la lacuna: {gap_description}"

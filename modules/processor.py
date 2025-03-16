import os
import yaml
import markdown
from modules.llm import generate_text

def read_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if lines[0].strip() == '---':
        end_index = lines[1:].index('---\n') + 1
        frontmatter = yaml.safe_load("".join(lines[1:end_index]))
        content = "".join(lines[end_index+1:])
    else:
        frontmatter = {}
        content = "".join(lines)
    
    return frontmatter, content

def index_markdown_files(directory='data'):
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
    Usa il LLM per analizzare il testo e identificare lacune.
    Ad esempio, il prompt può essere "Identifica eventuali lacune informative in questo testo: ..."
    """
    prompt = f"Identifica eventuali lacune informative in questo testo:\n\n{text}\n\nLacune:"
    return generate_text(prompt)

def generate_question(gap_description):
    """
    Usa il LLM per generare una domanda mirata a colmare la lacuna individuata.
    """
    prompt = f"Genera una domanda che possa colmare la seguente lacuna informativa: {gap_description}"
    return generate_text(prompt)

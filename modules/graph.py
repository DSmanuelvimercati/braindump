import os
import re
import networkx as nx

def build_graph_from_data(directory='data'):
    """
    Scansiona i file Markdown nella cartella 'data' e costruisce un grafo.
    I nodi rappresentano i file e gli archi collegano i file se vengono trovati hyperlink nel contenuto.
    """
    G = nx.DiGraph()
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            # Aggiungi il nodo con il contenuto come attributo
            G.add_node(filename, content=content)
            # Cerca link nel formato Markdown: [testo](link)
            links = re.findall(r'\[.*?\]\((.*?)\)', content)
            for link in links:
                G.add_edge(filename, link)
    return G

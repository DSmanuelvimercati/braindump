import requests
import json
from modules.ollama_config import OLLAMA_GENERATE_ENDPOINT, DEFAULT_MODEL, DEFAULT_PARAMS

def generate_text(prompt, max_new_tokens=None, temperature=None, top_p=None):
    """
    Invia il prompt all'API di Ollama e restituisce la risposta generata.
    
    Args:
        prompt: Il testo da inviare al modello
        max_new_tokens: Numero massimo di token da generare (override del valore predefinito)
        temperature: Temperatura per la generazione (override del valore predefinito)
        top_p: Parametro top_p per la generazione (override del valore predefinito)
    
    Returns:
        La risposta generata dal modello
    """
    try:
        # Utilizzo i parametri forniti o i default da ollama_config
        max_tokens = max_new_tokens or DEFAULT_PARAMS["max_tokens"]
        temp = temperature or DEFAULT_PARAMS["temperature"]
        topp = top_p or DEFAULT_PARAMS["top_p"]
        
        payload = {
            "model": DEFAULT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "top_p": topp,
                "num_predict": max_tokens
            }
        }
        
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            print(f"Errore nella chiamata a Ollama: {response.status_code}")
            print(f"Dettagli: {response.text}")
            return "Si è verificato un errore nella generazione del testo."
    except Exception as e:
        print(f"Eccezione durante la chiamata a Ollama: {str(e)}")
        return "Si è verificato un errore nella connessione a Ollama."

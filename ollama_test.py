#!/usr/bin/env python3
"""
Script di utilità per testare la connessione a Ollama e verificare quali modelli sono disponibili.
"""

import requests
import sys
from modules.ollama_config import OLLAMA_API_BASE, DEFAULT_MODEL, get_available_models
from modules.llm import generate_text

def check_ollama_running():
    """Verifica se Ollama è in esecuzione"""
    try:
        response = requests.get(f"{OLLAMA_API_BASE}/api/tags")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def main():
    print("Test di connessione a Ollama...")
    
    if not check_ollama_running():
        print("❌ Errore: Ollama non sembra essere in esecuzione.")
        print(f"   Verificare che Ollama sia avviato e in ascolto su: {OLLAMA_API_BASE}")
        print("\nSe Ollama non è installato:")
        print("1. Scaricarlo da: https://ollama.com/download")
        print("2. Installarlo e avviarlo")
        sys.exit(1)
    
    print("✅ Connessione a Ollama riuscita!")
    
    # Ottieni modelli disponibili
    models = get_available_models()
    
    if not models:
        print("\n❓ Non sono stati trovati modelli o si è verificato un errore nel recuperarli.")
        print("   Prova a eseguire 'ollama list' dal terminale per vedere i modelli disponibili.")
    else:
        print(f"\nModelli disponibili ({len(models)}):")
        for model in models:
            print(f"- {model}")
    
    print(f"\nModello configurato per l'uso: {DEFAULT_MODEL}")
    
    if DEFAULT_MODEL not in models and models:
        print(f"⚠️  ATTENZIONE: Il modello configurato '{DEFAULT_MODEL}' non sembra essere disponibile.")
        print(f"   Considera di scaricarlo con 'ollama pull {DEFAULT_MODEL}' o")
        print(f"   modificare il valore DEFAULT_MODEL in modules/ollama_config.py con uno dei modelli disponibili.")
    
    # Test di generazione di testo
    if input("\nVuoi eseguire un test di generazione di testo? (s/N): ").lower() == 's':
        try:
            prompt = "Scrivi una breve poesia sulla programmazione in italiano:"
            print(f"\nPrompt di test: {prompt}")
            print("\nGenerazione in corso...")
            
            response = generate_text(prompt)
            
            print("\nRisposta generata:")
            print("-" * 40)
            print(response)
            print("-" * 40)
            print("\n✅ Test completato con successo!")
        except Exception as e:
            print(f"\n❌ Errore durante il test di generazione: {str(e)}")

if __name__ == "__main__":
    main() 
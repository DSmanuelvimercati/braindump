"""
Modalità INTERVISTATORE: il modello fa domande attive all'utente per espandere il vault.
Legge il vault esistente per capire cosa manca e costruisce domande contestuali.
"""

from core.voice import Voice
from core.model import think
from core import extractor, vault


SYSTEM_INTERVIEWER = """Sei un intervistatore curioso e attento che aiuta una persona a costruire la propria autobiografia digitale.
Hai accesso al vault con le informazioni già raccolte sulla persona.
Il tuo compito è fare domande intelligenti per scoprire nuove informazioni o approfondire quelle già presenti.

Regole:
- Fai UNA sola domanda alla volta, breve e diretta
- Parti dal contesto esistente nel vault — non ripetere cose già note
- Alterna tra diversi ambiti: lavoro, persone, esperienze, idee, emozioni
- Le domande devono essere in italiano
- Non fare domande generiche tipo "come stai" — sii specifico e curioso
- Rispondi SOLO con la domanda, niente altro"""


def _generate_question(history: list) -> str:
    vault_ctx = vault.context_summary()
    history_str = "\n".join(f"- {h}" for h in history[-10:]) if history else "Nessuna domanda ancora."

    prompt = f"""Vault esistente:
{vault_ctx}

Domande già fatte in questa sessione:
{history_str}

Genera la prossima domanda. Deve essere diversa da quelle già fatte e approfondire qualcosa di interessante o mancante."""

    return think(SYSTEM_INTERVIEWER, prompt)


def run(voice: Voice):
    print("\n  🎤  Modalità INTERVISTATORE")
    print("  Di' 'fine' o 'stop' per terminare.\n")

    questions_asked = []
    answers_count = 0

    voice.speak("Cominciamo. Ti farò alcune domande per conoscerti meglio.")

    while True:
        # 1. Genera domanda
        print("  ⏳ Generazione domanda...", end="\r", flush=True)
        question = _generate_question(questions_asked)
        questions_asked.append(question)
        print("  " + " " * 30, end="\r")

        voice.speak(question)

        # 2. Ascolta risposta
        audio = voice.record_utterance()
        if audio is None:
            voice.speak("Non ho sentito nulla. Riproviamo.")
            continue

        # 3. Trascrivi
        print("  ✍  Trascrizione...", end="\r", flush=True)
        answer = voice.transcribe(audio)
        print("  " + " " * 25, end="\r")

        if not answer:
            voice.speak("Non ho capito. Puoi ripetere?")
            continue

        print(f"  Tu: {answer}")

        if answer.strip().lower() in ("fine", "stop", "esci", "basta"):
            voice.speak("Perfetto. Grazie per le risposte, ho salvato tutto.")
            break

        # 4. Estrai e salva nel vault
        print("  💾 Salvataggio nel vault...", end="\r", flush=True)
        combined = f"D: {question}\nR: {answer}"
        ops = extractor.extract(combined)
        extractor.apply(ops)
        answers_count += 1

        saved = [f"{op['folder']}/{op['title']}" for op in ops if op.get('title')]
        if saved:
            print(f"  ✅ Salvato in: {', '.join(saved)}")
        else:
            print(f"  ✅ Salvato nel journal")

        if answers_count % 5 == 0:
            voice.speak("Stai andando benissimo. Continuiamo.")

    print(f"\n  Sessione completata: {answers_count} risposte salvate nel vault.")

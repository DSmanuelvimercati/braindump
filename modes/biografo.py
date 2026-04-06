"""
Modalità BIOGRAFO: ascolta il journaling libero dell'utente.
Due sotto-modalità:
  - live:  trascrizione utterance per utterance, aggiornamento vault in tempo reale
  - batch: registra tutta la sessione, poi elabora
"""

from core.voice import Voice
from core import extractor, vault


SYSTEM_ACK = """Sei un ascoltatore empatico. L'utente sta facendo journaling.
Dopo ogni cosa che dice, rispondi con una breve frase di conferma (max 10 parole) in italiano,
che dimostri che hai capito e incoraggi a continuare. Niente domande, solo ascolto."""


def _acknowledge(transcript: str, voice: Voice):
    from core.model import think
    ack = think(SYSTEM_ACK, f'L\'utente ha detto: "{transcript}"')
    first = ack.split(".")[0].strip() + "."
    voice.speak(first)


def run_live(voice: Voice):
    """Ascolta utterance per utterance, elabora in tempo reale."""
    print("\n  📖  Modalità BIOGRAFO — live")
    print("  Parla liberamente. Di' 'fine' o 'stop' per terminare.\n")

    session_transcript = []

    while True:
        audio = voice.record_utterance()
        if audio is None:
            continue

        transcript = voice.transcribe(audio)
        if not transcript:
            continue

        print(f"  Tu: {transcript}")

        if transcript.strip().lower() in ("fine", "stop", "esci"):
            voice.speak("Sessione terminata. Ho salvato tutto nel vault.")
            break

        session_transcript.append(transcript)

        ops = extractor.extract(transcript)
        extractor.apply(ops)

        _acknowledge(transcript, voice)

    _end_summary(session_transcript, voice)


def run_batch(voice: Voice):
    """Registra tutta la sessione, poi elabora in un colpo solo."""
    print("\n  📖  Modalità BIOGRAFO — batch")
    print("  Premi INVIO per avviare la registrazione.\n")
    input("  ▶  ")

    audio = voice.record_session()

    if len(audio) == 0:
        voice.speak("Nessun audio registrato.")
        return

    voice.speak("Ho la registrazione. Sto trascrivendo.")
    print("  Trascrizione in corso...")

    transcript = voice.transcribe(audio)
    print(f"\n  Trascrizione:\n  {transcript}\n")

    if transcript:
        ops = extractor.extract(transcript)
        extractor.apply(ops)
        voice.speak("Tutto salvato nel vault. Ottima sessione.")
    else:
        voice.speak("Non sono riuscito a trascrivere nulla.")


def _end_summary(transcripts: list[str], voice: Voice):
    if not transcripts:
        return
    voice.speak(f"Sessione completata. Ho registrato {len(transcripts)} frammenti nel vault.")


def run(voice: Voice):
    print("\n  Come vuoi lavorare?")
    print("  1. Live (trascrizione in tempo reale)")
    print("  2. Batch (registra tutto, poi elaboro)\n")
    choice = input("  Scelta [1/2]: ").strip()
    if choice == "2":
        run_batch(voice)
    else:
        run_live(voice)

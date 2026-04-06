"""
Interfaccia testo: sostituisce la voce con input/output da tastiera.
Stessa interfaccia della classe Voice originale — i modi non cambiano.
"""


class Voice:
    def __init__(self):
        pass  # nessun modello da caricare

    def transcribe(self, audio) -> str:
        return audio  # in modalità testo, "audio" è già testo

    def record_utterance(self):
        try:
            text = input("  Tu: ").strip()
            return text if text else None
        except (EOFError, KeyboardInterrupt):
            return None

    def record_session(self):
        print("  Scrivi il tuo journal (riga vuota per terminare):")
        lines = []
        while True:
            try:
                line = input("  > ")
                if line == "":
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                break
        return " ".join(lines)

    def speak(self, text: str):
        print(f"\n  💬  {text}\n")

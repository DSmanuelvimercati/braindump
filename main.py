"""
Braindump — sistema di autobiografia personale con Gemma4.

Modalità:
  1. Biografo       — journaling libero
  2. Intervistatore — domande guidate con agent loop

Flag:
  --debug   mostra tool calls, prompt e risultati in tempo reale
"""

import sys
from core import vault
from core.voice import Voice

DEBUG = "--debug" in sys.argv


def menu():
    print()
    print("  ╔══════════════════════════════╗")
    print("  ║        B R A I N D U M P     ║")
    print("  ╚══════════════════════════════╝")
    if DEBUG:
        print("  ⚠  modalità DEBUG attiva")
    print()
    print("  1.  Biografo       — journaling libero")
    print("  2.  Intervistatore — domande guidate")
    print("  q.  Esci")
    print()
    return input("  Modalità: ").strip().lower()


def main():
    vault.init()
    voice = Voice()

    while True:
        choice = menu()

        if choice in ("q", "quit", "esci"):
            print("\n  Arrivederci.\n")
            break
        elif choice == "1":
            from modes.biografo import run
            run(voice)
        elif choice == "2":
            from modes.intervistatore import run
            run(voice, debug=DEBUG)
        else:
            print("  Scelta non valida.")


if __name__ == "__main__":
    main()

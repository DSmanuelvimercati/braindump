"""
Braindump — sistema di autobiografia personale con Gemma4 E4B-it.

Modalità:
  1. Biografo  — ascolta il tuo journaling libero e organizza nel vault
  2. Intervistatore — fa domande attive per costruire il tuo profilo
"""

from core import vault
from core.voice import Voice


def menu():
    print()
    print("  ╔══════════════════════════════╗")
    print("  ║        B R A I N D U M P     ║")
    print("  ╚══════════════════════════════╝")
    print()
    print("  1.  Biografo      — journaling libero")
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
            run(voice)
        else:
            print("  Scelta non valida.")


if __name__ == "__main__":
    main()

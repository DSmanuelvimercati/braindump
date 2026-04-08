"""
Modalità INTERVISTATORE.
La logica è in run_session(emit, get_input) — usabile sia da CLI che da WebSocket.
"""

import re
import json
from core.model import think
from core.agent import run as agent_run
from core import extractor, vault
from core.tools import tool_prompt_block


def _build_system(entity_queue: list, recent_questions: list, turn: int = 0) -> str:
    queue_str = (
        "\n".join(f"- {e}" for e in entity_queue[:5])
        if entity_queue else "nessuna"
    )
    recent_str = (
        "\n".join(f"- {q}" for q in recent_questions[-5:])
        if recent_questions else "nessuna"
    )

    # Suggerimento di focus — leggero, non obbligatorio
    hints = [
        "passato: studi, infanzia, origini",
        "persone: qualcuno di importante nella sua vita",
        "lavoro e progetti attuali",
        "valori, opinioni, scelte di vita",
        "qualcosa di inaspettato: hobby, ricordo specifico, periodo non ancora emerso",
    ]
    focus_hint = hints[turn % len(hints)]

    return f"""Sei un biografo che intervista una persona per costruire la sua autobiografia digitale.
Il tuo obiettivo è fare UNA domanda concreta e specifica per turno.

ARGOMENTO VIETATO — non chiedere mai di:
- Il progetto Braindump, questo sistema, Obsidian, LLM locali, l'autobiografia digitale in sé
- Questi sono il contesto in cui avviene l'intervista, non ciò su cui vuoi sapere di più

COME PROCEDERE:
1. Usa vault_search o vault_get_entity per capire cosa sai già su un aspetto della vita dell'intervistato
2. Identifica cosa manca o cosa puoi approfondire
3. Fai una domanda specifica su quello

AREA DI FOCUS PER QUESTO TURNO: {focus_hint}

AREE BIOGRAFICHE PRIORITARIE (in generale poco coperte):
- Famiglia, origini, dove è cresciuto
- Amici importanti, relazioni significative
- Transizioni di vita (perché ha lasciato X per fare Y)
- Vita fuori dal lavoro: hobby, sport, musica, luoghi
- Momenti formativi, fallimenti, svolte inaspettate
- Opinioni forti su temi che conosce bene

REGOLE PER LA DOMANDA:
- UNA domanda sola, breve, diretta
- Specifica: aggancia un dettaglio già emerso nel vault (nome, luogo, evento, periodo)
- Se il vault ha già qualcosa su un tema, approfondisci quello invece di cambiare argomento
- Non fare domande il cui tema è già stato rifiutato dall'utente

{tool_prompt_block()}

DOMANDE GIÀ FATTE (non ripetere): {recent_str}
PERSONE/COSE MENZIONATE MA NON APPROFONDITE: {queue_str}"""



def _extract_entities(text: str) -> list:
    prompt = f"""Estrai SOLO nomi propri (persone, luoghi, aziende, progetti) da questo testo.
Rispondi con JSON array di stringhe. Solo nomi, niente altro.
Esempio: ["Lucrezia", "Datapizza", "Milano"]

Testo: "{text}"

JSON:"""
    try:
        response = think("Rispondi solo con JSON valido.", prompt)
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return []


def _is_known(entity: str) -> bool:
    from core.tools import _vault_get_entity
    result = _vault_get_entity(entity)
    return "non è presente nel vault" not in result


def _seed_vault(emit, get_input):
    """
    Se il vault è vuoto, chiede a Manuel una breve presentazione
    e la salva come punto di partenza.
    """
    ctx = vault.context_summary(max_chars=100)
    if "Vault vuoto" not in ctx:
        return  # vault già popolato, skip

    emit({"type": "status", "message": "Il vault è vuoto. Iniziamo con una breve presentazione."})
    emit({"type": "question", "text": "Prima di iniziare: descriviti in poche righe. Chi sei, cosa fai, dove vivi. Anche un elenco va bene."})

    answer = get_input()
    if not answer or answer.strip().lower() in ("fine", "stop"):
        return

    emit({"type": "user_answer", "text": answer})
    emit({"type": "status", "message": "Salvo nel vault..."})

    ops = extractor.extract(answer)
    extractor.apply(ops)

    for op in ops:
        if op.get("title"):
            emit({"type": "vault_write", "folder": op["folder"],
                  "title": op["title"], "action": op.get("action", "merge")})

    emit({"type": "status", "message": "Perfetto. Ora posso farti domande specifiche."})


def run_session(emit, get_input, logger=None):
    """
    Logica di sessione pura.
    emit(dict)    — invia un evento (UI o CLI)
    get_input()   — ottieni risposta utente (bloccante)
    """
    # Onboarding se vault vuoto
    _seed_vault(emit, get_input)

    entity_queue = []
    known_entities = {}
    recent_questions = []
    history = []
    answers_count = 0   # risposte reali salvate nel vault
    turn_count = 0      # turni totali (include meta-comandi, guida la rotazione focus)

    emit({"type": "status", "message": "Pronto. Preparo la prima domanda..."})

    while True:
        system = _build_system(entity_queue, recent_questions, turn=turn_count)
        turn_count += 1

        if logger:
            logger.section(f"Turno {turn_count}")
        question, history = agent_run(system, history, emit=emit,
                                      log=logger.log_token if logger else None)
        recent_questions.append(question)

        # Aspetta input utente
        answer = get_input()
        if not answer or answer.strip().lower() in ("fine", "stop", "esci", "basta"):
            emit({"type": "status", "message": "Sessione terminata."})
            emit({"type": "session_end", "count": answers_count})
            break

        # Meta-comandi UI — non salvati nel vault, ma fanno avanzare il turn
        if answer.startswith("[[CHANGE_TOPIC]]"):
            entity_queue.clear()
            emit({"type": "status", "message": "Ok, cambio argomento..."})
            continue

        if answer.startswith("[[TOPIC:"):
            topic = answer[8:].rstrip("]").strip()
            entity_queue.insert(0, topic)
            emit({"type": "status", "message": f"Ok, ti chiedo di \"{topic}\"..."})
            continue

        emit({"type": "user_answer", "text": answer})
        history.append({"role": "user", "content": f"D: {question}\nR: {answer}"})

        # Estrai entità nuove
        entities = _extract_entities(answer)
        for e in entities:
            if e not in known_entities:
                known_entities[e] = True
                known = _is_known(e)
                emit({"type": "entity_found", "name": e, "known": known})
                if not known:
                    entity_queue.append(e)

        # Rimuovi dalla coda entità già discusse
        entity_queue = [e for e in entity_queue if e.lower() not in answer.lower()]

        # Salva nel vault
        ops = extractor.extract(f"D: {question}\nR: {answer}")
        extractor.apply(ops)
        answers_count += 1

        for op in ops:
            if op.get("title"):
                emit({"type": "vault_write",
                      "folder": op["folder"],
                      "title": op["title"],
                      "action": op.get("action", "merge")})

        # History compatta — solo le ultime 3 domande/risposte per non gonfiare il prompt
        if len(history) > 6:
            history = history[-6:]


# ------------------------------------------------------------------
# Entry point CLI
# ------------------------------------------------------------------

def run(voice, debug: bool = False):
    from core.agent import _debug_print

    def emit(event):
        if debug:
            _debug_print(event)
        t = event.get("type")
        if t == "question":
            voice.speak(event["text"])
        elif t == "status":
            print(f"  ℹ  {event['message']}")
        elif t == "vault_write":
            print(f"  💾 {event['folder']}/{event['title']}")
        elif t == "entity_found":
            icon = "✓" if event["known"] else "?"
            print(f"  [{icon}] entità: {event['name']}")
        elif t == "session_end":
            print(f"\n  Sessione completata: {event['count']} risposte.")

    def get_input():
        audio = voice.record_utterance()
        if audio is None:
            return ""
        return voice.transcribe(audio) if hasattr(voice, "_whisper") else audio

    print("\n  🎤  Modalità INTERVISTATORE  (digita 'fine' per uscire)\n")
    run_session(emit, get_input)

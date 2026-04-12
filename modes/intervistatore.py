"""
Modalità INTERVISTATORE (powered by datapizza-ai).
Fa domande biografiche specifiche, una alla volta, consultando il vault.
"""

import json
import re

from datapizza.agents import Agent
from datapizza.agents.agent import AgentHooks, StepContext, StepResult
from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools import tool
from datapizza.type import FunctionCallBlock, FunctionCallResultBlock, TextBlock

from core import vault, extractor
from core.model import think
from core import vault_search as vault_search_mod
from core.memory_utils import trim_memory
from config import OLLAMA_BASE, OLLAMA_MODEL, OLLAMA_NUM_CTX


# ── Tool definitions ──────────────────────────────────────────────────────

@tool
def vault_read(folder: str, title: str) -> str:
    """Leggi una nota specifica dal vault."""
    content = vault.read(folder.rstrip("/"), title)
    if not content:
        return f"Nota '{folder}/{title}' non trovata nel vault."
    return f"[{folder}/{title}]\n{content}"


@tool
def vault_search(query: str) -> str:
    """Cerca nel vault per keyword. Ritorna le note rilevanti."""
    return vault_search_mod.search(query)


@tool
def vault_get_entity(name: str) -> str:
    """Recupera tutto ciò che si sa su una persona o concetto specifico."""
    return vault_search_mod.get_entity(name)


@tool
def vault_get_gaps() -> str:
    """Trova aree del vault poco sviluppate: entità menzionate nei wikilinks ma senza nota dedicata."""
    return vault_search_mod.get_gaps()


@tool(end=True)
def ask_user(question: str) -> str:
    """Fai UNA domanda specifica a Manuel. Usalo SOLO quando hai abbastanza contesto dal vault."""
    return json.dumps({"_tool": "ask_user", "question": question}, ensure_ascii=False)


ALL_TOOLS = [vault_read, vault_search, vault_get_entity, vault_get_gaps, ask_user]


# ── Hooks per emettere eventi al frontend ─────────────────────────────────

class IntervistaHooks(AgentHooks):
    def __init__(self, emit, logger=None):
        self._emit = emit
        self._logger = logger

    def before_step(self, ctx: StepContext):
        if self._logger:
            self._logger.section(f"Step {ctx.step_index}")

        prompt_parts = []
        for turn in ctx.memory:
            for block in turn:
                if isinstance(block, TextBlock):
                    prompt_parts.append(block.content)
                elif isinstance(block, FunctionCallBlock):
                    prompt_parts.append(f"[tool_call: {block.name}({json.dumps(block.arguments, ensure_ascii=False)})]")
                elif isinstance(block, FunctionCallResultBlock):
                    preview = block.result[:500] if block.result else ""
                    prompt_parts.append(f"[result: {block.tool.name}] {preview}")

        self._emit({
            "type": "llm_call",
            "call_n": ctx.step_index,
            "system": ctx.agent.system_prompt,
            "prompt": "\n\n".join(prompt_parts),
        })

    def after_step(self, ctx: StepContext, result: StepResult):
        response_parts = []
        for block in result.content:
            if isinstance(block, TextBlock):
                response_parts.append(block.content)
            elif isinstance(block, FunctionCallBlock):
                response_parts.append(f"[tool_call: {block.name}({json.dumps(block.arguments, ensure_ascii=False)})]")

        self._emit({
            "type": "llm_response",
            "call_n": ctx.step_index,
            "text": "\n".join(response_parts),
        })

        for block in result.content:
            if isinstance(block, FunctionCallBlock):
                self._emit({
                    "type": "tool_call",
                    "tool": block.name,
                    "args": block.arguments,
                })
            elif isinstance(block, FunctionCallResultBlock):
                self._emit({
                    "type": "tool_result",
                    "tool": block.tool.name,
                    "result": block.result[:1000] if block.result else "",
                })


# ── System prompt ─────────────────────────────────────────────────────────

def _build_system(entity_queue: list, recent_questions: list, turn: int = 0) -> str:
    from core.prompts import get as get_prompt
    queue_str = (
        "\n".join(f"- {e}" for e in entity_queue[:5])
        if entity_queue else "nessuna"
    )
    recent_str = (
        "\n".join(f"- {q}" for q in recent_questions[-5:])
        if recent_questions else "nessuna"
    )
    hints = [
        "passato: studi, infanzia, origini",
        "persone: qualcuno di importante nella sua vita",
        "lavoro e progetti attuali",
        "valori, opinioni, scelte di vita",
        "qualcosa di inaspettato: hobby, ricordo specifico, periodo non ancora emerso",
    ]
    focus_hint = hints[turn % len(hints)]
    template = get_prompt("intervistatore")
    return template.format(focus_hint=focus_hint, recent_str=recent_str, queue_str=queue_str)


# ── Entity extraction (usa think() direttamente, fuori dal loop agent) ───

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
    result = vault_search_mod.get_entity(entity)
    return "non è presente nel vault" not in result


# ── Seed vault (se vuoto, chiede presentazione iniziale) ─────────────────

def _seed_vault(emit, get_input):
    ctx = vault.context_summary(max_chars=100)
    if "Vault vuoto" not in ctx:
        return

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


# ── Sessione principale ──────────────────────────────────────────────────

def run_session(emit, get_input, logger=None):
    """
    Ciclo intervistatore:
    - agent consulta il vault → chiama ask_user (end=True ferma il loop)
    - UI mostra la domanda
    - utente risponde
    - risposta salvata nel vault via extractor
    - agent continua con nuova domanda
    """
    _seed_vault(emit, get_input)

    from datapizza.memory import Memory
    from datapizza.memory.memory import ROLE
    from datapizza.type import TextBlock as DPTextBlock

    client = OpenAILikeClient(
        api_key="",
        model=OLLAMA_MODEL,
        base_url=f"{OLLAMA_BASE}/v1",
    )

    hooks = IntervistaHooks(emit, logger)
    entity_queue = []
    known_entities = {}
    recent_questions = []
    shared_memory = Memory()
    answers_count = 0
    turn_count = 0

    emit({"type": "status", "message": "Pronto. Preparo la prima domanda..."})

    while True:
        system = _build_system(entity_queue, recent_questions, turn=turn_count)
        turn_count += 1

        # Trim memory: budget dinamico basato su token, non turni fissi
        trim_memory(shared_memory, system)

        agent = Agent(
            name="intervistatore",
            system_prompt=system,
            client=client,
            tools=ALL_TOOLS,
            max_steps=8,
            hooks=hooks,
            terminate_on_text=True,
        )

        task = "Analizza il vault e fai una domanda biografica." if turn_count == 1 else ""
        result = agent.run(task, memory=shared_memory)

        if not result:
            emit({"type": "session_end", "count": answers_count})
            break

        # Cerca ask_user result nel content
        question_text = None
        for block in result.content:
            text = getattr(block, 'result', None) or getattr(block, 'content', None)
            if isinstance(text, str) and text.startswith('{'):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and parsed.get("_tool") == "ask_user":
                        question_text = parsed.get("question", "")
                        break
                except (json.JSONDecodeError, TypeError):
                    pass

        # Se l'agent ha prodotto testo diretto (senza ask_user), trattalo come domanda
        if not question_text and result.text:
            question_text = result.text

        if not question_text:
            emit({"type": "session_end", "count": answers_count})
            break

        emit({"type": "question", "text": question_text})
        recent_questions.append(question_text)

        # Aspetta input utente
        answer = get_input()
        if not answer or answer.strip().lower() in ("fine", "stop", "esci", "basta"):
            emit({"type": "status", "message": "Sessione terminata."})
            emit({"type": "session_end", "count": answers_count})
            break

        # Meta-comandi UI
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

        # Inietta Q+A nella memory persistente
        shared_memory.add_turn(
            DPTextBlock(content=f"D: {question_text}\nR: {answer}"),
            role=ROLE.USER,
        )

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
        ops = extractor.extract(f"D: {question_text}\nR: {answer}")
        extractor.apply(ops)
        answers_count += 1

        for op in ops:
            if op.get("title"):
                emit({"type": "vault_write",
                      "folder": op["folder"],
                      "title": op["title"],
                      "action": op.get("action", "merge")})


# ── Entry point CLI ──────────────────────────────────────────────────────

def run(voice, debug: bool = False):
    def emit(event):
        t = event.get("type")
        if t == "question":
            voice.speak(event["text"])
        elif t == "status":
            print(f"  i  {event['message']}")
        elif t == "vault_write":
            print(f"  S  {event['folder']}/{event['title']}")
        elif t == "entity_found":
            icon = "v" if event["known"] else "?"
            print(f"  [{icon}] entita: {event['name']}")
        elif t == "session_end":
            print(f"\n  Sessione completata: {event['count']} risposte.")

    def get_input():
        audio = voice.record_utterance()
        if audio is None:
            return ""
        return voice.transcribe(audio) if hasattr(voice, "_whisper") else audio

    print("\n  Modalita INTERVISTATORE  (digita 'fine' per uscire)\n")
    run_session(emit, get_input)

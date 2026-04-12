"""
Modalità ARCHIVISTA (powered by datapizza-ai).
Analizza il vault, propone riorganizzazioni una alla volta,
aspetta approvazione prima di eseguire.
"""

import json
import re
from pathlib import Path
from datapizza.agents import Agent
from datapizza.agents.agent import AgentHooks, StepContext, StepResult
from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools import tool
from datapizza.type import FunctionCallBlock, FunctionCallResultBlock, TextBlock

from core import vault
from core.memory_utils import trim_memory
from core import vault_search as vault_search_mod
from config import VAULT_PATH, OLLAMA_BASE, OLLAMA_MODEL, OLLAMA_NUM_CTX



ARCH_DIR = Path(VAULT_PATH) / "Archivista"


def _build_system(feedback_history: list) -> str:
    from core.prompts import get as get_prompt
    feedback_str = ""
    if feedback_history:
        feedback_str = "\nFEEDBACK RICEVUTO FINORA:\n" + "\n".join(
            f"- {f}" for f in feedback_history[-10:]
        )
    return get_prompt("archivista") + feedback_str


# ── Helpers ────────────────────────────────────────────────────────────────

def _safe(title: str) -> str:
    return re.sub(r'[<>:"/\\|?*\n\']', '', title).strip()


# ── Tool definitions ──────────────────────────────────────────────────────

@tool
def archivista_list() -> str:
    """Elenca le tue note di lavoro precedenti (piano, osservazioni, feedback)."""
    ARCH_DIR.mkdir(exist_ok=True)
    notes = [p.stem for p in ARCH_DIR.glob("*.md")]
    return "Note archivista: " + ", ".join(notes) if notes else "Nessuna nota precedente."


@tool
def archivista_read(title: str = "stato") -> str:
    """Leggi una tua nota di lavoro per recuperare stato, problemi, storico."""
    path = ARCH_DIR / f"{_safe(title)}.md"
    return path.read_text(encoding="utf-8") if path.exists() else f"Nota '{title}' non trovata."


@tool
def archivista_write(title: str = "stato", content: str = "") -> str:
    """Scrivi o aggiorna una nota di lavoro (stato, problemi, storico). Usalo SPESSO per non perdere contesto."""
    if not content:
        return "Errore: content non può essere vuoto."
    ARCH_DIR.mkdir(exist_ok=True)
    path = ARCH_DIR / f"{_safe(title)}.md"
    path.write_text(content, encoding="utf-8")
    return f"Nota '{title}' salvata."


@tool
def vault_list_folders() -> str:
    """Lista leggera del vault: solo cartelle e titoli delle note, zero contenuto."""
    lines = []
    skip = {".obsidian", "Archivista"}
    vault_path = Path(VAULT_PATH)
    for entry in sorted(vault_path.iterdir()):
        if not entry.is_dir() or entry.name in skip or entry.name.startswith("."):
            continue
        titles = [p.stem for p in sorted(entry.glob("*.md"))]
        if titles:
            lines.append(f"{entry.name}/: " + ", ".join(titles))
    return "\n".join(lines) if lines else "Vault vuoto."


@tool
def vault_read_folder(folder: str) -> str:
    """Leggi tutte le note di UNA cartella con il loro contenuto completo."""
    folder = folder.rstrip("/")
    notes = vault.list_all()
    parts = [f"=== {n['title']} ===\n{n['content']}"
             for n in notes if n["folder"] == folder]
    return "\n\n".join(parts) if parts else f"Nessuna nota in {folder}/."


@tool
def vault_read_note(folder: str, title: str) -> str:
    """Leggi una nota specifica dal vault."""
    content = vault.read(folder.rstrip("/"), title)
    return content if content else f"Nota {folder}/{title} non trovata."


@tool
def vault_audit() -> str:
    """Report completo del vault: statistiche, gap, duplicati, note senza tag, note troppo corte."""
    return vault_search_mod.audit()


@tool
def vault_find_duplicates() -> str:
    """Trova coppie di note probabilmente duplicate (fuzzy match su titolo e contenuto)."""
    dupes = vault_search_mod.find_duplicates()
    if not dupes:
        return "Nessun duplicato trovato."
    lines = [f"POSSIBILI DUPLICATI ({len(dupes)}):"]
    for d in dupes:
        lines.append(f"  {d['folder_a']}/{d['title_a']} ~ {d['folder_b']}/{d['title_b']} (sim: {d['similarity']})")
    return "\n".join(lines)


@tool(end=True)
def propose(motivation: str, before_json: str, after_json: str, delete_json: str) -> str:
    """Proponi una modifica al vault. Richiede approvazione dell'utente.
    Args:
        motivation: Spiegazione del perché della modifica
        before_json: JSON array di note coinvolte, es: [{"folder":"Idee","title":"Nota vecchia"}]
        after_json: JSON array di note da scrivere, es: [{"folder":"Concetti","title":"Nota","content":"testo","tags":["tag"]}]
        delete_json: JSON array di note da eliminare, es: [{"folder":"Idee","title":"Nota"}] oppure [] se nessuna
    """
    def _parse(s):
        try:
            return json.loads(s) if s else []
        except (json.JSONDecodeError, TypeError):
            return []

    return json.dumps({
        "_tool": "propose",
        "motivation": motivation,
        "before": _parse(before_json),
        "after": _parse(after_json),
        "delete": _parse(delete_json),
    }, ensure_ascii=False)


@tool(end=True)
def done(summary: str) -> str:
    """Hai finito l'analisi, nessuna altra modifica da proporre."""
    return json.dumps({"_tool": "done", "summary": summary}, ensure_ascii=False)


# ── Elenco tool ───────────────────────────────────────────────────────────

ALL_TOOLS = [
    archivista_list, archivista_read, archivista_write,
    vault_list_folders, vault_read_folder, vault_read_note,
    vault_audit, vault_find_duplicates,
    propose, done,
]


# ── Hooks per emettere eventi al frontend ─────────────────────────────────

class ArchHooks(AgentHooks):
    def __init__(self, emit, logger=None):
        self._emit = emit
        self._logger = logger

    def before_step(self, ctx: StepContext):
        if self._logger:
            self._logger.section(f"Step {ctx.step_index}")

        # Emetti llm_call con system prompt e history (per la Raw tab)
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
        # Ricostruisci la risposta LLM per la Raw tab
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

        # Emetti tool_call e tool_result per l'Activity panel
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


# ── Esecuzione operazioni approvate ───────────────────────────────────────

def _execute_operation(args: dict) -> str:
    """Esegue un'operazione approvata: scrive 'after', elimina 'delete'."""
    results = []
    for w in args.get("after", []):
        folder = w.get("folder", "").rstrip("/")
        title = w.get("title", "")
        content = w.get("content", "")
        tags = w.get("tags", [])
        if folder and title and content:
            vault.write(folder, title, content, tags)
            results.append(f"scritto: {folder}/{title}")
    for d in args.get("delete", []):
        folder = d.get("folder", "").rstrip("/")
        title = d.get("title", "")
        if folder and title and vault.delete(folder, title):
            results.append(f"eliminato: {folder}/{title}")
    return ", ".join(results) if results else "nessuna modifica effettuata"


# ── Sessione principale ──────────────────────────────────────────────────

def run_session(emit, get_input, logger=None):
    """
    Ciclo archivista:
    - agent ragiona e chiama propose (end=True ferma il loop)
    - UI mostra la proposta
    - utente approva o rifiuta con motivo
    - se approvata → esegue l'operazione → agent continua
    - se rifiutata → feedback all'agent → agent adatta
    """
    emit({"type": "status", "message": "Archivista avviato. Analizzo il vault..."})

    from datapizza.memory import Memory
    from datapizza.memory.memory import ROLE
    from datapizza.type import TextBlock as DPTextBlock

    client = OpenAILikeClient(
        api_key="",
        model=OLLAMA_MODEL,
        base_url=f"{OLLAMA_BASE}/v1",
    )

    hooks = ArchHooks(emit, logger)
    feedback_history = []
    shared_memory = Memory()  # Persistente tra i cicli
    ops_count = 0
    first_run = True

    while True:
        system = _build_system(feedback_history)

        # Trim memory: budget dinamico basato su token, non turni fissi
        trim_memory(shared_memory, system)

        agent = Agent(
            name="archivista",
            system_prompt=system,
            client=client,
            tools=ALL_TOOLS,
            max_steps=12,
            hooks=hooks,
            terminate_on_text=True,
        )

        task = "Analizza il vault e proponi miglioramenti." if first_run else ""
        result = agent.run(task, memory=shared_memory)
        first_run = False

        if not result:
            emit({"type": "session_end", "count": ops_count})
            break

        # Cerca il risultato dei tool end (propose / done) nel content
        proposal = None
        for block in result.content:
            # FunctionCallResultBlock ha .result (str), TextBlock ha .content (str)
            text = getattr(block, 'result', None) or getattr(block, 'content', None)
            if isinstance(text, str) and text.startswith('{'):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and "_tool" in parsed:
                        proposal = parsed
                        break
                except (json.JSONDecodeError, TypeError):
                    pass

        # done → fine sessione
        if proposal and proposal.get("_tool") == "done":
            summary = proposal.get("summary", "Analisi completata.")
            emit({"type": "status", "message": summary})
            emit({"type": "session_end", "count": ops_count})
            break

        # propose → mostra all'utente
        if proposal and proposal.get("_tool") == "propose":
            emit({
                "type": "proposal",
                "motivation": proposal.get("motivation", ""),
                "before": proposal.get("before", []),
                "after": proposal.get("after", []),
            })

            raw_input = get_input()

            if not raw_input or raw_input.strip().lower() in ("fine", "stop", "esci"):
                emit({"type": "status", "message": "Sessione interrotta."})
                emit({"type": "session_end", "count": ops_count})
                break

            if raw_input.startswith("[[APPROVE]]"):
                exec_result = _execute_operation(proposal)
                feedback = f"Approvata ed eseguita. Risultato: {exec_result}"
                ops_count += 1

                for w in proposal.get("after", []):
                    emit({"type": "vault_write",
                          "folder": w.get("folder", ""),
                          "title": w.get("title", ""),
                          "action": "archivista"})

            elif raw_input.startswith("[[REJECT:"):
                reason = raw_input[9:].rstrip("]").strip()
                feedback = f"Rifiutata. Motivo: {reason}"
                feedback_history.append(
                    f"Proposta su '{proposal.get('motivation', '')}' → rifiutata: {reason}"
                )
            else:
                feedback = "Rifiutata."

            emit({"type": "status", "message": feedback})
            # Inietta il feedback nella memory persistente
            shared_memory.add_turn(DPTextBlock(content=feedback), role=ROLE.USER)
            continue

        # Testo libero (ask_user equivalente) — mostra e aspetta risposta
        if result.text:
            emit({"type": "question", "text": result.text})
            raw_input = get_input()
            if not raw_input or raw_input.strip().lower() in ("fine", "stop", "esci"):
                emit({"type": "session_end", "count": ops_count})
                break
            emit({"type": "user_answer", "text": raw_input})
            shared_memory.add_turn(DPTextBlock(content=raw_input), role=ROLE.USER)
            continue

        # Nessun output comprensibile
        emit({"type": "session_end", "count": ops_count})
        break

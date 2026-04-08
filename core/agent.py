"""
Agent loop con sistema a eventi.
Ogni passo emette un evento via callback emit(dict).
Funziona sia da CLI che da WebSocket — l'I/O è iniettato dall'esterno.
"""

import json
import re
from core.model import think
from core import tools


MAX_TOOL_CALLS = 8


def run(system: str, history: list, emit=None, debug: bool = False, log=None,
        extra_tools: dict = None) -> tuple:
    """
    Esegue un ciclo agente fino a:
    - ask_user  → restituisce la domanda, aggiorna history
    - risposta  → restituisce il testo, aggiorna history

    Args:
        system:  system prompt
        history: lista {"role": str, "content": str}
        emit:    callable(event_dict) — se None usa print in debug
        debug:   stampa eventi su stdout anche senza emit

    Returns:
        (risposta: str, history_aggiornata: list)
    """
    def _emit(event):
        if emit:
            emit(event)
        if debug:
            _debug_print(event)

    ctx = history.copy()
    _emit({"type": "thinking", "message": "consulto il vault..."})

    tools_called = {}  # {tool_name: count} — previene loop viziosi

    for i in range(MAX_TOOL_CALLS):
        prompt = _build_prompt(ctx)

        # Emetti lo scambio completo prima di chiamare Gemma
        _emit({"type": "llm_call", "call_n": i, "system": system, "prompt": prompt})

        # Accumula la risposta per emetterla completa dopo
        response_buf = []
        def on_token(token, _buf=response_buf):
            _buf.append(token)
            if log:
                log(token, end="")

        response = think(system, prompt, on_token=on_token)
        if log:
            log("\n---\n")

        _emit({"type": "llm_response", "call_n": i, "text": response})

        # Parsa TUTTI i tool call presenti nella risposta
        tool_calls = _parse_all_tool_calls(response, _log=log)

        if not tool_calls:
            # Risposta testuale diretta
            ctx.append({"role": "assistant", "content": response})
            _emit({"type": "response", "text": response})
            return response, ctx

        ctx.append({"role": "assistant", "content": response})

        # Esegui i tool call in ordine; fermati al primo ask_user
        tool_results = []
        asked = False
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool", "")
            args = tool_call.get("args", {})

            _emit({"type": "tool_call", "tool": tool_name, "args": args})

            # ask_user: rompe tutto, restituisce la domanda
            if tool_name == "ask_user":
                question = args.get("question", "")
                _emit({"type": "question", "text": question})
                for r in tool_results:
                    ctx.append(r)
                return question, ctx

            # propose: rompe tutto, restituisce la proposta (archivista)
            if tool_name == "propose":
                _emit({"type": "proposal",
                       "motivation": args.get("motivation", ""),
                       "before": args.get("before", []),
                       "after": args.get("after", []),
                       "operation": args.get("operation", {})})
                for r in tool_results:
                    ctx.append(r)
                return {"_tool": "propose", **args}, ctx

            # Blocca chiamate identiche (stesso tool + stessi args) nello stesso turno
            call_key = (tool_name, str(sorted(args.items()) if isinstance(args, dict) else args))
            tools_called[call_key] = tools_called.get(call_key, 0) + 1
            if tools_called[call_key] > 1:
                result = f"Hai già chiamato {tool_name} con questi stessi argomenti. Cambia parametri o usa un tool diverso."
                _emit({"type": "tool_result", "tool": tool_name, "result": result})
                tool_results.append({"role": "tool", "content": f"[Risultato {tool_name}]\n{result}"})
                continue

            # Esegui tool locale (extra_tools hanno priorità)
            if extra_tools and tool_name in extra_tools:
                result = extra_tools[tool_name](args)
            elif tool_name == "done":
                # Segnale di fine — restituisce dict distinguibile da ask_user
                summary = args.get("summary", "Analisi completata.")
                ctx.append({"role": "assistant", "content": response})
                _emit({"type": "response", "text": summary})
                return {"_tool": "done", "summary": summary}, ctx
            elif tool_name not in tools.TOOL_NAMES:
                result = f"Tool '{tool_name}' non esiste."
            else:
                result = tools.execute(tool_name, args)

            _emit({"type": "tool_result", "tool": tool_name, "result": result})
            tool_results.append({"role": "tool", "content": f"[Risultato {tool_name}]\n{result}"})

        # Aggiungi tutti i risultati al ctx e vai al prossimo turno LLM
        for r in tool_results:
            ctx.append(r)

    return "Non sono riuscito a formulare una domanda.", ctx


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _preprocess(text: str) -> str:
    """Pulizia iniziale del testo prima del parsing JSON."""
    # Rimuove code fence markdown (```json ... ``` o ``` ... ```)
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```', '', text)
    # Rimuove virgole trailing prima di } o ] (errore comune di Gemma)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text


def _repair_json(text: str) -> str:
    """
    Corregge JSON malformato:
    - Newline/tab letterali dentro stringhe → \\n, \\t
    - Parentesi sbagliate o mancanti
    """
    result = []
    in_string = False
    escape = False
    stack = []

    for c in text:
        if escape:
            escape = False
            result.append(c)
            continue
        if c == '\\' and in_string:
            escape = True
            result.append(c)
            continue
        if c == '"':
            in_string = not in_string
            result.append(c)
            continue
        if in_string:
            # Dentro una stringa: escape caratteri di controllo non escapati
            if c == '\n':
                result.append('\\n')
            elif c == '\r':
                result.append('\\r')
            elif c == '\t':
                result.append('\\t')
            else:
                result.append(c)
            continue
        # Fuori dalle stringhe: gestisci parentesi
        if c in '{[':
            stack.append(c)
        elif c in '}]':
            if stack:
                opener = stack[-1]
                expected = '}' if opener == '{' else ']'
                if c != expected:
                    result.append(expected)  # corregge parentesi sbagliata
                    stack.pop()
                    continue
                stack.pop()
        result.append(c)

    # Chiude parentesi mancanti (dal più interno)
    while stack:
        opener = stack.pop()
        result.append('}' if opener == '{' else ']')

    return ''.join(result)


def _parse_all_tool_calls(text: str, _log=None) -> list:
    """Parsa TUTTI i JSON object con chiave 'tool' presenti nel testo."""
    text = _preprocess(text)

    decoder = json.JSONDecoder()
    calls = []
    pos = 0
    while pos < len(text):
        match = re.search(r'\{', text[pos:])
        if not match:
            break
        start = pos + match.start()
        snippet = text[start:]

        # Tentativo 1: JSON valido as-is
        try:
            obj, length = decoder.raw_decode(snippet)
            if isinstance(obj, dict) and "tool" in obj:
                calls.append(obj)
            pos = start + length
            continue
        except json.JSONDecodeError:
            pass

        # Tentativo 2: repair (newline letterali + parentesi)
        repaired = _repair_json(snippet)
        try:
            obj = json.loads(repaired)
            if isinstance(obj, dict) and "tool" in obj:
                if _log:
                    _log(f"[repair_json] riparato tool call: {obj.get('tool')}")
                calls.append(obj)
            pos = start + len(snippet)
            continue
        except json.JSONDecodeError:
            pass

        # Tentativo 3: estrazione regex dei campi principali (fallback greedy)
        tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', snippet)
        if tool_match:
            extracted = _extract_fields_regex(snippet)
            if extracted and "tool" in extracted:
                if _log:
                    _log(f"[regex_fallback] estratto tool call: {extracted.get('tool')}")
                calls.append(extracted)
            pos = start + len(snippet)
            continue

        pos = start + 1

    return calls


def _extract_fields_regex(text: str) -> dict | None:
    """
    Fallback: estrae i campi di primo livello con regex quando JSON.parse fallisce.
    Funziona solo per valori stringa semplici e oggetti/array top-level.
    """
    result = {}

    # Estrai "tool": "value"
    m = re.search(r'"tool"\s*:\s*"([^"]+)"', text)
    if not m:
        return None
    result["tool"] = m.group(1)

    # Prova ad estrarre "args": { ... } trovando le parentesi bilanciate
    args_match = re.search(r'"args"\s*:\s*(\{)', text)
    if args_match:
        brace_start = args_match.start(1)
        depth = 0
        in_str = False
        esc = False
        end = brace_start
        for i, c in enumerate(text[brace_start:]):
            if esc:
                esc = False
                continue
            if c == '\\' and in_str:
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if not in_str:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = brace_start + i + 1
                        break
        args_str = text[brace_start:end]
        try:
            result["args"] = json.loads(_repair_json(args_str))
        except Exception:
            result["args"] = {}

    return result


def _parse_tool_call(text: str):
    """Cerca e parsa il primo JSON object con chiave 'tool'. (legacy)"""
    calls = _parse_all_tool_calls(text)
    return calls[0] if calls else None


def _build_prompt(history: list) -> str:
    parts = []
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            parts.append(f"MANUEL: {content}")
        elif role == "assistant":
            parts.append(f"TU: {content}")
        elif role == "tool":
            parts.append(f"SISTEMA: {content}")
    return "\n\n".join(parts)


def _debug_print(event: dict):
    t = event.get("type", "")
    if t == "thinking":
        print(f"  [{chr(9203)}] {event.get('message', '')}", flush=True)
    elif t == "tool_call":
        print(f"  [{chr(128269)}] {event['tool']}({json.dumps(event.get('args', {}), ensure_ascii=False)})", flush=True)
    elif t == "tool_result":
        result = event.get("result", "")[:120].replace("\n", " ")
        print(f"  [{chr(128203)}] {event['tool']} -> {result}", flush=True)
    elif t == "question":
        print(f"  [?] {event['text']}", flush=True)
    elif t == "vault_write":
        print(f"  [S] {event.get('folder')}/{event.get('title')} ({event.get('action', '')})", flush=True)
    elif t == "entity_found":
        known = "v" if event.get("known") else "?"
        print(f"  [U] {event.get('name')} {known}", flush=True)

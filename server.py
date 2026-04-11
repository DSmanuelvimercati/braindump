"""
Server FastAPI + WebSocket per Braindump.
Avvia con: python server.py
Poi apri http://localhost:7860
"""

import asyncio
import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from core import vault
from core.backup import backup_vault

app = FastAPI()
vault.init()

# Backup vault all'avvio — mantiene le ultime 3 copie
_backup_path = backup_vault()
if _backup_path:
    print(f"  [backup] vault → {_backup_path}")

HTML = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/")
async def root():
    return HTMLResponse(HTML)


@app.get("/vault/note")
async def vault_note(folder: str, title: str):
    """Legge una nota specifica — usata dalla UI per mostrare il 'before' nelle proposte."""
    content = vault.read(folder.rstrip("/"), title)
    return JSONResponse({"content": content or "(nota non trovata)"})


@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Riceve un file audio dal browser, restituisce la trascrizione."""
    try:
        from core.transcriber import transcribe
        data = await audio.read()
        suffix = "." + (audio.filename or "audio.webm").rsplit(".", 1)[-1]
        text = await asyncio.get_event_loop().run_in_executor(
            None, transcribe, data, suffix
        )
        return JSONResponse({"text": text})
    except Exception as e:
        return JSONResponse({"error": str(e), "text": ""}, status_code=500)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()

    # Code per comunicazione thread ↔ async
    event_q = asyncio.Queue()   # agent → WS
    input_q = queue.Queue()     # WS → agent (sync)

    def emit(event: dict):
        """Chiamato dal thread agent — mette evento nella queue async."""
        asyncio.run_coroutine_threadsafe(event_q.put(event), loop)

    def get_input() -> str:
        """Chiamato dal thread agent — blocca finché non arriva input dal WS."""
        return input_q.get()

    # Ricevi il messaggio di init
    try:
        init_raw = await websocket.receive_text()
        init = json.loads(init_raw)
    except Exception:
        return

    mode = init.get("mode", "intervistatore")

    # Manda system prompt iniziale e stato vault
    from core.tools import tool_prompt_block
    from modes.intervistatore import _build_system
    system_preview = _build_system([], [])
    await websocket.send_json({"type": "session_start", "mode": mode, "system_prompt": system_preview})

    # Avvia sessione in thread separato
    def run_agent():
        from core.logger import SessionLogger
        logger = SessionLogger(mode)
        try:
            if mode == "intervistatore":
                from modes.intervistatore import run_session
                run_session(emit, get_input, logger=logger)
            elif mode == "biografo":
                from modes.biografo import run_session_ws
                run_session_ws(emit, get_input)
            elif mode == "archivista":
                from modes.archivista import run_session
                run_session(emit, get_input, logger=logger)
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                event_q.put({"type": "error", "message": str(e)}), loop
            )
        finally:
            logger.close()
            asyncio.run_coroutine_threadsafe(event_q.put(None), loop)

    agent_thread = threading.Thread(target=run_agent, daemon=True)
    agent_thread.start()

    # Due task paralleli: forwarda eventi e ricevi input
    async def forward_events():
        while True:
            event = await event_q.get()
            if event is None:
                break
            await websocket.send_json(event)

    async def receive_inputs():
        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                if msg.get("type") == "user_input":
                    input_q.put(msg.get("text", ""))
        except WebSocketDisconnect:
            pass

    fwd_task = asyncio.create_task(forward_events())
    rcv_task = asyncio.create_task(receive_inputs())
    try:
        await asyncio.gather(fwd_task, rcv_task)
    except Exception:
        pass
    finally:
        fwd_task.cancel()
        rcv_task.cancel()
        input_q.put("fine")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

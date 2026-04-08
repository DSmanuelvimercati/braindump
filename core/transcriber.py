"""
Trascrizione audio con faster-whisper (CPU).
Il modello viene caricato una sola volta e riusato.
"""

import os
import tempfile
from config import WHISPER_MODEL, WHISPER_LANGUAGE

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        print(f"  [whisper] carico modello '{WHISPER_MODEL}'...", flush=True)
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("  [whisper] pronto.", flush=True)
    return _model


def transcribe(audio_bytes: bytes, suffix: str = ".webm") -> str:
    """
    Trascrive audio_bytes (qualsiasi formato supportato da ffmpeg).
    Restituisce il testo trascritto, stringa vuota se nulla.
    """
    model = _get_model()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        segments, _ = model.transcribe(
            tmp_path,
            language=WHISPER_LANGUAGE,
            vad_filter=True,          # salta silenzio
            vad_parameters={"min_silence_duration_ms": 500},
        )
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        os.unlink(tmp_path)

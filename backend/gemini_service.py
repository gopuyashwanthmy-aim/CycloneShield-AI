from __future__ import annotations
import os
import time
from dotenv import load_dotenv

load_dotenv()
try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
GEMINI_MAX_ATTEMPTS = max(1, int(os.getenv("GEMINI_MAX_ATTEMPTS", "2")))
client = genai.Client(api_key=GEMINI_API_KEY) if genai and GEMINI_API_KEY else None

FALLBACK_MESSAGE = "Gemini AI is temporarily unavailable. Deterministic risk, hazard, infrastructure and planning results remain available."


def _is_retryable(exc: Exception) -> bool:
    message = str(exc).upper()
    # Daily quota exhaustion will not recover in a few seconds. Do not burn
    # additional requests by retrying it.
    if "GENERATE_CONTENT_FREETIER_REQUESTS" in message or "REQUESTS_PER_DAY" in message:
        return False
    code = getattr(exc, "code", None)
    return code in {429, 500, 502, 503, 504} or any(token in message for token in ("429", "500", "502", "503", "504", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))


def _call_text(prompt: str) -> str:
    if client is None:
        return FALLBACK_MESSAGE
    for attempt in range(GEMINI_MAX_ATTEMPTS):
        try:
            chat = client.chats.create(model=GEMINI_MODEL)
            response = chat.send_message(prompt)
            text = getattr(response, "text", None)
            if text and text.strip():
                return text.strip()
            return FALLBACK_MESSAGE
        except Exception as exc:
            if attempt < 2 and _is_retryable(exc):
                time.sleep(2 ** attempt)
                continue
            print("Gemini text error:", exc)
            return FALLBACK_MESSAGE
    return FALLBACK_MESSAGE


def _call_multimodal(prompt: str, image_bytes: bytes) -> str:
    if client is None or types is None:
        return FALLBACK_MESSAGE
    for attempt in range(GEMINI_MAX_ATTEMPTS):
        try:
            chat = client.chats.create(model=GEMINI_MODEL)
            contents = [
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            ]
            response = chat.send_message(contents)
            text = getattr(response, "text", None)
            if text and text.strip():
                return text.strip()
            return FALLBACK_MESSAGE
        except Exception as exc:
            if attempt < 2 and _is_retryable(exc):
                time.sleep(2 ** attempt)
                continue
            print("Gemini multimodal error:", exc)
            return FALLBACK_MESSAGE
    return FALLBACK_MESSAGE


def analyze_cyclone(prompt: str) -> str:
    return _call_text(prompt)


def analyze_multimodal(prompt: str, image_bytes: bytes | None = None) -> str:
    if not image_bytes:
        return _call_text(prompt)
    return _call_multimodal(prompt, image_bytes)

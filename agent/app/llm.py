from google import genai
from google.genai import types

from .config import settings

_client = None


def _c():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def generate(prompt: str, system: str | None = None, temperature: float = 0.4) -> str:
    r = _c().models.generate_content(
        model=settings.chat_model,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system, temperature=temperature),
    )
    return (r.text or "").strip()


def embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), 50):
        r = _c().models.embed_content(model=settings.embed_model, contents=texts[i : i + 50])
        out.extend(e.values for e in r.embeddings)
    return out

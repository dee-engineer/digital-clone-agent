import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


class Settings:
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    chat_model = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
    embed_model = os.getenv("EMBED_MODEL", "gemini-embedding-001")
    api_key = os.getenv("API_KEY", "")
    chroma_path = os.getenv("CHROMA_PATH", "./data/chroma")
    state_db = os.getenv("STATE_DB", "./data/state.db")
    persona_store = os.getenv("PERSONA_STORE", "./data/persona.md")
    custom_skills_dir = os.getenv("CUSTOM_SKILLS_DIR", "./skills")
    send_webhook_url = os.getenv("SEND_WEBHOOK_URL", "")
    send_webhook_secret = os.getenv("SEND_WEBHOOK_SECRET", "")

    @property
    def persona(self) -> str:
        for p in (Path(self.persona_store), BASE / "persona.example.md"):
            if p.is_file():
                return p.read_text(encoding="utf-8")
        raise FileNotFoundError("No persona file found")

    def save_persona(self, text: str):
        p = Path(self.persona_store)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


settings = Settings()

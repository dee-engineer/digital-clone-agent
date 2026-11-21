import hashlib
import os
import tempfile

_d = tempfile.mkdtemp()
os.environ.update(
    API_KEY="test-key", CHROMA_PATH=_d + "/chroma", STATE_DB=_d + "/state.db", PERSONA_STORE=_d + "/persona.md",
    CUSTOM_SKILLS_DIR=_d + "/skills", SEND_WEBHOOK_URL="",
)

import pytest  # noqa: E402

from app import llm  # noqa: E402
from tests.helpers import PROMPTS  # noqa: E402

@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    PROMPTS.clear()
    monkeypatch.setattr(llm, "embed", lambda ts: [[b / 255 for b in hashlib.sha256(t.encode()).digest()[:16]] for t in ts])

    def gen(prompt, system=None, temperature=0.4):
        PROMPTS.append(prompt)
        if "Classify" in prompt:
            return "spam" if "WIN A PRIZE" in prompt else "client"
        return "Draft output."

    monkeypatch.setattr(llm, "generate", gen)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


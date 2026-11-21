import secrets
import uuid
from pathlib import Path
from typing import Literal, Optional

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel

from . import files, llm, memory, skills, store
from .config import settings
from .graph import get_graph, lock

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Digital Clone Agent", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def security_headers(request, call_next):
    r = await call_next(request)
    r.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "no-referrer"
    return r


def auth(x_api_key: str = Header(default="")):
    # Secure default: if API_KEY is unset, nothing is allowed.
    if not settings.api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(401, "unauthorized")


A = [Depends(auth)]


class Email(BaseModel):
    sender: str
    subject: str = ""
    body: str
    message_id: str = ""


class Decision(BaseModel):
    action: Literal["approve", "reject"]
    edited: Optional[str] = None


class Feedback(BaseModel):
    action: Literal["accept", "reject"]
    edited: Optional[str] = None


class Doc(BaseModel):
    source: str
    text: str


class RunReq(BaseModel):
    inputs: dict[str, str]


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatReq(BaseModel):
    message: str
    history: list[Turn] = []


class Persona(BaseModel):
    persona: str


def _cfg(tid: str):
    return {"configurable": {"thread_id": tid}}


# ---------------- UI ----------------
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/review", include_in_schema=False)
def review_alias():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"ok": True}


# ---------------- knowledge ----------------
@app.post("/ingest", dependencies=A)
def ingest(d: Doc):
    return {"chunks": memory.ingest(d.source[:200], d.text)}


@app.post("/ingest/files", dependencies=A)
def ingest_files(upload: list[UploadFile] = File(...)):
    results = []
    for f in upload:
        data = f.file.read(files.MAX_BYTES + 1)
        if len(data) > files.MAX_BYTES:
            results.append({"file": f.filename, "error": "larger than 5 MB"})
            continue
        try:
            n = memory.ingest(Path(f.filename or "upload").name, files.extract_text(f.filename or "", data))
            results.append({"file": f.filename, "chunks": n})
        except Exception as e:  # unsupported type, corrupt pdf, ...
            results.append({"file": f.filename, "error": str(e)[:200]})
    return results


@app.get("/knowledge", dependencies=A)
def knowledge():
    return memory.sources()


@app.delete("/knowledge/{source:path}", dependencies=A)
def knowledge_delete(source: str):
    memory.delete_source(source)
    return {"deleted": source}


@app.get("/persona", dependencies=A)
def get_persona():
    return {"persona": settings.persona}


@app.put("/persona", dependencies=A)
def put_persona(p: Persona):
    if not p.persona.strip() or len(p.persona) > 20000:
        raise HTTPException(422, "Persona must be 1-20000 characters")
    settings.save_persona(p.persona)
    return {"ok": True}


# ---------------- skills ----------------
@app.get("/skills", dependencies=A)
def list_skills():
    return [skills.public(s) for s in skills.load().values()]


@app.post("/run/{name}", dependencies=A)
def run_skill(name: str, r: RunReq):
    sk = skills.load().get(name)
    if not sk:
        raise HTTPException(404, "unknown skill")
    try:
        out = skills.run(sk, r.inputs)
    except ValueError as e:
        raise HTTPException(422, str(e))
    rid = str(uuid.uuid4())
    store.add_run(rid, name, r.inputs, out["output"], out["sources"])
    return {"run_id": rid, **out}


@app.post("/runs/{rid}/feedback", dependencies=A)
def feedback(rid: str, f: Feedback):
    run = store.get_run(rid)
    if not run:
        raise HTTPException(404, "no such run")
    if f.action == "accept":
        memory.add_example(run["skill"], run["input_text"], (f.edited or run["output"]).strip())
        store.set_status(rid, "accepted")
        return {"saved_as_example": True}
    store.set_status(rid, "rejected")
    return {"saved_as_example": False}


@app.get("/runs", dependencies=A)
def runs():
    return store.recent_runs()


# ---------------- chat with your clone ----------------
@app.post("/chat", dependencies=A)
def chat(c: ChatReq):
    hits = memory.search(c.message[:1500], k=6)
    notes = "\n---\n".join(f"[{h['source']}] {h['text']}" for h in hits) or "(no notes found)"
    hist = "\n".join(f"{t.role}: {t.content[:2000]}" for t in c.history[-10:])
    prompt = f"Notes:\n{notes}\n\nConversation so far:\n{hist}\n\nuser: {c.message[:4000]}\nassistant:"
    system = (
        settings.persona
        + "\n\nYou are talking privately with your owner. Answer from the notes; if they do not cover it, say so "
        "instead of guessing. Mention source names in [brackets] when you rely on them."
    )
    return {"answer": llm.generate(prompt, system=system), "sources": sorted({h["source"] for h in hits if h["source"]})}


# ---------------- email approval flow (used by n8n) ----------------
@app.post("/triage", dependencies=A)
def triage(e: Email):
    tid = str(uuid.uuid4())
    with lock:
        res = get_graph().invoke(
            {"sender": e.sender, "subject": e.subject, "body": e.body, "message_id": e.message_id}, _cfg(tid)
        )
    inputs = {"sender": e.sender, "subject": e.subject, "body": e.body}
    if "__interrupt__" in res:
        payload = res["__interrupt__"][0].value
        store.add(tid, {**payload, "message_id": e.message_id, "body": e.body[:2000]})
        store.add_run(tid, "email_reply", inputs, payload["draft"], payload.get("sources", []), "pending")
        return {"thread_id": tid, "status": "pending_approval", **payload}
    store.add_run(tid, "email_reply", inputs, "", [], "skipped")
    return {"thread_id": tid, "status": res.get("decision", "skipped"), "category": res.get("category")}


@app.get("/pending", dependencies=A)
def pending():
    return store.all_pending()


@app.post("/approve/{tid}", dependencies=A)
def approve(tid: str, d: Decision):
    item = store.get(tid)
    if not item:
        raise HTTPException(404, "no such pending item")
    with lock:
        res = get_graph().invoke(Command(resume={"action": d.action, "edited": d.edited}), _cfg(tid))
    store.remove(tid)
    final = res.get("final")
    sent = False
    if final:
        memory.add_example("email_reply", f"sender: {item['sender']}\nsubject: {item['subject']}\nbody: {item['body']}", final)
        if settings.send_webhook_url:
            r = httpx.post(
                settings.send_webhook_url,
                json={"message_id": item["message_id"], "to": item["sender"], "subject": item["subject"], "reply": final},
                headers={"X-Webhook-Secret": settings.send_webhook_secret},
                timeout=20,
            )
            sent = r.is_success
    store.set_status(tid, "approved" if final else "rejected")
    return {"decision": res.get("decision"), "final": final, "sent": sent}

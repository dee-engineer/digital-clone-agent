import json
import sqlite3
import threading
import time
from contextlib import closing

from .config import settings

_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(settings.state_db)
    c.execute("CREATE TABLE IF NOT EXISTS pending (thread_id TEXT PRIMARY KEY, payload TEXT)")
    c.execute(
        "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, ts REAL, skill TEXT, status TEXT,"
        " input_text TEXT, output TEXT, sources TEXT)"
    )
    return c


def _exec(sql, args=()):
    with _lock, closing(_conn()) as c:
        with c:
            cur = c.execute(sql, args)
            return cur.fetchall()


# ---- email approval queue ----
def add(thread_id: str, payload: dict):
    _exec("INSERT OR REPLACE INTO pending VALUES (?, ?)", (thread_id, json.dumps(payload)))


def get(thread_id: str):
    r = _exec("SELECT payload FROM pending WHERE thread_id=?", (thread_id,))
    return json.loads(r[0][0]) if r else None


def remove(thread_id: str):
    _exec("DELETE FROM pending WHERE thread_id=?", (thread_id,))


def all_pending() -> list[dict]:
    return [{"thread_id": t, **json.loads(p)} for t, p in _exec("SELECT thread_id, payload FROM pending")]


# ---- run history (audit log + feedback) ----
def input_text(inputs: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in inputs.items())[:4000]


def add_run(rid: str, skill: str, inputs: dict, output: str, sources: list, status: str = "draft"):
    _exec(
        "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?)",
        (rid, time.time(), skill, status, input_text(inputs), output, json.dumps(sources)),
    )


def get_run(rid: str):
    r = _exec("SELECT id, skill, status, input_text, output FROM runs WHERE id=?", (rid,))
    return dict(zip(("id", "skill", "status", "input_text", "output"), r[0])) if r else None


def set_status(rid: str, status: str):
    _exec("UPDATE runs SET status=? WHERE id=?", (status, rid))


def recent_runs(limit: int = 50) -> list[dict]:
    rows = _exec("SELECT id, ts, skill, status, output FROM runs ORDER BY ts DESC LIMIT ?", (limit,))
    return [dict(zip(("id", "ts", "skill", "status", "output"), r)) for r in rows]

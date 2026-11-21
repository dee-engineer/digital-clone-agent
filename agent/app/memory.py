"""Memory: (1) your professional history, (2) approved examples that teach the clone your style."""
import hashlib

import chromadb

from . import llm
from .config import settings

_client = None
_cols: dict = {}


def _col(name: str):
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    if name not in _cols:
        _cols[name] = _client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
    return _cols[name]


def chunk(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    text = text.strip()
    if not text:
        return []
    step = size - overlap
    return [text[i : i + size] for i in range(0, len(text), step)]


def ingest(source: str, text: str) -> int:
    chunks = chunk(text)
    for i in range(0, len(chunks), 64):
        batch = chunks[i : i + 64]
        ids = [hashlib.sha1(f"{source}:{i + j}:{c}".encode()).hexdigest() for j, c in enumerate(batch)]
        _col("professional_history").upsert(
            ids=ids, embeddings=llm.embed(batch), documents=batch, metadatas=[{"source": source}] * len(batch)
        )
    return len(chunks)


def search(query: str, k: int = 5) -> list[dict]:
    c = _col("professional_history")
    n = c.count()
    if n == 0:
        return []
    r = c.query(query_embeddings=llm.embed([query]), n_results=min(k, n))
    return [{"text": d, "source": (m or {}).get("source", "")} for d, m in zip(r["documents"][0], r["metadatas"][0])]


def sources() -> list[dict]:
    counts: dict[str, int] = {}
    for m in _col("professional_history").get(include=["metadatas"])["metadatas"]:
        counts[m["source"]] = counts.get(m["source"], 0) + 1
    return [{"source": s, "chunks": n} for s, n in sorted(counts.items())]


def delete_source(source: str):
    _col("professional_history").delete(where={"source": source})


# ---- learning from approvals -------------------------------------------------
def add_example(skill: str, task_input: str, output: str):
    task_input = task_input[:1500]
    _col("approved_examples").upsert(
        ids=[hashlib.sha1(f"{skill}:{task_input}:{output}".encode()).hexdigest()],
        embeddings=llm.embed([task_input]),
        documents=[output],
        metadatas=[{"skill": skill, "input": task_input}],
    )


def find_examples(skill: str, query: str, k: int = 3) -> list[dict]:
    c = _col("approved_examples")
    n = len(c.get(where={"skill": skill})["ids"])
    if n == 0:
        return []
    r = c.query(query_embeddings=llm.embed([query[:1500]]), n_results=min(k, n), where={"skill": skill})
    return [{"input": m["input"], "output": d} for d, m in zip(r["documents"][0], r["metadatas"][0])]

"""Usage: python -m app.ingest_cli /knowledge   (ingests every .md / .txt file)"""
import sys
from pathlib import Path

from . import memory

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/knowledge")
total = 0
for p in sorted(root.rglob("*")):
    if p.suffix.lower() in {".md", ".txt"}:
        n = memory.ingest(str(p.relative_to(root)), p.read_text(encoding="utf-8", errors="ignore"))
        print(f"{p.name}: {n} chunks")
        total += n
print(f"done, {total} chunks")

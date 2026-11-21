import io
from pathlib import Path

TEXT = {".md", ".txt", ".csv", ".json", ".log", ".rst"}
MAX_BYTES = 5 * 1024 * 1024


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    if ext in TEXT:
        return data.decode("utf-8", "ignore")
    raise ValueError(f"Unsupported file type: {ext or 'none'} (use .pdf .md .txt .csv .json)")

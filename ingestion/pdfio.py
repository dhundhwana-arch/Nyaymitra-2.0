"""PDF access. Text is returned exactly as the PDF text layer yields it (no normalisation)."""
from __future__ import annotations

from pathlib import Path


class ExtractionError(Exception):
    pass


def _open(path: Path):
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover
        raise ExtractionError("PyMuPDF is not installed (pip install -r requirements-ingestion.txt)") from exc
    path = Path(path)
    if not path.exists():
        raise ExtractionError(f"file not found: {path}")
    if path.stat().st_size == 0:
        raise ExtractionError(f"file is empty: {path}")
    try:
        doc = pymupdf.open(str(path), filetype="pdf")
    except Exception as exc:
        raise ExtractionError(f"cannot open PDF {path.name}: {exc}") from exc
    if doc.needs_pass:
        raise ExtractionError(f"PDF is encrypted: {path.name}")
    if doc.page_count == 0:
        raise ExtractionError(f"PDF has no pages: {path.name}")
    return doc


def pdf_metadata(path: Path) -> dict:
    with _open(path) as doc:
        return {"page_count": doc.page_count,
                "metadata": {k: v for k, v in (doc.metadata or {}).items() if v}}


def page_texts(path: Path) -> list[str]:
    """One string per page, straight from the text layer."""
    with _open(path) as doc:
        try:
            return [page.get_text("text") for page in doc]
        except Exception as exc:
            raise ExtractionError(f"text extraction failed for {Path(path).name}: {exc}") from exc

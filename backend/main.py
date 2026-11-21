"""Compatibility entry point.

The legacy single-file backend was removed in the 2.1 rewrite (see
docs/REPOSITORY_AUDIT.md §5.1: it could not even be imported). This module keeps the old
``uvicorn backend.main:app`` / ``cd backend && python main.py`` commands working by
delegating to the real application.

Preferred commands from the repository root:
    uvicorn backend.app.main:app --reload
    python -m backend.app.main
"""
from __future__ import annotations

from backend.app.main import app, main

__all__ = ["app", "main"]

if __name__ == "__main__":  # pragma: no cover
    main()

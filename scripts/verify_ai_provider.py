#!/usr/bin/env python3
"""Live end-to-end probe for a real model provider.

This asks a real question through the same code path the API uses
(``ai.rag.answer_question``), so everything that matters is exercised together:

* retrieval over the FTS index,
* "memory" injection (the triage guide and the department block that are added to the prompt),
* answer validation (the guard rejects invented article numbers or unsafe advice),
* citations back to the retrieved articles.

It never fabricates a result. If no provider is configured, or it cannot be reached, the probe
says so and exits 3 — it does not print a canned answer and call it a model test.

    # Ollama on the same host (model must already be pulled):
    ollama pull llama3.2:3b
    NYAYMITRA_DB_PATH=data/nyaymitra.db \
    NYAYMITRA_AI_PROVIDER=openai_compatible \
    NYAYMITRA_AI_BASE_URL=http://127.0.0.1:11434/v1 \
    NYAYMITRA_AI_MODEL=llama3.2:3b \
    NYAYMITRA_AI_API_KEY=ollama \
    python scripts/verify_ai_provider.py --question "What does equality before the law mean?"

Exit codes: 0 live model verified · 3 provider not configured/unreachable · 4 answered but failed
grounding or citation checks.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.ai import rag  # noqa: E402
from backend.app.ai.registry import describe  # noqa: E402
from backend.app.config import Settings, load_settings  # noqa: E402
from backend.app.db import apply_migrations, get_db  # noqa: E402

EXIT_LIVE = 0
EXIT_UNAVAILABLE = 3
EXIT_UNGROUNDED = 4

DEFAULT_QUESTION = "What does equality before the law mean in India?"
DEFAULT_LANGUAGE = "en"


def requirement(settings: Settings) -> str:
    """The exact environment needed for a real provider, with the current values."""
    return f"""\
A live model was not verifiable in this environment.

What is required (any OpenAI-compatible endpoint works — this is the Ollama recipe):

    1. Install and start Ollama:      https://ollama.com/download
    2. Pull a model that fits the box: ollama pull llama3.2:3b
    3. Export these variables (the API key is a placeholder for Ollama; it must be set
       because the provider refuses to run without one):

         NYAYMITRA_AI_PROVIDER=openai_compatible
         NYAYMITRA_AI_BASE_URL=http://127.0.0.1:11434/v1
         NYAYMITRA_AI_MODEL=llama3.2:3b
         NYAYMITRA_AI_API_KEY=ollama

    4. Re-run: python scripts/verify_ai_provider.py

A hosted endpoint (OpenAI, Groq, vLLM, Gemini compatibility) works the same way with its own
base URL, model name and key. Nothing needs to be installed in the application itself.

Current configuration:
    provider preference : {settings.ai_provider}
    base URL            : {settings.ai_base_url or '(unset)'}
    model               : {settings.ai_model or '(unset)'}
    API key             : {'set' if settings.ai_api_key else '(unset)'}
    fallback mode       : {settings.ai_fallback_mode}
"""


def preflight(settings: Settings, *, timeout: float = 5.0) -> dict:
    """Check whether the endpoint answers, and whether it lists the configured model."""
    info: dict = {"reachable": False, "models": [], "detail": ""}
    if not settings.ai_base_url:
        info["detail"] = "no base URL configured"
        return info
    try:
        import httpx
    except ImportError:  # pragma: no cover - httpx is a runtime dependency
        info["detail"] = "httpx is not installed"
        return info

    url = settings.ai_base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"} if settings.ai_api_key else {}
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
    except Exception as exc:  # noqa: BLE001 - network errors come in many types
        info["detail"] = f"could not reach {url} ({type(exc).__name__})"
        return info

    if response.status_code >= 400:
        # Some gateways do not implement /models; a 404 there is not fatal, it is unknown.
        info["detail"] = f"{url} returned HTTP {response.status_code}"
        info["reachable"] = response.status_code in {404, 405}
        return info

    info["reachable"] = True
    info["detail"] = f"{url} answered HTTP 200"
    try:
        data = response.json()
    except ValueError:
        return info
    rows = data.get("data") if isinstance(data, dict) else None
    if isinstance(rows, list):
        info["models"] = [
            row.get("id") for row in rows if isinstance(row, dict) and row.get("id")
        ]
    return info


def evaluate(result: dict) -> tuple[str, list[str]]:
    """Classify a RAG result as live / unavailable / ungrounded, with the reasons."""
    problems: list[str] = []
    provider = result.get("provider")
    warnings = result.get("warnings") or []
    rejected = [
        w for w in warnings
        if w.startswith("model_rejected") or w == "fell_back_to_offline_grounded"
    ]
    if rejected:
        # The model answered but the guard refused its output: that is a model failure,
        # not a missing provider, and must not be reported as "cannot test".
        return "ungrounded", [f"the guard rejected the model output ({w})" for w in rejected]
    if provider in (None, "", "offline"):
        failed = [w for w in warnings if w.startswith("provider_unavailable")]
        problems.append("the answer came from the offline provider, not a model")
        problems.extend(f"the provider failed during generation ({w})" for w in failed)
        return "unavailable", problems
    if not result.get("grounded"):
        problems.append("the answer was not marked grounded")
    if not result.get("citations"):
        problems.append("the answer carried no citations")
    if not (result.get("answer") or "").strip():
        problems.append("the answer was empty")
    if problems:
        return "ungrounded", problems
    return "live", []


def probe(conn, settings: Settings, *, question: str, language: str) -> dict:
    result = rag.answer_question(
        conn, settings, question=question, language=language, category=None, request_id="provider-probe"
    )
    status, problems = evaluate(result)
    labels = [citation.get("article_label") for citation in result.get("citations") or []]
    return {"status": status, "problems": problems, "result": result, "cited_labels": labels}


def _print_report(payload: dict, *, question: str, info: dict) -> None:
    result = payload["result"]
    print(f"question        : {question}")
    print(f"provider        : {result.get('provider')}")
    print(f"model           : {result.get('model') or '(none)'}")
    print(f"grounded        : {result.get('grounded')}")
    print(f"degraded        : {result.get('degraded')}")
    print(f"latency         : {result.get('latency_ms')} ms")
    print(f"sources cited   : {len(result.get('citations') or [])} "
          f"{payload['cited_labels'] if payload['cited_labels'] else ''}".rstrip())
    print(f"warnings        : {', '.join(result.get('warnings') or []) or '(none)'}")
    print(f"endpoint check  : {info['detail']}"
          + (f" · models: {', '.join(info['models'][:6])}" if info.get("models") else ""))
    answer = (result.get("answer") or "").strip().replace("\n", " ")
    print(f"answer (first 240 chars): {answer[:240]}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a real AI provider end to end")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, choices=["en", "gu"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    settings = load_settings()

    if settings.ai_provider == "offline" or not settings.ai_configured:
        print(requirement(settings), file=sys.stderr)
        if args.json:
            print(json.dumps({"status": "unavailable", "reason": "not configured"}))
        return EXIT_UNAVAILABLE

    info = preflight(settings)
    if not info["reachable"]:
        print(f"endpoint check  : {info['detail']}", file=sys.stderr)
        print(requirement(settings), file=sys.stderr)
        if args.json:
            print(json.dumps({"status": "unavailable", "reason": info["detail"]}))
        return EXIT_UNAVAILABLE

    with get_db(settings.db_path) as conn:
        apply_migrations(conn, settings.migrations_dir)
        available = conn.execute(
            "SELECT COUNT(*) FROM constitution_articles WHERE"
            " COALESCE(text_en, '') <> '' OR COALESCE(text_gu, '') <> ''"
            " OR COALESCE(citizen_explanation_en, '') <> ''"
            " OR COALESCE(citizen_explanation_gu, '') <> ''"
        ).fetchone()[0]
        if not available:
            print("warning: the corpus has no article text, so retrieval cannot ground an answer",
                  file=sys.stderr)
        payload = probe(conn, settings, question=args.question, language=args.language)

    if args.json:
        print(json.dumps({
            "status": payload["status"],
            "problems": payload["problems"],
            "provider": payload["result"].get("provider"),
            "model": payload["result"].get("model"),
            "citations": payload["cited_labels"],
            "latency_ms": payload["result"].get("latency_ms"),
            "endpoint": info,
        }, indent=2))
    else:
        _print_report(payload, question=args.question, info=info)

    if payload["status"] == "live":
        print("RESULT: LIVE — a real model answered with grounded, cited output")
        return EXIT_LIVE
    if payload["status"] == "unavailable":
        print("RESULT: UNAVAILABLE — " + "; ".join(payload["problems"]), file=sys.stderr)
        print(requirement(settings), file=sys.stderr)
        return EXIT_UNAVAILABLE
    print("RESULT: UNGROUNDED — " + "; ".join(payload["problems"]), file=sys.stderr)
    return EXIT_UNGROUNDED


if __name__ == "__main__":
    raise SystemExit(main())

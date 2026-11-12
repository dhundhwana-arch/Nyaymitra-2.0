"""Retrieval-augmented, citation-validated answering.

Pipeline
--------
1. triage match (deterministic keyword model over curated guides)
2. retrieval of at most 4 constitution rows (FTS5/bm25)
3. prompt-injection scan of the question (warn, do not block)
4. provider call — live model, or the deterministic offline composer
5. validation: reject uncited article references and unsafe advice
6. persistence: redacted query log + answer record
7. response with citations, verification status, warnings and disclaimers
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any

from ..config import Settings
from ..errors import AppError
from ..metrics import metrics
from ..services import constitution, departments, monitoring, triage
from . import guard, offline
from .base import ProviderResult, ProviderUnavailable, AIProviderError
from .registry import build_provider, describe

DISCLAIMERS = [
    "NYAYMITRA is not a lawyer, a court or a judge, and does not decide cases.",
    "Answers are information built from the sources listed; they are not legal advice.",
    "Verify anything important against the official source or with free legal aid (15100).",
]

NO_INFO_GU = (
    "માફ કરશો — આ પ્રશ્ન માટે મારી પાસે ચકાસાયેલ માહિતી નથી. હાલના ડેટાબેઝમાં સંબંધિત કલમ કે "
    "માર્ગદર્શિકા ઉપલબ્ધ નથી, તેથી હું અનુમાન કરીશ નહીં. મફત કાનૂની સહાય માટે ૧૫૧૦૦ પર કૉલ કરો "
    "અથવા નજીકની DLSA કચેરીનો સંપર્ક કરો."
)
NO_INFO_EN = (
    "Sorry — I do not have verified information for that question. No matching article or guide is "
    "loaded in the database, so I will not guess. Call free legal aid on 15100 or contact your "
    "nearest DLSA office."
)


def _citations(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [
        {
            "article_id": row["id"],
            "article_label": row["article_label"],
            "title": row["title_en"] or row["title_gu"],
            "verification_status": row["verification_status"],
            "source_url": row["source_url"],
        }
        for row in rows
    ]


def _offline_text(
    *, question: str, language: str, rows: list[sqlite3.Row], guide: dict | None, deps: list[dict]
) -> str:
    return offline.compose(
        question=question,
        language=language,
        articles=[dict(r) for r in rows],
        guide=guide,
        departments=deps,
    )


def answer_question(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    question: str,
    language: str,
    category: str | None,
    request_id: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    warnings: list[str] = list(f"input:{w}" for w in guard.scan_input(question))

    guide_row = triage.match(conn, question, category)
    guide = triage.shape_guide(guide_row, language) if guide_row else None
    rows = constitution.retrieve_for_ai(conn, question, limit=4)
    deps = departments.get_many(conn, [guide["department_key"]] if guide and guide["department_key"] else [])
    if not deps:
        # No category matched: suggest the free legal-aid channels only. Dumping the
        # first three rows of the directory (cyber crime, land records) for a question
        # about equality is misleading, so the fallback list is explicit.
        deps = departments.get_many(
            conn, ["nalsa-legal-aid", "dlsa-district", "tele-law-csc"]
        )

    provider_info = describe(settings)
    provider_name = "offline"
    model: str | None = None
    degraded = False
    grounded = True
    answer_text: str | None = None
    usage: dict | None = None

    if not rows and not guide:
        answer_text = NO_INFO_GU if language == "gu" else NO_INFO_EN
        grounded = False
        warnings.append("insufficient_sources")
        metrics.inc("ai.insufficient_sources_total")
        provider = build_provider(settings)
        provider_name = getattr(provider, "name", "offline")
    else:
        try:
            provider = build_provider(settings)
        except ProviderUnavailable:
            if settings.ai_fallback_mode == "strict":
                _log(conn, request_id, language, question, log_category(category, guide), "error",
                     "provider_unavailable", started)
                raise AppError("provider_unavailable") from None
            provider = offline.OfflineGroundedProvider()
            degraded = True
            warnings.append("provider_not_configured")

        provider_name = getattr(provider, "name", "offline")
        model = getattr(provider, "model", None)

        if provider_name == "offline":
            answer_text = _offline_text(
                question=question, language=language, rows=rows, guide=guide, deps=deps
            )
            degraded = degraded or provider_info.live
        else:
            system_prompt, user_prompt = guard.build_prompts(
                question=question, language=language, sources=[dict(r) for r in rows], guide=guide
            )
            try:
                result: ProviderResult = provider.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_output_tokens=settings.ai_max_output_tokens,
                )
                allowed = {row["article_label"] for row in rows}
                ok, problems = guard.validate_answer(result.text, allowed_article_labels=allowed)
                if not ok:
                    warnings.extend(f"model_rejected:{p}" for p in problems)
                    metrics.inc("ai.model_rejected_total")
                    warnings.append("fell_back_to_offline_grounded")
                    answer_text = _offline_text(
                        question=question, language=language, rows=rows, guide=guide, deps=deps
                    )
                    provider_name, model, degraded = "offline", None, True
                    grounded = True
                else:
                    answer_text = result.text
                    grounded = True
                    usage = result.usage
                    prompt_tokens = (usage or {}).get("prompt_tokens")
                    completion_tokens = (usage or {}).get("completion_tokens")
                    if isinstance(prompt_tokens, int):
                        metrics.inc("ai.prompt_tokens_total", prompt_tokens)
                    if isinstance(completion_tokens, int):
                        metrics.inc("ai.completion_tokens_total", completion_tokens)
            except (ProviderUnavailable, AIProviderError) as exc:
                if settings.ai_fallback_mode == "strict":
                    _log(conn, request_id, language, question, log_category(category, guide), "error",
                         type(exc).__name__, started)
                    raise AppError("provider_unavailable") from exc
                warnings.append("provider_unavailable_fallback")
                metrics.inc("ai.provider_fallback_total")
                answer_text = _offline_text(
                    question=question, language=language, rows=rows, guide=guide, deps=deps
                )
                provider_name, model, degraded = "offline", None, True
                grounded = True

    latency = int((time.perf_counter() - started) * 1000)
    query_log_id = _log(
        conn, request_id, language, question, log_category(category, guide), "ok", None, started,
        provider=provider_name,
    )
    citations = _citations(rows)
    monitoring.log_answer(
        conn,
        query_log_id=query_log_id,
        provider=provider_name,
        model=model,
        grounded=grounded,
        degraded=degraded,
        citations=citations,
        answer_text=answer_text or "",
        warnings=warnings,
        usage=usage,
    )
    if degraded:
        warnings.append("answer_degraded_offline_grounded")

    return {
        "answer": answer_text or "",
        "language": language,
        "provider": provider_name,
        "model": model,
        "grounded": grounded,
        "degraded": degraded,
        "citations": citations,
        "guide": guide,
        "departments": deps,
        "warnings": sorted(set(warnings)),
        "disclaimers": DISCLAIMERS,
        "request_id": request_id,
        "latency_ms": latency,
    }


def log_category(category: str | None, guide: dict | None) -> str | None:
    """Prefer the triage guide key for analytics; fall back to the supplied category."""
    if guide:
        return guide["guide_key"]
    return category


def _log(
    conn: sqlite3.Connection,
    request_id: str,
    language: str,
    question: str,
    category: str | None,
    status: str,
    error_code: str | None,
    started: float,
    provider: str | None = None,
) -> int:
    return monitoring.log_query(
        conn,
        request_id=request_id,
        language=language,
        query_text=question,
        category=category,
        provider=provider,
        latency_ms=int((time.perf_counter() - started) * 1000),
        status=status,
        error_code=error_code,
    )

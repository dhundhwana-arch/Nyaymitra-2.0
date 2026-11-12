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

import re
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


# "Article 21A", "Art. 14", "અનુચ્છેદ ૨૧", "આર્ટિકલ 32"; "કલમ N" only when the question is
# about the Constitution (કલમ is also used for sections of other Acts).
_ARTICLE_REF = re.compile(
    r"(?:\barticle|\bart\.?|અનુચ્છેદ|આર્ટિકલ|(?P<kalam>કલમ))\s*[-:]?\s*"
    r"(?P<no>[0-9\u0AE6-\u0AEF]{1,3}[A-Za-z]{0,2})(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_GU_DIGITS = str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789")


def requested_articles(question: str) -> list[str]:
    """Article numbers the user explicitly named, normalised to e.g. '21A'."""
    found: list[str] = []
    for m in _ARTICLE_REF.finditer(question or ""):
        if m.group("kalam") and "બંધારણ" not in question:
            continue
        number = m.group("no").translate(_GU_DIGITS).upper()
        if number not in found:
            found.append(number)
    return found[:4]


def _missing_note(missing: list[str], language: str) -> str:
    labels = ", ".join(f"Article {n}" for n in missing)
    if language == "gu":
        return (f"નોંધ: {labels} હાલ NYAYMITRA ડેટાબેઝમાં ઉપલબ્ધ નથી, તેથી તેના વિશે કોઈ માહિતી "
                "આપવામાં આવી નથી. સત્તાવાર લખાણ માટે India Code (indiacode.nic.in) જુઓ.")
    return (f"Note: {labels} is not available in the NYAYMITRA database yet, so nothing is stated "
            "about it here. For the official text see India Code (indiacode.nic.in).")


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
    # An explicitly named article is looked up exactly: shown first if stored, and reported
    # as unavailable (never guessed) if it is not.
    missing: list[str] = []
    for number in requested_articles(question):
        exact = conn.execute(
            "SELECT * FROM constitution_articles WHERE article_no = ? COLLATE NOCASE", (number,)
        ).fetchone()
        if exact is None:
            missing.append(number)
        elif all(r["id"] != exact["id"] for r in rows):
            rows = [exact, *rows][:4]
    if missing:
        warnings.extend(f"article_not_available:{n}" for n in missing)
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

    if missing:
        answer_text = _missing_note(missing, language) + "\n\n" + (answer_text or "")

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

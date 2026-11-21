"""Query logging, audit trail, error log and admin statistics.

Everything written here is already redacted (see ``app/logging_utils.redact``).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ..logging_utils import redact, redact_and_truncate


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log_query(
    conn: sqlite3.Connection,
    *,
    request_id: str,
    language: str,
    query_text: str,
    category: str | None,
    provider: str | None,
    latency_ms: int | None,
    status: str = "ok",
    error_code: str | None = None,
) -> int:
    import hashlib

    digest = hashlib.sha256(query_text.encode("utf-8")).hexdigest()[:32]
    cur = conn.execute(
        """INSERT INTO query_logs (request_id, language, query_text, query_hash, category,
                                   provider, latency_ms, status, error_code)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            request_id,
            language,
            redact_and_truncate(query_text),
            digest,
            category,
            provider,
            latency_ms,
            status,
            error_code,
        ),
    )
    return int(cur.lastrowid)


def log_answer(
    conn: sqlite3.Connection,
    *,
    query_log_id: int | None,
    provider: str,
    model: str | None,
    grounded: bool,
    degraded: bool,
    citations: list[dict],
    answer_text: str,
    warnings: list[str],
    usage: dict | None = None,
) -> int:
    """Record one answer, including token counts when the provider reported them."""
    prompt_tokens = (usage or {}).get("prompt_tokens")
    completion_tokens = (usage or {}).get("completion_tokens")
    cur = conn.execute(
        """INSERT INTO ai_answers (query_log_id, provider, model, grounded, degraded,
                                   citations_json, answer_text, warnings_json,
                                   prompt_tokens, completion_tokens)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            query_log_id,
            provider,
            model,
            1 if grounded else 0,
            1 if degraded else 0,
            json.dumps(citations, ensure_ascii=False),
            redact_and_truncate(answer_text, 4000),
            json.dumps(warnings, ensure_ascii=False),
            int(prompt_tokens) if isinstance(prompt_tokens, int) else None,
            int(completion_tokens) if isinstance(completion_tokens, int) else None,
        ),
    )
    return int(cur.lastrowid)


def usage_summary(conn: sqlite3.Connection, days: int = 30) -> dict:
    """Aggregate token usage, grounding and latency per provider/model."""
    since = f"-{max(1, int(days))} days"
    rows = conn.execute(
        """SELECT COALESCE(a.provider, 'unknown')      AS provider,
                  COALESCE(a.model, '(none)')          AS model,
                  COUNT(*)                             AS answers,
                  SUM(CASE WHEN a.grounded = 1 THEN 1 ELSE 0 END) AS grounded,
                  SUM(CASE WHEN a.degraded = 1 THEN 1 ELSE 0 END) AS degraded,
                  COALESCE(SUM(a.prompt_tokens), 0)     AS prompt_tokens,
                  COALESCE(SUM(a.completion_tokens), 0) AS completion_tokens,
                  MAX(a.created_at)                     AS last_at
           FROM ai_answers a
           WHERE a.created_at >= datetime('now', ?)
           GROUP BY provider, model
           ORDER BY provider, model""",
        (since,),
    ).fetchall()
    items = [dict(row) for row in rows]
    totals = {
        "answers": sum(item["answers"] for item in items),
        "grounded": sum(item["grounded"] for item in items),
        "degraded": sum(item["degraded"] for item in items),
        "prompt_tokens": sum(item["prompt_tokens"] for item in items),
        "completion_tokens": sum(item["completion_tokens"] for item in items),
    }
    latency = conn.execute(
        """SELECT COUNT(*) AS answers, AVG(latency_ms) AS avg_ms, MAX(latency_ms) AS max_ms
           FROM query_logs WHERE created_at >= datetime('now', ?)""",
        (since,),
    ).fetchone()
    return {
        "days": max(1, int(days)),
        "providers": items,
        "totals": totals,
        "latency": {
            "answers": latency["answers"],
            "avg_ms": round(latency["avg_ms"], 1) if latency["avg_ms"] is not None else None,
            "max_ms": latency["max_ms"],
        },
    }


def audit(
    conn: sqlite3.Connection,
    *,
    actor: str,
    action: str,
    target: str | None = None,
    detail: dict | None = None,
    ip_hash: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO audit_log (actor, action, target, detail, ip_hash) VALUES (?,?,?,?,?)",
        (actor, action, target, json.dumps(detail or {}, ensure_ascii=False), ip_hash),
    )


def log_error(
    conn: sqlite3.Connection,
    *,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    error_type: str,
    message: str | None,
) -> None:
    conn.execute(
        """INSERT INTO error_log (request_id, method, path, status_code, error_type, message)
           VALUES (?,?,?,?,?,?)""",
        (request_id, method, path, status_code, error_type, redact(message)),
    )


def recent_errors(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        "SELECT at, request_id, method, path, status_code, error_type, message "
        "FROM error_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def recent_queries(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        """SELECT created_at, language, category, provider, latency_ms, status, error_code,
                  query_text, query_hash
           FROM query_logs ORDER BY id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def recent_answers(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        """SELECT a.created_at, a.provider, a.model, a.grounded, a.degraded, a.warnings_json,
                  a.citations_json, a.query_log_id
           FROM ai_answers a ORDER BY a.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["warnings"] = json.loads(item.pop("warnings_json") or "[]")
        item["citations"] = json.loads(item.pop("citations_json") or "[]")
        out.append(item)
    return out


def audit_trail(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    rows = conn.execute(
        "SELECT at, actor, action, target, detail FROM audit_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["detail"] = json.loads(item["detail"] or "{}")
        except json.JSONDecodeError:  # pragma: no cover
            pass
        out.append(item)
    return out


def stats(conn: sqlite3.Connection) -> dict[str, Any]:
    def scalar(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0])

    counts = {
        "articles": scalar("SELECT COUNT(*) FROM constitution_articles"),
        "sources": scalar("SELECT COUNT(*) FROM legal_sources"),
        "departments": scalar("SELECT COUNT(*) FROM departments"),
        "triage_guides": scalar("SELECT COUNT(*) FROM triage_guides"),
        "complaints": scalar("SELECT COUNT(*) FROM complaints"),
        "documents": scalar("SELECT COUNT(*) FROM documents"),
        "query_logs": scalar("SELECT COUNT(*) FROM query_logs"),
        "feedback": scalar("SELECT COUNT(*) FROM feedback"),
        "legacy_chunks_quarantined": scalar("SELECT COUNT(*) FROM legacy_import_chunks"),
        "verified_articles": scalar(
            "SELECT COUNT(*) FROM constitution_articles WHERE verification_status = 'verified'"
        ),
        "verified_departments": scalar(
            "SELECT COUNT(*) FROM departments WHERE verification_status = 'verified'"
        ),
    }
    days = conn.execute(
        "SELECT COUNT(*) FROM query_logs WHERE created_at >= datetime('now','-1 day')"
    ).fetchone()[0]
    degraded = conn.execute(
        "SELECT COUNT(*) FROM ai_answers WHERE degraded = 1"
    ).fetchone()[0]
    recent_errors = conn.execute(
        "SELECT COUNT(*) FROM error_log WHERE at >= datetime('now','-1 day')"
    ).fetchone()[0]
    return {
        "counts": counts,
        "ai": {
            "queries_last_24h": int(days),
            "degraded_answers": int(degraded),
        },
        "corpus": {
            "with_verified_text": counts["articles"] - scalar(
                "SELECT COUNT(*) FROM constitution_articles WHERE text_status != 'verified_source_text'"
            ),
            "requires_human_verification": scalar(
                "SELECT COUNT(*) FROM constitution_articles "
                "WHERE verification_status = 'requires_human_verification'"
            ),
        },
        "recent_errors": int(recent_errors),
    }

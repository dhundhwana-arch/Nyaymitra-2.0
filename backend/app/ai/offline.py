"""Deterministic "offline grounded" provider.

It is not a language model. It assembles an answer exclusively from
(a) the retrieved article rows and (b) the curated triage guide, using fixed
templates. That makes it structurally incapable of inventing a provision, which is
exactly why it is the fallback when no provider is configured.
"""
from __future__ import annotations

from typing import Any

from .base import ProviderResult


def _bullet(items: list[str]) -> str:
    return "\n".join(f"• {item}" for item in items)


def compose(
    *,
    question: str,
    language: str,
    articles: list[dict[str, Any]],
    guide: dict[str, Any] | None,
    departments: list[dict[str, Any]],
) -> str:
    lang = "gu" if language == "gu" else "en"
    blocks: list[str] = []

    if lang == "gu":
        blocks.append("તમે પૂછેલ પ્રશ્ન પરથી મળતી સામાન્ય માહિતી નીચે છે.")
        if guide:
            blocks.append(f"શ્રેણી: {guide['category_gu']}.")
            if guide.get("summary"):
                blocks.append(guide["summary"])
            if guide.get("steps"):
                blocks.append("આગળના સંભવિત પગલાં:\n" + _bullet(guide["steps"]))
            if guide.get("documents"):
                blocks.append("તૈયાર રાખવાના દસ્તાવેજો:\n" + _bullet(guide["documents"]))
        if not articles:
            blocks.append("આ પ્રશ્ન સાથે સીધી સંબંધિત બંધારણીય કલમ હાલના ડેટાબેઝમાં મળી નથી.")
        if not articles:
            blocks.append("No constitution article directly matching this question is loaded in the database.")
        if articles:
            cited = []
            for art in articles:
                title = art.get("title_gu") or art.get("title_en") or ""
                explanation = art.get("citizen_explanation_gu") or art.get("text_gu")
                kind = (" [સમજૂતી — સત્તાવાર લખાણ નથી]" if art.get("citizen_explanation_gu") or not explanation
                        else " [સ્રોત દસ્તાવેજનું લખાણ — માનવ ચકાસણી બાકી]")
                cited.append(f"{art['article_label']} — {title}" + (f": {explanation}" if explanation else "") + kind)
            blocks.append("સંબંધિત બંધારણીય જોગવાઈઓ (સ્રોત સાથે):\n" + _bullet(cited))
        if departments:
            blocks.append(
                "સંપર્ક માટેની કચેરીઓ:\n"
                + _bullet(
                    [
                        f"{d['name_gu']}" + (f" — હેલ્પલાઇન {d['helpline']}" if d.get("helpline") else "")
                        + (" (ચકાસાયેલ નથી)" if d["verification_status"] != "verified" else "")
                        for d in departments
                    ]
                )
            )
        blocks.append(
            "આ માહિતી છે, કાનૂની સલાહ નથી. તમારા કેસ માટે વકીલ કે મફત કાનૂની સહાય (15100) નો સંપર્ક કરો."
        )
    else:
        blocks.append("Here is general information assembled from the sources in this database.")
        if guide:
            blocks.append(f"Category: {guide['category_en']}.")
            if guide.get("summary"):
                blocks.append(guide["summary"])
            if guide.get("steps"):
                blocks.append("Possible next steps:\n" + _bullet(guide["steps"]))
            if guide.get("documents"):
                blocks.append("Documents to keep ready:\n" + _bullet(guide["documents"]))
        if not articles:
            blocks.append("આ પ્રશ્ન સાથે સીધી સંબંધિત બંધારણીય કલમ હાલના ડેટાબેઝમાં મળી નથી.")
        if not articles:
            blocks.append("No constitution article directly matching this question is loaded in the database.")
        if articles:
            cited = []
            for art in articles:
                title = art.get("title_en") or art.get("title_gu") or ""
                explanation = art.get("citizen_explanation_en") or art.get("text_en")
                kind = (" [explanation — not the official text]" if art.get("citizen_explanation_en") or not explanation
                        else " [text from the source document — human verification pending]")
                cited.append(f"{art['article_label']} — {title}" + (f": {explanation}" if explanation else "") + kind)
            blocks.append("Relevant constitutional provisions (with source):\n" + _bullet(cited))
        if departments:
            blocks.append(
                "Offices you can contact:\n"
                + _bullet(
                    [
                        d["name_en"]
                        + (f" — helpline {d['helpline']}" if d.get("helpline") else "")
                        + (" (not verified)" if d["verification_status"] != "verified" else "")
                        for d in departments
                    ]
                )
            )
        blocks.append(
            "This is information, not legal advice. For your own case contact a lawyer or free legal aid (15100)."
        )

    return "\n\n".join(blocks)


class OfflineGroundedProvider:
    """Implements the ``AIProvider`` protocol without any model call."""

    name = "offline"
    model = None

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        # The payload is injected by the RAG layer (it needs the DB rows).
        self._payload = payload or {}

    def available(self) -> bool:
        return True

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        temperature: float = 0.1,
    ) -> ProviderResult:  # pragma: no cover - RAG calls compose() directly
        text = compose(
            question=user_prompt,
            language=self._payload.get("language", "gu"),
            articles=self._payload.get("articles", []),
            guide=self._payload.get("guide"),
            departments=self._payload.get("departments", []),
        )
        return ProviderResult(text=text, provider=self.name, model=None)

"""Provider abstraction.

Rules encoded here:
* A provider never sees the database. It receives text the retrieval layer built.
* A provider that is not configured is *absent*, not silent: the caller decides between
  a deterministic grounded answer and a hard ``503 provider_unavailable``.
* No provider may be imported from a hard-coded vendor SDK; everything goes through
  the ``AIProvider`` protocol so a new vendor is one file.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class AIProviderError(Exception):
    """Base class for provider failures (always mapped to a safe client error)."""


class ProviderUnavailable(AIProviderError):
    """No provider configured, or the configured provider could not be reached."""


class ProviderRejected(AIProviderError):
    """The provider answered, but the answer violated our grounding/safety rules."""


@dataclass(frozen=True)
class ProviderResult:
    text: str
    provider: str
    model: str | None
    degraded: bool = False
    usage: dict | None = None


@runtime_checkable
class AIProvider(Protocol):
    name: str
    model: str | None

    def available(self) -> bool: ...

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        temperature: float = 0.1,
    ) -> ProviderResult: ...

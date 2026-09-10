"""Retriever protocol and base classes."""
from __future__ import annotations

from typing import Protocol

from core.models import RetrievalResult


class Retriever(Protocol):
    def search(self, query: str, *, limit: int = 10) -> RetrievalResult: ...

"""Flat FTS baseline retrieval — simple FTS5 over entire corpus."""
from __future__ import annotations

import time

from core.models import EvidenceItem, RetrievalResult
from storage.database import Database


class FlatFTSRetriever:
    def __init__(self, db: Database):
        self.db = db

    def search(self, query: str, *, limit: int = 10) -> RetrievalResult:
        t0 = time.perf_counter()

        rows = self.db.search_fts(query, limit=limit)
        evidence = []
        for r in rows:
            resource = self.db.get_resource_by_id(r["resource_id"])
            source_path = resource["absolute_path"] if resource else "unknown"
            evidence.append(EvidenceItem(
                resource_id=r["resource_id"],
                source_path=source_path,
                passage_id=r["passage_id"],
                text=r["text"],
                score=0.5,
                node_id=r.get("node_id"),
            ))

        latency = (time.perf_counter() - t0) * 1000
        return RetrievalResult(
            query=query,
            strategy="flat_fts",
            evidence=evidence,
            files_considered=len(self.db.get_all_resources()),
            passages_considered=len(rows),
            bytes_read=sum(len(e.text.encode()) for e in evidence),
            retrieval_latency_ms=latency,
        )

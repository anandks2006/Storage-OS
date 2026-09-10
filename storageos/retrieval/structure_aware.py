"""Structure-aware retrieval — uses precompiled structural model to narrow search."""
from __future__ import annotations

import re
import time

from core.models import EvidenceItem, RetrievalResult
from storage.database import Database


class StructureAwareRetriever:
    def __init__(self, db: Database):
        self.db = db

    def search(self, query: str, *, limit: int = 10) -> RetrievalResult:
        t0 = time.perf_counter()
        files_considered = 0
        nodes_visited = 0
        passages_considered = 0
        bytes_read = 0

        resources = self.db.get_all_resources()
        files_considered = len(resources)

        # Phase 1: narrow to candidate documents using heading/title matches
        query_lower = query.lower()
        query_tokens = set(re.findall(r"\w+", query_lower))

        candidate_resources = []
        for res in resources:
            res_id = res["resource_id"]
            nodes = self.db.get_nodes_for_resource(res_id)
            nodes_visited += len(nodes)

            # Check if any heading matches query tokens
            score = 0.0
            for node in nodes:
                title_lower = node["title"].lower()
                title_tokens = set(re.findall(r"\w+", title_lower))
                overlap = query_tokens & title_tokens
                if overlap:
                    score += len(overlap) / len(query_tokens) if query_tokens else 0
                # Also check filename
                fname_tokens = set(re.findall(r"\w+", res["filename"].lower()))
                fname_overlap = query_tokens & fname_tokens
                if fname_overlap:
                    score += 0.5

            candidate_resources.append((res_id, score, res))

        # Sort by score, take top candidates (minimum 20% of corpus or all if few)
        candidate_resources.sort(key=lambda x: x[1], reverse=True)
        min_candidates = max(1, len(candidate_resources) // 5)
        candidates = candidate_resources[:min_candidates]

        # Phase 2: FTS within candidate documents
        candidate_ids = {c[0] for c in candidates}
        all_evidence = []

        for res_id, _, res in candidates:
            passages = self.db.get_passages_for_resource(res_id)
            for p in passages:
                passages_considered += 1
                text_bytes = len(p["text"].encode())
                bytes_read += text_bytes

                # Simple token match scoring for passages
                passage_lower = p["text"].lower()
                matches = sum(1 for t in query_tokens if t in passage_lower)
                if matches > 0:
                    score = matches / len(query_tokens) if query_tokens else 0
                    all_evidence.append(EvidenceItem(
                        resource_id=res_id,
                        source_path=res["absolute_path"],
                        passage_id=p["passage_id"],
                        text=p["text"],
                        score=score,
                        node_id=p.get("node_id"),
                    ))

        # Sort evidence by score and take top limit
        all_evidence.sort(key=lambda e: e.score, reverse=True)
        evidence = all_evidence[:limit]

        latency = (time.perf_counter() - t0) * 1000
        return RetrievalResult(
            query=query,
            strategy="structure_aware",
            evidence=evidence,
            files_considered=files_considered,
            passages_considered=passages_considered,
            structural_nodes_visited=nodes_visited,
            bytes_read=bytes_read,
            retrieval_latency_ms=latency,
        )

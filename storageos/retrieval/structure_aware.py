"""Structure-aware retrieval — uses precompiled structural model to narrow search."""
from __future__ import annotations

import re
import time
from collections import defaultdict

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
        fallback_used = False

        resources = self.db.get_all_resources()
        files_considered = len(resources)

        # Batch-fetch all nodes and passages once (avoids N+1 queries)
        all_nodes = self.db.get_all_nodes()
        all_passages = self.db.get_all_passages()
        nodes_by_res = defaultdict(list)
        for n in all_nodes:
            nodes_by_res[n["resource_id"]].append(n)
        passages_by_res = defaultdict(list)
        for p in all_passages:
            passages_by_res[p["resource_id"]].append(p)

        # Phase 1: narrow to candidate documents using heading/title matches
        query_lower = query.lower()
        query_tokens = set(re.findall(r"\w+", query_lower))

        candidate_resources = []
        for res in resources:
            res_id = res["resource_id"]
            nodes = nodes_by_res.get(res_id, [])
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

        # Step 1 fix: retain only positively-scored candidates
        # Fallback: if zero scored > 0, use full corpus so we never return nothing
        candidate_resources.sort(key=lambda x: x[1], reverse=True)
        candidates = [(rid, sc, res) for rid, sc, res in candidate_resources if sc > 0]
        if not candidates:
            candidates = candidate_resources
            fallback_used = True

        # Phase 2: passage inspection with structural narrowing
        all_evidence = []

        for res_id, _, res in candidates:
            passages = passages_by_res.get(res_id, [])
            nodes = nodes_by_res.get(res_id, [])

            # Step 2 fix: score structural nodes, narrow to passages within
            # positively-scored node ranges
            node_scores = {}
            for node in nodes:
                title_lower = node["title"].lower()
                title_tokens = set(re.findall(r"\w+", title_lower))
                overlap = query_tokens & title_tokens
                if overlap:
                    node_scores[node["node_id"]] = (
                        len(overlap) / len(query_tokens) if query_tokens else 0,
                        node["start_offset"],
                        node["end_offset"],
                    )

            # Determine which passages to inspect
            if node_scores:
                # Only passages whose start falls within a positively-scored node
                candidate_passages = []
                for p in passages:
                    for nid, (_, ns, ne) in node_scores.items():
                        if ns <= p["start_offset"] < ne:
                            candidate_passages.append(p)
                            break
            else:
                # Fallback: inspect all passages in this document
                candidate_passages = passages
                if passages:
                    fallback_used = True

            for p in candidate_passages:
                passages_considered += 1
                text_bytes = len(p["text"].encode())
                bytes_read += text_bytes

                # Token match scoring for passages
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

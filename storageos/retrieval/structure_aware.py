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
        fallback_used = False

        # Step 1: get resource list only (1 query)
        resources = self.db.get_all_resources()
        files_considered = len(resources)

        query_lower = query.lower()
        query_tokens = set(re.findall(r"\w+", query_lower))

        # Step 2: score resources — filename scoring is free (from resource row),
        # heading scoring requires per-resource node fetch
        resource_scores = []
        filename_only_candidates = []
        need_node_fetch = []

        for res in resources:
            res_id = res["resource_id"]
            fname_tokens = set(re.findall(r"\w+", res["filename"].lower()))
            fname_score = 0.5 if (query_tokens & fname_tokens) else 0.0

            if fname_score > 0:
                # Filename matches — score without fetching nodes yet
                resource_scores.append((res_id, fname_score, res))
                filename_only_candidates.append((res_id, fname_score, res))
            else:
                need_node_fetch.append((res_id, res))

        # Step 3: fetch nodes only for resources that need heading scoring
        for res_id, res in need_node_fetch:
            nodes = self.db.get_nodes_for_resource(res_id)
            nodes_visited += len(nodes)
            score = 0.0
            for node in nodes:
                title_lower = node["title"].lower()
                title_tokens = set(re.findall(r"\w+", title_lower))
                overlap = query_tokens & title_tokens
                if overlap:
                    score += len(overlap) / len(query_tokens) if query_tokens else 0
            resource_scores.append((res_id, score, res))

        # Step 4: select positively-scored candidates (no corpus-wide floor)
        resource_scores.sort(key=lambda x: x[1], reverse=True)
        candidates = [(rid, sc, res) for rid, sc, res in resource_scores if sc > 0]
        if not candidates:
            candidates = resource_scores
            fallback_used = True

        # Step 5: for each candidate, fetch nodes + passages selectively
        all_evidence = []

        for res_id, _, res in candidates:
            nodes = self.db.get_nodes_for_resource(res_id)
            nodes_visited += len(nodes)
            passages = self.db.get_passages_for_resource(res_id)

            # Node scoring for passage filtering
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

            # Filter passages by node ranges
            if node_scores:
                candidate_passages = []
                for p in passages:
                    for nid, (_, ns, ne) in node_scores.items():
                        if ns <= p["start_offset"] < ne:
                            candidate_passages.append(p)
                            break
            else:
                candidate_passages = passages
                if passages:
                    fallback_used = True

            # Passage scoring
            for p in candidate_passages:
                passages_considered += 1
                text_bytes = len(p["text"].encode())
                bytes_read += text_bytes

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

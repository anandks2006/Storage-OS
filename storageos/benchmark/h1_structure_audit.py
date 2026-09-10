"""Read-only audit of StructureAwareRetriever behavior.

Instruments the retriever by wrapping its search method to capture
intermediate state at each phase. No modifications to any source files.
"""
from __future__ import annotations

import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.database import Database
from ingest.scanner import scan_directory
from representation.compiler import compile_all
from retrieval.structure_aware import StructureAwareRetriever
from retrieval.flat_fts import FlatFTSRetriever

# ---------------------------------------------------------------------------
# Corpus assembly (same as benchmark)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGEOS_PKG = PROJECT_ROOT / "storageos"

CORPUS_FILES_MD = [
    PROJECT_ROOT / "PRD.md",
    PROJECT_ROOT / "H1_EXPERIMENT.md",
    PROJECT_ROOT / "README.md",
]
CORPUS_FILES_PY = sorted(STORAGEOS_PKG.rglob("*.py"))


def assemble_corpus(target: Path) -> Path:
    corpus = target / "corpus"
    corpus.mkdir(exist_ok=True)
    for f in CORPUS_FILES_MD:
        if f.exists():
            shutil.copy2(f, corpus / f.name)
    for f in CORPUS_FILES_PY:
        if f.exists():
            rel = f.relative_to(STORAGEOS_PKG)
            dest = corpus / str(rel.with_suffix(".txt"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
    return corpus

import shutil


# ---------------------------------------------------------------------------
# Questions (exact 20 from H1 benchmark)
# ---------------------------------------------------------------------------
QUESTIONS = [
    {"id": "Q01", "text": "What is the StorageOS research hypothesis?", "bucket": "heading-aligned"},
    {"id": "Q02", "text": "What source types are supported in H1?", "bucket": "heading-aligned"},
    {"id": "Q03", "text": "What is the representation manifest?", "bucket": "heading-aligned"},
    {"id": "Q04", "text": "What are the non-goals for H1?", "bucket": "heading-aligned"},
    {"id": "Q05", "text": "What does the SQLite persistence section specify?", "bucket": "heading-aligned"},
    {"id": "Q06", "text": "What is the evidence model?", "bucket": "heading-aligned"},
    {"id": "Q07", "text": "How does the system detect whether a file has changed?", "bucket": "heading-misaligned"},
    {"id": "Q08", "text": "What algorithm is used for content hashing?", "bucket": "heading-misaligned"},
    {"id": "Q09", "text": "How are passages split in the markdown parser?", "bucket": "heading-misaligned"},
    {"id": "Q10", "text": "What happens when a PDF library is not installed?", "bucket": "heading-misaligned"},
    {"id": "Q11", "text": "How does the structure-aware retriever narrow candidates?", "bucket": "heading-misaligned"},
    {"id": "Q12", "text": "What triggers are attached to the FTS virtual table?", "bucket": "heading-misaligned"},
    {"id": "Q13", "text": "What is the full pipeline from filesystem to evidence set?", "bucket": "cross-document"},
    {"id": "Q14", "text": "How is source immutability enforced across the codebase?", "bucket": "cross-document"},
    {"id": "Q15", "text": "What is the relationship between resources, versions, and passages?", "bucket": "cross-document"},
    {"id": "Q16", "text": "How do the two retrieval strategies differ in their approach?", "bucket": "cross-document"},
    {"id": "Q17", "text": "What is the complete set of SQLite tables used by StorageOS?", "bucket": "cross-document"},
    {"id": "Q18", "text": "How does incremental indexing avoid reprocessing unchanged files?", "bucket": "cross-document"},
    {"id": "Q19", "text": "What metrics does the benchmark harness need to record?", "bucket": "cross-document"},
    {"id": "Q20", "text": "How are structural nodes organized in the heading hierarchy?", "bucket": "cross-document"},
]


# ---------------------------------------------------------------------------
# Instrumented search — captures Phase 1 and Phase 2 intermediate state
# ---------------------------------------------------------------------------
def instrumented_search(retriever: StructureAwareRetriever, query: str) -> dict[str, Any]:
    """Reproduce the exact StructureAwareRetriever logic, capturing every intermediate value."""
    db = retriever.db

    # Phase 1 (exact replica of lines 22-54)
    resources = db.get_all_resources()
    total_files = len(resources)

    query_lower = query.lower()
    query_tokens = set(re.findall(r"\w+", query_lower))

    all_resource_nodes = {}
    scored_resources = []

    for res in resources:
        res_id = res["resource_id"]
        nodes = db.get_nodes_for_resource(res_id)
        all_resource_nodes[res_id] = nodes

        score = 0.0
        heading_signals = []
        filename_signal = None

        for node in nodes:
            title_lower = node["title"].lower()
            title_tokens = set(re.findall(r"\w+", title_lower))
            overlap = query_tokens & title_tokens
            if overlap:
                contribution = len(overlap) / len(query_tokens) if query_tokens else 0
                score += contribution
                heading_signals.append((node["title"], overlap, contribution))

        fname_tokens = set(re.findall(r"\w+", res["filename"].lower()))
        fname_overlap = query_tokens & fname_tokens
        if fname_overlap:
            score += 0.5
            filename_signal = (res["filename"], fname_overlap)

        scored_resources.append({
            "resource_id": res_id,
            "filename": res["filename"],
            "path": res["absolute_path"],
            "score": score,
            "heading_signals": heading_signals,
            "filename_signal": filename_signal,
            "node_count": len(nodes),
            "heading_titles": [n["title"] for n in nodes],
        })

    # Sort and apply min_candidates threshold
    scored_resources.sort(key=lambda x: x["score"], reverse=True)
    total_nodes = sum(r["node_count"] for r in scored_resources)

    min_candidates = max(1, len(scored_resources) // 5)
    candidates = scored_resources[:min_candidates]
    candidate_ids = {c["resource_id"] for c in candidates}

    # Count how many have score > 0
    nonzero_scored = [r for r in scored_resources if r["score"] > 0]

    # Phase 2 (exact replica of lines 56-79)
    passages_considered = 0
    bytes_read = 0
    matched_passages = 0

    for res_id, _, _ in [(c["resource_id"], c["score"], c) for c in candidates]:
        passages = db.get_passages_for_resource(res_id)
        for p in passages:
            passages_considered += 1
            text_bytes = len(p["text"].encode())
            bytes_read += text_bytes

            passage_lower = p["text"].lower()
            matches = sum(1 for t in query_tokens if t in passage_lower)
            if matches > 0:
                matched_passages += 1

    return {
        "query": query,
        "query_tokens": sorted(query_tokens),
        "total_files": total_files,
        "total_nodes": total_nodes,
        "scored_resources": scored_resources,
        "nonzero_scored_count": len(nonzero_scored),
        "nonzero_scored": nonzero_scored,
        "min_candidates_threshold": min_candidates,
        "candidates_after": len(candidates),
        "candidate filenames": [c["filename"] for c in candidates],
        "passages_considered": passages_considered,
        "bytes_read": bytes_read,
        "matched_passages": matched_passages,
    }


# ---------------------------------------------------------------------------
# Corpus content inspection for theoretical headroom
# ---------------------------------------------------------------------------
def inspect_corpus(corpus: Path) -> dict[str, Any]:
    """Read all corpus files and return content summary for headroom analysis."""
    files = {}
    for f in sorted(corpus.rglob("*")):
        if f.is_file():
            rel = f.relative_to(corpus)
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                files[str(rel)] = {
                    "size": len(content),
                    "headings": re.findall(r"^#{1,6}\s+(.+)$", content, re.MULTILINE),
                    "first_500": content[:500],
                }
            except Exception:
                files[str(rel)] = {"size": 0, "headings": [], "first_500": ""}
    return files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("StructureAwareRetriever Read-Only Audit")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        corpus = assemble_corpus(tmp)

        # Build index
        db_path = tmp / "audit.db"
        db = Database(db_path)
        db.init_schema()
        space_id = db.create_space("audit", str(corpus), time.time())
        scan_directory(corpus, db, space_id)
        compile_all(db)

        # Corpus stats
        all_resources = db.get_all_resources()
        total_files = len(all_resources)
        total_passages = sum(len(db.get_passages_for_resource(r["resource_id"])) for r in all_resources)
        total_nodes = sum(len(db.get_nodes_for_resource(r["resource_id"])) for r in all_resources)

        print(f"\nCorpus: {total_files} files, {total_nodes} nodes, {total_passages} passages")

        # File listing
        print("\n--- Corpus files ---")
        for r in all_resources:
            nodes = db.get_nodes_for_resource(r["resource_id"])
            passages = db.get_passages_for_resource(r["resource_id"])
            headings = [n["title"] for n in nodes if n["title"]]
            print(f"  {r['filename']:40s}  nodes={len(nodes):3d}  passages={len(passages):3d}  headings={headings[:5]}")

        # Run instrumented search for each question
        retriever = StructureAwareRetriever(db)
        results = []

        print("\n--- Per-question audit ---")
        for q in QUESTIONS:
            audit = instrumented_search(retriever, q["text"])
            audit["bucket"] = q["bucket"]
            audit["question_id"] = q["id"]
            results.append(audit)

            print(f"\n{q['id']} [{q['bucket']}]: {q['text']}")
            print(f"  Query tokens: {audit['query_tokens']}")
            print(f"  Files with score > 0: {audit['nonzero_scored_count']}/{audit['total_files']}")
            for nr in audit["nonzero_scored"]:
                signals = []
                if nr["heading_signals"]:
                    for title, overlap, contrib in nr["heading_signals"]:
                        signals.append(f"heading '{title}' -> {overlap} (+{contrib:.3f})")
                if nr["filename_signal"]:
                    fname, foverlap = nr["filename_signal"]
                    signals.append(f"filename '{fname}' -> {foverlap} (+0.5)")
                print(f"    + {nr['filename']:35s} score={nr['score']:.3f}  {', '.join(signals)}")
            print(f"  min_candidates threshold: {audit['min_candidates_threshold']} (20% of {audit['total_files']})")
            print(f"  Candidates after narrowing: {audit['candidates_after']}")
            print(f"  Passages inspected: {audit['passages_considered']}")
            print(f"  Bytes read: {audit['bytes_read']}")

        db.close()

    # Write results JSON
    import json
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = results_dir / f"h1_structure_audit_{date_str}.json"

    # Serialize (remove non-serializable items)
    json_results = []
    for r in results:
        jr = {k: v for k, v in r.items()}
        json_results.append(jr)

    json_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_files": total_files,
        "total_nodes": total_nodes,
        "total_passages": total_passages,
        "questions": json_results,
    }, indent=2, default=str), encoding="utf-8")
    print(f"\nAudit data written to: {json_path}")


if __name__ == "__main__":
    main()

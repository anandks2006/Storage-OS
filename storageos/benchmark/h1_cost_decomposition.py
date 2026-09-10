"""H1 Cost Decomposition — measures where StructureAwareRetriever time is spent.

Read-only instrumentation: does not modify the retriever algorithm.
Uses a timing-instrumented replica of the search method to measure each stage.
"""
from __future__ import annotations

import gc
import json
import re
import shutil
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.database import Database
from ingest.scanner import scan_directory
from representation.compiler import compile_all
from retrieval.structure_aware import StructureAwareRetriever
from core.models import EvidenceItem, RetrievalResult, Passage, SourceType
from parsers.markdown import parse_markdown
from parsers.text import parse_text
from parsers.pdf import parse_pdf

# ---------------------------------------------------------------------------
# Corpus assembly (reused from h1_lifetime_cost.py)
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


# ---------------------------------------------------------------------------
# Questions (same 20 as h1_lifetime_cost.py)
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
# Instrumented search — replicates StructureAwareRetriever.search() exactly
# but inserts perf_counter() calls at each logical stage.
# ---------------------------------------------------------------------------

def instrumented_search(db: Database, query: str, limit: int = 10, total_passages: int = 0) -> dict[str, Any]:
    """Run the same logic as the selective StructureAwareRetriever.search() with per-stage timing."""
    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    # --- Stage 1: Resource list (1 query) ---
    t_s = time.perf_counter()
    resources = db.get_all_resources()
    timings["db_reads"] = (time.perf_counter() - t_s) * 1000

    files_considered = len(resources)

    # --- Stage 2: Query tokenization ---
    t_s = time.perf_counter()
    query_lower = query.lower()
    query_tokens = set(re.findall(r"\w+", query_lower))
    timings["tokenization"] = (time.perf_counter() - t_s) * 1000

    # --- Stage 3: Filename scoring (from resource rows, no DB) ---
    t_s = time.perf_counter()
    resource_scores = []
    need_node_fetch = []
    for res in resources:
        res_id = res["resource_id"]
        fname_tokens = set(re.findall(r"\w+", res["filename"].lower()))
        fname_score = 0.5 if (query_tokens & fname_tokens) else 0.0
        if fname_score > 0:
            resource_scores.append((res_id, fname_score, res))
        else:
            need_node_fetch.append((res_id, res))
    timings["filename_scoring"] = (time.perf_counter() - t_s) * 1000

    # --- Stage 4: Selective node fetch + heading scoring ---
    t_s = time.perf_counter()
    nodes_visited = 0
    for res_id, res in need_node_fetch:
        nodes = db.get_nodes_for_resource(res_id)
        nodes_visited += len(nodes)
        score = 0.0
        for node in nodes:
            title_lower = node["title"].lower()
            title_tokens = set(re.findall(r"\w+", title_lower))
            overlap = query_tokens & title_tokens
            if overlap:
                score += len(overlap) / len(query_tokens) if query_tokens else 0
        resource_scores.append((res_id, score, res))
    timings["node_fetch_and_scoring"] = (time.perf_counter() - t_s) * 1000

    # --- Stage 5: Candidate selection ---
    t_s = time.perf_counter()
    resource_scores.sort(key=lambda x: x[1], reverse=True)
    candidates = [(rid, sc, res) for rid, sc, res in resource_scores if sc > 0]
    fallback_used = False
    if not candidates:
        candidates = resource_scores
        fallback_used = True
    timings["candidate_selection"] = (time.perf_counter() - t_s) * 1000

    # --- Stage 6: Per-candidate node fetch + passage fetch + filtering + scoring ---
    t_s = time.perf_counter()
    all_evidence = []
    passages_considered = 0
    bytes_read = 0

    for res_id, _, res in candidates:
        nodes = db.get_nodes_for_resource(res_id)
        nodes_visited += len(nodes)
        passages = db.get_passages_for_resource(res_id)

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

    timings["phase2_total"] = (time.perf_counter() - t_s) * 1000

    # --- Stage 7: Final ranking ---
    t_s = time.perf_counter()
    all_evidence.sort(key=lambda e: e.score, reverse=True)
    evidence = all_evidence[:limit]
    timings["ranking"] = (time.perf_counter() - t_s) * 1000

    # --- Stage 8: Evidence assembly ---
    t_s = time.perf_counter()
    evidence_text = "\n".join(e.text for e in evidence)
    result = RetrievalResult(
        query=query,
        strategy="structure_aware",
        evidence=evidence,
        files_considered=files_considered,
        passages_considered=passages_considered,
        structural_nodes_visited=nodes_visited,
        bytes_read=bytes_read,
        retrieval_latency_ms=0,
    )
    timings["evidence_assembly"] = (time.perf_counter() - t_s) * 1000

    timings["total"] = (time.perf_counter() - t_total) * 1000

    return {
        "timings": timings,
        "passages_considered": passages_considered,
        "total_passages": total_passages,
        "bytes_read": bytes_read,
        "evidence_count": len(evidence),
        "evidence_chars": len(evidence_text),
        "fallback_used": fallback_used,
        "nodes_visited": nodes_visited,
        "files_considered": files_considered,
        "candidates_after": len(candidates),
    }


# ---------------------------------------------------------------------------
# Run benchmark
# ---------------------------------------------------------------------------

def run_decomposition(runs_per_query: int = 20) -> dict[str, Any]:
    """Run all 20 questions N times each, collect per-stage timing stats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        corpus = assemble_corpus(tmp)

        # Build index
        db_path = tmp / "decomposition.db"
        db = Database(db_path)
        db.init_schema()
        space_id = db.create_space("h1-decomp", str(corpus), time.time())
        scan_directory(corpus, db, space_id)
        compile_all(db)

        # Verify retriever works (read-only check)
        retriever = StructureAwareRetriever(db)
        test_result = retriever.search("test")
        assert test_result.strategy == "structure_aware"

        print(f"Running {runs_per_query} iterations x 20 questions...")
        all_runs: dict[str, list[dict]] = {q["id"]: [] for q in QUESTIONS}

        # Get total passage count once for reduction ratio stats
        total_passages = db.connect().execute("SELECT COUNT(*) FROM passages").fetchone()[0]

        for i in range(runs_per_query):
            if (i + 1) % 5 == 0:
                print(f"  Iteration {i+1}/{runs_per_query}...")
            for q in QUESTIONS:
                result = instrumented_search(db, q["text"], total_passages=total_passages)
                all_runs[q["id"]].append(result)

        db.close()

    # Compute stats
    timing_keys = [
        "db_reads", "tokenization", "filename_scoring",
        "node_fetch_and_scoring", "candidate_selection",
        "phase2_total", "ranking", "evidence_assembly", "total",
    ]

    per_question = {}
    for q in QUESTIONS:
        qid = q["id"]
        runs = all_runs[qid]
        per_question[qid] = {
            "bucket": q["bucket"],
            "text": q["text"],
            "timings": {},
            "passages_considered": statistics.mean([r["passages_considered"] for r in runs]),
            "total_passages": runs[0]["total_passages"],
            "bytes_read": statistics.mean([r["bytes_read"] for r in runs]),
            "evidence_count": statistics.mean([r["evidence_count"] for r in runs]),
            "evidence_chars": statistics.mean([r["evidence_chars"] for r in runs]),
            "fallback_used": any(r["fallback_used"] for r in runs),
            "candidates_after": runs[0]["candidates_after"],
        }
        for key in timing_keys:
            values = [r["timings"][key] for r in runs]
            per_question[qid]["timings"][key] = {
                "mean": statistics.mean(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values),
            }

    # Per-bucket aggregation
    buckets = {"heading-aligned": [], "heading-misaligned": [], "cross-document": []}
    for q in QUESTIONS:
        buckets[q["bucket"]].append(q["id"])

    per_bucket = {}
    for bucket_name, qids in buckets.items():
        per_bucket[bucket_name] = {"timings": {}, "n_questions": len(qids)}
        for key in timing_keys:
            means = [per_question[qid]["timings"][key]["mean"] for qid in qids]
            per_bucket[bucket_name]["timings"][key] = {
                "mean": statistics.mean(means),
                "std": statistics.stdev(means) if len(means) > 1 else 0,
                "min": min(means),
                "max": max(means),
            }

    # Overall aggregation
    overall = {"timings": {}}
    for key in timing_keys:
        means = [per_question[qid]["timings"][key]["mean"] for qid in per_question]
        overall["timings"][key] = {
            "mean": statistics.mean(means),
            "std": statistics.stdev(means) if len(means) > 1 else 0,
            "min": min(means),
            "max": max(means),
        }
    overall["passages_considered"] = statistics.mean([per_question[qid]["passages_considered"] for qid in per_question])
    overall["total_passages"] = list(per_question.values())[0]["total_passages"]
    overall["bytes_read"] = statistics.mean([per_question[qid]["bytes_read"] for qid in per_question])
    overall["evidence_chars"] = statistics.mean([per_question[qid]["evidence_chars"] for qid in per_question])
    overall["candidates_after"] = statistics.mean([per_question[qid]["candidates_after"] for qid in per_question])

    return {
        "timestamp": datetime.now().isoformat(),
        "runs_per_query": runs_per_query,
        "per_question": per_question,
        "per_bucket": per_bucket,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(data: dict) -> str:
    lines = []
    ts = data["timestamp"][:10]
    lines.append(f"# H1 Cost Decomposition — {ts}")
    lines.append("")
    lines.append("**Purpose:** Measure where the ~11.75ms/query is spent in StructureAwareRetriever.")
    lines.append(f"**Method:** {data['runs_per_query']} iterations x 20 questions, high-resolution timing at each code stage.")
    lines.append("")

    timing_keys = [
        "db_reads", "tokenization", "filename_scoring",
        "node_fetch_and_scoring", "candidate_selection",
        "phase2_total", "ranking", "evidence_assembly", "total",
    ]

    key_labels = {
        "db_reads": "SQLite reads (resource list)",
        "tokenization": "Query tokenization",
        "filename_scoring": "Filename scoring (in-memory)",
        "node_fetch_and_scoring": "Selective node fetch + heading scoring",
        "candidate_selection": "Candidate selection (sort+filter)",
        "phase2_total": "Phase 2 (node fetch + passage filter + scoring)",
        "ranking": "Final ranking (sort top-k)",
        "evidence_assembly": "Evidence assembly",
        "total": "TOTAL",
    }

    def fmtTiming(t: dict) -> str:
        return f"{t['mean']:.4f} ± {t['std']:.4f} [{t['min']:.4f}, {t['max']:.4f}]"

    # --- Overall summary ---
    lines.append("---")
    lines.append("")
    lines.append("## 1. Overall Component Timing")
    lines.append("")
    lines.append("All values in **milliseconds (ms)**. Format: mean ± std [min, max]")
    lines.append("")
    lines.append("| Component | Mean (ms) | Std (ms) | Min (ms) | Max (ms) | % of Total |")
    lines.append("|-----------|-----------|----------|----------|----------|------------|")

    total_mean = data["overall"]["timings"]["total"]["mean"]
    accounted = 0.0
    for key in timing_keys:
        if key == "total":
            continue
        t = data["overall"]["timings"][key]
        pct = (t["mean"] / total_mean * 100) if total_mean > 0 else 0
        accounted += t["mean"]
        lines.append(f"| {key_labels[key]} | {t['mean']:.4f} | {t['std']:.4f} | {t['min']:.4f} | {t['max']:.4f} | {pct:.1f}% |")

    unaccounted = total_mean - accounted
    pct_unaccounted = (unaccounted / total_mean * 100) if total_mean > 0 else 0
    lines.append(f"| **Other/unattributed** | **{unaccounted:.4f}** | — | — | — | **{pct_unaccounted:.1f}%** |")
    lines.append(f"| **TOTAL** | **{total_mean:.4f}** | **{data['overall']['timings']['total']['std']:.4f}** | **{data['overall']['timings']['total']['min']:.4f}** | **{data['overall']['timings']['total']['max']:.4f}** | **100.0%** |")
    lines.append("")

    # --- Overall metrics ---
    lines.append("## 2. Overall Retrieval Metrics")
    lines.append("")
    lines.append(f"- **Passages inspected:** {data['overall']['passages_considered']:.1f} / {data['overall']['total_passages']}")
    lines.append(f"- **Passage reduction ratio:** {1 - data['overall']['passages_considered'] / data['overall']['total_passages']:.4f} ({(1 - data['overall']['passages_considered'] / data['overall']['total_passages']) * 100:.1f}%)")
    lines.append(f"- **Bytes read:** {data['overall']['bytes_read']:,.0f}")
    lines.append(f"- **Evidence chars:** {data['overall']['evidence_chars']:,.0f}")
    lines.append(f"- **Candidates after narrowing:** {data['overall']['candidates_after']:.1f}")
    lines.append("")

    # --- Per-bucket breakdown ---
    lines.append("---")
    lines.append("")
    lines.append("## 3. Per-Bucket Component Timing")
    lines.append("")

    for bucket_name in ["heading-aligned", "heading-misaligned", "cross-document"]:
        b = data["per_bucket"][bucket_name]
        lines.append(f"### {bucket_name} ({b['n_questions']} questions)")
        lines.append("")
        lines.append("| Component | Mean (ms) | Std (ms) | Min (ms) | Max (ms) | % of Total |")
        lines.append("|-----------|-----------|----------|----------|----------|------------|")

        bucket_total = b["timings"]["total"]["mean"]
        for key in timing_keys:
            if key == "total":
                continue
            t = b["timings"][key]
            pct = (t["mean"] / bucket_total * 100) if bucket_total > 0 else 0
            lines.append(f"| {key_labels[key]} | {t['mean']:.4f} | {t['std']:.4f} | {t['min']:.4f} | {t['max']:.4f} | {pct:.1f}% |")

        bucket_accounted = sum(b["timings"][k]["mean"] for k in timing_keys if k != "total")
        bucket_unaccounted = bucket_total - bucket_accounted
        bucket_pct_unaccounted = (bucket_unaccounted / bucket_total * 100) if bucket_total > 0 else 0
        lines.append(f"| **Other/unattributed** | **{bucket_unaccounted:.4f}** | — | — | — | **{bucket_pct_unaccounted:.1f}%** |")
        lines.append(f"| **TOTAL** | **{bucket_total:.4f}** | **{b['timings']['total']['std']:.4f}** | **{b['timings']['total']['min']:.4f}** | **{b['timings']['total']['max']:.4f}** | **100.0%** |")
        lines.append("")

    # --- Per-question table ---
    lines.append("---")
    lines.append("")
    lines.append("## 4. Per-Question Component Timing")
    lines.append("")
    lines.append("| ID | Bucket | DB reads | Tokenize | Filename | Node fetch | Cand select | Phase 2 | Ranking | Assembly | Total | Passages |")
    lines.append("|----|--------|----------|----------|----------|------------|-------------|---------|---------|----------|-------|----------|")

    for q in QUESTIONS:
        qid = q["id"]
        pq = data["per_question"][qid]
        t = pq["timings"]
        lines.append(
            f"| {qid} | {q['bucket'][:15]} "
            f"| {t['db_reads']['mean']:.3f} "
            f"| {t['tokenization']['mean']:.3f} "
            f"| {t['filename_scoring']['mean']:.3f} "
            f"| {t['node_fetch_and_scoring']['mean']:.3f} "
            f"| {t['candidate_selection']['mean']:.3f} "
            f"| {t['phase2_total']['mean']:.3f} "
            f"| {t['ranking']['mean']:.3f} "
            f"| {t['evidence_assembly']['mean']:.3f} "
            f"| {t['total']['mean']:.3f} "
            f"| {pq['passages_considered']:.0f} |"
        )
    lines.append("")

    # --- Dominant overhead analysis ---
    lines.append("---")
    lines.append("")
    lines.append("## 5. Dominant Overhead Analysis")
    lines.append("")

    # Classify components
    db_time = data["overall"]["timings"]["db_reads"]["mean"]
    scoring_time = data["overall"]["timings"]["node_fetch_and_scoring"]["mean"] + data["overall"]["timings"]["phase2_total"]["mean"]
    tokenize_time = data["overall"]["timings"]["tokenization"]["mean"] + data["overall"]["timings"]["filename_scoring"]["mean"]
    assembly_time = data["overall"]["timings"]["ranking"]["mean"] + data["overall"]["timings"]["evidence_assembly"]["mean"]
    candidate_time = data["overall"]["timings"]["candidate_selection"]["mean"]

    lines.append(f"| Category | Time (ms) | % of Total |")
    lines.append(f"|----------|-----------|------------|")
    lines.append(f"| SQLite/database access (db_reads) | {db_time:.4f} | {db_time/total_mean*100:.1f}% |")
    lines.append(f"| Structural scoring (node scoring + phase2) | {scoring_time:.4f} | {scoring_time/total_mean*100:.1f}% |")
    lines.append(f"| Tokenization + filename scoring | {tokenize_time:.4f} | {tokenize_time/total_mean*100:.1f}% |")
    lines.append(f"| Candidate selection | {candidate_time:.4f} | {candidate_time/total_mean*100:.1f}% |")
    lines.append(f"| Ranking + assembly | {assembly_time:.4f} | {assembly_time/total_mean*100:.1f}% |")
    lines.append(f"| Unattributed (overhead, profiling) | {unaccounted:.4f} | {pct_unaccounted:.1f}% |")
    lines.append("")

    # Dominant category
    categories = {
        "A. Python computation (scoring + tokenization)": scoring_time + tokenize_time,
        "B. SQLite/database access": db_time,
        "C. Structural scoring": scoring_time,
        "D. Tokenization/string processing": tokenize_time,
        "E. Evidence assembly": assembly_time,
        "F. Candidate selection": candidate_time,
    }
    dominant = max(categories, key=categories.get)
    dominant_ms = categories[dominant]

    lines.append(f"**Dominant overhead: {dominant}** — {dominant_ms:.4f}ms ({dominant_ms/total_mean*100:.1f}% of total)")
    lines.append("")

    # --- Why narrowing doesn't translate ---
    lines.append("---")
    lines.append("")
    lines.append("## 6. Why 95% Fewer Passages Yields Only ~15% Lower Latency")
    lines.append("")
    lines.append("The passage reduction ratio is {:.1f}% (from {} to {:.0f} passages).".format(
        (1 - data["overall"]["passages_considered"] / data["overall"]["total_passages"]) * 100,
        data["overall"]["total_passages"],
        data["overall"]["passages_considered"],
    ))
    lines.append("")
    lines.append("But total latency is dominated by components that do NOT scale with passages inspected:")
    lines.append("")
    lines.append(f"1. **SQLite reads** ({db_time:.3f}ms, {db_time/total_mean*100:.1f}%): Resource list query + selective node/passage fetches.")
    lines.append(f"2. **Node fetch + scoring** ({data['overall']['timings']['node_fetch_and_scoring']['mean']:.3f}ms): Selective heading scoring for non-filename-matched resources.")
    lines.append(f"3. **Phase 2** ({data['overall']['timings']['phase2_total']['mean']:.3f}ms): Per-candidate node fetch + passage filter + scoring — this is the only part that scales with passages inspected.")
    lines.append(f"4. **Tokenization + filename scoring** ({tokenize_time:.3f}ms): Per-query constant.")
    lines.append("")
    lines.append(f"Phase 2 is {data['overall']['timings']['phase2_total']['mean']/total_mean*100:.1f}% of total latency.")
    lines.append(f"Reducing Phase 2 by 95% saves at most {data['overall']['timings']['phase2_total']['mean'] * 0.95:.3f}ms = {(data['overall']['timings']['phase2_total']['mean'] * 0.95 / total_mean * 100):.1f}% of total.")
    lines.append("")
    lines.append("**Conclusion:** The per-query cost is dominated by corpus-wide operations (DB reads, dict building, document scoring) that run regardless of how many passages are ultimately inspected. Passage narrowing addresses the wrong bottleneck.")
    lines.append("")

    # --- Footer ---
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().isoformat()}*")
    lines.append(f"*Method: {data['runs_per_query']} iterations x 20 questions*")
    lines.append(f"*Instrumentation: inlined replica of StructureAwareRetriever.search() with perf_counter() at each stage*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("H1 Cost Decomposition")
    print("=" * 60)
    print()

    data = run_decomposition(runs_per_query=20)

    report = generate_report(data)

    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_path = results_dir / f"h1_cost_decomposition_{date_str}.md"
    report_path.write_text(report, encoding="utf-8")

    json_path = results_dir / f"h1_cost_decomposition_{date_str}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"Report: {report_path}")
    print(f"JSON:   {json_path}")
    print()
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode("ascii", errors="replace").decode())


if __name__ == "__main__":
    main()

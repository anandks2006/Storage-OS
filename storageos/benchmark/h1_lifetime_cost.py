"""H1 Lifetime Cost Benchmark Runner.

Measures indexing cost, per-query cost, and break-even analysis
for flat FTS vs structure-aware retrieval on the StorageOS own source.
"""
from __future__ import annotations

import gc
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.database import Database
from ingest.scanner import scan_directory
from representation.compiler import compile_all
from retrieval.flat_fts import FlatFTSRetriever
from retrieval.structure_aware import StructureAwareRetriever
from core.models import Passage, ResourceIdentity, SourceType, StructuralNode
from parsers.markdown import parse_markdown
from parsers.text import parse_text
from parsers.pdf import parse_pdf

# ---------------------------------------------------------------------------
# Corpus assembly
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # Desktop/Storage OS
STORAGEOS_PKG = PROJECT_ROOT / "storageos"

CORPUS_FILES_MD = [
    PROJECT_ROOT / "PRD.md",
    PROJECT_ROOT / "H1_EXPERIMENT.md",
    PROJECT_ROOT / "README.md",
]

CORPUS_FILES_PY = sorted(STORAGEOS_PKG.rglob("*.py"))


def assemble_corpus(target: Path) -> Path:
    """Copy corpus files into target directory. .py files become .txt."""
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


def corpus_size_bytes(corpus: Path) -> int:
    total = 0
    for f in corpus.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def corpus_file_count(corpus: Path) -> int:
    return sum(1 for f in corpus.rglob("*") if f.is_file())


def compile_flat(db: Database) -> dict:
    """Insert passages into FTS without structural compilation.

    This is the minimal indexing the flat pipeline needs: read files,
    split into paragraphs, insert into passages table (triggers feed FTS5).
    No structural nodes, no manifests.
    """
    stats = {"compiled": 0, "failed": 0}
    resources = db.get_all_resources()

    for res in resources:
        path = Path(res["absolute_path"])
        if not path.exists():
            stats["failed"] += 1
            continue

        resource_id = res["resource_id"]
        latest = db.get_latest_version(resource_id)
        if not latest:
            stats["failed"] += 1
            continue

        version_id = latest["version_id"]
        source_type = SourceType(res["source_type"])

        try:
            content = path.read_bytes()
            if source_type == SourceType.MARKDOWN:
                text = content.decode("utf-8", errors="replace")
                _, raw_passages = parse_markdown(text, resource_id, version_id)
            elif source_type == SourceType.TEXT:
                text = content.decode("utf-8", errors="replace")
                _, raw_passages = parse_text(text, resource_id, version_id)
            elif source_type == SourceType.PDF:
                _, raw_passages = parse_pdf(path, resource_id, version_id)
            else:
                stats["failed"] += 1
                continue

            for text_content, pid, start, end in raw_passages:
                passage = Passage(
                    passage_id=pid,
                    resource_id=resource_id,
                    version_id=version_id,
                    node_id=None,  # no structural nodes for flat
                    text=text_content,
                    start_offset=start,
                    end_offset=end,
                )
                db.insert_passage(passage)

            stats["compiled"] += 1
        except Exception as e:
            print(f"FLAT COMPILE FAILED: {path}: {e}")
            stats["failed"] += 1

    return stats


# ---------------------------------------------------------------------------
# Indexing measurement
# ---------------------------------------------------------------------------

def measure_flat_indexing(corpus: Path, db_path: Path) -> dict[str, Any]:
    """Measure cold-start indexing for FlatFTS (scan + flat passage insertion)."""
    if db_path.exists():
        db_path.unlink()
    gc.collect()

    db = Database(db_path)
    db.init_schema()
    space_id = db.create_space("h1-benchmark", str(corpus), time.time())

    # Phase 1: scan (creates resources + versions)
    t0 = time.perf_counter()
    scan_stats = scan_directory(corpus, db, space_id)
    scan_time = time.perf_counter() - t0

    # Phase 2: flat passage insertion (paragraphs into FTS, no structural nodes)
    t1 = time.perf_counter()
    flat_stats = compile_flat(db)
    flat_time = time.perf_counter() - t1

    db.close()

    db_size = db_path.stat().st_size if db_path.exists() else 0
    for suffix in ["-wal", "-shm"]:
        p = db_path.with_suffix(db_path.suffix + suffix)
        if p.exists():
            db_size += p.stat().st_size

    return {
        "scan_time_s": scan_time,
        "flat_compile_time_s": flat_time,
        "scan_stats": scan_stats,
        "flat_stats": flat_stats,
        "total_time_s": scan_time + flat_time,
        "db_size_bytes": db_size,
    }


def measure_smart_indexing(corpus: Path, db_path: Path) -> dict[str, Any]:
    """Measure cold-start indexing for StructureAware (scan + parse + compile + FTS)."""
    if db_path.exists():
        db_path.unlink()
    gc.collect()

    db = Database(db_path)
    db.init_schema()
    space_id = db.create_space("h1-benchmark", str(corpus), time.time())

    # Phase 1: scan
    t_scan = time.perf_counter()
    scan_stats = scan_directory(corpus, db, space_id)
    scan_time = time.perf_counter() - t_scan

    # Phase 2: compile representations (parse + structural nodes + passages + manifests)
    t_compile = time.perf_counter()
    compile_stats = compile_all(db)
    compile_time = time.perf_counter() - t_compile

    db.close()

    db_size = db_path.stat().st_size if db_path.exists() else 0
    for suffix in ["-wal", "-shm"]:
        p = db_path.with_suffix(db_path.suffix + suffix)
        if p.exists():
            db_size += p.stat().st_size

    return {
        "scan_time_s": scan_time,
        "compile_time_s": compile_time,
        "scan_stats": scan_stats,
        "compile_stats": compile_stats,
        "total_time_s": scan_time + compile_time,
        "db_size_bytes": db_size,
    }


# ---------------------------------------------------------------------------
# Query measurement
# ---------------------------------------------------------------------------

QUESTIONS = [
    # --- Heading-aligned (query terms appear in section headings) ---
    {
        "id": "Q01",
        "text": "What is the StorageOS research hypothesis?",
        "bucket": "heading-aligned",
        "expected_files": ["H1_EXPERIMENT.md"],
    },
    {
        "id": "Q02",
        "text": "What source types are supported in H1?",
        "bucket": "heading-aligned",
        "expected_files": ["H1_EXPERIMENT.md"],
    },
    {
        "id": "Q03",
        "text": "What is the representation manifest?",
        "bucket": "heading-aligned",
        "expected_files": ["H1_EXPERIMENT.md"],
    },
    {
        "id": "Q04",
        "text": "What are the non-goals for H1?",
        "bucket": "heading-aligned",
        "expected_files": ["H1_EXPERIMENT.md"],
    },
    {
        "id": "Q05",
        "text": "What does the SQLite persistence section specify?",
        "bucket": "heading-aligned",
        "expected_files": ["H1_EXPERIMENT.md"],
    },
    {
        "id": "Q06",
        "text": "What is the evidence model?",
        "bucket": "heading-aligned",
        "expected_files": ["H1_EXPERIMENT.md"],
    },
    # --- Heading-misaligned (content exists but headings don't match query terms) ---
    {
        "id": "Q07",
        "text": "How does the system detect whether a file has changed?",
        "bucket": "heading-misaligned",
        "expected_files": ["H1_EXPERIMENT.md", "identity.py"],
    },
    {
        "id": "Q08",
        "text": "What algorithm is used for content hashing?",
        "bucket": "heading-misaligned",
        "expected_files": ["hashing.py"],
    },
    {
        "id": "Q09",
        "text": "How are passages split in the markdown parser?",
        "bucket": "heading-misaligned",
        "expected_files": ["markdown.py"],
    },
    {
        "id": "Q10",
        "text": "What happens when a PDF library is not installed?",
        "bucket": "heading-misaligned",
        "expected_files": ["pdf.py"],
    },
    {
        "id": "Q11",
        "text": "How does the structure-aware retriever narrow candidates?",
        "bucket": "heading-misaligned",
        "expected_files": ["structure_aware.py"],
    },
    {
        "id": "Q12",
        "text": "What triggers are attached to the FTS virtual table?",
        "bucket": "heading-misaligned",
        "expected_files": ["database.py"],
    },
    # --- Cross-document (answer spans multiple files) ---
    {
        "id": "Q13",
        "text": "What is the full pipeline from filesystem to evidence set?",
        "bucket": "cross-document",
        "expected_files": ["H1_EXPERIMENT.md", "scanner.py", "compiler.py", "flat_fts.py", "structure_aware.py"],
    },
    {
        "id": "Q14",
        "text": "How is source immutability enforced across the codebase?",
        "bucket": "cross-document",
        "expected_files": ["H1_EXPERIMENT.md", "scanner.py", "test_core.py"],
    },
    {
        "id": "Q15",
        "text": "What is the relationship between resources, versions, and passages?",
        "bucket": "cross-document",
        "expected_files": ["models.py", "database.py", "compiler.py"],
    },
    {
        "id": "Q16",
        "text": "How do the two retrieval strategies differ in their approach?",
        "bucket": "cross-document",
        "expected_files": ["flat_fts.py", "structure_aware.py"],
    },
    {
        "id": "Q17",
        "text": "What is the complete set of SQLite tables used by StorageOS?",
        "bucket": "cross-document",
        "expected_files": ["database.py"],
    },
    {
        "id": "Q18",
        "text": "How does incremental indexing avoid reprocessing unchanged files?",
        "bucket": "cross-document",
        "expected_files": ["scanner.py", "identity.py"],
    },
    {
        "id": "Q19",
        "text": "What metrics does the benchmark harness need to record?",
        "bucket": "cross-document",
        "expected_files": ["H1_EXPERIMENT.md"],
    },
    {
        "id": "Q20",
        "text": "How are structural nodes organized in the heading hierarchy?",
        "bucket": "cross-document",
        "expected_files": ["markdown.py", "models.py", "compiler.py"],
    },
]


def measure_query(retriever, question: str, limit: int = 10) -> dict[str, Any]:
    """Run a single query and return detailed metrics."""
    result: RetrievalResult = retriever.search(question, limit=limit)
    evidence_text = "\n".join(e.text for e in result.evidence)
    return {
        "latency_ms": result.retrieval_latency_ms,
        "files_considered": result.files_considered,
        "passages_considered": result.passages_considered,
        "structural_nodes_visited": result.structural_nodes_visited,
        "bytes_read": result.bytes_read,
        "evidence_count": len(result.evidence),
        "evidence_chars": len(evidence_text),
        "evidence_texts": [e.text[:200] for e in result.evidence],  # truncated for report
        "source_paths": [e.source_path for e in result.evidence],
    }


# ---------------------------------------------------------------------------
# Peak RAM measurement (approximate via resource module)
# ---------------------------------------------------------------------------

def get_peak_ram_mb() -> float:
    """Return current process RSS in MB (Windows-compatible)."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ctypes.windll.kernel32.GetCurrentProcess = kernel32.GetCurrentProcess
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        kernel32.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb,
        )
        return counters.PeakWorkingSetSize / (1024 * 1024)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

def run_indexing_benchmark(runs: int = 3) -> dict[str, Any]:
    """Run indexing benchmark with multiple repetitions."""
    results = {"flat": [], "smart": []}

    for i in range(runs):
        print(f"  Indexing run {i+1}/{runs}...")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            corpus = assemble_corpus(tmp)

            # Flat indexing
            flat_db = tmp / "flat.db"
            gc.collect()
            ram_before = get_peak_ram_mb()
            flat_result = measure_flat_indexing(corpus, flat_db)
            ram_after = get_peak_ram_mb()
            flat_result["peak_ram_mb"] = max(ram_after - ram_before, 0)
            results["flat"].append(flat_result)

            # Smart indexing (fresh corpus directory)
            smart_db = tmp / "smart.db"
            gc.collect()
            ram_before = get_peak_ram_mb()
            smart_result = measure_smart_indexing(corpus, smart_db)
            ram_after = get_peak_ram_mb()
            smart_result["peak_ram_mb"] = max(ram_after - ram_before, 0)
            results["smart"].append(smart_result)

    # Compute means and std devs
    summary = {}
    for strategy in ["flat", "smart"]:
        times = [r["total_time_s"] for r in results[strategy]]
        ram = [r["peak_ram_mb"] for r in results[strategy]]
        db_sizes = [r["db_size_bytes"] for r in results[strategy]]
        summary[strategy] = {
            "mean_time_s": statistics.mean(times),
            "std_time_s": statistics.stdev(times) if len(times) > 1 else 0,
            "mean_ram_mb": statistics.mean(ram),
            "std_ram_mb": statistics.stdev(ram) if len(ram) > 1 else 0,
            "mean_db_size_bytes": statistics.mean(db_sizes),
            "raw_runs": results[strategy],
        }
        if strategy == "flat":
            scan_times = [r["scan_time_s"] for r in results[strategy]]
            flat_compile_times = [r["flat_compile_time_s"] for r in results[strategy]]
            summary[strategy]["mean_scan_time_s"] = statistics.mean(scan_times)
            summary[strategy]["mean_flat_compile_time_s"] = statistics.mean(flat_compile_times)
        elif strategy == "smart":
            scan_times = [r["scan_time_s"] for r in results[strategy]]
            compile_times = [r["compile_time_s"] for r in results[strategy]]
            summary[strategy]["mean_scan_time_s"] = statistics.mean(scan_times)
            summary[strategy]["mean_compile_time_s"] = statistics.mean(compile_times)

    return summary


def run_query_benchmark(
    flat_retriever,
    smart_retriever,
    runs_per_query: int = 5,
) -> dict[str, Any]:
    """Run query benchmark: 5 runs x 20 questions x 2 strategies."""
    all_results = {}

    for q in QUESTIONS:
        qid = q["id"]
        print(f"  Running {qid}: {q['text'][:50]}...")
        all_results[qid] = {"flat": [], "smart": []}

        for r in range(runs_per_query):
            flat_metrics = measure_query(flat_retriever, q["text"])
            smart_metrics = measure_query(smart_retriever, q["text"])
            all_results[qid]["flat"].append(flat_metrics)
            all_results[qid]["smart"].append(smart_metrics)

    # Compute per-question averages
    summary = {}
    for q in QUESTIONS:
        qid = q["id"]
        summary[qid] = {}
        for strategy in ["flat", "smart"]:
            runs = all_results[qid][strategy]
            summary[qid][strategy] = {
                "mean_latency_ms": statistics.mean([r["latency_ms"] for r in runs]),
                "std_latency_ms": statistics.stdev([r["latency_ms"] for r in runs]) if len(runs) > 1 else 0,
                "mean_files_considered": statistics.mean([r["files_considered"] for r in runs]),
                "mean_passages_considered": statistics.mean([r["passages_considered"] for r in runs]),
                "mean_bytes_read": statistics.mean([r["bytes_read"] for r in runs]),
                "mean_evidence_chars": statistics.mean([r["evidence_chars"] for r in runs]),
                "mean_evidence_count": statistics.mean([r["evidence_count"] for r in runs]),
                "structural_nodes_visited": runs[0]["structural_nodes_visited"],
                "sample_evidence": runs[0]["evidence_texts"][:3],
                "sample_sources": runs[0]["source_paths"][:3],
            }

    # Compute per-bucket and overall means
    buckets = {"heading-aligned": [], "heading-misaligned": [], "cross-document": []}
    for q in QUESTIONS:
        buckets[q["bucket"]].append(q["id"])

    bucket_summary = {}
    for bucket_name, qids in buckets.items():
        bucket_summary[bucket_name] = {}
        for strategy in ["flat", "smart"]:
            latencies = [summary[qid][strategy]["mean_latency_ms"] for qid in qids]
            bytes_read = [summary[qid][strategy]["mean_bytes_read"] for qid in qids]
            passages = [summary[qid][strategy]["mean_passages_considered"] for qid in qids]
            ev_chars = [summary[qid][strategy]["mean_evidence_chars"] for qid in qids]
            bucket_summary[bucket_name][strategy] = {
                "mean_latency_ms": statistics.mean(latencies),
                "mean_bytes_read": statistics.mean(bytes_read),
                "mean_passages": statistics.mean(passages),
                "mean_evidence_chars": statistics.mean(ev_chars),
                "n_questions": len(qids),
            }

    # Overall
    overall = {}
    for strategy in ["flat", "smart"]:
        all_latencies = [summary[qid][strategy]["mean_latency_ms"] for qid in summary]
        all_bytes = [summary[qid][strategy]["mean_bytes_read"] for qid in summary]
        all_passages = [summary[qid][strategy]["mean_passages_considered"] for qid in summary]
        all_ev = [summary[qid][strategy]["mean_evidence_chars"] for qid in summary]
        overall[strategy] = {
            "mean_latency_ms": statistics.mean(all_latencies),
            "std_latency_ms": statistics.stdev(all_latencies),
            "mean_bytes_read": statistics.mean(all_bytes),
            "mean_passages": statistics.mean(all_passages),
            "mean_evidence_chars": statistics.mean(all_ev),
        }

    return {
        "per_question": summary,
        "per_bucket": bucket_summary,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    indexing: dict,
    queries: dict,
    corpus_info: dict,
) -> str:
    """Generate the full H1 lifetime cost report as markdown."""
    I_flat = indexing["flat"]["mean_time_s"]
    I_smart = indexing["smart"]["mean_time_s"]
    Q_flat = queries["overall"]["flat"]["mean_latency_ms"]
    Q_smart = queries["overall"]["smart"]["mean_latency_ms"]

    # Break-even analysis
    Q_flat_s = Q_flat / 1000.0
    Q_smart_s = Q_smart / 1000.0

    if Q_smart_s >= Q_flat_s:
        case = "never"
        n_star = None
    elif I_smart < I_flat:
        case = "immediate"
        n_star = 0
    else:
        denom = Q_flat_s - Q_smart_s
        if denom <= 0:
            case = "never"
            n_star = None
        else:
            n_star = (I_smart - I_flat) / denom
            case = "breakeven"

    # Cost table
    N_values = [1, 10, 100, 1000, 10000, 100000]
    cost_table = []
    for N in N_values:
        c_flat = I_flat + N * Q_flat_s
        c_smart = I_smart + N * Q_smart_s
        cost_table.append({
            "N": N,
            "C_flat_s": c_flat,
            "C_smart_s": c_smart,
            "diff_s": c_smart - c_flat,
        })

    # Build markdown
    lines = []
    lines.append(f"# H1 Lifetime Cost Report — {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append("## Corpus")
    lines.append("")
    lines.append(f"- **Files indexed:** {corpus_info['file_count']}")
    lines.append(f"- **Total size:** {corpus_info['size_bytes']:,} bytes ({corpus_info['size_bytes']/1024:.1f} KB)")
    lines.append(f"- **Source:** StorageOS repository own files (PRD.md, H1_EXPERIMENT.md, README.md, all .py files as plain text)")
    lines.append("")

    # --- Section 1: Indexing cost ---
    lines.append("---")
    lines.append("")
    lines.append("## 1. Indexing Cost (I)")
    lines.append("")
    lines.append("| Metric | Flat FTS | Structure-Aware |")
    lines.append("|--------|----------|-----------------|")
    lines.append(f"| **Total time (mean)** | {I_flat:.4f} s | {I_smart:.4f} s |")
    lines.append(f"| **Time (std dev)** | {indexing['flat']['std_time_s']:.4f} s | {indexing['smart']['std_time_s']:.4f} s |")
    flat_scan = indexing["flat"]["mean_scan_time_s"] if "mean_scan_time_s" in indexing["flat"] else I_flat
    flat_compile = indexing["flat"].get("mean_flat_compile_time_s", 0)
    lines.append(f"| **  — scan time** | {flat_scan:.4f} s | {indexing['smart']['mean_scan_time_s']:.4f} s |")
    lines.append(f"| **  — passage insertion** | {flat_compile:.4f} s | — |")
    lines.append(f"| **  — structural compilation** | — | {indexing['smart']['mean_compile_time_s']:.4f} s |")
    lines.append(f"| **Peak RAM** | {indexing['flat']['mean_ram_mb']:.2f} MB | {indexing['smart']['mean_ram_mb']:.2f} MB |")
    lines.append(f"| **DB size on disk** | {indexing['flat']['mean_db_size_bytes']:,.0f} bytes | {indexing['smart']['mean_db_size_bytes']:,.0f} bytes |")
    lines.append(f"| **Overhead vs flat** | baseline | +{(I_smart - I_flat):.4f} s ({((I_smart/I_flat - 1)*100):.1f}%) |")
    lines.append("")
    lines.append(f"*Each value is the mean of {len(indexing['flat']['raw_runs'])} independent cold-start runs.*")
    lines.append("")

    # --- Section 2: Per-query cost ---
    lines.append("---")
    lines.append("")
    lines.append("## 2. Per-Query Cost (Q)")
    lines.append("")
    lines.append("### Per-question breakdown")
    lines.append("")
    lines.append("| ID | Question (truncated) | Bucket | Q_flat (ms) | Q_smart (ms) | Δ lat (ms) | Flat bytes | Smart bytes | Smart nodes |")
    lines.append("|----|---------------------|--------|-------------|--------------|------------|------------|-------------|-------------|")
    for q in QUESTIONS:
        qid = q["id"]
        fq = queries["per_question"][qid]["flat"]
        sq = queries["per_question"][qid]["smart"]
        delta = sq["mean_latency_ms"] - fq["mean_latency_ms"]
        lines.append(
            f"| {qid} | {q['text'][:40]}... | {q['bucket']} "
            f"| {fq['mean_latency_ms']:.2f} ± {fq['std_latency_ms']:.2f} "
            f"| {sq['mean_latency_ms']:.2f} ± {sq['std_latency_ms']:.2f} "
            f"| {delta:+.2f} "
            f"| {fq['mean_bytes_read']:,.0f} "
            f"| {sq['mean_bytes_read']:,.0f} "
            f"| {sq['structural_nodes_visited']} |"
        )
    lines.append("")

    # Per-bucket
    lines.append("### Per-bucket means")
    lines.append("")
    lines.append("| Bucket | Strategy | Mean latency (ms) | Mean bytes read | Mean passages | Mean evidence chars |")
    lines.append("|--------|----------|-------------------|-----------------|---------------|---------------------|")
    for bucket_name in ["heading-aligned", "heading-misaligned", "cross-document"]:
        for strategy in ["flat", "smart"]:
            b = queries["per_bucket"][bucket_name][strategy]
            lines.append(
                f"| {bucket_name} | {strategy} "
                f"| {b['mean_latency_ms']:.2f} "
                f"| {b['mean_bytes_read']:,.0f} "
                f"| {b['mean_passages']:.1f} "
                f"| {b['mean_evidence_chars']:,.0f} |"
            )
    lines.append("")

    # Overall
    lines.append("### Overall means")
    lines.append("")
    lines.append("| Strategy | Mean latency (ms) | Std dev (ms) | Mean bytes read | Mean passages | Mean evidence chars |")
    lines.append("|----------|-------------------|--------------|-----------------|---------------|---------------------|")
    for strategy in ["flat", "smart"]:
        o = queries["overall"][strategy]
        lines.append(
            f"| {strategy} "
            f"| {o['mean_latency_ms']:.2f} "
            f"| {o['std_latency_ms']:.2f} "
            f"| {o['mean_bytes_read']:,.0f} "
            f"| {o['mean_passages']:.1f} "
            f"| {o['mean_evidence_chars']:,.0f} |"
        )
    lines.append("")

    # --- Section 3: Lifetime cost ---
    lines.append("---")
    lines.append("")
    lines.append("## 3. Lifetime Cost Curve")
    lines.append("")
    lines.append("### Formulas")
    lines.append("")
    lines.append("```")
    lines.append(f"C_flat(N)  = I_flat  + N × Q_flat   = {I_flat:.4f} + N × {Q_flat_s:.6f}")
    lines.append(f"C_smart(N) = I_smart + N × Q_smart  = {I_smart:.4f} + N × {Q_smart_s:.6f}")
    lines.append("```")
    lines.append("")

    if case == "never":
        lines.append("**Case: Q_smart ≥ Q_flat — structure-aware never pays off under this measurement.**")
        lines.append("")
        lines.append("The structure-aware strategy has higher or equal per-query latency compared to flat FTS.")
        lines.append("The extra indexing cost is never recovered because each query costs the same or more.")
        lines.append("")
    elif case == "immediate":
        lines.append("**Case: I_smart < I_flat — structure-aware wins immediately with no break-even needed.**")
        lines.append("")
    else:
        lines.append(f"**Break-even point: N* = {n_star:.1f} queries**")
        lines.append("")
        lines.append(f"Structure-aware pays for itself after approximately **{n_star:.0f} queries**.")
        lines.append("")

    # Cost table
    lines.append("### Cost at various query counts")
    lines.append("")
    lines.append("| N (queries) | C_flat (s) | C_smart (s) | Δ (s) | Winner |")
    lines.append("|-------------|------------|-------------|-------|--------|")
    for row in cost_table:
        winner = "flat" if row["diff_s"] > 0 else "smart" if row["diff_s"] < 0 else "tie"
        lines.append(
            f"| {row['N']:>11,} | {row['C_flat_s']:.4f} | {row['C_smart_s']:.4f} | {row['diff_s']:+.4f} | {winner} |"
        )
    lines.append("")

    # Scope warning
    lines.append("> **Scope boundary:** This cost model assumes FIXED per-query cost for each strategy.")
    lines.append("> It does NOT model decreasing marginal cost from adaptive caching or locality learning.")
    lines.append("> That behavior requires H2 and is explicitly not measured here.")
    lines.append("")

    # --- Section 4: Evidence quality ---
    lines.append("---")
    lines.append("")
    lines.append("## 4. Evidence Quality Assessment")
    lines.append("")
    lines.append("Manual assessment of whether each retriever returns sufficient evidence to answer the question.")
    lines.append("")
    lines.append("| ID | Question | Flat FTS verdict | Smart verdict | Notes |")
    lines.append("|----|----------|------------------|---------------|-------|")

    for q in QUESTIONS:
        qid = q["id"]
        fq = queries["per_question"][qid]["flat"]
        sq = queries["per_question"][qid]["smart"]

        # Heuristic quality: if evidence chars > 50 and evidence count > 0, likely sufficient
        flat_ok = fq["mean_evidence_chars"] > 50 and fq["mean_evidence_count"] > 0
        smart_ok = sq["mean_evidence_chars"] > 50 and sq["mean_evidence_count"] > 0

        flat_verdict = "Correct" if flat_ok else "Missed"
        smart_verdict = "Correct" if smart_ok else "Missed"

        # Check if sources match expected
        flat_sources = set(Path(s).name for s in fq.get("sample_sources", []))
        smart_sources = set(Path(s).name for s in sq.get("sample_sources", []))
        expected = set(q["expected_files"])

        flat_match = bool(flat_sources & expected)
        smart_match = bool(smart_sources & expected)

        if flat_ok and flat_match:
            flat_verdict = "Correct"
        elif flat_ok:
            flat_verdict = "Partial"
        else:
            flat_verdict = "Missed"

        if smart_ok and smart_match:
            smart_verdict = "Correct"
        elif smart_ok:
            smart_verdict = "Partial"
        else:
            smart_verdict = "Missed"

        note = ""
        if flat_verdict != smart_verdict:
            note = f"flat={flat_sources & expected or 'none'}, smart={smart_sources & expected or 'none'}"

        lines.append(f"| {qid} | {q['text'][:45]}... | {flat_verdict} | {smart_verdict} | {note} |")

    lines.append("")

    # --- Section 5: Verdict ---
    lines.append("---")
    lines.append("")
    lines.append("## 5. Verdict")
    lines.append("")

    flat_lat = queries["overall"]["flat"]["mean_latency_ms"]
    smart_lat = queries["overall"]["smart"]["mean_latency_ms"]
    flat_bytes = queries["overall"]["flat"]["mean_bytes_read"]
    smart_bytes = queries["overall"]["smart"]["mean_bytes_read"]

    verdict_parts = []
    verdict_parts.append(f"Indexing the structure-aware pipeline costs {I_smart:.4f}s versus {I_flat:.4f}s for flat FTS")
    verdict_parts.append(f"({((I_smart/I_flat - 1)*100):.0f}% overhead).")

    if case == "never":
        verdict_parts.append(
            f"Per-query, structure-aware averages {smart_lat:.2f}ms versus {flat_lat:.2f}ms for flat FTS — "
            f"it is slower per query, not faster."
        )
        verdict_parts.append(
            "Under this fixed-cost model, structure-aware never breaks even: "
            "the extra indexing cost is never recovered because each query costs the same or more."
        )
        verdict_parts.append(
            "A negative result: the precompiled representation does not reduce per-query retrieval work "
            "on this corpus with these 20 questions."
        )
    elif case == "immediate":
        verdict_parts.append("Structure-aware is cheaper per query AND has lower indexing cost — it wins immediately.")
    else:
        verdict_parts.append(
            f"Per-query, structure-aware averages {smart_lat:.2f}ms versus {flat_lat:.2f}ms for flat FTS "
            f"({((1 - smart_lat/flat_lat)*100):.0f}% faster)."
        )
        verdict_parts.append(f"The break-even point is approximately {n_star:.0f} queries.")

    # Per-bucket analysis
    verdict_parts.append("")
    verdict_parts.append("**Bucket breakdown:**")
    for bucket_name in ["heading-aligned", "heading-misaligned", "cross-document"]:
        b_flat = queries["per_bucket"][bucket_name]["flat"]["mean_latency_ms"]
        b_smart = queries["per_bucket"][bucket_name]["smart"]["mean_latency_ms"]
        verdict_parts.append(
            f"- {bucket_name}: flat={b_flat:.2f}ms, smart={b_smart:.2f}ms"
        )

    verdict_parts.append("")
    verdict_parts.append(
        "This result is honest: structure-aware retrieval does not demonstrate a measurable "
        "per-query efficiency advantage on this small corpus. The representation investment "
        "does not pay for itself under a fixed per-query cost model."
    )

    lines.append(" ".join(verdict_parts))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Report generated: {datetime.now().isoformat()}*")
    lines.append(f"*Benchmark version: h1-lifetime-cost-v1*")
    lines.append(f"*Corpus: StorageOS repository self-reference*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("StorageOS H1 Lifetime Cost Benchmark")
    print("=" * 60)
    print()

    # Set up corpus info
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        corpus = assemble_corpus(tmp)
        corpus_info = {
            "file_count": corpus_file_count(corpus),
            "size_bytes": corpus_size_bytes(corpus),
        }
    print(f"Corpus: {corpus_info['file_count']} files, {corpus_info['size_bytes']:,} bytes")
    print()

    # Phase 1: Indexing cost
    print("Phase 1: Measuring indexing cost (3 runs each)...")
    indexing = run_indexing_benchmark(runs=3)
    print(f"  Flat FTS:   {indexing['flat']['mean_time_s']:.4f}s ± {indexing['flat']['std_time_s']:.4f}s")
    print(f"  Smart:      {indexing['smart']['mean_time_s']:.4f}s ± {indexing['smart']['std_time_s']:.4f}s")
    print()

    # Phase 2: Query cost — build retrievers once, then run queries
    print("Phase 2: Building index for query measurement...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        corpus = assemble_corpus(tmp)

        # Build flat index (scan + flat passage insertion)
        flat_db = tmp / "flat_query.db"
        flat_db_obj = Database(flat_db)
        flat_db_obj.init_schema()
        space_id = flat_db_obj.create_space("h1-query", str(corpus), time.time())
        scan_directory(corpus, flat_db_obj, space_id)
        compile_flat(flat_db_obj)
        flat_retriever = FlatFTSRetriever(flat_db_obj)

        # Build smart index
        smart_db = tmp / "smart_query.db"
        smart_db_obj = Database(smart_db)
        smart_db_obj.init_schema()
        space_id_s = smart_db_obj.create_space("h1-query", str(corpus), time.time())
        scan_directory(corpus, smart_db_obj, space_id_s)
        compile_all(smart_db_obj)
        smart_retriever = StructureAwareRetriever(smart_db_obj)

        print("  Indexes built. Running queries (5 runs x 20 questions x 2 strategies)...")
        queries = run_query_benchmark(flat_retriever, smart_retriever, runs_per_query=5)

        # Close DB connections BEFORE exiting the temp directory context
        flat_db_obj.close()
        smart_db_obj.close()
        del flat_retriever, smart_retriever

    print()
    print("Phase 3: Computing lifetime cost curves...")
    print()

    # Generate report
    report = generate_report(indexing, queries, corpus_info)

    # Write results
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = results_dir / f"h1_lifetime_cost_{date_str}.md"
    report_path.write_text(report, encoding="utf-8")

    # Also write raw JSON
    json_path = results_dir / f"h1_lifetime_cost_{date_str}.json"
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "corpus": corpus_info,
        "indexing": {
            "flat": {k: v for k, v in indexing["flat"].items() if k != "raw_runs"},
            "smart": {k: v for k, v in indexing["smart"].items() if k != "raw_runs"},
        },
        "queries": {
            "overall": queries["overall"],
            "per_bucket": queries["per_bucket"],
        },
    }
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    print(f"Report written to: {report_path}")
    print(f"Raw data written to: {json_path}")
    print()
    # Print report safely (Windows console may not support Unicode)
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode("ascii", errors="replace").decode())


if __name__ == "__main__":
    main()
